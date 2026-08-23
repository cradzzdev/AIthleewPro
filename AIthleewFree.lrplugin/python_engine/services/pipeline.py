"""
LR Auto Color Pro - Analysis Pipeline
Pure Cloud Vision AI Engine (NVIDIA NIM / OpenRouter) with Computer Vision & Histogram Preprocessing.
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Analysis pipeline powered by Cloud Vision AI combined with Precision Histogram Metering.
    """

    CLOUD_TIMEOUT_MS = 15000

    def __init__(self, cloud_client, traditional_cv):
        self.cloud_client = cloud_client
        self.traditional_cv = traditional_cv
        self._analysis_count = 0
        self._cache = {}

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the pipeline."""
        return {
            "status": "online",
            "cloud_available": self.cloud_client is not None and self.cloud_client.is_available(),
            "analyses_performed": self._analysis_count,
        }

    def analyze(
        self,
        image_path: str,
        mode: str = "full",
        use_cloud: bool = True,
        scene_hint: Optional[str] = None,
        intensity_level: str = "normal",
    ) -> Dict[str, Any]:
        """
        Analyze an image using Cloud Vision AI and precision Histogram metering.
        """
        start_time = time.time()
        self._analysis_count += 1

        logger.info(f"Starting Cloud Vision AI + Histogram analysis of: {image_path} (Intensity: {intensity_level})")

        # Step 1: Pre-process with CV for 5-zone histogram & HSL metrics
        cv_result = self.traditional_cv.analyze(image_path) if self.traditional_cv else {}

        # Step 2: Cloud Vision inference
        cloud_result = None
        if self.cloud_client:
            hist_data = cv_result.get("histogram_analysis", {})
            cloud_result = self._try_cloud_analysis(image_path, mode, photometric_data=hist_data, intensity_level=intensity_level)

        if not cloud_result:
            logger.warning("Cloud AI unavailable, generating baseline adjustments from CV & Histogram")
            cloud_result = {
                "scene": scene_hint or "general",
                "confidence": 0.6,
                "adjustments": {},
                "model_used": "Baseline Vision"
            }

        # Step 3: Merge CV histogram measurements & AI color grading
        final_result = self._merge_results(cv_result, cloud_result)

        final_result["inference_time_ms"] = int((time.time() - start_time) * 1000)
        final_result["model_used"] = cloud_result.get("model_used", "NVIDIA NIM Vision AI")

        logger.info(f"Analysis complete in {final_result['inference_time_ms']}ms using {final_result['model_used']}")
        return final_result

    def _try_cloud_analysis(self, image_path: str, mode: str, photometric_data: Optional[Dict] = None, intensity_level: str = "normal") -> Optional[Dict]:
        """Attempt cloud vision analysis with timeout handling."""
        try:
            if not self.cloud_client:
                return None
            result = self.cloud_client.analyze(image_path, mode=mode, timeout=self.CLOUD_TIMEOUT_MS, photometric_data=photometric_data, intensity_level=intensity_level)
            return result
        except Exception as e:
            logger.warning(f"Cloud analysis failed: {e}")
            return None

    def _safe_num(self, val, default: float = 0.0) -> float:
        """Safely convert a value to float."""
        try:
            if isinstance(val, (int, float)):
                return float(val)
            return float(str(val))
        except (ValueError, TypeError):
            return default

    def _merge_results(self, cv_result: Dict, cloud_result: Dict) -> Dict:
        """Merge results from Cloud Vision AI and Precision Histogram metrics into a complete adjustment set."""
        merged = dict(cloud_result)

        scene = str(merged.get("scene", "general"))
        confidence = float(merged.get("confidence", 0.8))

        possible_scenes = cv_result.get("scene_heuristics", {}).get("possible_scenes", [])
        if (scene == "general" or confidence <= 0.3) and possible_scenes:
            top_scene = possible_scenes[0]
            scene = top_scene.get("scene", "general")
            confidence = float(top_scene.get("score", 0.75))
            merged["scene"] = scene
            merged["confidence"] = round(confidence, 2)

        adj = merged.setdefault("adjustments", {})
        hist = cv_result.get("histogram_analysis", {})
        merged["histogram_analysis"] = hist

        # Precision Light Metering from Histogram
        rec_ev = self._safe_num(hist.get("recommended_ev", 0.0))
        mean_luma_pct = self._safe_num(hist.get("mean_luminance_pct", 46.0))
        hl_clip = self._safe_num(hist.get("highlight_clipping", 0.0))
        sh_clip = self._safe_num(hist.get("shadow_clipping", 0.0))
        z_highlights = self._safe_num(hist.get("zone_highlights", 20.0))
        z_whites = self._safe_num(hist.get("zone_whites", 5.0))
        z_shadows = self._safe_num(hist.get("zone_shadows", 25.0))
        z_blacks = self._safe_num(hist.get("zone_blacks", 5.0))

        # 1. Exposure: Calibrate mathematically using 18% middle gray & skin tone histogram
        skin_detected = hist.get("skin_detected", False)
        if "exposure" not in adj or adj["exposure"] == 0:
            adj["exposure"] = rec_ev
        else:
            ai_exp = self._safe_num(adj["exposure"])
            if skin_detected:
                # 75% weight on skin-tone photometric meter + 25% AI intent
                blended_exp = rec_ev * 0.75 + ai_exp * 0.25
            else:
                # 65% weight on 18% linear middle-gray meter + 35% AI intent
                blended_exp = rec_ev * 0.65 + ai_exp * 0.35
            adj["exposure"] = round(blended_exp, 2)

        # 2. Contrast: Boost contrast according to scene and dynamic range
        if "contrast" not in adj or adj["contrast"] == 0:
            adj["contrast"] = 22 if scene in ["landscape", "street", "sunset", "cityscape"] else 18

        # 3. Highlights: Protect highlight headroom measured directly from histogram
        if "highlights" not in adj or adj["highlights"] == 0:
            adj["highlights"] = int(hist.get("recommended_highlights", -35))

        # 4. Shadows: Lift shadows to recover detail based on shadow crushing measured from histogram
        if "shadows" not in adj or adj["shadows"] == 0:
            adj["shadows"] = int(hist.get("recommended_shadows", 30))

        # 5. Whites & Blacks: Dynamic range calibration from histogram percentiles
        if "whites" not in adj or adj["whites"] == 0:
            adj["whites"] = int(hist.get("recommended_whites", 15))
        if "blacks" not in adj or adj["blacks"] == 0:
            adj["blacks"] = int(hist.get("recommended_blacks", -15))

        # 6. Vibrance & Saturation
        cv_color = cv_result.get("color_analysis", {})
        avg_sat = cv_color.get("avg_saturation", 0.3)
        if "vibrance" not in adj or adj["vibrance"] == 0:
            scene_vibrance = {"landscape": 28, "sunset": 35, "food": 25, "portrait": 18, "beach": 25, "macro": 22}.get(scene, 20)
            if avg_sat < 0.2:
                scene_vibrance += 10
            adj["vibrance"] = int(round(scene_vibrance))

        if "saturation" not in adj or adj["saturation"] == 0:
            scene_sat = {"landscape": 8, "sunset": 12, "food": 8, "portrait": -2, "night": -5}.get(scene, 0)
            adj["saturation"] = int(round(scene_sat))

        # 7. Presence (Texture, Clarity, Dehaze)
        if "texture" not in adj or adj["texture"] == 0:
            if scene in ["portrait", "baby_kids"]:
                adj["texture"] = -6
            elif scene in ["landscape", "architecture", "macro", "wildlife"]:
                adj["texture"] = 18
            else:
                adj["texture"] = 10

        if "clarity" not in adj or adj["clarity"] == 0:
            if scene in ["portrait", "baby_kids"]:
                adj["clarity"] = 8
            elif scene in ["landscape", "street", "architecture"]:
                adj["clarity"] = 18
            else:
                adj["clarity"] = 12

        if "dehaze" not in adj or adj["dehaze"] == 0:
            if scene in ["landscape", "beach", "seascape", "aerial"]:
                adj["dehaze"] = 14
            elif scene == "sunset":
                adj["dehaze"] = 10
            else:
                adj["dehaze"] = 6

        # 8. Detail & Sharpness
        if "sharpness" not in adj or adj["sharpness"] == 0:
            if scene in ["portrait", "baby_kids"]:
                adj["sharpness"] = 48
            else:
                adj["sharpness"] = 58

        if "sharpen_radius" not in adj:
            adj["sharpen_radius"] = 1.0
        if "sharpen_detail" not in adj:
            adj["sharpen_detail"] = 25
        if "sharpen_masking" not in adj:
            adj["sharpen_masking"] = 50 if scene in ["portrait", "baby_kids", "wedding"] else 15

        if "luminance_smoothing" not in adj or adj["luminance_smoothing"] == 0:
            adj["luminance_smoothing"] = 0
        if "color_noise_reduction" not in adj or adj["color_noise_reduction"] == 0:
            adj["color_noise_reduction"] = 25

        if "vignette" not in adj or adj["vignette"] == 0:
            adj["vignette"] = -8 if scene in ["portrait", "product", "food", "wedding"] else 0

        if "grain" not in adj or adj["grain"] == 0:
            adj["grain"] = 0

        # 9. Color Grading (Split Toning)
        cg = merged.get("color_grading") or adj.get("color_grading")
        if not cg or not (isinstance(cg, dict) and cg.get("shadows") and (cg["shadows"].get("hue") or cg["shadows"].get("saturation"))):
            cg = self._default_color_grading(scene)

        if "shadows" in cg and "lum" not in cg["shadows"]:
            cg["shadows"]["lum"] = -5
        if "midtones" in cg and "lum" not in cg["midtones"]:
            cg["midtones"]["lum"] = 5
        if "highlights" in cg and "lum" not in cg["highlights"]:
            cg["highlights"]["lum"] = 5
        if "blending" not in cg:
            cg["blending"] = 50
        if "balance" not in cg:
            cg["balance"] = 0

        merged["color_grading"] = cg
        adj["color_grading"] = cg

        # 10. HSL 8 Channels
        if "hsl" not in adj or not adj["hsl"]:
            cv_hsl = cv_result.get("hsl_analysis", {})
            if cv_hsl:
                adj["hsl"] = cv_hsl

        if not merged.get("color_analysis"):
            merged["color_analysis"] = cv_color

        return merged

    def _default_color_grading(self, scene: str) -> Dict[str, Any]:
        """Default bold 3-way color grading presets per scene."""
        defaults = {
            "portrait": {
                "shadows": {"hue": 220, "saturation": 18, "lum": -5},
                "midtones": {"hue": 35, "saturation": 12, "lum": 5},
                "highlights": {"hue": 45, "saturation": 22, "lum": 5},
            },
            "wedding": {
                "shadows": {"hue": 210, "saturation": 16, "lum": -5},
                "midtones": {"hue": 40, "saturation": 14, "lum": 8},
                "highlights": {"hue": 45, "saturation": 25, "lum": 5},
            },
            "landscape": {
                "shadows": {"hue": 215, "saturation": 28, "lum": -10},
                "midtones": {"hue": 115, "saturation": 20, "lum": 5},
                "highlights": {"hue": 48, "saturation": 30, "lum": 8},
            },
            "sunset": {
                "shadows": {"hue": 260, "saturation": 32, "lum": -15},
                "midtones": {"hue": 25, "saturation": 36, "lum": 10},
                "highlights": {"hue": 38, "saturation": 42, "lum": 12},
            },
        }
        return defaults.get(scene, {
            "shadows": {"hue": 215, "saturation": 18, "lum": -5},
            "midtones": {"hue": 35, "saturation": 12, "lum": 5},
            "highlights": {"hue": 45, "saturation": 22, "lum": 5},
        })

    def get_presets(self, category: str = "all") -> Dict[str, Any]:
        """Get available presets."""
        presets = {
            "portraits": [
                {"name": "Natural Portrait", "settings": {}},
                {"name": "Warm Portrait", "settings": {}},
                {"name": "Soft Portrait", "settings": {}},
            ],
            "landscapes": [
                {"name": "Vivid Landscape", "settings": {}},
                {"name": "Golden Hour", "settings": {}},
                {"name": "Dramatic Sky", "settings": {}},
            ],
        }
        if category == "all":
            return presets
        return {category: presets.get(category, [])}

    def clear_cache(self):
        """Clear the analysis cache."""
        self._cache.clear()
        logger.info("Analysis cache cleared")
