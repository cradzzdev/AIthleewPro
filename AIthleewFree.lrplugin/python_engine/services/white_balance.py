"""
AIthleewPro - AI Auto White Balance Service
Analyzes images to determine optimal neutral Color Temperature (Kelvin 2,000K-50,000K for RAW; -100 to +100 for Non-RAW).
Reads camera/current photo Temperature to calculate exact neutral temperature offset.
Exclusively manages Color Temperature without interfering with Tint.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

from services.cloud_client import CloudAPIClient
from services.traditional_cv import TraditionalCV

logger = logging.getLogger(__name__)

WB_SYSTEM_PROMPT = """You are an expert color science and white balance mastering specialist for Lightroom Classic.
Your task is to analyze the photograph, detect any color temperature cast (such as warm tungsten, harsh yellow sunlight, cold blue shade, or blue skylight cast), and calculate the EXACT target neutral Color Temperature.

CRITICAL TEMPERATURE RULES:
1. RAW Files:
   - "target_kelvin": integer between 2000 and 50000 Kelvin (typical daylight 5200-5600K, cloudy 6000-6500K, shade 7000-8000K, tungsten 2800-3400K).
2. Non-RAW / Rendered Files (JPEG, TIFF, PNG):
   - "relative_temp": integer between -100 and 100 (Negative = cooler/blue; Positive = warmer/yellow).

You will be given the photo's CURRENT Temperature setting along with Computer Vision physical measurements. Calculate the exact neutral target temperature.

