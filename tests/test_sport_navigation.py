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
        self.assertIn('/sports/unified-home.js', html)
        self.assertIn('/sports/unified-home.css', html)
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

    def test_venue_page_does_not_overlay_the_fixed_sport_navigation(self):
        legacy = (STATIC / "styles" / "legacy_v118_v221.css").read_text(encoding="utf-8")
        start = legacy.index("/* Venue-only layout:")
        end = legacy.index("/* v195", start)
        venue = legacy[start:end]
        self.assertIn(".smart-venue-page>.smart-venue-topbar", venue)
        self.assertIn("top:var(--arvexq-nav-h", venue)
        self.assertIn("position:sticky!important", venue)
        self.assertNotIn("position:fixed!important", venue)
        self.assertNotIn("padding-top:calc(174px", venue)
        self.assertNotIn("padding-top:calc(163px", venue)
        switch = (STATIC / "sports" / "switch.css").read_text(encoding="utf-8")
        self.assertIn(".arvexq-sport-nav", switch)
        self.assertIn("position:fixed!important", switch)
        app = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn("smart-shell smart-venue-page", app)

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
        self.assertTrue((dist / "sports" / "unified-home.js").is_file())
        self.assertTrue((dist / "sports" / "unified-home.css").is_file())
        self.assertIn("/sports/all-races.css",horse)
        self.assertIn("/sports/all-races.css",boat)


if __name__ == "__main__":
    unittest.main()
