"""Horse-only ARVEXQ web and PWA image assets regression."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'arvexq'/'ui'/'static'
class HorseBrandAssetsTest(unittest.TestCase):
    def test_original_horse_assets_exist(self):
        hero=(STATIC/'cinematic-hero-webp.webp').read_bytes()
        self.assertTrue(hero.startswith(b'RIFF') and hero[8:12]==b'WEBP')
        self.assertGreater(len(hero),300_000)
        self.assertTrue((STATIC/'arvexq-icon-source-192.png').read_bytes().startswith(bytes([137,80,78,71])))
        self.assertTrue((STATIC/'arvexq-icon-source-512.png').read_bytes().startswith(bytes([137,80,78,71])))
        shell=(STATIC/'index.html').read_text(encoding='utf-8')
        self.assertIn('manifest-arvexq-v362.webmanifest',shell)
        self.assertIn('arvexq-touch-v361.png',shell)
        self.assertNotIn('arvexq-sport-nav',shell)
        self.assertNotIn('/kyotei/',shell)
        self.assertNotIn('/sports/switch.css',shell)
    def test_compiled_horse_only(self):
        dist=ROOT/'dist'
        if not (dist/'index.html').exists():
            self.skipTest('Build static first')
        html=(dist/'index.html').read_text(encoding='utf-8')
        self.assertIn('/sports/horse-portal.js',html)
        self.assertIn('/sports/unified-home.js',html)
        self.assertNotIn('__ARVEXQ_SPORT_HASH__',html)
        self.assertFalse((dist/'kyotei').exists())
        self.assertFalse((dist/'sports'/'boat-app').exists())
        self.assertFalse((dist/'sports'/'switch.css').exists())
        self.assertEqual((dist/'arvexq-racing-hero.webp').read_bytes(),(STATIC/'arvexq-horse-hero-v361.webp').read_bytes())
        for name in ('arvexq-touch-v361.png','arvexq-icon-v361-192.png','arvexq-icon-v361-512.png','manifest-arvexq-v362.webmanifest'):
            self.assertTrue((dist/name).is_file(),name)
        self.assertIn('arvexq-horse-hero-v361.webp', str(STATIC / 'arvexq-horse-hero-v361.webp'))
        for source,output in [('arvexq-horse-icon-v361-192.png','arvexq-icon-v361-192.png'),('arvexq-horse-icon-v361-512.png','arvexq-icon-v361-512.png'),('arvexq-horse-touch-v361.png','arvexq-touch-v361.png')]:
            self.assertEqual((STATIC/source).read_bytes(),(dist/output).read_bytes())
        self.assertTrue((dist/'keiba'/'index.html').is_file())
        self.assertFalse((dist/'sports'/'arvexq-unified-hero.webp').exists())
if __name__=='__main__':
    unittest.main()
