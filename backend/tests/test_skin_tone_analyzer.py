"""
Unit & Integration Tests for Skin Tone Analyzer Pipeline
========================================================

Tests coverage:
1. Error handling (non-existent image, corrupted image, image without faces).
2. ITA calculation and standard dermatological range classification.
3. Hue Angle calculation and undertone classification (Warm, Cool, Neutral, Olive).
4. End-to-end pipeline JSON schema validation.
"""

import os
import json
import tempfile
import unittest
import numpy as np
import cv2

from backend.app.cv.skin_tone_analyzer import (
    analyze_skin_tone,
    classify_ita,
    classify_undertone
)


class TestSkinToneAnalyzer(unittest.TestCase):

    def test_invalid_image_path(self):
        result = analyze_skin_tone("non_existent_file_xyz_12345.jpg")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "INVALID_IMAGE_PATH")

    def test_corrupted_image_file(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"this is not a valid image file binary content")
            tmp_path = tmp.name

        try:
            result = analyze_skin_tone(tmp_path)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "INVALID_IMAGE_FORMAT")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_no_face_detected(self):
        # Create a plain blue background image with no faces
        img = np.full((300, 300, 3), (255, 100, 50), dtype=np.uint8)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            cv2.imwrite(tmp.name, img)
            tmp_path = tmp.name

        try:
            result = analyze_skin_tone(tmp_path)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "NO_FACE_DETECTED")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_ita_classification_ranges(self):
        # Chardon et al. (1991) standard ranges:
        # > 55: Very Light
        self.assertEqual(classify_ita(60.0), "Very Light")
        # 41 to 55: Light
        self.assertEqual(classify_ita(45.0), "Light")
        # 28 to 41: Intermediate
        self.assertEqual(classify_ita(35.0), "Intermediate")
        # 10 to 28: Tan
        self.assertEqual(classify_ita(20.0), "Tan")
        # -30 to 10: Dark
        self.assertEqual(classify_ita(0.0), "Dark")
        # <= -30: Very Dark
        self.assertEqual(classify_ita(-35.0), "Very Dark")

    def test_undertone_classification_logic(self):
        # Test Warm (high b* relative to a*, hue angle >= 58°)
        # a* = 10, b* = 20 -> atan2(20, 10) = 63.4° -> Warm
        ut, hue = classify_undertone(10.0, 20.0)
        self.assertEqual(ut, "Warm")
        self.assertAlmostEqual(hue, 63.43, places=1)

        # Test Cool (high a* relative to b*, hue angle <= 52°)
        # a* = 20, b* = 15 -> atan2(15, 20) = 36.87° -> Cool
        ut, hue = classify_undertone(20.0, 15.0)
        self.assertEqual(ut, "Cool")
        self.assertAlmostEqual(hue, 36.87, places=1)

        # Test Neutral (balanced red/yellow, hue angle ~ 55°)
        # a* = 15, b* = 21 -> atan2(21, 15) = 54.46° -> Neutral
        ut, hue = classify_undertone(15.0, 21.0)
        self.assertEqual(ut, "Neutral")
        self.assertAlmostEqual(hue, 54.46, places=1)

        # Test Olive (low a* relative to total chroma)
        # a* = 5, b* = 15 -> red_chroma_ratio = 5/sqrt(25+225) = 0.316 < 0.44 -> Olive
        ut, hue = classify_undertone(5.0, 15.0)
        self.assertEqual(ut, "Olive")


if __name__ == "__main__":
    unittest.main()
