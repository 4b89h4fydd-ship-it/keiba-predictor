"""Verify legacy endpoint identity and unchanged static scripts after ownership migration."""
from pathlib import Path
from arvexq.components.runtime import component_path
from arvexq.ui.assets import read_asset
from arvexq.ingest.jra_identifiers import _jra_race_no_from_cname
from arvexq.components.item_011.race_number import _jra_race_no_from_cname as owned_race_number
from arvexq.ingest.d1_day_readback import get_json
from arvexq.components.item_160.readback_retry import get_json as owned_readback

ROOT = Path(__file__).resolve().parents[1]
CASES = [[58,"history/temporal.js"],[182,"history/view.js"],[185,"forecast/prediction_frame.js"],[186,"forecast/mark_frame.js"],[187,"forecast/ticket_frame.js"]]


def test_old_python_imports_keep_same_owned_function_object():
    assert _jra_race_no_from_cname is owned_race_number
    assert get_json is owned_readback


def test_owner_scripts_match_existing_static_assets_byte_for_byte():
    for owner, name in CASES:
        original = ROOT / "arvexq/ui/static" / name
        moved = component_path(owner) / "ui" / Path(name).name
        assert moved.read_bytes() == original.read_bytes()
        assert read_asset(name).encode("utf-8") == original.read_bytes()
