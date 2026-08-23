import unittest
import os
import sys
import tempfile
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.white_balance import WhiteBalanceService


class TestWhiteBalanceService(unittest.TestCase):
    def setUp(self):
        self.service = WhiteBalanceService()
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = [180, 150, 120]  # Warm cast image
        pil_img = Image.fromarray(img)
        pil_img.save(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_raw_temperature(self):
        res = self.service.evaluate_white_balance(
            self.temp_file.name,
            is_raw=True,
            original_ext="cr3",
            current_temp=5600.0
        )
        self.assertTrue(res["is_raw"])
        self.assertIn("target_kelvin", res)
        self.assertGreaterEqual(res["target_kelvin"], 2000)
        self.assertLessEqual(res["target_kelvin"], 50000)
        self.assertEqual(res["temperature"], res["target_kelvin"])

    def test_non_raw_temperature(self):
        res = self.service.evaluate_white_balance(
            self.temp_file.name,
            is_raw=False,
            original_ext="jpg",
            current_temp=0.0
        )
        self.assertFalse(res["is_raw"])
        self.assertIn("relative_temp", res)
        self.assertGreaterEqual(res["relative_temp"], -100)
        self.assertLessEqual(res["relative_temp"], 100)
        self.assertEqual(res["temperature"], res["relative_temp"])


if __name__ == "__main__":
    unittest.main()
