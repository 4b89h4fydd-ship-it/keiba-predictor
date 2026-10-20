"""Worker entry wrappers preserve JS exports and canonical module structure."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_worker_entry_paths_keep_reexports():
    expected = {139: ("workers/api_full_snapshot.mjs", "api_full_snapshot.mjs"),
                145: ("workers/live_odds.mjs", "live_odds.mjs"),
                173: ("workers/api.mjs", "api.mjs")}
    for owner, (old, filename) in expected.items():
        legacy = (ROOT/old).read_text()
        assert "export" in legacy
        assert (ROOT/"arvexq/components"/f"item_{owner:03d}"/filename).is_file()
    assert "storageEnvironment" in (ROOT/"arvexq/components/item_174/d1_binding.mjs").read_text()
