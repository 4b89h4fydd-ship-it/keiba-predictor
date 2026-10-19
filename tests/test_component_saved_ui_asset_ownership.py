"""Verify saved pre-off and prior-day UI scripts remain byte-identical."""
from pathlib import Path
from arvexq.components.runtime import component_path
from arvexq.ui.assets import read_asset

ROOT = Path(__file__).resolve().parents[1]


def test_preoff_and_previous_day_owners_match_original_static_bytes():
    for owner, name in [(134, "morning/saved_ticket_receipt.js"), (137, "previous_ai_results.js")]:
        original = (ROOT / "arvexq/ui/static" / name).read_bytes()
        canonical = (component_path(owner) / "ui" / Path(name).name).read_bytes()
        assert canonical == original
        assert read_asset(name).encode("utf-8") == original
