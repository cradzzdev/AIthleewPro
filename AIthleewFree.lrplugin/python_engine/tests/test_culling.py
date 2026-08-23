import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
import numpy as np
from PIL import Image
import tempfile
import json
from unittest.mock import MagicMock, patch

from services.culling import CullingEngine
from services.cloud_client import CloudAPIClient


class TestCullingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CullingEngine()
        self.temp_dir = tempfile.mkdtemp()
        self.client = CloudAPIClient(api_key="nvapi-test-key")

    def _create_sample_image(self, name: str) -> str:
        path = os.path.join(self.temp_dir, name)
        # Create patterned image with sharp edges
        arr = np.zeros((300, 300, 3), dtype=np.uint8)
        arr[::20, :, :] = 255
        arr[:, ::20, :] = 255
        Image.fromarray(arr).save(path, "JPEG")
        return path

    def test_pure_ai_culling_evaluation(self):
        img_path = self._create_sample_image("test_portrait.jpg")

        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "total_score": 94.0,
                        "sub_scores": {
                            "sharpness": 96.0,
                            "exposure": 92.0,
                            "expression": 95.0,
                            "composition": 93.0
                        },
                        "verdict": "keeper",
                        "reasons": [
                            "Chủ thể lấy nét cực kỳ sắc nét vào đôi mắt",
                            "Biểu cảm tươi cười tự nhiên",
                            "Ánh sáng ven mềm mại không bị cháy chi tiết"
                        ]
                    })
                }
            }]
        }

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_post.return_value = mock_resp

            res = self.engine.evaluate_photo(
                image_path=img_path,
                cloud_client=self.client
            )

            self.assertGreater(res["total_score"], 70.0)
            self.assertEqual(res["verdict"], "keeper")
            self.assertEqual(res["recommended_flag"], 1)
            self.assertIn(res["recommended_rating"], [4, 5])
            self.assertEqual(res["recommended_label"], "Green")
            self.assertIn("Vision AI", res["model_used"])

            # Verify base64 image was sent in request
            self.assertTrue(mock_post.called)
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs["json"]
            img_url = payload["messages"][1]["content"][1]["image_url"]["url"]
            self.assertTrue(img_url.startswith("data:image/jpeg;base64,"))

    def test_offline_fallback_culling(self):
        img_path = self._create_sample_image("test_offline.jpg")
        # Offline without client
        res = self.engine.evaluate_photo(
            image_path=img_path,
            cloud_client=None
        )
        self.assertIn("total_score", res)
        self.assertIn(res["verdict"], ["keeper", "acceptable", "reject"])
        self.assertIn(res["recommended_flag"], [1, 0, -1])
        self.assertIn(res["recommended_label"], ["Green", "Yellow", "Red"])
        self.assertIn("Computer Vision", res["model_used"])

    def tearDown(self):
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)


if __name__ == "__main__":
    unittest.main()

