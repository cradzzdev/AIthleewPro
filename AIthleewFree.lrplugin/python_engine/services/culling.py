"""
AIthleewPro - Hybrid Vision AI & Computer Vision Photo Culling & Scoring Engine
Evaluates photo keeper quality (0-100 score) using:
1. Multimodal Cloud Vision AI (Sharpness, Subject Expression, Lighting, Composition)
2. High-precision Local Computer Vision (Laplacian sharpness, exposure clipping, dynamic range)
3. Automatic seamless offline fallback if Cloud AI is unavailable or rate-limited.
"""

import base64
import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing CV2 & PIL
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


CULLING_SYSTEM_PROMPT = """You are a world-class professional photographer, judge, and photo editor performing photo selection (culling).
Analyze the entire image in high detail and evaluate its overall keeper quality.

Evaluate across these 4 core criteria:
1. Sharpness & Focus (0-100): Is the focal point crisp on the subject? Are eyes sharp? Motion blur, camera shake, or lens softness?
2. Lighting & Exposure (0-100): Dynamic range, highlight/shadow details, flattering light direction, no accidental severe clipping.
3. Subject & Expression (0-100): For people/portraits: eyes open vs blinking, genuine expressions, flattering pose. For landscapes/objects: clear subject, no distracting awkward elements.
4. Composition & Aesthetics (0-100): Framing, rule of thirds/geometry, clean background, visual storytelling and impact.

Return ONLY a valid raw JSON object with this exact structure (no markdown formatting, no code block backticks):
{
    "total_score": float (0.0 to 100.0),
    "sub_scores": {
        "sharpness": float (0-100),
        "exposure": float (0-100),
        "expression": float (0-100),
        "composition": float (0-100)
    },
    "verdict": "keeper" | "acceptable" | "reject"
}

Scoring Guidelines:
- 85-100 (Keeper / 5 Stars): Exceptional sharpness, perfect timing/expression, outstanding lighting & composition.
- 70-84 (Keeper / 4 Stars): Sharp focus, good lighting, solid keeper.
- 50-69 (Acceptable / 2-3 Stars): Usable backup shot, but slight flaws in focus, lighting or expression.
- 0-49 (Reject / 0-1 Star): Out of focus, blinks/closed eyes, motion blur, harsh unflattering light, or bad framing.
"""


