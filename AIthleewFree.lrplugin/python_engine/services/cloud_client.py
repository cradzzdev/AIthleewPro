"""
LR Auto Color Pro - NVIDIA NIM Cloud API Client
Handles communication with NVIDIA NIM (Inference Microservices) for vision AI analysis.
"""

import base64
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# API endpoints
NVIDIA_NIM_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_NIM_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
KILO_CODE_API_URL = "https://api.kilo.ai/api/gateway/chat/completions"

NVIDIA_NIM_VISION_MODELS = [
    # OpenRouter
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B IT (OpenRouter Free Vision)",
        "provider": "OpenRouter",
    },
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Google Gemma 4 26B A4B IT (OpenRouter Free Vision)",
        "provider": "OpenRouter",
    },
    # Kilo Code
    {
        "id": "thinkingmachines/inkling:free",
        "name": "ThinkingMachines Inkling (Kilo Code Free) - ⚠️ Dữ liệu ảnh có thể bị khai thác bởi bên thứ 3",
        "provider": "Kilo Code",
    },
    {
        "id": "stepfun/step-3.7-flash:free",
        "name": "StepFun Step 3.7 Flash (Kilo Code Free)",
        "provider": "Kilo Code",
    },
    {
        "id": "thinkingmachines/inkling-small:free",
        "name": "ThinkingMachines Inkling Small (Kilo Code Free) - ⚠️ Dữ liệu ảnh có thể bị khai thác bởi bên thứ 3",
        "provider": "Kilo Code",
    },
    # NVIDIA NIM
    {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "name": "Meta Llama 3.2 11B Vision Instruct (Nhanh & Chuẩn xác - Khuyên dùng)",
        "provider": "Meta",
    },
    {
        "id": "meta/llama-3.2-90b-vision-instruct",
        "name": "Meta Llama 3.2 90B Vision Instruct (Chất lượng cao nhất)",
        "provider": "Meta",
    },
    {
        "id": "minimaxai/minimax-m3",
        "name": "MiniMax M3 Vision (NVIDIA NIM)",
        "provider": "MiniMax",
    },
    {
        "id": "meta/muse-glimmer-30b",
        "name": "Meta Muse Glimmer 30B (NVIDIA NIM)",
        "provider": "Meta",
    },
    {
        "id": "google/diffusiongemma-26b-a4b-it",
        "name": "Google DiffusionGemma 26B A4B IT (NVIDIA NIM)",
        "provider": "Google",
    },
    {
        "id": "google/gemma-4-31b-it",
        "name": "Google Gemma 4 31B IT (NVIDIA NIM)",
        "provider": "Google",
    },
    {
        "id": "stepfun-ai/step-3.7-flash",
        "name": "StepFun Step 3.7 Flash (NVIDIA NIM)",
        "provider": "StepFun",
    },
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "name": "NVIDIA Nemotron-3 Nano Omni 30B A3B Reasoning (NVIDIA NIM)",
        "provider": "NVIDIA",
    },
]

DEFAULT_NIM_MODEL = "meta/llama-3.2-11b-vision-instruct"

