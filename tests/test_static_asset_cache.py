"""Immutable browser cache is only legal for assets with versioned URLs."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionedAssetCacheTest(unittest.TestCase):
    def test_page_assets_are_version_pinned_and_modules_retired(self):
        source = (ROOT / "arvexq/ui/static/index.html").read_text(encoding="utf-8")
        # The retired module families are no longer referenced
        # by the page at all (minimal app, 2026-11-28, user
        # instruction): no asset of theirs is loaded, so none
        # can be cached — immutably or otherwise.
        for prefix in ("/betting/","/morning/","/research/","/styles/"):
            urls = re.findall(r'["\'](' + re.escape(prefix) + r'[^"\']+)["\']', source)
            self.assertEqual(urls, [], prefix)
        # Every script and stylesheet the page does load
        # carries a version pin (?fix=...), so nothing
        # unversioned is served to the browser.
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', source)
        self.assertTrue(scripts)
        for url in scripts:
            self.assertIn("?fix=", url, url)
        styles = re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', source)
        self.assertTrue(styles)
        for url in styles:
            self.assertIn("?fix=", url, url)

    def test_version_manifest_names_current_live_model_not_retired_factor_scorer(self):
        import json
        dist = ROOT / "dist"
        manifest = dist / "version.json"
        if not manifest.exists():
            self.skipTest("run static build first")
        version = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(version["shell"], "independent-production-boundaries")
        from arvexq.forecast.engine import VERSION
        self.assertEqual(version["model"], VERSION)
        self.assertNotEqual(version["model"], "arvexq-prediction-removed")
        self.assertEqual(version["model"], "arvexq-empirical-fusion-v1")
        self.assertNotIn("three-factor", str(version).lower())

    def test_immutable_headers_are_only_on_versioned_asset_families(self):
        dist = ROOT / "dist"
        if not (dist / "_headers").exists():
            self.skipTest("run static build first")
        headers=(dist / "_headers").read_text(encoding="utf-8")
        for prefix in ("/betting/*","/morning/*","/research/*","/styles/*"):
            self.assertIn(prefix+"\n  Cache-Control: public, max-age=31536000, immutable",headers)
        self.assertIn("/racecards/*\n  Cache-Control: no-cache, must-revalidate",headers)
        self.assertIn("/sports/*\n  Cache-Control: no-cache, must-revalidate",headers)
        self.assertRegex(headers, r"/app-v\d+\.js\n  Cache-Control: no-cache, must-revalidate")


if __name__=="__main__":
    unittest.main()
