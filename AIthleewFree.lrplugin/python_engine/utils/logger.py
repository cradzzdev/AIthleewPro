"""
LR Auto Color Pro - Python Utilities
Logging and helper utilities for the AI engine.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level: str = "DEBUG"):
    """
    Setup logging for the AI engine.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "ai_engine.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] [%(name)-25s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        "[%(levelname)-8s] %(name)s: %(message)s"
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))

    # Clear existing handlers
    root_logger.handlers.clear()

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logging.info("Logging initialized at level: %s", level)


def get_engine_version() -> str:
    """Get the AI engine version."""
    return "1.0.0"


def check_dependencies() -> dict:
    """
    Check which dependencies are available.

    Returns:
        Dictionary with dependency availability status
    """
    deps = {}

    try:
        import numpy
        deps["numpy"] = numpy.__version__
    except ImportError:
        deps["numpy"] = None

    try:
        import cv2
        deps["opencv"] = cv2.__version__
    except ImportError:
        deps["opencv"] = None

    try:
        from PIL import Image
        deps["pillow"] = Image.__version__ if hasattr(Image, '__version__') else "available"
    except ImportError:
        deps["pillow"] = None

    try:
        import onnxruntime
        deps["onnxruntime"] = onnxruntime.__version__
    except ImportError:
        deps["onnxruntime"] = None

    try:
        import requests
        deps["requests"] = requests.__version__
    except ImportError:
        deps["requests"] = None

    return deps


def ensure_directory(path: str) -> str:
    """Ensure a directory exists, create if needed."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return path