class CullingEngine:
    """Hybrid Vision AI + Computer Vision engine for photo culling."""

    def __init__(self):
        pass

    def _analyze_local_cv(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image quality locally via OpenCV or PIL.
        Calculates sharpness, exposure clipping, contrast, and noise.
        """
        metrics = {
            "sharpness_score": 75.0,
            "exposure_score": 75.0,
            "contrast_score": 75.0,
            "highlight_clipping_pct": 0.0,
            "shadow_clipping_pct": 0.0,
            "mean_brightness": 128.0,
            "is_valid": False,
        }

        try:
            if CV2_AVAILABLE:
                img = cv2.imread(image_path)
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    h, w = gray.shape

                    # 1. Sharpness via Laplacian variance
                    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                    lap_var = float(np.var(laplacian))

                    # Normalize lap_var (typically 50-800 for web previews)
                    if lap_var < 50:
                        sharpness_score = max(10.0, lap_var * 0.8)
                    elif lap_var < 200:
                        sharpness_score = 40.0 + (lap_var - 50) * (30.0 / 150.0)
                    elif lap_var < 600:
                        sharpness_score = 70.0 + (lap_var - 200) * (20.0 / 400.0)
                    else:
                        sharpness_score = min(98.0, 90.0 + (lap_var - 600) * 0.02)

                    # 2. Exposure & Clipping
                    total_pixels = h * w
                    shadow_pixels = np.sum(gray < 5)
                    highlight_pixels = np.sum(gray > 250)

                    shadow_pct = (shadow_pixels / total_pixels) * 100.0
                    highlight_pct = (highlight_pixels / total_pixels) * 100.0
                    mean_val = float(np.mean(gray))
                    std_val = float(np.std(gray))

                    # Exposure penalty
                    exp_score = 90.0
                    if highlight_pct > 5.0:
                        exp_score -= min(40.0, highlight_pct * 3.0)
                    if shadow_pct > 15.0:
                        exp_score -= min(30.0, shadow_pct * 1.5)
                    if mean_val < 40 or mean_val > 215:
                        exp_score -= 20.0

                    exp_score = max(15.0, min(95.0, exp_score))

                    # Contrast score
                    contrast_score = min(95.0, max(20.0, std_val * 1.4))

                    metrics.update({
                        "sharpness_score": round(sharpness_score, 1),
                        "exposure_score": round(exp_score, 1),
                        "contrast_score": round(contrast_score, 1),
                        "highlight_clipping_pct": round(highlight_pct, 2),
                        "shadow_clipping_pct": round(shadow_pct, 2),
                        "mean_brightness": round(mean_val, 1),
                        "laplacian_var": round(lap_var, 1),
                        "is_valid": True,
                    })

            elif PIL_AVAILABLE:
                with Image.open(image_path) as im:
                    im_gray = im.convert("L")
                    stat = ImageStat.Stat(im_gray)
                    mean_val = stat.mean[0]
                    std_val = stat.stddev[0]

                    exp_score = 85.0
                    if mean_val < 40 or mean_val > 215:
                        exp_score -= 25.0
                    contrast_score = min(90.0, max(20.0, std_val * 1.3))

                    metrics.update({
                        "sharpness_score": 75.0,
                        "exposure_score": round(exp_score, 1),
                        "contrast_score": round(contrast_score, 1),
                        "mean_brightness": round(mean_val, 1),
                        "is_valid": True,
                    })

        except Exception as e:
            logger.warning(f"Local CV analysis warning: {e}")

        return metrics

    def evaluate_photo(
        self,
        image_path: str,
        cloud_client: Any = None,
        cloud_model: Optional[str] = None,
        timeout: int = 25000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluate photo quality using Hybrid Vision AI with Computer Vision grounding & fallback.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # 1. Compute local CV metrics
        cv_metrics = self._analyze_local_cv(image_path)

        res = None
        used_model = "Local Computer Vision Engine"

        # 2. If Cloud AI is available, attempt multimodal analysis
        if cloud_client and cloud_client.is_available():
            target_model = cloud_model or getattr(cloud_client, "preferred_model", "meta/llama-3.2-11b-vision-instruct")
            used_model = f"Vision AI ({target_model})"

            cv_hint = ""
            if cv_metrics.get("is_valid"):
                cv_hint = f" (Instrumented metrics: Laplacian Sharpness={cv_metrics.get('sharpness_score')}/100, Highlight Clipping={cv_metrics.get('highlight_clipping_pct')}%, Shadow Clipping={cv_metrics.get('shadow_clipping_pct')}%)."

            user_prompt = f"Carefully inspect this entire image for sharpness, subject focus, eyes/expression, dynamic range, lighting, and composition{cv_hint}. Return raw JSON evaluation."

            try:
                res = cloud_client.call_chat_vision(
                    prompt=user_prompt,
                    image_path=image_path,
                    model=target_model,
                    timeout=timeout,
                    system_prompt=CULLING_SYSTEM_PROMPT
                )
            except Exception as e:
                logger.warning(f"Cloud vision call failed: {e}. Falling back to Computer Vision.")
                res = None

        # 3. If Cloud Vision returned valid data, parse and synthesize
        if res and isinstance(res, dict):
            raw_score = res.get("total_score") or res.get("score") or res.get("quality_score") or 75.0
            try:
                ai_score = float(raw_score)
            except (ValueError, TypeError):
                ai_score = 75.0

            # Weight AI score with measured physical sharpness
            if cv_metrics.get("is_valid"):
                meas_sharp = cv_metrics.get("sharpness_score", 75.0)
                # Blend 70% Vision AI reasoning + 30% measured optical sharpness
                total_score = (ai_score * 0.7) + (meas_sharp * 0.3)
            else:
                total_score = ai_score

            total_score = max(0.0, min(100.0, round(total_score, 1)))

            sub_scores = res.get("sub_scores", {})
            if not isinstance(sub_scores, dict):
                sub_scores = {
                    "sharpness": total_score,
                    "exposure": total_score,
                    "expression": total_score,
                    "composition": total_score
                }

            verdict = res.get("verdict")
            if not verdict or verdict not in ["keeper", "acceptable", "reject"]:
                if total_score >= 75:
                    verdict = "keeper"
                elif total_score >= 50:
                    verdict = "acceptable"
                else:
                    verdict = "reject"

        else:
            # 4. Fallback to Local Computer Vision Scoring
            sharp_sc = cv_metrics.get("sharpness_score", 75.0)
            exp_sc = cv_metrics.get("exposure_score", 75.0)
            cont_sc = cv_metrics.get("contrast_score", 75.0)

            # CV Formula: 45% Sharpness + 35% Exposure + 20% Contrast
            total_score = (sharp_sc * 0.45) + (exp_sc * 0.35) + (cont_sc * 0.20)
            total_score = max(0.0, min(100.0, round(total_score, 1)))

            sub_scores = {
                "sharpness": sharp_sc,
                "exposure": exp_sc,
                "expression": 70.0,
                "composition": cont_sc
            }

            if total_score >= 75:
                verdict = "keeper"
            elif total_score >= 50:
                verdict = "acceptable"
            else:
                verdict = "reject"

            used_model = "Local Computer Vision (Offline Fallback)"

        # 5. Recommendation flags & ratings
        if total_score >= 75:
            flag = 1
            rating = 5 if total_score >= 88 else 4
            color_label = "Green"
        elif total_score >= 50:
            flag = 0
            rating = 3 if total_score >= 62 else 2
            color_label = "Yellow"
        else:
            flag = -1
            rating = 0
            color_label = "Red"

        return {
            "image_path": image_path,
            "total_score": total_score,
            "verdict": verdict,
            "recommended_flag": flag,
            "recommended_rating": rating,
            "recommended_label": color_label,
            "scores": sub_scores,
            "details": {
                "sub_scores": sub_scores,
                "cv_metrics": cv_metrics,
                "ai_eval": bool(res is not None)
            },
            "model_used": used_model
        }

