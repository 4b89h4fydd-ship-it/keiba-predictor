"""Every executable import must be independent of removed six-stage calculators."""
import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
DISALLOWED=(
    re.compile(r"\b(?:from|import)\s+arvexq\.research\.stage6[34]\b"),
    re.compile(r"arvexq-stage64-product-v1"),
    re.compile(r"_attach_existing_stage64_products"),
)


class RetiredPipelineRemovalTests(unittest.TestCase):
    def test_no_live_legacy_module_imports_or_product_versions(self):
        bad=[]
        sources=[ROOT/"app.py",*(ROOT/"arvexq").rglob("*.py"),
                 *(ROOT/"scripts").rglob("*.py")]
        for path in sources:
            if not path.is_file():
                continue
            text=path.read_text(encoding="utf-8",errors="replace")
            for matcher in DISALLOWED:
                if matcher.search(text):
                    bad.append(str(path.relative_to(ROOT))+": "+matcher.pattern)
        self.assertEqual(bad,[],f"legacy references: {bad[:30]}")

    def test_old_six_stage_modules_are_physically_absent(self):
        for name in ("stage63","stage64"):
            self.assertFalse((ROOT/"arvexq"/"research"/name).exists())


if __name__=="__main__":
    unittest.main()
