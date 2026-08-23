"""
LR Auto Color Pro - Traditional Computer Vision
Implements classical image analysis algorithms as a fallback and supplement
to ML-based analysis.

Algorithms implemented:
- White Balance: Gray World, White Patch (Retinex), PCA-based
- Tone: Histogram analysis, CLAHE, auto-levels
- Color: K-means clustering, color harmony, dominant color extraction
- Scene: Heuristic scene detection based on color/brightness/metadata
- Detail: Sharpness estimation, noise detection
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try to import OpenCV - gracefully degrade if not available
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available, traditional CV limited")

# Try to import Pillow
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available, image loading limited")


class TraditionalCV:
    """
    Traditional computer vision algorithms for image analysis:
    - Histogram analysis for exposure
    - Gray world white balance
    - Color clustering for dominant colors
    - Scene detection heuristics
    """

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Run all traditional CV analyses on an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Running traditional CV analysis on: {image_path}")

        if not CV2_AVAILABLE and not PIL_AVAILABLE:
            logger.warning("No image processing libraries available")
            return self._empty_result()

        try:
            # Load image
            img = self._load_image(image_path)
            if img is None:
                return self._empty_result()

            results = {
                "white_balance": self._estimate_white_balance_combined(img),
                "tone_analysis": self._analyze_tone_enhanced(img),
                "color_analysis": self._analyze_colors_enhanced(img),
                "hsl_analysis": self._analyze_hsl_channels(img),
                "scene_heuristics": self._scene_heuristics_enhanced(img),
                "histogram": self._compute_histogram(img),
                "detail_analysis": self._analyze_detail(img),
                "color_harmony": self._analyze_color_harmony(img),
                "histogram_analysis": self._analyze_histogram_exposure(img),
            }

            return results

        except Exception as e:
            logger.error(f"Traditional CV analysis failed: {e}")
            return self._empty_result()

    def _load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Load an image as RGB numpy array."""
        try:
            if CV2_AVAILABLE:
                img = cv2.imread(image_path)
                if img is not None:
                    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            elif PIL_AVAILABLE:
                img = Image.open(image_path).convert("RGB")
                return np.array(img)
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
        return None

    # =========================================================================
    # WHITE BALANCE ALGORITHMS
    # =========================================================================

    def _estimate_white_balance_combined(self, img: np.ndarray) -> Dict[str, float]:
        """
        Combined white balance estimation using multiple algorithms.
        Uses weighted average of Gray World and White Patch methods.
        """
        if img is None or img.size == 0:
            return {"temp": 0, "tint": 0, "confidence": 0}

        # Downsample for speed
        h, w = img.shape[:2]
        scale = min(1.0, 256.0 / max(h, w))
        small = self._resize(img, scale) if scale < 1.0 else img

        # Method 1: Gray World
        gw_temp, gw_tint = self._gray_world(small)

        # Method 2: White Patch (Retinex)
        wp_temp, wp_tint = self._white_patch(small)

        # Method 3: PCA-based (if OpenCV available)
        if CV2_AVAILABLE:
            pca_temp, pca_tint = self._pca_white_balance(small)
            # Weighted average: Gray World 0.4, White Patch 0.3, PCA 0.3
            temp = gw_temp * 0.4 + wp_temp * 0.3 + pca_temp * 0.3
            tint = gw_tint * 0.4 + wp_tint * 0.3 + pca_tint * 0.3
        else:
            # Weighted average: Gray World 0.6, White Patch 0.4
            temp = gw_temp * 0.6 + wp_temp * 0.4
            tint = gw_tint * 0.6 + wp_tint * 0.4

        # Calculate confidence based on agreement between methods
        temp_variance = np.var([gw_temp, wp_temp])
        tint_variance = np.var([gw_tint, wp_tint])
        confidence = max(0, 1.0 - (temp_variance + tint_variance) / 1000)

        return {
            "temp": round(temp, 1),
            "tint": round(tint, 1),
            "confidence": round(confidence, 3),
            "methods": {
                "gray_world": {"temp": round(gw_temp, 1), "tint": round(gw_tint, 1)},
                "white_patch": {"temp": round(wp_temp, 1), "tint": round(wp_tint, 1)},
            }
        }

    def _gray_world(self, img: np.ndarray) -> Tuple[float, float]:
        """
        Gray World assumption: the average color of a scene is gray.
        """
        avg_r = np.mean(img[:, :, 0])
        avg_g = np.mean(img[:, :, 1])
        avg_b = np.mean(img[:, :, 2])

        total_avg = (avg_r + avg_g + avg_b) / 3.0
        if total_avg == 0:
            return 0, 0

        # Temperature adjustment (positive = warmer)
        temp_shift = ((avg_b - avg_r) / total_avg) * 50

        # Tint adjustment (positive = magenta)
        tint_shift = ((avg_g - (avg_r + avg_b) / 2) / total_avg) * 30

        return (
            max(-100, min(100, temp_shift)),
            max(-100, min(100, tint_shift))
        )

    def _white_patch(self, img: np.ndarray, percentile: float = 95.0) -> Tuple[float, float]:
        """
        White Patch (Retinex) algorithm: the brightest pixels should be white.
        Uses the top percentile of luminance as reference white.
        """
        luminance = self._to_luminance(img)

        # Find the reference white point (top percentile)
        threshold = np.percentile(luminance, percentile)
        mask = luminance >= threshold

        if np.sum(mask) < 10:
            return self._gray_world(img)

        # Get average color of bright pixels
        bright_r = np.mean(img[:, :, 0][mask])
        bright_g = np.mean(img[:, :, 1][mask])
        bright_b = np.mean(img[:, :, 2][mask])

        max_val = max(bright_r, bright_g, bright_b)
        if max_val == 0:
            return 0, 0

        # Calculate correction needed
        temp_shift = ((bright_b - bright_r) / max_val) * 40
        tint_shift = ((bright_g - (bright_r + bright_b) / 2) / max_val) * 25

        return (
            max(-100, min(100, temp_shift)),
            max(-100, min(100, tint_shift))
        )

    def _pca_white_balance(self, img: np.ndarray) -> Tuple[float, float]:
        """
        PCA-based white balance: finds the principal color direction
        and corrects it to be neutral.
        """
        pixels = img.reshape(-1, 3).astype(np.float64)

        # Compute PCA
        mean = np.mean(pixels, axis=0)
        centered = pixels - mean
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        # The principal direction
        principal = eigenvectors[:, -1]

        # If principal direction has strong color cast, correct it
        color_strength = np.abs(principal - np.mean(principal))
        if np.max(color_strength) < 0.05:
            return 0, 0

        # Estimate correction from principal direction
        r, g, b = principal
        temp_shift = (b - r) * 30
        tint_shift = (g - (r + b) / 2) * 20

        return (
            max(-100, min(100, temp_shift)),
            max(-100, min(100, tint_shift))
        )

    # =========================================================================
    # TONE ANALYSIS
    # =========================================================================

    def _analyze_tone_enhanced(self, img: np.ndarray) -> Dict[str, Any]:
        """Enhanced tone analysis with auto-levels and CLAHE recommendations."""
        if img is None:
            return {"exposure_adjustment": 0, "contrast": 0}

        # Convert to luminance
        luminance = self._to_luminance(img)

        # Calculate statistics
        mean_luma = np.mean(luminance)
        median_luma = np.median(luminance)
        std_luma = np.std(luminance)

        # Percentile analysis
        p5 = np.percentile(luminance, 5)
        p25 = np.percentile(luminance, 25)
        p75 = np.percentile(luminance, 75)
        p95 = np.percentile(luminance, 95)

        # Exposure adjustment: aim for mean luminance ~0.45
        exposure_adj = (0.45 - mean_luma) * 0.5
        exposure_adj = max(-1.0, min(1.0, exposure_adj))

        # Contrast: based on interquartile range
        iqr = p75 - p25
        target_iqr = 0.35
        contrast_adj = (target_iqr - iqr) * 150
        contrast_adj = max(-50, min(50, contrast_adj))

        # Auto-levels: stretch histogram to use full range
        black_point = max(0, p5 - 0.02)
        white_point = min(1, p95 + 0.02)

        # Detect clipped highlights/shadows
        highlight_clip = np.sum(luminance > 0.98) / luminance.size
        shadow_clip = np.sum(luminance < 0.02) / luminance.size

        # CLAHE recommendation
        needs_clahe = std_luma < 0.15 and (highlight_clip < 0.01 and shadow_clip < 0.01)

        # Tone curve recommendation
        tone_curve = self._recommend_tone_curve(luminance, mean_luma, p5, p95)

        return {
            "exposure_adjustment": round(exposure_adj, 3),
            "contrast": round(contrast_adj, 1),
            "mean_luminance": round(mean_luma, 3),
            "median_luminance": round(median_luma, 3),
            "std_luminance": round(std_luma, 3),
            "percentiles": {"p5": round(p5, 3), "p25": round(p25, 3), "p75": round(p75, 3), "p95": round(p95, 3)},
            "highlight_clipping": round(highlight_clip, 4),
            "shadow_clipping": round(shadow_clip, 4),
            "auto_levels": {"black_point": round(black_point, 3), "white_point": round(white_point, 3)},
            "needs_clahe": needs_clahe,
            "tone_curve": tone_curve,
        }

    def _recommend_tone_curve(self, luminance: np.ndarray, mean_luma: float,
                               p5: float, p95: float) -> Dict[str, float]:
        """Generate a recommended tone curve based on image analysis."""
        # Calculate shadows/midtones/highlights adjustments
        shadows_adj = 0
        highlights_adj = 0

        # If shadows are crushed, lift them
        if p5 > 0.05:
            shadows_adj = -10  # Darken shadows slightly
        elif p5 < 0.01:
            shadows_adj = 15  # Lift shadows

        # If highlights are blown, recover them
        if p95 < 0.90:
            highlights_adj = 15  # Brighten highlights
        elif p95 > 0.98:
            highlights_adj = -20  # Recover highlights

        # Midtones adjustment based on mean
        if mean_luma < 0.35:
            midtones_adj = 15
        elif mean_luma > 0.55:
            midtones_adj = -10
        else:
            midtones_adj = 0

        return {
            "shadows": shadows_adj,
            "midtones": midtones_adj,
            "highlights": highlights_adj,
        }

    # =========================================================================
    # COLOR ANALYSIS ENHANCED
    # =========================================================================

    def _analyze_histogram_exposure(self, img: np.ndarray) -> Dict[str, Any]:
        """
        Advanced Photographic Histogram & Exposure Metering Engine.
        Uses 18% middle gray calibration, skin-tone isolation, ETTR highlight protection,
        and multi-zone luminance analysis to compute highly accurate Exposure EV and tone parameters.
        """
        if img is None or img.size == 0:
            return {}

        # 1. Luminance & Linear Space conversion (sRGB gamma 2.2 -> linear)
        rgb_norm = img.astype(np.float32) / 255.0
        # sRGB gamma approx 2.2
        linear_rgb = np.power(rgb_norm, 2.2)
        # Rec. 709 linear luminance: Y = 0.2126 R + 0.7152 G + 0.0722 B
        linear_luma = 0.2126 * linear_rgb[:, :, 0] + 0.7152 * linear_rgb[:, :, 1] + 0.0722 * linear_rgb[:, :, 2]
        # sRGB perceptual luminance (0.0 to 1.0)
        perceptual_luma = 0.299 * rgb_norm[:, :, 0] + 0.587 * rgb_norm[:, :, 1] + 0.114 * rgb_norm[:, :, 2]

        total_pixels = float(perceptual_luma.size)
        if total_pixels == 0:
            return {}

        # 2. Key Photometric Percentiles
        p1 = float(np.percentile(perceptual_luma, 1))
        p5 = float(np.percentile(perceptual_luma, 5))
        p25 = float(np.percentile(perceptual_luma, 25))
        p50 = float(np.percentile(perceptual_luma, 50))
        p75 = float(np.percentile(perceptual_luma, 75))
        p95 = float(np.percentile(perceptual_luma, 95))
        p99 = float(np.percentile(perceptual_luma, 99))

        mean_luma = float(np.mean(perceptual_luma))
        std_luma = float(np.std(perceptual_luma))

        # 3. Ansel Adams 5-Zone Distribution
        z_blacks = float(np.sum(perceptual_luma < 0.05)) / total_pixels * 100.0
        z_shadows = float(np.sum((perceptual_luma >= 0.05) & (perceptual_luma < 0.25))) / total_pixels * 100.0
        z_midtones = float(np.sum((perceptual_luma >= 0.25) & (perceptual_luma < 0.70))) / total_pixels * 100.0
        z_highlights = float(np.sum((perceptual_luma >= 0.70) & (perceptual_luma < 0.95))) / total_pixels * 100.0
        z_whites = float(np.sum(perceptual_luma >= 0.95)) / total_pixels * 100.0

        # Clipping percentages
        shadow_clip = float(np.sum(perceptual_luma < 0.01)) / total_pixels * 100.0
        highlight_clip = float(np.sum(perceptual_luma > 0.99)) / total_pixels * 100.0

        # 4. Standard 18% Middle Gray Calibration in Linear Space
        # 18% middle gray in linear space is 0.180
        linear_med = max(0.005, float(np.median(linear_luma)))
        # Target middle gray EV shift: log2(0.18 / linear_med)
        gray18_ev = float(np.log2(0.180 / linear_med))

        # 5. Skin Tone Detection & Subject Luminance Metering
        # Detect human skin pixels in HSV space
        has_skin = False
        skin_luma_mean = 0.0
        skin_ev_shift = 0.0

        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            h = hsv[:, :, 0]
            s = hsv[:, :, 1]
            v = hsv[:, :, 2]
            # Standard skin tone range: Hue [0..25] or [165..180], Sat [30..170], Val [50..250]
            skin_mask = ((h <= 25) | (h >= 165)) & (s >= 30) & (s <= 170) & (v >= 50) & (v <= 250)
            skin_count = np.sum(skin_mask)
            if skin_count > (total_pixels * 0.015):  # > 1.5% skin pixels
                has_skin = True
                skin_luma_mean = float(np.mean(perceptual_luma[skin_mask]))
                # Target skin luminance in sRGB is Zone VI (~ 0.58 - 0.64)
                target_skin = 0.60
                if skin_luma_mean > 0.05:
                    skin_ev_shift = float(np.log2(target_skin / skin_luma_mean)) * 1.2

        # 6. Multi-Zone Optimal Exposure EV Calculation
        # Base EV from perceptual mean vs 0.46 target
        perceptual_ev = (0.46 - mean_luma) * 1.8

        if has_skin:
            # Weighted metering: 65% skin tone priority + 35% global middle gray
            optimal_ev = skin_ev_shift * 0.65 + gray18_ev * 0.35
        else:
            # Weighted metering: 60% 18% linear gray + 40% perceptual
            optimal_ev = gray18_ev * 0.60 + perceptual_ev * 0.40

        # Protect against blowing out highlights (Highlight headroom / ETTR)
        if p99 > 0.96 or highlight_clip > 1.0:
            optimal_ev = min(optimal_ev, 0.15)
        if p99 > 0.99 or highlight_clip > 2.5:
            optimal_ev = min(optimal_ev, -0.30)

        # Protect against severe underexposure
        if p50 < 0.20 and highlight_clip < 0.5:
            optimal_ev = max(optimal_ev, 0.40)

        optimal_ev = round(max(-2.5, min(2.5, optimal_ev)), 2)

        # 7. Dynamic Range & Contrast in EV Stops
        dr_p1 = max(0.001, p1)
        dr_p99 = min(1.0, p99)
        dr_ev = float(np.log2(dr_p99 / dr_p1)) if dr_p99 > dr_p1 else 0.0
        dr_ev = round(max(1.0, min(14.0, dr_ev)), 1)

        # 8. Precise Tone Parameter Recommendations derived from Histogram
        # Highlights: pull down to recover if highlights are dense
        if highlight_clip > 1.5 or z_whites > 8.0:
            rec_highlights = -55
        elif z_highlights > 28.0 or p95 > 0.90:
            rec_highlights = -45
        else:
            rec_highlights = -30

        # Shadows: lift if crushed or heavy in shadow zones
        if shadow_clip > 2.0 or z_blacks > 12.0:
            rec_shadows = 48
        elif z_shadows > 30.0 or p5 < 0.05:
            rec_shadows = 36
        else:
            rec_shadows = 24

        # Whites: push to add brilliance if headroom exists without clipping
        rec_whites = 18 if (z_whites < 4.0 and highlight_clip < 0.5) else 0
        # Blacks: anchor deep blacks without clipping
        rec_blacks = -18 if (z_blacks < 4.0 and shadow_clip < 0.5) else -8

        # Contrast: calibrated to IQR (p75 - p25)
        iqr = p75 - p25
        if iqr < 0.25:  # Low contrast / hazy
            rec_contrast = 28
        elif iqr > 0.45:  # High contrast
            rec_contrast = 15
        else:
            rec_contrast = 22

        return {
            "zone_blacks": round(z_blacks, 1),
            "zone_shadows": round(z_shadows, 1),
            "zone_midtones": round(z_midtones, 1),
            "zone_highlights": round(z_highlights, 1),
            "zone_whites": round(z_whites, 1),
            "shadow_clipping": round(shadow_clip, 2),
            "highlight_clipping": round(highlight_clip, 2),
            "mean_luminance_pct": round(mean_luma * 100.0, 1),
            "median_luminance_pct": round(p50 * 100.0, 1),
            "skin_detected": has_skin,
            "skin_luminance_pct": round(skin_luma_mean * 100.0, 1) if has_skin else None,
            "dynamic_range_ev": dr_ev,
            "recommended_ev": optimal_ev,
            "recommended_highlights": rec_highlights,
            "recommended_shadows": rec_shadows,
            "recommended_whites": rec_whites,
            "recommended_blacks": rec_blacks,
            "recommended_contrast": rec_contrast,
        }

    def _analyze_colors_enhanced(self, img: np.ndarray) -> Dict[str, Any]:
        """Enhanced color analysis with warmth, saturation, and harmony."""
        if img is None:
            return {}

        # Downsample for k-means
        h, w = img.shape[:2]
        scale = min(1.0, 128.0 / max(h, w))
        small = self._resize(img, scale) if scale < 1.0 else img

        # Reshape for clustering
        pixels = small.reshape(-1, 3).astype(np.float32)

        # K-means clustering for dominant colors
        dominant_colors = self._extract_dominant_colors(pixels, k=5)

        # Calculate color warmth
        avg_r = np.mean(img[:, :, 0])
        avg_g = np.mean(img[:, :, 1])
        avg_b = np.mean(img[:, :, 2])
        warmth = (avg_r - avg_b) / 255.0

        # Saturation analysis
        avg_saturation = self._calculate_avg_saturation(img)

        # Color diversity (how many distinct colors)
        color_diversity = len([c for c in dominant_colors if c["percentage"] > 0.05])

        return {
            "dominant_colors": dominant_colors,
            "warmth": round(warmth, 3),
            "is_warm": bool(warmth > 0.05),
            "is_cool": bool(warmth < -0.05),
            "avg_saturation": round(avg_saturation, 3),
            "color_diversity": color_diversity,
            "color_temperature_k": self._estimate_color_temperature(avg_r, avg_g, avg_b),
        }

    def _extract_dominant_colors(self, pixels: np.ndarray, k: int = 5) -> List[Dict]:
        """Extract dominant colors using k-means clustering."""
        if CV2_AVAILABLE and len(pixels) >= k:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(
                pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS
            )

            # Sort by frequency
            counts = np.bincount(labels.flatten(), minlength=k)
            sorted_idx = np.argsort(-counts)

            dominant_colors = []
            for idx in sorted_idx:
                color = centers[idx].astype(int)
                percentage = counts[idx] / len(labels)
                dominant_colors.append({
                    "rgb": [int(color[0]), int(color[1]), int(color[2])],
                    "percentage": round(percentage, 3),
                })
            return dominant_colors
        else:
            # Simple averaging without OpenCV
            mean_color = np.mean(pixels, axis=0).astype(int)
            return [{
                "rgb": [int(mean_color[0]), int(mean_color[1]), int(mean_color[2])],
                "percentage": 1.0,
            }]

    def _calculate_avg_saturation(self, img: np.ndarray) -> float:
        """Calculate average saturation of the image."""
        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            return float(np.mean(hsv[:, :, 1])) / 255.0
        else:
            # Approximation without OpenCV
            max_c = np.max(img, axis=2).astype(float)
            min_c = np.min(img, axis=2).astype(float)
            diff = max_c - min_c
            mask = max_c > 0
            if np.any(mask):
                return float(np.mean(diff[mask] / max_c[mask]))
            return 0.0

    def _estimate_color_temperature(self, r: float, g: float, b: float) -> int:
        """Estimate color temperature in Kelvin from RGB averages."""
        # Simplified McCamy formula
        if b == 0 or g == 0:
            return 5500

        ratio = r / b
        # Approximate mapping from ratio to Kelvin
        if ratio > 1.5:
            return 3000  # Very warm
        elif ratio > 1.2:
            return 4000  # Warm
        elif ratio > 0.9:
            return 5500  # Neutral
        elif ratio > 0.7:
            return 6500  # Cool
        else:
            return 8000  # Very cool

    def _analyze_color_harmony(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze color harmony and suggest complementary adjustments."""
        if img is None:
            return {}

        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            h_channel = hsv[:, :, 0].astype(float) * 2  # 0-360 degrees

            # Find dominant hue ranges
            hist, bin_edges = np.histogram(h_channel, bins=12, range=(0, 360))
            dominant_hue_idx = np.argmax(hist)
            dominant_hue = (bin_edges[dominant_hue_idx] + bin_edges[dominant_hue_idx + 1]) / 2

            # Complementary hue (opposite on color wheel)
            complementary = (dominant_hue + 180) % 360

            # Analogous hues
            analogous1 = (dominant_hue + 30) % 360
            analogous2 = (dominant_hue - 30) % 360

            return {
                "dominant_hue": round(dominant_hue, 1),
                "complementary_hue": round(complementary, 1),
                "analogous_hues": [round(analogous1, 1), round(analogous2, 1)],
                "harmony_type": self._classify_harmony(dominant_hue, hist),
            }

        return {"dominant_hue": 0, "complementary_hue": 180, "analogous_hues": [30, 330]}

    def _classify_harmony(self, dominant_hue: float, hue_hist: np.ndarray) -> str:
        """Classify the color harmony type."""
        # Find number of significant hue peaks
        peaks = np.sum(hue_hist > np.max(hue_hist) * 0.3)

        if peaks <= 2:
            return "monochromatic"
        elif peaks <= 4:
            return "complementary"
        else:
            return "analogous"

    def _analyze_hsl_channels(self, img: np.ndarray) -> Dict[str, Dict[str, int]]:
        """
        Analyze 8 HSL color channels (Red, Orange, Yellow, Green, Aqua, Blue, Purple, Magenta)
        and suggest optimal Hue, Saturation, and Luminance adjustments.
        """
        if img is None or not CV2_AVAILABLE:
            return {}

        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            h = hsv[:, :, 0].astype(float) * 2.0  # 0 to 360
            s = hsv[:, :, 1].astype(float) / 255.0  # 0 to 1
            v = hsv[:, :, 2].astype(float) / 255.0  # 0 to 1

            channels_def = {
                "red": ((h >= 345) | (h < 15)) & (s > 0.15),
                "orange": (h >= 15) & (h < 40) & (s > 0.15),
                "yellow": (h >= 40) & (h < 70) & (s > 0.15),
                "green": (h >= 70) & (h < 165) & (s > 0.15),
                "aqua": (h >= 165) & (h < 200) & (s > 0.15),
                "blue": (h >= 200) & (h < 260) & (s > 0.15),
                "purple": (h >= 260) & (h < 315) & (s > 0.15),
                "magenta": (h >= 315) & (h < 345) & (s > 0.15),
            }

            hsl_adjustments = {}
            for ch_name, mask in channels_def.items():
                pixel_count = np.count_nonzero(mask)
                if pixel_count > 50:
                    ch_s = np.mean(s[mask])
                    ch_v = np.mean(v[mask])

                    sat_adj = 0
                    lum_adj = 0
                    hue_adj = 0

                    if ch_name == "orange":
                        # Skin tones: brighten noticeably and clean redness
                        lum_adj = int(np.clip((0.68 - ch_v) * 40, 5, 22))
                        sat_adj = int(np.clip((0.45 - ch_s) * 30, -12, 12))
                    elif ch_name == "green":
                        # Lush emerald foliage
                        hue_adj = 20
                        sat_adj = 18
                        lum_adj = 8
                    elif ch_name == "blue":
                        # Deep rich sky/water
                        hue_adj = -5
                        lum_adj = -18
                        sat_adj = 25
                    elif ch_name == "yellow":
                        hue_adj = -6
                        sat_adj = 18
                        lum_adj = 8
                    elif ch_name == "aqua":
                        hue_adj = -8
                        sat_adj = 22
                        lum_adj = -10
                    elif ch_name == "red":
                        hue_adj = 4
                        sat_adj = 15
                        lum_adj = 5

                    hsl_adjustments[ch_name] = {
                        "hue": int(hue_adj),
                        "saturation": int(sat_adj),
                        "luminance": int(lum_adj)
                    }
                else:
                    hsl_adjustments[ch_name] = {"hue": 0, "saturation": 0, "luminance": 0}

            return hsl_adjustments
        except Exception as e:
            logger.warning(f"HSL channel analysis failed: {e}")
            return {}

    # =========================================================================
    # SCENE HEURISTICS ENHANCED
    # =========================================================================

    def _scene_heuristics_enhanced(self, img: np.ndarray) -> Dict[str, Any]:
        """
        Enhanced multi-feature heuristic scene detection covering 26 photography genres.
        Combines colorimetry, spatial geometry, face detection, and texture cues.
        """
        if img is None:
            return {"possible_scenes": []}

        h, w = img.shape[:2]
        aspect_ratio = w / h

        avg_h, avg_s, avg_v = self._avg_hsv(img)
        mean_v = float(np.mean(avg_v)) if isinstance(avg_v, np.ndarray) else float(avg_v)
        avg_h = float(np.mean(avg_h)) if isinstance(avg_h, np.ndarray) else float(avg_h)
        avg_s = float(np.mean(avg_s)) if isinstance(avg_s, np.ndarray) else float(avg_s)

        edge_density = self._calculate_edge_density(img)
        skin_score = self._detect_skin_tones(img)
        sky_score = self._detect_sky(img)
        green_score = self._detect_green(img)

        # Detect face count if cascade available
        face_count = 0
        face_area_ratio = 0.0
        if CV2_AVAILABLE:
            try:
                cv_data = getattr(cv2, 'data', None)
                if cv_data and hasattr(cv_data, 'haarcascades'):
                    face_cascade_path = os.path.join(cv_data.haarcascades, 'haarcascade_frontalface_default.xml')
                    if os.path.exists(face_cascade_path):
                        face_cascade = cv2.CascadeClassifier(face_cascade_path)
                        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(30, 30))
                        face_count = len(faces)
                        if face_count > 0:
                            total_face_area = sum(fw * fh for (_, _, fw, fh) in faces)
                            face_area_ratio = total_face_area / (h * w)
            except Exception:
                pass

        # Bottom half water / sand check for seascape
        water_score = 0.0
        if CV2_AVAILABLE:
            try:
                lower_half = img[h//2:, :, :]
                lh_hsv = cv2.cvtColor(lower_half, cv2.COLOR_RGB2HSV)
                water_mask = cv2.inRange(lh_hsv, np.array([85, 30, 60]), np.array([135, 255, 255]))
                water_score = float(np.sum(water_mask > 0)) / water_mask.size
            except Exception:
                pass

        possible_scenes = []

        # 1. Black & White
        if avg_s < 0.06:
            possible_scenes.append(("black_and_white", 0.95))

        # 2. People / Portrait categories
        if face_count >= 2:
            possible_scenes.append(("group_portrait", min(0.92, 0.70 + face_count * 0.08)))
        elif face_count == 1:
            if face_area_ratio > 0.10:
                possible_scenes.append(("portrait", min(0.95, 0.75 + face_area_ratio)))
            else:
                possible_scenes.append(("fashion", 0.78))
                possible_scenes.append(("portrait", 0.75))
        elif skin_score > 0.35:
            possible_scenes.append(("portrait", min(0.85, skin_score)))
            possible_scenes.append(("fashion", 0.65))

        # 3. Night & Astro
        if mean_v < 0.28:
            if edge_density > 0.15:
                possible_scenes.append(("concert", 0.70))
                possible_scenes.append(("night", 0.85))
            elif sky_score > 0.2:
                possible_scenes.append(("astro", 0.75))
                possible_scenes.append(("night", 0.88))
            else:
                possible_scenes.append(("night", min(0.92, 0.70 + (0.28 - mean_v) * 2)))

        # 4. Sunset / Sunrise
        if (10 < avg_h < 50) and avg_s > 0.35 and mean_v > 0.25:
            sunset_conf = min(0.90, 0.55 + (avg_s * 0.4))
            possible_scenes.append(("sunset", sunset_conf))

        # 5. Seascape / Beach
        if water_score > 0.25 or (sky_score > 0.25 and 180 < avg_h < 240):
            possible_scenes.append(("seascape", min(0.88, 0.50 + water_score * 0.5 + sky_score * 0.3)))

        # 6. Nature Landscape vs Aerial
        if green_score > 0.30 or (sky_score > 0.25 and green_score > 0.15):
            landscape_conf = min(0.90, max(green_score, sky_score) + 0.2)
            possible_scenes.append(("landscape", landscape_conf))

        # 7. Architecture & Cityscape
        if edge_density > 0.22 and avg_s < 0.35:
            if sky_score > 0.2 and aspect_ratio > 1.3:
                possible_scenes.append(("cityscape", 0.75))
                possible_scenes.append(("architecture", 0.72))
            else:
                possible_scenes.append(("architecture", 0.78))
                possible_scenes.append(("interior", 0.60))

        # 8. Food
        if 20 < avg_h < 65 and avg_s > 0.35 and 0.4 < mean_v < 0.85 and skin_score < 0.15 and face_count == 0:
            possible_scenes.append(("food", 0.70))

        # 9. Macro & Product
        if edge_density > 0.28 and face_count == 0 and skin_score < 0.1:
            possible_scenes.append(("macro", 0.68))
        elif edge_density < 0.08 and 0.4 < mean_v < 0.85 and face_count == 0:
            possible_scenes.append(("product", 0.62))

        # 10. Street & Documentary
        if 0.12 < edge_density < 0.24 and 0.15 < avg_s < 0.5 and mean_v > 0.3:
            possible_scenes.append(("street", 0.58))
            possible_scenes.append(("documentary", 0.52))

        # 11. Snow & Winter
        if mean_v > 0.68 and avg_s < 0.18:
            possible_scenes.append(("snow", min(0.90, 0.60 + mean_v * 0.3)))

        # Default fallback if empty
        if not possible_scenes:
            possible_scenes.append(("general", 0.50))

        # Sort by confidence score descending
        possible_scenes.sort(key=lambda x: -x[1])

        return {
            "possible_scenes": [
                {"scene": s, "score": round(score, 2)}
                for s, score in possible_scenes
            ],
            "features": {
                "avg_hue": round(float(avg_h), 1),
                "avg_saturation": round(float(avg_s), 3),
                "mean_brightness": round(float(mean_v), 3),
                "edge_density": round(edge_density, 3),
                "skin_score": round(skin_score, 3),
                "face_count": face_count,
                "sky_score": round(sky_score, 3),
                "green_score": round(green_score, 3),
                "water_score": round(water_score, 3),
                "aspect_ratio": round(aspect_ratio, 2),
            }
        }

    def _calculate_edge_density(self, img: np.ndarray) -> float:
        """Calculate edge density using Sobel or Canny."""
        if not CV2_AVAILABLE:
            return 0.1

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            return float(np.sum(edges > 0)) / edges.size
        except Exception:
            return 0.1

    def _detect_skin_tones(self, img: np.ndarray) -> float:
        """Detect skin tone pixels in the image (indicator of portrait)."""
        if not CV2_AVAILABLE:
            return 0.0

        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

            # Skin tone range in OpenCV HSV
            # Hue: 0-50 (reds, oranges, yellows in OpenCV's 0-180 range)
            # Saturation: 20-180 (not too gray, not oversaturated)
            # Value: 70-255 (not too dark)
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([30, 180, 255], dtype=np.uint8)

            mask = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_ratio = np.sum(mask > 0) / mask.size

            # Scale up for confidence (skin usually occupies small portion)
            return min(1.0, skin_ratio * 3)
        except Exception:
            return 0.0

    def _detect_sky(self, img: np.ndarray) -> float:
        """Detect sky by analyzing upper portion of image for blue/cyan colors."""
        h, w = img.shape[:2]
        upper = img[:h//3, :, :]  # Top third of image

        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(upper, cv2.COLOR_RGB2HSV)
            # Sky is typically blue/cyan: H=180-240 in OpenCV HSV (90-120 in 0-360)
            sky_mask = cv2.inRange(hsv, np.array([90, 30, 100]), np.array([130, 255, 255]))
            return float(np.sum(sky_mask > 0)) / sky_mask.size
        else:
            # Approximate sky detection
            avg_b = np.mean(upper[:, :, 2])
            avg_r = np.mean(upper[:, :, 0])
            if avg_b > avg_r * 1.2:
                return 0.5
            return 0.1

    def _detect_green(self, img: np.ndarray) -> float:
        """Detect green coverage (grass, trees, foliage)."""
        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            # Green range in OpenCV HSV
            green_mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
            return float(np.sum(green_mask > 0)) / green_mask.size
        else:
            avg_g = np.mean(img[:, :, 1])
            avg_r = np.mean(img[:, :, 0])
            avg_b = np.mean(img[:, :, 2])
            if avg_g > avg_r * 1.1 and avg_g > avg_b * 1.1:
                return 0.4
            return 0.1

    # =========================================================================
    # DETAIL ANALYSIS
    # =========================================================================

    def _analyze_detail(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze image detail: sharpness and noise."""
        if img is None or not CV2_AVAILABLE:
            return {"sharpness": 0, "noise_level": 0}

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            # Sharpness: variance of Laplacian
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = float(np.var(laplacian))
            # Normalize to 0-1 range (typical range 0-1000)
            normalized_sharpness = min(1.0, sharpness / 500.0)

            # Noise estimation using high-frequency content
            # Apply a blur and measure difference
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            noise_diff = np.abs(gray.astype(float) - blurred.astype(float))
            noise_level = float(np.mean(noise_diff)) / 255.0

            return {
                "sharpness": round(normalized_sharpness, 3),
                "noise_level": round(noise_level, 4),
                "needs_sharpening": bool(normalized_sharpness < 0.3),
                "needs_noise_reduction": bool(noise_level > 0.03),
            }
        except Exception as e:
            logger.warning(f"Detail analysis failed: {e}")
            return {"sharpness": 0, "noise_level": 0}

    def _compute_histogram(self, img: np.ndarray) -> Dict[str, Any]:
        """Compute RGB histogram data."""
        histograms = {}
        for i, channel in enumerate(["red", "green", "blue"]):
            hist = np.histogram(img[:, :, i], bins=64, range=(0, 256))
            histograms[channel] = hist[0].tolist()

        luminance_hist = np.histogram(self._to_luminance(img), bins=64, range=(0, 1))
        histograms["luminance"] = luminance_hist[0].tolist()

        return histograms

    def _to_luminance(self, img: np.ndarray) -> np.ndarray:
        """Convert RGB image to luminance."""
        return (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]) / 255.0

    def _avg_hsv(self, img: np.ndarray) -> Tuple[float, float, float]:
        """Get average HSV values."""
        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            h, s, v = cv2.split(hsv)
            return float(np.mean(h)), float(np.mean(s)) / 255.0, float(np.mean(v)) / 255.0
        else:
            # Simple approximation
            return 0.0, 0.5, 0.5

    def _resize(self, img: np.ndarray, scale: float) -> np.ndarray:
        """Resize image by a scale factor."""
        if CV2_AVAILABLE:
            new_w = int(img.shape[1] * scale)
            new_h = int(img.shape[0] * scale)
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return img

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result when analysis fails."""
        return {
            "white_balance": {"temp": 0, "tint": 0, "confidence": 0},
            "tone_analysis": {"exposure_adjustment": 0, "contrast": 0},
            "color_analysis": {"dominant_colors": []},
            "scene_heuristics": {"possible_scenes": []},
            "histogram": {},
            "detail_analysis": {"sharpness": 0, "noise_level": 0},
            "color_harmony": {},
        }