# System prompt for image analysis with rich scene classification & bold high-impact styling
ANALYSIS_SYSTEM_PROMPT = """You are an elite master colorist and art director.
Analyze the photo in detail, recognize its genre, and generate BOLD, NOTICEABLE, HIGH-IMPACT, VIBRANT and CINEMATIC color grading and tone adjustments (avoid timid or barely visible tweaks; photographers want rich depth, crisp contrast, and striking color harmony).

Return ONLY a valid raw JSON object with the following structure (no markdown, no code block backticks):

{
    "scene": "portrait|group_portrait|wedding|fashion|baby_kids|landscape|seascape|sunset|cityscape|architecture|interior|street|documentary|night|astro|food|product|macro|wildlife|sports|automotive|vintage|black_and_white|concert|aerial|snow",
    "confidence": 0.0-1.0,
    "adjustments": {
        "exposure": float (-2.0 to 2.0, bold correction),
        "contrast": integer (15 to 45 for punchy contrast),
        "highlights": integer (-30 to -70 for deep highlight recovery),
        "shadows": integer (20 to 60 for clean shadow lift),
        "whites": integer (10 to 35),
        "blacks": integer (-10 to -35),
        "texture": integer (-15 to 30),
        "clarity": integer (10 to 30),
        "dehaze": integer (8 to 25),
        "vibrance": integer (18 to 45),
        "saturation": integer (-10 to 25),
        "sharpness": integer (45 to 80),
        "luminance_smoothing": integer (0 to 60),
        "color_noise_reduction": integer (25),
        "vignette": integer (-20 to 10),
        "grain": integer (0 to 30),
        "hsl": {
            "red": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "orange": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "yellow": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "green": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "aqua": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "blue": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "purple": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100},
            "magenta": {"hue": -100 to 100, "saturation": -100 to 100, "luminance": -100 to 100}
        }
    },
    "color_grading": {
        "shadows": {"hue": 0-360, "saturation": 15-35, "lum": -30 to 30},
        "midtones": {"hue": 0-360, "saturation": 10-25, "lum": -20 to 20},
        "highlights": {"hue": 0-360, "saturation": 18-40, "lum": -20 to 20},
        "blending": 40-70,
        "balance": -30 to 30
    },
    "analysis_notes": "Detailed description of lighting, mood, color harmony, and subject"
}

Classification Criteria:
- portrait: Individual portrait of an adult or model
- group_portrait: Group photo, family, team, graduation, crowd of people
- wedding: Wedding ceremony, bride, groom, reception, romantic couple photoshoot
- fashion: Fashion editorial, lookbook, stylish outfit, studio modeling
- baby_kids: Baby, newborn, toddler, children
- landscape: Nature landscape, mountains, hills, valley, countryside, forest
- seascape: Ocean, sea, beach, waves, coast, water shore
- sunset: Sunset, sunrise, golden hour, twilight, dawn/dusk sky
- cityscape: Urban city view, skyline, tall buildings panorama
- architecture: Architecture details, building structures, facades, historical monuments
- interior: Indoor spaces, room decor, hotel/cafe interior, real estate interior
- street: Street photography, urban daily life, candid moments in public
- documentary: Photojournalism, cultural festival, events, reportage
- night: Night scene, low light, city night ambiance, dark background
- astro: Astrophotography, Milky Way, night sky, stars, aurora
- food: Food, culinary dishes, beverages, bakery, restaurant food
- product: Commercial product, e-commerce, packshot, jewelry, cosmetics, objects
- macro: Extreme close-up of flowers, insects, water droplets, textures
- wildlife: Animals in nature, pets (dogs, cats), birds, safari
- sports: Sports, athletes, motion, action, racing, fitness
- automotive: Cars, motorcycles, vehicles, automotive beauty shots
- vintage: Retro style, nostalgic film look, warm faded aesthetic
- black_and_white: Artistic monochrome, black & white fine art
- concert: Concert, stage live performance, colorful dramatic stage lights
- aerial: Drone, aerial view from high above, bird's eye perspective
- snow: Winter snow scene, ice, frost, foggy winter landscape

Rules:
- Select the most precise scene category matching the primary subject
- Keep adjustment values tasteful and photorealistic
- Output ONLY the raw JSON object"""


