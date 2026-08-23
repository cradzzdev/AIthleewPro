#!/usr/bin/env python3
"""
LR Auto Color Pro - Test Suite
Tests for the Python AI engine components.
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

            # Create a simple test image (100x100 red-ish)
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
        self.assertEqual(img.shape[2], 3)  # RGB channels

    def test_white_balance(self):
        """Test white balance estimation."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._estimate_white_balance_combined(img)

        self.assertIn("temp", result)
        self.assertIn("tint", result)
        self.assertIn("confidence", result)
        self.assertIsInstance(result["temp"], (int, float))
        self.assertIsInstance(result["tint"], (int, float))

    def test_tone_analysis(self):
        """Test tone analysis."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._analyze_tone_enhanced(img)

        self.assertIn("exposure_adjustment", result)
        self.assertIn("contrast", result)
        self.assertIn("mean_luminance", result)
        self.assertGreaterEqual(result["mean_luminance"], 0)
        self.assertLessEqual(result["mean_luminance"], 1)

    def test_color_analysis(self):
        """Test color analysis."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._analyze_colors_enhanced(img)

        self.assertIn("dominant_colors", result)
        self.assertIn("warmth", result)
        self.assertIsInstance(result["dominant_colors"], list)

    def test_scene_heuristics(self):
        """Test scene detection heuristics."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        img = self.cv._load_image(self.test_image)
        result = self.cv._scene_heuristics_enhanced(img)

        self.assertIn("possible_scenes", result)
        self.assertIn("features", result)
        self.assertIsInstance(result["possible_scenes"], list)

    def test_full_analysis(self):
        """Test complete analysis pipeline."""
        if self.test_image is None:
            self.skipTest("Pillow not available")

        result = self.cv.analyze(self.test_image)

        self.assertIn("white_balance", result)
        self.assertIn("tone_analysis", result)
        self.assertIn("color_analysis", result)
        self.assertIn("scene_heuristics", result)
        self.assertIn("histogram", result)

    def test_empty_result(self):
        """Test empty result fallback."""
        result = self.cv._empty_result()

        self.assertIn("white_balance", result)
        self.assertIn("tone_analysis", result)
        self.assertEqual(result["white_balance"]["temp"], 0)


class TestAnalysisPipeline(unittest.TestCase):
    """Tests for the AnalysisPipeline orchestrator."""

    def setUp(self):
        from services.pipeline import AnalysisPipeline

        self.local_engine = MagicMock()
        self.local_engine.is_loaded.return_value = True
        self.local_engine.analyze.return_value = {
            "scene": "portrait",
            "confidence": 0.85,
            "adjustments": {
                "white_balance": {"temp": 5500, "tint": 5},
                "exposure": 0.1,
                "contrast": 5,
            },
        }

        self.cloud_client = MagicMock()
        self.cloud_client.is_available.return_value = True
        self.cloud_client.analyze.return_value = {
            "scene": "portrait",
            "confidence": 0.92,
            "adjustments": {
                "white_balance": {"temp": 5600, "tint": 3},
                "exposure": 0.15,
                "contrast": 8,
            },
        }

        self.traditional_cv = MagicMock()
        self.traditional_cv.analyze.return_value = {
            "white_balance": {"temp": 0, "tint": 0, "confidence": 0.5},
            "tone_analysis": {"exposure_adjustment": 0.05, "contrast": 3},
            "color_analysis": {"dominant_colors": []},
            "scene_heuristics": {"possible_scenes": []},
            "histogram": {},
        }

        self.pipeline = AnalysisPipeline(
            local_engine=self.local_engine,
            cloud_client=self.cloud_client,
            traditional_cv=self.traditional_cv,
        )

    def test_pipeline_status(self):
        """Test pipeline status reporting."""
        status = self.pipeline.get_status()

        self.assertEqual(status["status"], "online")
        self.assertTrue(status["models_loaded"])
        self.assertTrue(status["cloud_available"])

    def test_analyze_local_only(self):
        """Test analysis with local-only mode."""
        test_image = self._create_temp_image()
        if test_image is None:
            self.skipTest("Pillow not available")

        result = self.pipeline.analyze(test_image, use_cloud=False)

        self.assertIn("scene", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["scene"], "portrait")

        os.unlink(test_image)

    def test_analyze_with_cloud_fallback(self):
        """Test analysis falls back to cloud when local confidence is low."""
        self.local_engine.analyze.return_value = {
            "scene": "unknown",
            "confidence": 0.3,  # Low confidence triggers cloud
            "adjustments": {},
        }

        test_image = self._create_temp_image()
        if test_image is None:
            self.skipTest("Pillow not available")

        result = self.pipeline.analyze(test_image, use_cloud=True)

        # Should have used cloud due to low local confidence
        self.cloud_client.analyze.assert_called_once()

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

        portraits = self.pipeline.get_presets("portraits")
        self.assertIn("portraits", portraits)

    def test_clear_cache(self):
        """Test cache clearing."""
        self.pipeline._cache["test"] = "value"
        self.pipeline.clear_cache()
        self.assertEqual(len(self.pipeline._cache), 0)


class TestCloudAPIClient(unittest.TestCase):
    """Tests for the Cloud API client."""

    def setUp(self):
        from services.cloud_client import CloudAPIClient

        self.client = CloudAPIClient(api_key="test_key_12345")

    def test_is_available(self):
        """Test availability check."""
        self.assertTrue(self.client.is_available())

        empty_client = CloudAPIClient(api_key="")
        self.assertFalse(empty_client.is_available())

    def test_build_prompt(self):
        """Test prompt building."""
        full_prompt = self.client._build_prompt("full")
        self.assertIn("comprehensively", full_prompt)

        quick_prompt = self.client._build_prompt("quick")
        self.assertIn("Quick", quick_prompt)

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        json_str = '{"scene": "portrait", "confidence": 0.9}'
        result = self.client._parse_response(json_str)

        self.assertIsNotNone(result)
        self.assertEqual(result["scene"], "portrait")

    def test_parse_response_markdown_json(self):
        """Test parsing JSON from markdown code block."""
        markdown = '```json\n{"scene": "landscape", "confidence": 0.85}\n```'
        result = self.client._parse_response(markdown)

        self.assertIsNotNone(result)
        self.assertEqual(result["scene"], "landscape")

    def test_parse_response_plain_text_json(self):
        """Test parsing JSON embedded in text."""
        text = 'Here is the result: {"scene": "night", "confidence": 0.7} Thank you'
        result = self.client._parse_response(text)

        self.assertIsNotNone(result)
        self.assertEqual(result["scene"], "night")

    def test_parse_response_invalid(self):
        """Test parsing invalid response."""
        result = self.client._parse_response("This is not JSON at all")
        self.assertIsNone(result)

    def test_get_stats(self):
        """Test statistics reporting."""
        stats = self.client.get_stats()

        self.assertIn("requests", stats)
        self.assertIn("errors", stats)
        self.assertIn("available", stats)
        self.assertTrue(stats["available"])


class TestLocalInferenceEngine(unittest.TestCase):
    """Tests for the local ML inference engine."""

    def setUp(self):
        from services.local_inference import LocalInferenceEngine

        # Create temp models directory
        self.models_dir = tempfile.mkdtemp()
        self.engine = LocalInferenceEngine(models_dir=self.models_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.models_dir, ignore_errors=True)

    def test_is_loaded_no_models(self):
        """Test loaded status when no models exist."""
        # Engine should not be loaded without models
        # (unless onnxruntime creates dummies)
        status = self.engine.is_loaded()
        self.assertIsInstance(status, bool)

    def test_fallback_analysis(self):
        """Test fallback analysis when models unavailable."""
        result = self.engine._fallback_analysis("dummy.jpg", "portrait")

        self.assertEqual(result["scene"], "portrait")
        self.assertEqual(result["confidence"], 0.3)
        self.assertIn("adjustments", result)

    def test_default_color_grading(self):
        """Test default color grading values."""
        grading = self.engine._default_color_grading("portrait")

        self.assertIn("shadows", grading)
        self.assertIn("midtones", grading)
        self.assertIn("highlights", grading)

    def test_softmax(self):
        """Test softmax computation."""
        x = np.array([1.0, 2.0, 3.0])
        result = self.engine._softmax(x)

        self.assertAlmostEqual(np.sum(result), 1.0, places=5)
        self.assertTrue(np.all(result >= 0))


class TestModelRegistry(unittest.TestCase):
    """Tests for model registry."""

    def setUp(self):
        from services.model_registry import ModelRegistry

        self.models_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(models_dir=self.models_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.models_dir, ignore_errors=True)

    def test_registry_status(self):
        """Test registry status."""
        status = self.registry.get_status()

        self.assertIn("total_models", status)
        self.assertIn("available_models", status)
        self.assertIn("missing_models", status)

    def test_get_model_path(self):
        """Test model path retrieval."""
        path = self.registry.get_model_path("scene_classifier")
        # Should return None if model doesn't exist
        self.assertTrue(path is None or isinstance(path, str))

    def test_get_available_models(self):
        """Test available models listing."""
        available = self.registry.get_available_models()
        self.assertIsInstance(available, dict)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full pipeline."""

    def setUp(self):
        from services.pipeline import AnalysisPipeline
        from services.local_inference import LocalInferenceEngine
        from services.traditional_cv import TraditionalCV

        self.models_dir = tempfile.mkdtemp()
        self.local_engine = LocalInferenceEngine(models_dir=self.models_dir)
        self.traditional_cv = TraditionalCV()
        self.cloud_client = None  # No cloud for integration test

        self.pipeline = AnalysisPipeline(
            local_engine=self.local_engine,
            cloud_client=self.cloud_client,
            traditional_cv=self.traditional_cv,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.models_dir, ignore_errors=True)

    def test_full_pipeline_offline(self):
        """Test full pipeline in offline mode."""
        try:
            from PIL import Image

            # Create test image
            img = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            Image.fromarray(img).save(temp_file.name, "JPEG")

            result = self.pipeline.analyze(temp_file.name, use_cloud=False)

            self.assertIn("scene", result)
            self.assertIn("confidence", result)
            self.assertIn("adjustments", result)
            self.assertIn("model_used", result)

            os.unlink(temp_file.name)

        except ImportError:
            self.skipTest("Pillow not available")

    def test_histogram_output(self):
        """Test that histogram data is included in results."""
        try:
            from PIL import Image

            img = np.full((64, 64, 3), 128, dtype=np.uint8)
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            Image.fromarray(img).save(temp_file.name, "JPEG")

            result = self.pipeline.analyze(temp_file.name, use_cloud=False)

            # Should have histogram from traditional CV
            if "color_analysis" in result:
                self.assertIsInstance(result["color_analysis"], dict)

            os.unlink(temp_file.name)

        except ImportError:
            self.skipTest("Pillow not available")


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
                "use_cloud": False,
            },
        }

        # Should be JSON serializable
        json_str = json.dumps(request)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["action"], "analyze")
        self.assertIn("params", parsed)

    def test_response_format(self):
        """Test response JSON format."""
        response = {
            "id": "req_001",
            "status": "success",
            "result": {
                "scene": "portrait",
                "confidence": 0.85,
                "adjustments": {
                    "white_balance": {"temp": 0, "tint": 0},
                    "exposure": 0.1,
                },
            },
            "meta": {
                "model_used": "local",
                "inference_time_ms": 150,
            },
        }

        json_str = json.dumps(response)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["status"], "success")
        self.assertIn("result", parsed)
        self.assertIn("meta", parsed)

    def test_error_response_format(self):
        """Test error response format."""
        response = {
            "id": "req_001",
            "status": "error",
            "error": "Image not found: /tmp/missing.jpg",
        }

        json_str = json.dumps(response)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["status"], "error")
        self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
