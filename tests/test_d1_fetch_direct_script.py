"""Direct workflow CLI execution must resolve the in-repository codec."""
import subprocess
import sys
import unittest
from pathlib import Path


class DirectD1FetchEntrypointTests(unittest.TestCase):
    def test_help_without_pythonpath_from_external_directory(self):
        root = Path(__file__).resolve().parents[1]
        script = root / 'scripts' / 'arvexq_fetch_d1_bundle.py'
        completed = subprocess.run(
            [sys.executable, str(script), '--help'],
            cwd='/tmp', env={'PATH': '/usr/bin:/bin'}, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('--api-base', completed.stdout)


if __name__ == '__main__':
    unittest.main()
