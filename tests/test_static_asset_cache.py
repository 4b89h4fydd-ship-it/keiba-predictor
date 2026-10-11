"""Immutable browser cache is only legal for assets with versioned URLs."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionedAssetCacheTest(unittest.TestCase):
    def test_horse_modules_have_content_fingerprint_in_html(self):
        source = (ROOT / "arvexq/ui/static/index.html").read_text(encoding="utf-8")
        for prefix in ("/betting/","/morning/","/research/","/styles/"):
            urls = re.findall(r'["\'](' + re.escape(prefix) + r'[^"\']+)["\']', source)
            self.assertTrue(urls, prefix)
            self.assertTrue(all("?v=__ARVEXQ_" in u for u in urls), (prefix,urls))

    def test_immutable_headers_are_only_on_versioned_asset_families(self):
        dist = ROOT / "dist"
        if not (dist / "_headers").exists():
            self.skipTest("run static build first")
        headers=(dist / "_headers").read_text(encoding="utf-8")
        for prefix in ("/betting/*","/morning/*","/research/*","/styles/*"):
            self.assertIn(prefix+"\n  Cache-Control: public, max-age=31536000, immutable",headers)
        self.assertIn("/racecards/*\n  Cache-Control: no-cache, must-revalidate",headers)
        self.assertIn("/sports/*\n  Cache-Control: no-cache, must-revalidate",headers)
        self.assertIn("/app-v329.js\n  Cache-Control: no-cache, must-revalidate",headers)


if __name__=="__main__":
    unittest.main()
