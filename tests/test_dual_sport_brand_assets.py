"""Shared ARVEXQ home brand regression — real image and valid icon assets."""
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/"arvexq"/"ui"/"static"


class SharedBrandAssetsTest(unittest.TestCase):
    def test_source_assets_are_real(self):
        hero=(STATIC/"arvexq-unified-hero.webp").read_bytes()
        icon=(STATIC/"arvexq-unified-icon-128.png").read_bytes()
        self.assertTrue(hero.startswith(b"RIFF") and hero[8:12]==b"WEBP")
        self.assertTrue(icon.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II",icon[16:24]),(128,128))

    def test_build_copies_hero_and_correctly_resizes_pwa_icons(self):
        dist=ROOT/"dist"
        if not (dist/"index.html").exists():
            self.skipTest("Run static builder first")
        self.assertEqual((dist/"sports"/"arvexq-unified-hero.webp").read_bytes(),
                         (STATIC/"arvexq-unified-hero.webp").read_bytes())
        for file,size in (("arvexq-touch-v181.png",180),
                          ("arvexq-icon-v181-192.png",192),
                          ("arvexq-icon-v181-512.png",512)):
            png=(dist/file).read_bytes()
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"),file)
            self.assertEqual(struct.unpack(">II",png[16:24]),(size,size))
        for page in ("keiba","kyotei"):
            html=(dist/page/"index.html").read_text(encoding="utf-8")
            self.assertIn("/sports/unified-home.js",html)
            self.assertIn("/sports/unified-home.css",html)
            self.assertIn("/arvexq-touch-v181.png",html)
            self.assertNotIn("__ARVEXQ_SPORT_HASH__",html)


if __name__=="__main__":
    unittest.main()