Return ONLY a valid raw JSON object with NO markdown backticks:
{
    "color_cast": "warm_yellow|cool_blue|neutral",
    "cast_description": "Vietnamese explanation of lighting condition, detected cast, and corrective action",
    "target_kelvin": 2000-50000,
    "relative_temp": -100 to 100,
    "confidence": 0.0-1.0
}"""


class WhiteBalanceService:
    """Service to evaluate and compute neutral Color Temperature for RAW and Non-RAW images."""

    def __init__(self, cloud_client: Optional[CloudAPIClient] = None,
                 traditional_cv: Optional[TraditionalCV] = None):
        self.cloud_client = cloud_client
        self.traditional_cv = traditional_cv or TraditionalCV()

    def evaluate_white_balance(self, image_path: str, is_raw: bool = False,
                               original_ext: Optional[str] = None,
                               current_temp: Optional[float] = None,
                               current_tint: Optional[float] = None) -> Dict[str, Any]:
        """
        Evaluate color temperature of an image and return optimal neutral settings.

        Args:
            image_path: Path to preview image
            is_raw: True if source photo is a RAW file
            original_ext: File extension of source photo (e.g. .cr3, .arw, .jpg)
            current_temp: Current Kelvin (for RAW) or relative temp (for Non-RAW) from Lightroom metadata

        Returns:
            Dict containing calculated Temperature parameters for RAW and Non-RAW.
        """
        logger.info(f"Analyzing Color Temperature for: {image_path} (is_raw={is_raw}, ext={original_ext}, cur_temp={current_temp})")

        # 1. Physical Computer Vision Analysis (Gray World + White Patch + PCA)
        img = self.traditional_cv._load_image(image_path)
        if img is not None:
            cv_wb = self.traditional_cv._estimate_white_balance_combined(img)
        else:
            cv_wb = {}

        temp_shift = float(cv_wb.get("temp", 0.0))
        cv_conf = float(cv_wb.get("confidence", 0.75))

        if is_raw:
            base_temp = float(current_temp) if (current_temp is not None and 2000 <= current_temp <= 50000) else 5500.0
            
            # Kelvin adjustment (CV temp scale ~ 35K per shift unit)
            cv_kelvin = int(max(2000, min(50000, round(base_temp + (temp_shift * 35.0)))))
            cv_relative_temp = int(max(-100, min(100, round((cv_kelvin - base_temp) / 50.0))))
        else:
            base_temp = float(current_temp or 0.0)
            cv_relative_temp = int(max(-100, min(100, round(base_temp + temp_shift))))
            cv_kelvin = 5500

        # Generate human-readable Vietnamese description
        cast_type, cast_desc = self._classify_cast(temp_shift, is_raw, cv_kelvin)

        result = {
            "is_raw": is_raw,
            "original_ext": original_ext or ("RAW" if is_raw else "JPEG"),
            "current_temp": base_temp,
            "color_cast": cast_type,
            "cast_description": cast_desc,
            "target_kelvin": cv_kelvin,
            "relative_temp": cv_relative_temp,
            "temperature": cv_kelvin if is_raw else cv_relative_temp,
            "confidence": cv_conf,
            "model_used": "Computer Vision (Gray World & White Patch)",
        }

        # 2. Cloud Vision AI Analysis
        if self.cloud_client and self.cloud_client.is_available():
            try:
                raw_info = f"Source format: {'RAW (' + str(original_ext) + ')' if is_raw else 'Non-RAW (' + str(original_ext) + ')'}."
                current_info = f"Current Lightroom Temperature = {base_temp:.0f}{'K' if is_raw else ''}."
                cv_info = f"Physical CV Analysis: Temp Shift = {temp_shift:+.1f}."
                user_prompt = f"{raw_info} {current_info} {cv_info} Analyze the color temperature cast in this image and calculate the precise target neutral Color Temperature. Return ONLY raw JSON."

                ai_res = self.cloud_client._try_model(
                    model=self.cloud_client.preferred_model or "meta/llama-3.2-11b-vision-instruct",
                    image_data=self._encode_image(image_path),
                    user_prompt=user_prompt,
                    timeout=25000,
                    system_prompt=WB_SYSTEM_PROMPT
                )

                if ai_res and isinstance(ai_res, dict):
                    logger.info("Successfully received Vision AI Temperature inference")
                    if "target_kelvin" in ai_res and is_raw:
                        k = int(ai_res["target_kelvin"])
                        result["target_kelvin"] = max(2000, min(50000, k))
                        result["temperature"] = result["target_kelvin"]
                    if "relative_temp" in ai_res and not is_raw:
                        rt = int(ai_res["relative_temp"])
                        result["relative_temp"] = max(-100, min(100, rt))
                        result["temperature"] = result["relative_temp"]
                    if "color_cast" in ai_res:
                        result["color_cast"] = ai_res["color_cast"]
                    if "cast_description" in ai_res and ai_res["cast_description"]:
                        result["cast_description"] = ai_res["cast_description"]
                    if "confidence" in ai_res:
                        result["confidence"] = float(ai_res["confidence"])

                    result["model_used"] = self.cloud_client.preferred_model
            except Exception as e:
                logger.warning(f"Cloud AI Temperature inference fallback to CV: {e}")

        logger.info(f"Final WB Result: Temp={result['temperature']} (is_raw={is_raw})")
        return result

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _classify_cast(self, temp_shift: float, is_raw: bool, kelvin: int) -> Tuple[str, str]:
        """Generate clean, natural Vietnamese description of color temperature cast."""
        if abs(temp_shift) < 3.0:
            return "neutral", "Nhiệt độ màu ảnh đang cân bằng và chuẩn tự nhiên."

        if temp_shift > 4.5:
            desc = "Ảnh phát hiện ám lạnh/xanh dương (cần bù ấm)."
            cast_type = "cool_blue"
        elif temp_shift < -4.5:
            desc = "Ảnh phát hiện ám vàng ấm/nhiệt độ màu cao (cần hạ nhiệt)."
            cast_type = "warm_yellow"
        else:
            desc = "Ảnh lệch nhẹ nhiệt độ màu."
            cast_type = "neutral"

        if is_raw:
            desc += f" Tối ưu về {kelvin:,}K."
        else:
            desc += f" Khuyến nghị bù trừ Temp {temp_shift:+.0f}."
        return cast_type, desc
