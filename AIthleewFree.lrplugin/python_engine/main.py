#!/usr/bin/env python3
"""
LR Auto Color Pro - Python Cloud Vision AI Engine (NVIDIA NIM)
Main entry point for the AI analysis and culling engine.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.pipeline import AnalysisPipeline
from services.cloud_client import CloudAPIClient
from services.traditional_cv import TraditionalCV
from services.culling import CullingEngine
from utils.logger import setup_logging

import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder to safely serialize NumPy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super().default(obj)


def analyze_single_image(image_path: str, output_path: str, mode: str = "full",
                         use_cloud: bool = True, scene_hint: str = None,
                         cloud_model: Optional[str] = None,
                         api_key: Optional[str] = None,
                         intensity: str = "normal") -> bool:
    """
    Analyze a single image using Cloud Vision AI and write results to a JSON file.
    """
    setup_logging("INFO")
    logging.info(f"Analyzing image: {image_path} (Intensity: {intensity})")

    if not os.path.exists(image_path):
        logging.error(f"Image not found: {image_path}")
        return False

    active_key = (
        api_key
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVIDIA_NIM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("KILO_API_KEY")
        or os.environ.get("KILO_CODE_API_KEY")
        or ""
    )
    cloud_client = CloudAPIClient(
        api_key=active_key,
        preferred_model=cloud_model
    )
    traditional_cv = TraditionalCV()

    pipeline = AnalysisPipeline(
        cloud_client=cloud_client,
        traditional_cv=traditional_cv
    )

    try:
        result = pipeline.analyze(
            image_path=image_path,
            mode=mode,
            use_cloud=True,
            scene_hint=scene_hint,
            intensity_level=intensity
        )

        with open(output_path, "w") as f:
            json.dump(result, f, cls=NumpyEncoder, indent=2)

        logging.info(f"Analysis successful for: {image_path}")
        return True

    except Exception as e:
        logging.error(f"Analysis failed: {e}", exc_info=True)
        with open(output_path, "w") as f:
            json.dump({"status": "error", "error": str(e)}, f)
        return False


def cull_single_image(image_path: str, output_path: str, use_cloud: bool = True,
                       cloud_model: Optional[str] = None,
                       api_key: Optional[str] = None) -> bool:
    """
    Evaluate a single photo for quality culling (0-100 score).
    """
    setup_logging("INFO")
    logging.info(f"Culling evaluation for image: {image_path}")

    if not os.path.exists(image_path):
        logging.error(f"Image not found: {image_path}")
        return False

    active_key = (
        api_key
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVIDIA_NIM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("KILO_API_KEY")
        or os.environ.get("KILO_CODE_API_KEY")
        or ""
    )
    cloud_client = CloudAPIClient(
        api_key=active_key,
        preferred_model=cloud_model
    )
    culling_engine = CullingEngine()

    try:
        result = culling_engine.evaluate_photo(
            image_path=image_path,
            use_cloud=use_cloud,
            cloud_client=cloud_client,
            cloud_model=cloud_model
        )

        with open(output_path, "w") as f:
            json.dump({"status": "ok", "result": result}, f, cls=NumpyEncoder, indent=2)

        logging.info(f"Culling score: {result.get('total_score')} (verdict: {result.get('verdict')})")
        return True
    except Exception as e:
        logging.error(f"Culling failed: {e}", exc_info=True)
        with open(output_path, "w") as f:
            json.dump({"status": "error", "error": str(e)}, f)
        return False


def wb_single_image(image_path: str, output_path: str, is_raw: bool = False,
                    original_ext: Optional[str] = None,
                    current_temp: Optional[float] = None,
                    current_tint: Optional[float] = None,
                    cloud_model: Optional[str] = None,
                    api_key: Optional[str] = None) -> bool:
    """
    Analyze and determine neutral White Balance for an image.
    """
    setup_logging("INFO")
    logging.info(f"Analyzing White Balance for: {image_path} (is_raw={is_raw}, ext={original_ext}, cur_temp={current_temp}, cur_tint={current_tint})")

    if not os.path.exists(image_path):
        logging.error(f"Image not found: {image_path}")
        return False

    active_key = (
        api_key
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVIDIA_NIM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("KILO_API_KEY")
        or os.environ.get("KILO_CODE_API_KEY")
        or ""
    )
    cloud_client = CloudAPIClient(
        api_key=active_key,
        preferred_model=cloud_model
    )

    from services.white_balance import WhiteBalanceService
    wb_service = WhiteBalanceService(cloud_client=cloud_client)

    try:
        result = wb_service.evaluate_white_balance(
            image_path=image_path,
            is_raw=is_raw,
            original_ext=original_ext,
            current_temp=current_temp,
            current_tint=current_tint
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"status": "ok", "result": result}, f, cls=NumpyEncoder, indent=2, ensure_ascii=False)

        logging.info(f"White balance evaluated: Temp={result.get('temperature')}, Tint={result.get('tint')}")
        return True
    except Exception as e:
        logging.error(f"White balance analysis failed: {e}", exc_info=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "error": str(e)}, f, ensure_ascii=False)
        return False


def chat_edit_single_image(image_path: str, output_path: str, user_prompt: str,
                           cloud_model: Optional[str] = None,
                           api_key: Optional[str] = None) -> bool:
    """
    Execute AI chat edit on a single image and output Lightroom adjustments JSON.
    """
    setup_logging("INFO")
    logging.info(f"Chat edit for image: {image_path} with prompt: {user_prompt[:60]}...")

    if not os.path.exists(image_path):
        logging.error(f"Image not found: {image_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "error": f"Image not found: {image_path}"}, f, ensure_ascii=False)
        return False

    active_key = (
        api_key
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVIDIA_NIM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("KILO_API_KEY")
        or os.environ.get("KILO_CODE_API_KEY")
        or ""
    )
    cloud_client = CloudAPIClient(
        api_key=active_key,
        preferred_model=cloud_model
    )

    try:
        result = cloud_client.chat_edit(
            image_path=image_path,
            prompt=user_prompt
        )

        if result and "adjustments" in result:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"status": "ok", "result": result}, f, cls=NumpyEncoder, indent=2, ensure_ascii=False)
            logging.info(f"Chat edit successful: {result.get('summary')}")
            return True
        else:
            err_msg = "Không nhận được phản hồi chỉnh sửa hợp lệ từ mô hình AI"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"status": "error", "error": err_msg}, f, ensure_ascii=False)
            return False
    except Exception as e:
        logging.error(f"Chat edit failed: {e}", exc_info=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "error": str(e)}, f, ensure_ascii=False)
        return False


def test_connection_command(api_key: Optional[str] = None, model: Optional[str] = None,
                            output_path: Optional[str] = None) -> bool:
    """Test API connection and authentication."""
    setup_logging("INFO")
    key = (
        api_key
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVIDIA_NIM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("KILO_API_KEY")
        or os.environ.get("KILO_CODE_API_KEY")
        or ""
    )
    client = CloudAPIClient(api_key=key, preferred_model=model)
    result = client.test_connection(model=model)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    return result.get("status") == "ok"


def list_models_command(output_path: Optional[str] = None):
    """List available vision models from Cloud AI."""
    models = CloudAPIClient.list_available_vision_models()
    if output_path:
        with open(output_path, "w") as f:
            json.dump({"status": "ok", "models": models}, f, indent=2)
    print(json.dumps({"status": "ok", "models": models}, indent=2))
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LR Auto Color Pro Cloud Vision Engine (NVIDIA NIM)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze mode
    cli_parser = subparsers.add_parser("analyze", help="Analyze a single image")
    cli_parser.add_argument("image", help="Path to image file")
    cli_parser.add_argument("--output", required=True, help="Path to output JSON file")
    cli_parser.add_argument("--mode", default="full", choices=["quick", "full", "color_only"],
                           help="Analysis mode")
    cli_parser.add_argument("--use-cloud", action="store_true", default=True, help="Use Cloud Vision AI")
    cli_parser.add_argument("--cloud-model", default=None, help="Preferred Cloud Vision AI model")
    cli_parser.add_argument("--scene-hint", default=None, help="Scene type hint")
    cli_parser.add_argument("--api-key", default=None, help="API key")
    cli_parser.add_argument("--intensity", default="normal", choices=["subtle", "normal", "strong", "extreme"],
                           help="Color grading intervention intensity")

    # Chat Edit mode
    chat_parser = subparsers.add_parser("chat-edit", help="Chat with Vision AI to edit photo via natural language prompt")
    chat_parser.add_argument("image", help="Path to image preview file")
    chat_parser.add_argument("--output", required=True, help="Path to output JSON file")
    chat_parser.add_argument("--prompt", default=None, help="User editing prompt text")
    chat_parser.add_argument("--prompt-file", default=None, help="Path to text file containing user prompt")
    chat_parser.add_argument("--cloud-model", default=None, help="Preferred Cloud Vision AI model")
    chat_parser.add_argument("--api-key", default=None, help="API key")

    # Culling mode
    cull_parser = subparsers.add_parser("cull", help="Evaluate and score photo quality for culling")
    cull_parser.add_argument("image", help="Path to image file")
    cull_parser.add_argument("--output", required=True, help="Path to output JSON file")
    cull_parser.add_argument("--use-cloud", action="store_true", default=True, help="Use Cloud Vision AI")
    cull_parser.add_argument("--cloud-model", default=None, help="Preferred Cloud Vision AI model")
    cull_parser.add_argument("--api-key", default=None, help="API key")

    # White Balance mode
    wb_parser = subparsers.add_parser("wb", help="Analyze and recommend neutral White Balance")
    wb_parser.add_argument("image", help="Path to image file")
    wb_parser.add_argument("--output", required=True, help="Path to output JSON file")
    wb_parser.add_argument("--is-raw", action="store_true", default=False, help="Source photo is RAW format")
    wb_parser.add_argument("--original-ext", default=None, help="Source file extension (e.g. .cr3)")
    wb_parser.add_argument("--current-temp", type=float, default=None, help="Current Kelvin or relative temperature")
    wb_parser.add_argument("--current-tint", type=float, default=None, help="Current Tint")
    wb_parser.add_argument("--cloud-model", default=None, help="Preferred Cloud Vision AI model")
    wb_parser.add_argument("--api-key", default=None, help="API key")

    # Test connection mode
    test_parser = subparsers.add_parser("test-connection", help="Test API connection and key")
    test_parser.add_argument("--api-key", default=None, help="API key to test")
    test_parser.add_argument("--model", default=None, help="Model to test")
    test_parser.add_argument("--output", default=None, help="Path to output JSON file")

    # List models mode
    list_parser = subparsers.add_parser("list-models", help="List available vision models")
    list_parser.add_argument("--output", default=None, help="Path to output JSON file")

    # Tether FTP server mode
    tether_parser = subparsers.add_parser("tether", help="Start Tether FTP Server")
    tether_parser.add_argument("--port", type=int, default=2121, help="FTP Port")
    tether_parser.add_argument("--user", default="a7", help="FTP Username")
    tether_parser.add_argument("--pass", dest="password", default="12345678", help="FTP Password")
    tether_parser.add_argument("--output", default=None, help="Inbox directory")
    tether_parser.add_argument("--profile", default="sony_a7iv", help="Camera profile")

    args = parser.parse_args()

    if args.command == "analyze":
        success = analyze_single_image(
            image_path=args.image,
            output_path=args.output,
            mode=args.mode,
            use_cloud=True,
            scene_hint=args.scene_hint,
            cloud_model=args.cloud_model,
            api_key=args.api_key,
            intensity=getattr(args, "intensity", "normal")
        )
        sys.exit(0 if success else 1)
    elif args.command == "chat-edit":
        prompt_text = args.prompt or ""
        if args.prompt_file and os.path.exists(args.prompt_file):
            try:
                with open(args.prompt_file, "r", encoding="utf-8") as pf:
                    prompt_text = pf.read().strip()
            except Exception as e:
                logging.error(f"Failed to read prompt file: {e}")
        
        success = chat_edit_single_image(
            image_path=args.image,
            output_path=args.output,
            user_prompt=prompt_text,
            cloud_model=args.cloud_model,
            api_key=args.api_key
        )
        sys.exit(0 if success else 1)
    elif args.command == "cull":
        success = cull_single_image(
            image_path=args.image,
            output_path=args.output,
            use_cloud=True,
            cloud_model=args.cloud_model,
            api_key=args.api_key
        )
        sys.exit(0 if success else 1)
    elif args.command == "wb":
        success = wb_single_image(
            image_path=args.image,
            output_path=args.output,
            is_raw=args.is_raw,
            original_ext=args.original_ext,
            current_temp=args.current_temp,
            current_tint=args.current_tint,
            cloud_model=args.cloud_model,
            api_key=args.api_key
        )
        sys.exit(0 if success else 1)
    elif args.command == "test-connection":
        success = test_connection_command(api_key=args.api_key, model=args.model, output_path=args.output)
        sys.exit(0 if success else 1)
    elif args.command == "list-models":
        success = list_models_command(args.output)
        sys.exit(0 if success else 1)
    elif args.command == "tether":
        from tether.tether_manager import cmd_start
        cmd_start(port=args.port, username=args.user, password=args.password, camera=args.profile, output=args.output)
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
