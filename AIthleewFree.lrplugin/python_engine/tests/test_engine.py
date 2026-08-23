#!/usr/bin/env python3
"""
LR Auto Color Pro - Test Suite
Tests for Cloud Vision AI engine components.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTraditionalCV(unittest.TestCase):
    """Tests for TraditionalCV analysis algorithms."""

    def setUp(self):
        from services.traditional_cv import TraditionalCV
        self.cv = TraditionalCV()
        self.test_image = self._create_test_image()

    def _create_test_image(self):
        """Create a test image file."""
        try:
            from PIL import Image

            img = np.zeros((100, 100, 3), dtype=np.uint8)
            img[:, :, 0] = 180  # R
            img[:, :, 1] = 120  # G
            img[:, :, 2] = 100  # B

            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            pil_img = Image.fromarray(img)
            pil_img.save(temp_file.name, "JPEG")
            return temp_file.name
        except ImportError:
            return None

    def tearDown(self):
        if self.test_image and os.path.exists(self.test_image):
            os.unlink(self.test_image)

    def test_load_image(self):
        """Test image loading."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        self.assertIsNotNone(img)
        self.assertEqual(img.shape[2], 3)

    def test_white_balance(self):
        """Test white balance estimation."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._estimate_white_balance_combined(img)

        self.assertIn("temp", result)
        self.assertIn("tint", result)
        self.assertIn("confidence", result)

    def test_tone_analysis(self):
        """Test tone analysis."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._analyze_tone_enhanced(img)

        self.assertIn("exposure_adjustment", result)
        self.assertIn("contrast", result)

    def test_color_analysis(self):
        """Test color analysis."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._analyze_colors_enhanced(img)

        self.assertIn("dominant_colors", result)
        self.assertIn("warmth", result)

    def test_hsl_analysis(self):
        """Test HSL 8-channel analysis."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._analyze_hsl_channels(img)

        self.assertIsInstance(result, dict)
        self.assertIn("orange", result)
        self.assertIn("green", result)
        self.assertIn("blue", result)


class TestCloudAPIClient(unittest.TestCase):
    """Tests for the Cloud API client."""

    def setUp(self):
        from services.cloud_client import CloudAPIClient

        self.client = CloudAPIClient(api_key="test_key_12345")
        self.empty_client = CloudAPIClient(api_key="")

    def test_is_available(self):
        """Test availability check."""
        self.assertTrue(self.client.is_available())
        self.assertFalse(self.empty_client.is_available())

    def test_build_prompt(self):
        """Test prompt building."""
        full_prompt = self.client._build_prompt("full")
        self.assertIn("comprehensively", full_prompt)

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        json_str = '{"scene": "portrait", "confidence": 0.9, "analysis_notes": "Test photo"}'
        result = self.client._parse_response(json_str)

        self.assertIsNotNone(result)
        self.assertEqual(result["scene"], "portrait")

    def test_parse_response_markdown_json(self):
        """Test parsing JSON from markdown code block."""
        markdown = "```json\n{\"scene\": \"landscape\", \"confidence\": 0.85}\n```"
        result = self.client._parse_response(markdown)

        self.assertIsNotNone(result)
        self.assertEqual(result["scene"], "landscape")

    def test_get_stats(self):
        """Test statistics reporting."""
        stats = self.client.get_stats()
        self.assertIn("available", stats)


class TestAnalysisPipeline(unittest.TestCase):
    """Tests for AnalysisPipeline."""

    def setUp(self):
        from services.pipeline import AnalysisPipeline

        self.cloud_client = MagicMock()
        self.cloud_client.is_available.return_value = True
        self.cloud_client.analyze.return_value = {
            "scene": "portrait",
            "confidence": 0.95,
            "adjustments": {
                "exposure": 0.15,
                "contrast": 8,
                "highlights": -15,
                "shadows": 10,
            },
            "color_grading": {
                "shadows": {"hue": 220, "saturation": 8},
                "midtones": {"hue": 35, "saturation": 5},
                "highlights": {"hue": 45, "saturation": 10},
            },
            "editing_rationale": [
                "Ánh sáng: Tăng nhẹ Exposure +0.15",
                "Chi tiết: Giữ độ mịn màng da mặt",
                "Color Grading: Teal and orange",
                "HSL: Nâng sáng da mặt"
            ]
        }

        self.traditional_cv = MagicMock()
        self.traditional_cv.analyze.return_value = {
            "white_balance": {"temp": 0, "tint": 0, "confidence": 0.5},
            "tone_analysis": {"exposure_adjustment": 0.05, "contrast": 3},
            "color_analysis": {"dominant_colors": []},
            "scene_heuristics": {"possible_scenes": []},
            "histogram": {},
            "hsl_analysis": {
                "orange": {"hue": 0, "saturation": -5, "luminance": 8},
                "green": {"hue": 12, "saturation": -5, "luminance": 5},
                "blue": {"hue": 0, "saturation": 10, "luminance": -8},
            }
        }

        self.pipeline = AnalysisPipeline(
            cloud_client=self.cloud_client,
            traditional_cv=self.traditional_cv,
        )

    def test_pipeline_status(self):
        """Test pipeline status reporting."""
        status = self.pipeline.get_status()
        self.assertEqual(status["status"], "online")
        self.assertTrue(status["cloud_available"])

    def test_analyze(self):
        """Test cloud vision analysis."""
        test_image = self._create_temp_image()
        if test_image is None:
            self.skipTest("Pillow not available")

        result = self.pipeline.analyze(test_image, use_cloud=True)

        self.assertIn("scene", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["scene"], "portrait")
        self.assertIn("adjustments", result)
        self.assertIn("hsl", result["adjustments"])
        self.assertIn("histogram_analysis", result)

        os.unlink(test_image)

    def _create_temp_image(self):
        """Create a temporary test image."""
        try:
            from PIL import Image

            img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            Image.fromarray(img).save(temp_file.name, "JPEG")
            return temp_file.name
        except ImportError:
            return None

    def test_get_presets(self):
        """Test preset retrieval."""
        presets = self.pipeline.get_presets("all")
        self.assertIsInstance(presets, dict)

    def test_clear_cache(self):
        """Test cache clearing."""
        self.pipeline._cache["test"] = "value"
        self.pipeline.clear_cache()
        self.assertEqual(len(self.pipeline._cache), 0)


class TestProtocol(unittest.TestCase):
    """Test the Lua-Python communication protocol."""

    def test_request_format(self):
        """Test request JSON format."""
        request = {
            "id": "req_001",
            "action": "analyze",
            "params": {
                "image_path": "/tmp/test.jpg",
                "mode": "full",
                "use_cloud": True,
            },
        }

        json_str = json.dumps(request)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["action"], "analyze")
        self.assertIn("params", parsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
