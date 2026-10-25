"""Read-only tests of internal video provider security gates (no network)."""
from __future__ import annotations

import os
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.arvexq_vision_internal import _allowed, main, process_internal_feed


class InternalFeedSafetyTests(TestCase):
    def test_refuses_http_unknown_host_and_redirect_like_url(self):
        hosts = {"approved.example"}
        for url in ("http://approved.example/video.mp4",
                    "https://unapproved.example/video.mp4",
                    "https://user:pass@approved.example/video.mp4",
                    "https://approved.example:8080/video.mp4",
                    "https://approved.example/video.mp4#fragment"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    _allowed(url, hosts)
        _allowed("https://approved.example/video.mp4", hosts)

    def test_missing_provider_does_not_claim_analysis(self):
        with patch.dict(os.environ, {"ARVEXQ_VIDEO_FEED_URL": ""}):
            self.assertEqual(main(["--date", "2026-10-24"]), 2)

    def test_authorized_provider_requires_local_free_model_before_download(self):
        with TemporaryDirectory() as folder:
            with patch.dict(os.environ, {
                "ARVEXQ_VIDEO_FEED_URL": "https://approved.example/feed.json",
                "ARVEXQ_VIDEO_FEED_TOKEN": "fake-only",
                "ARVEXQ_VIDEO_ALLOWED_HOSTS": "approved.example",
                "ARVEXQ_VISION_MODEL_DIR": folder}, clear=False):
                # Missing RT-DETR model is an explicit no-data error; no
                # remote provider video is fetched yet.
                self.assertEqual(main(["--date", "2026-10-24"]), 1)

    def test_token_and_allowlist_required(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "token and allowlist"):
                process_internal_feed(
                    feed_url="https://approved.example/feed.json", token="",
                    allowed_hosts={"approved.example"},
                    target_date="2026-10-24", output_dir=Path(folder))
