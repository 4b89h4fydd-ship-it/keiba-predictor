"""Dual-sport build regression tests: keep the existing horse page intact."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "arvexq" / "ui" / "static"


class SportNavigationTest(unittest.TestCase):
    def test_horse_shell_has_both_sport_links(self):
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/keiba/"', html)
        self.assertIn('href="/kyotei/"', html)
        self.assertIn('id="app"', html)
        self.assertIn('src="/app-v329.js?', html)

    def test_boat_shell_does_not_load_horse_app(self):
        html = (STATIC / "sports" / "boat.html").read_text(encoding="utf-8")
        self.assertIn('href="/keiba/"', html)
        self.assertIn('href="/kyotei/"', html)
        self.assertIn('/sports/boat-app/app.js', html)
        self.assertNotIn('/app-v329.js', html)
        self.assertNotIn('arvexq/ui/static/app.js', html)
        self.assertIn('3連単最大6点', html)
        self.assertIn('id="boat-root"', html)

    def test_static_builder_creates_distinct_routes(self):
        script = (ROOT / "build_static.py").read_text(encoding="utf-8")
        self.assertIn('(DIST / "keiba" / "index.html").write_text(index_html', script)
        self.assertIn('(DIST / "kyotei" / "index.html").write_text(boat_html', script)
        self.assertIn('shutil.copytree(SPORT_DIR / "boat-app"', script)

    def test_boat_does_not_fabricate_predictions(self):
        script = (STATIC / "sports" / "boat-app" / "core" / "contract.js").read_text(encoding="utf-8")
        self.assertIn('verified', script)
        self.assertIn('validTicket', script)
        self.assertNotIn('Math.random', script)

    def test_compiled_outputs(self):
        dist = ROOT / "dist"
        if not (dist / "index.html").exists():
            self.skipTest("Run build_static.py to inspect generated routes")
        horse = (dist / "keiba" / "index.html").read_text(encoding="utf-8")
        boat = (dist / "kyotei" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/kyotei/"', horse)
        self.assertIn('href="/keiba/"', boat)
        self.assertIn('app-v329.js', horse)
        self.assertNotIn('app-v329.js', boat)
        self.assertNotIn('__ARVEXQ_SPORT_HASH__', horse)
        self.assertNotIn('__ARVEXQ_SPORT_HASH__', boat)
        self.assertTrue((dist / "sports" / "boat-app" / "app.js").is_file())
        self.assertTrue((dist / "sports" / "boat-app" / "core" / "stats.js").is_file())
        self.assertTrue((dist / "sports" / "boat-app" / "features" / "all-races.js").is_file())
        self.assertIn('/sports/horse-portal.js',horse)
        self.assertTrue((dist / "sports" / "all-races.css").is_file())
        self.assertIn("/sports/all-races.css",horse)
        self.assertIn("/sports/all-races.css",boat)


if __name__ == "__main__":
    unittest.main()