class CloudAPIClient:
    """
    Client for NVIDIA NIM vision AI analysis.
    Supports multiple models with automatic fallback.
    """

    def __init__(self, api_key: str, preferred_model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY", "")
        self.preferred_model = preferred_model or DEFAULT_NIM_MODEL
        self._available = bool(self.api_key)
        self._request_count = 0
        self._error_count = 0

    def test_connection(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Test API connection with a lightweight ping request.
        """
        if not self.api_key:
            return {
                "status": "error",
                "error": "Chưa nhập API Key. Vui lòng nhập API Key trong Cài đặt.",
                "code": 400
            }

        target_model = model or self.preferred_model
        is_kilo = (
            target_model in ["thinkingmachines/inkling:free", "stepfun/step-3.7-flash:free", "thinkingmachines/inkling-small:free"]
            or "thinkingmachines/" in target_model
            or (isinstance(self.api_key, str) and self.api_key.startswith("kilo-"))
        )
        is_openrouter = (
            not is_kilo
            and (
                target_model == "google/gemma-4-31b-it:free"
                or ":free" in target_model
                or (isinstance(self.api_key, str) and (self.api_key.startswith("sk-or-") or self.api_key.startswith("sk-")))
            )
        )

        if is_kilo:
            api_url = KILO_CODE_API_URL
            provider_name = "Kilo Code"
        elif is_openrouter:
            api_url = OPENROUTER_API_URL
            provider_name = "OpenRouter"
            if target_model == "meta/llama-3.2-11b-vision-instruct":
                target_model = "meta-llama/llama-3.2-11b-vision-instruct"
        else:
            api_url = NVIDIA_NIM_API_URL
            provider_name = "NVIDIA NIM"

        start_time = time.time()

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            if is_openrouter or is_kilo:
                headers["HTTP-Referer"] = "https://github.com/cradzz/AIthleewPro"
                headers["X-Title"] = "AIthleewPro"

            payload = {
                "model": target_model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, reply with OK."
                    }
                ],
                "max_tokens": 5,
                "temperature": 0.1,
            }

            resp = requests.post(api_url, headers=headers, json=payload, timeout=12)
            latency_ms = int((time.time() - start_time) * 1000)

            if resp.status_code == 200:
                return {
                    "status": "ok",
                    "latency_ms": latency_ms,
                    "model": target_model,
                    "provider": provider_name,
                    "message": f"Kết nối thành công tới {target_model} qua {provider_name} ({latency_ms}ms)!"
                }
            elif resp.status_code == 401:
                return {
                    "status": "error",
                    "error": f"API Key {provider_name} không hợp lệ hoặc đã hết hạn (401 Unauthorized).",
                    "code": 401
                }
            elif resp.status_code == 403:
                return {
                    "status": "error",
                    "error": f"API Key không có quyền truy cập mô hình này trên {provider_name} (403 Forbidden).",
                    "code": 403
                }
            elif resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Mô hình '{target_model}' không tìm thấy trên {provider_name} (404 Not Found).",
                    "code": 404
                }
            else:
                return {
                    "status": "error",
                    "error": f"{provider_name} HTTP {resp.status_code}: {resp.text[:200]}",
                    "code": resp.status_code
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Quá thời gian kết nối (Timeout sau 12s) tới {provider_name}.",
                "code": 408
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Lỗi kết nối tới {provider_name}: {str(e)}",
                "code": 500
            }

    def is_available(self) -> bool:
        """Check if the cloud client is available and functional."""
        return self._available and bool(self.api_key)

    def fetch_available_models(self) -> List[Dict[str, str]]:
        """Fetch list of available models from NVIDIA NIM."""
        if not self.is_available():
            return NVIDIA_NIM_VISION_MODELS

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            resp = requests.get(NVIDIA_NIM_MODELS_URL, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models_data = data.get("data", [])

                vision_keywords = ["vision", "vl", "pixtral", "neva", "vila", "multimodal", "image"]
                found_models = []
                found_ids = set()

                for m in models_data:
                    m_id = m.get("id", "")
                    if any(kw in m_id.lower() for kw in vision_keywords):
                        found_models.append({
                            "id": m_id,
                            "name": f"{m_id} (NVIDIA NIM)",
                            "provider": m.get("owned_by", "NVIDIA NIM"),
                        })
                        found_ids.add(m_id)

                # Append any default vision models not returned by API
                for default_m in NVIDIA_NIM_VISION_MODELS:
                    if default_m["id"] not in found_ids:
                        found_models.append(default_m)

                if found_models:
                    return found_models
        except Exception as e:
            logger.warning(f"Could not fetch models dynamically from NVIDIA NIM: {e}")

        return NVIDIA_NIM_VISION_MODELS

    def call_chat_vision(
        self,
        prompt: str,
        image_path: str,
        model: Optional[str] = None,
        timeout: int = 15000,
        system_prompt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a general chat prompt with an image to Cloud Vision AI and parse JSON response.
        """
        if not self.is_available() or not os.path.exists(image_path):
            return None

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read image for vision chat: {e}")
            return None

        target_model = model or self.preferred_model
        sys_p = system_prompt or "You are an expert AI photography judge. Return strictly valid raw JSON without markdown formatting."
        return self._try_model(target_model, image_data, prompt, timeout, system_prompt=sys_p)

    def chat_edit(self, image_path: str, prompt: str, timeout: int = 45000) -> Optional[Dict]:
        """
        Chat with AI to generate customized Lightroom develop adjustments from a user prompt.
        """
        if not self.is_available():
            logger.warning("Cloud Vision AI not available (no API key)")
            return None

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read image for chat edit: {e}")
            return None

        system_prompt = """You are an elite master photo editor, colorist, and Lightroom expert.
The user provides a photo and a custom creative editing instruction or prompt (in Vietnamese or English).
Analyze the photo and generate the exact Lightroom develop parameters to achieve ONLY the user's requested style, mood, color palette, or corrections.

CRITICAL INSTRUCTIONS:
1. STRICTLY DO NOT modify White Balance (Temperature or Tint) — leave them completely untouched (set temperature and tint to null). Keep White Balance untouched so the photographer's camera WB is preserved.
2. Only modify the specific parameters that are directly relevant to fulfilling the user's request (e.g. Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Texture, Clarity, Dehaze, Vibrance, Saturation, HSL, Color Grading).

Return ONLY a valid raw JSON object (strictly no markdown formatting, no code block backticks):
{
    "summary": "Short Vietnamese summary of what changes were made according to the user request (e.g. 'Hạ Highlight -30, tăng Shadow +25, tăng Vibrance +18 và chỉnh dải màu theo yêu cầu')",
    "intent": "Brief analysis of the user prompt",
    "adjustments": {
        "exposure": float (-3.0 to 3.0, 0.0 is unchanged),
        "contrast": integer (-100 to 100),
        "highlights": integer (-100 to 100),
        "shadows": integer (-100 to 100),
        "whites": integer (-100 to 100),
        "blacks": integer (-100 to 100),
        "texture": integer (-100 to 100),
        "clarity": integer (-100 to 100),
        "dehaze": integer (-100 to 100),
        "vibrance": integer (-100 to 100),
        "saturation": integer (-100 to 100),
        "sharpness": integer (0 to 150),
        "luminance_smoothing": integer (0 to 100),
        "color_noise_reduction": integer (0 to 100),
        "hsl": {
            "hue": { "red": 0, "orange": 0, "yellow": 0, "green": 0, "aqua": 0, "blue": 0, "purple": 0, "magenta": 0 },
            "saturation": { "red": 0, "orange": 0, "yellow": 0, "green": 0, "aqua": 0, "blue": 0, "purple": 0, "magenta": 0 },
            "luminance": { "red": 0, "orange": 0, "yellow": 0, "green": 0, "aqua": 0, "blue": 0, "purple": 0, "magenta": 0 }
        },
        "color_grade": {
            "shadows": { "hue": 0, "sat": 0, "lum": 0 },
            "midtones": { "hue": 0, "sat": 0, "lum": 0 },
            "highlights": { "hue": 0, "sat": 0, "lum": 0 },
            "balance": 0
        }
    }
}"""

        user_content = f"User Editing Request: {prompt}\n\nPlease analyze this image and output the exact Lightroom adjustment JSON that fulfills my request without touching White Balance."
        
        target_model = self.preferred_model or DEFAULT_NIM_MODEL
        logger.info(f"Executing Chat Edit with model: {target_model}")
        
        result = self._try_model(target_model, image_data, user_content, timeout, system_prompt=system_prompt)
        if result:
            result["model_used"] = target_model
            # Tự động loại bỏ hoàn toàn White Balance khỏi adjustments
            if isinstance(result.get("adjustments"), dict):
                adj = result["adjustments"]
                adj.pop("temperature", None)
                adj.pop("tint", None)
                adj.pop("target_kelvin", None)
                adj.pop("relative_temp", None)
                adj.pop("relative_tint", None)
                adj.pop("wb", None)
                adj.pop("WhiteBalance", None)
            return result
        return None

    def analyze(self, image_path: str, mode: str = "full", 
                timeout: int = 45000, 
                photometric_data: Optional[Dict] = None, 
                intensity_level: str = "normal") -> Optional[Dict]:
        """
        Analyze an image with Cloud Vision AI.

        Args:
            image_path: Path to the image file
            mode: Analysis mode ('full', 'quick', 'color_only')
            timeout: Request timeout in milliseconds
            photometric_data: Histogram and dynamic range metrics from Traditional CV
            intensity_level: Color intervention strength ('subtle', 'normal', 'strong', 'extreme')

        Returns:
            Dictionary with analysis results or None on failure
        """
        if not self.is_available():
            logger.warning("Cloud Vision AI not available (no API key)")
            return None

        # Encode image as base64
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read image: {e}")
            return None

        user_prompt = self._build_prompt(mode, photometric_data, intensity_level)

        is_kilo = (
            self.preferred_model in ["thinkingmachines/inkling:free", "stepfun/step-3.7-flash:free", "thinkingmachines/inkling-small:free"]
            or "thinkingmachines/" in self.preferred_model
            or (isinstance(self.api_key, str) and self.api_key.startswith("kilo-"))
        )
        is_openrouter = (
            not is_kilo
            and (
                self.preferred_model == "google/gemma-4-31b-it:free"
                or ":free" in self.preferred_model
                or (isinstance(self.api_key, str) and (self.api_key.startswith("sk-or-") or self.api_key.startswith("sk-")))
            )
        )

        target_model = self.preferred_model or DEFAULT_NIM_MODEL
        logger.info(f"Executing Cloud Vision AI strictly with selected model: {target_model}")

        result = self._try_model(target_model, image_data, user_prompt, timeout)
        if result:
            if is_kilo or "thinkingmachines" in target_model:
                prov_tag = "Kilo Code"
            elif is_openrouter or ":free" in target_model:
                prov_tag = "OpenRouter"
            else:
                prov_tag = "NVIDIA NIM"
            result["model_used"] = f"{prov_tag} ({target_model})"
            return result

        logger.error(f"Cloud Vision model '{target_model}' analysis failed.")
        return None

    def _try_model(self, model: str, image_data: str, prompt: str, timeout: int, system_prompt: Optional[str] = None) -> Optional[Dict]:
        """Try analysis with a specific Cloud Vision AI model (NVIDIA NIM, Kilo Code, or OpenRouter)."""
        try:
            self._request_count += 1

            target_model = model
            is_kilo = (
                target_model in ["thinkingmachines/inkling:free", "stepfun/step-3.7-flash:free", "thinkingmachines/inkling-small:free"]
                or "thinkingmachines/" in target_model
                or (isinstance(self.api_key, str) and self.api_key.startswith("kilo-"))
            )
            is_openrouter = (
                not is_kilo
                and (
                    target_model == "google/gemma-4-31b-it:free"
                    or ":free" in target_model
                    or (isinstance(self.api_key, str) and (self.api_key.startswith("sk-or-") or self.api_key.startswith("sk-")))
                )
            )

            if is_kilo:
                api_url = KILO_CODE_API_URL
                provider_name = "Kilo Code"
            elif is_openrouter:
                api_url = OPENROUTER_API_URL
                provider_name = "OpenRouter"
                if target_model == "meta/llama-3.2-11b-vision-instruct":
                    target_model = "meta-llama/llama-3.2-11b-vision-instruct"
            else:
                api_url = NVIDIA_NIM_API_URL
                provider_name = "NVIDIA NIM"

            payload = {
                "model": target_model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt or ANALYSIS_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                },
                            },
                        ],
                    },
                ],
                "max_tokens": 1024,
                "temperature": 0.2,
                "top_p": 0.7,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            if is_openrouter or is_kilo:
                headers["HTTP-Referer"] = "https://github.com/cradzz/AIthleewPro"
                headers["X-Title"] = "AIthleewPro"

            logger.info(f"Sending request to {provider_name} with model: {target_model}")

            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=timeout / 1000,
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                result = self._parse_response(content)
                if result:
                    logger.info(f"NVIDIA NIM analysis successful with {model}")
                    return result
                else:
                    logger.warning(f"Failed to parse JSON response from {model}")
                    return None

            elif response.status_code == 429:
                logger.warning(f"Rate limited by NVIDIA NIM ({model}), trying fallback...")
                return None

            elif response.status_code == 401 or response.status_code == 403:
                logger.error(f"Authentication error with NVIDIA NIM: {response.text[:200]}")
                return None

            else:
                logger.warning(f"NVIDIA NIM model {model} returned status {response.status_code}: {response.text[:200]}")
                return None

        except requests.Timeout:
            logger.warning(f"Timeout with NVIDIA NIM model {model}")
        except requests.ConnectionError:
            logger.warning(f"Connection error with NVIDIA NIM model {model}")
        except Exception as e:
            logger.error(f"Error with NVIDIA NIM model {model}: {e}")
            self._error_count += 1

        return None

    def _build_prompt(self, mode: str, photometric_data: Optional[Dict] = None, intensity_level: str = "normal") -> str:
        """Build the user prompt based on analysis mode, physical histogram readings, and requested color grading intensity."""
        prompts = {
            "full": "Analyze this photo comprehensively. Identify the scene, lighting conditions, and recommend precise Lightroom adjustment values for tone, presence, and color grading. Return ONLY raw JSON.",
            "quick": "Quick analysis: Analyze this photo and provide key Lightroom develop adjustments. Return ONLY raw JSON.",
            "color_only": "Focus only on color grading. Analyze color harmony and recommend Color Grading (Shadows, Midtones, Highlights) and White Balance. Return ONLY raw JSON.",
        }
        base_prompt = prompts.get(mode, prompts["full"])

        # Intensity guidelines for AI parameter generation
        intensity_instructions = {
            "subtle": (
                "\n[Mức độ can thiệp màu: NHẸ / SUBTLE]\n"
                "- Yêu cầu: Tinh chỉnh nhẹ nhàng, giữ vẻ đẹp mộc mạc và chân thực của ảnh gốc.\n"
                "- Độ tương phản dịu (Contrast: 8-20), bão hòa & độ rực nhẹ (Vibrance: 5-18, Saturation: -5 đến 10).\n"
                "- Color Grading độ bão hòa thấp (5-15), độ lệch dải màu HSL tinh tế (trong phạm vi ±15).\n"
                "- Giữ tone da tự nhiên tuyệt đối, không gây bết màu hay ám màu nặng."
            ),
            "normal": (
                "\n[Mức độ can thiệp màu: BÌNH THƯỜNG / NORMAL (CÂN BẰNG)]\n"
                "- Yêu cầu: Phong cách thương mại chuẩn mực, màu sắc tươi sáng, trong trẻo và có chiều sâu.\n"
                "- Độ tương phản chuẩn (Contrast: 15-35), bão hòa & độ rực hài hòa (Vibrance: 15-35, Saturation: 0 đến 20).\n"
                "- Color Grading cân đối (Saturation: 15-30), dải màu HSL chuẩn mực (trong phạm vi ±35)."
            ),
            "strong": (
                "\n[Mức độ can thiệp màu: MẠNH / STRONG (ĐẬM ĐÀ)]\n"
                "- Yêu cầu: Màu sắc ấn tượng, tương phản mạnh, phân tách màu sắc điện ảnh rõ rệt.\n"
                "- Độ tương phản cao (Contrast: 30-55), bão hòa & độ rực đậm đà (Vibrance: 28-55, Saturation: 10 đến 35).\n"
                "- Color Grading rõ nét (Saturation: 25-45), dải màu HSL chuyển tone rõ rệt (trong phạm vi ±60)."
            ),
            "extreme": (
                "\n[Mức độ can thiệp màu: CỰC MẠNH / EXTREME (ĐIỆN ẢNH ĐỘT PHÁ)]\n"
                "- Yêu cầu: Phong cách nghệ thuật mạnh mẽ, tương phản kịch tính, độ bão hòa cao và phối màu điện ảnh đậm chất Cinematic.\n"
                "- Độ tương phản rất cao (Contrast: 45-75), dải sáng phân khối sâu, độ rực rỡ mạnh (Vibrance: 40-70, Saturation: 20 đến 45).\n"
                "- Color Grading cường độ cao (Saturation: 40-65), dải màu HSL can thiệp mạnh mẽ (trong phạm vi ±85)."
            ),
        }
        base_prompt += intensity_instructions.get(intensity_level, intensity_instructions["normal"])

        if photometric_data and isinstance(photometric_data, dict):
            mean_luma = photometric_data.get("mean_luminance_pct", 46.0)
            dr_ev = photometric_data.get("dynamic_range_ev", 8.0)
            rec_ev = photometric_data.get("recommended_ev", 0.0)
            hl_clip = photometric_data.get("highlight_clipping", 0.0)
            sh_clip = photometric_data.get("shadow_clipping", 0.0)
            skin_luma = photometric_data.get("skin_luminance_pct")

            metering_info = (
                f"\n[Physical Histogram Metering: Mean Luma: {mean_luma}%, DR: {dr_ev} EV, "
                f"Calculated Exposure Base: {rec_ev:+.2f} EV, Highlights Clipping: {hl_clip}%, "
                f"Shadows Clipping: {sh_clip}%"
            )
            if skin_luma is not None:
                metering_info += f", Skin Luma: {skin_luma}%"
            metering_info += ". Use this histogram data to calibrate Exposure and Tone accurately.]"
            base_prompt += metering_info

        return base_prompt

    def _parse_response(self, content: str) -> Optional[Dict]:
        """Parse JSON from the AI response."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try markdown code block
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find outermost JSON object in text
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse JSON from response: {content[:200]}")
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "available": self.is_available(),
            "preferred_model": self.preferred_model,
        }

