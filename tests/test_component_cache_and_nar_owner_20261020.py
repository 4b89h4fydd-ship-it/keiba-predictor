"""Preserve exact old cache-key/version and NAR provider contracts."""
import importlib
from arvexq.storage.cache_keys import race_detail_key, horse_history_key
from arvexq.components.item_143.race_detail_key import race_detail_key as owned_race
from arvexq.components.item_144.horse_history_key import horse_history_key as owned_history
from arvexq.ingest.full_snapshot_codec import VERSION, pack_detail, unpack_detail
from arvexq.components.item_148.version import VERSION as owned_version, valid_envelope


def test_existing_cache_keys_use_owned_functions_without_changed_names():
    assert race_detail_key is owned_race
    assert horse_history_key is owned_history
    assert race_detail_key("jra-1") == "race-detail:v1:jra-1"
    assert horse_history_key("horse") == "horse-history:v1:horse"


def test_full_snapshot_version_and_restore_bytes_are_unchanged():
    assert VERSION == owned_version == "arvexq-full-payload-v1"
    assert valid_envelope({"version":VERSION,"bytes":12})
    original={"id":"nar-20261020","horses":[{"horseNumber":1}],"missing":None}
    assert unpack_detail(pack_detail(original))==original


def test_old_nar_imports_alias_canonical_component_objects():
    for old,canonical in [("arvexq.ingest.nar_official_card","arvexq.components.item_156.nar_official_card"),("arvexq.ingest.official_changes","arvexq.components.item_158.official_changes")]:
        assert importlib.import_module(old) is importlib.import_module(canonical)
