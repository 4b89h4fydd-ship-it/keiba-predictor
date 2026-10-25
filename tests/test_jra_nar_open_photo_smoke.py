"""No-video, no-betting, CC-photo JRA/NAR detector smoke contracts."""
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.arvexq_jra_nar_cc_photo_smoke import (
    SAMPLES, evaluate, download_cc_photo, VERSION,
)


class PhotoSmokeTests(TestCase):
    def test_two_circuits_and_attributed_photo_license(self):
        self.assertEqual({s["circuit"] for s in SAMPLES}, {"JRA", "NAR"})
        self.assertEqual(len({s["source"] for s in SAMPLES}), 2)
        for s in SAMPLES:
            self.assertTrue(s["source"].startswith("https://commons.wikimedia.org/wiki/File:"))
            self.assertIn("creativecommons.org/licenses/by-sa", s["license"])
            self.assertTrue(s["author"])

    def test_refuse_arbitrary_images(self):
        with self.assertRaisesRegex(ValueError, "individually sourced"):
            download_cc_photo({"file": "untrusted.jpg"})
        with self.assertRaisesRegex(ValueError, "individually sourced"):
            download_cc_photo({})

    def test_research_only_numeric_detection_contract(self):
        with TemporaryDirectory() as folder:
            result = evaluate(
                Path(folder),
                downloader=lambda s: b"fake source image bytes",  # no actual media
                inferrer=lambda image, model: {
                    "detectedHorseObjects": 2, "maxDetectionConfidence": .75,
                    "width": 640, "height": 480,
                    "isHumanValidated": False,
                },
            )
        self.assertEqual(result["version"], VERSION)
        self.assertEqual(len(result["cases"]), 2)
        self.assertFalse(result["forecastUpdated"])
        self.assertFalse(result["independentlyReviewedDetections"])
        for item in result["cases"]:
            self.assertEqual(item["detectedHorseObjects"], 2)
            self.assertIsNone(item["horseNumberAccuracy"])
            self.assertIsNone(item["groundTruthHorseCount"])
            self.assertFalse(item["reidentificationTested"])
            self.assertFalse(item["horseMotionOrPaceTested"])
            self.assertFalse(item["modelImprovesBettingProven"])

    def test_invalid_model_response_is_rejected(self):
        for count in (None, -1, "2", True):
            with self.subTest(count=count):
                with self.assertRaisesRegex(ValueError, "detection count"):
                    evaluate(Path("/not-important"),
                             downloader=lambda s: b"fake photo",
                             inferrer=lambda blob, model: {
                                 "detectedHorseObjects": count
                             })

    def test_image_fetch_rejects_external_redirect(self):
        class Untrusted:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return "https://evil.example/horse.jpg"
            def read(self, amt): return b"x" * 3000
        with self.assertRaisesRegex(ValueError, "outside Wikimedia"):
            download_cc_photo(SAMPLES[0], opener=lambda *a, **kw: Untrusted())
