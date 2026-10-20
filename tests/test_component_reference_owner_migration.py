"""Existing source imports preserve implementation identities and circuit labels."""
import importlib
from arvexq.ingest.odds_results_merge import _merge_result_fields
from arvexq.components.item_084.result_merge import _merge_result_fields as owned
from arvexq.v3.data.quality import normalize_circuit
from arvexq.components.item_128.circuit import normalize_circuit as circuit_owner


def test_compatibility_import_identity():
    for src,owned_path in [("arvexq.ingest.netkeiba_odds_parser","arvexq.components.item_063.netkeiba_odds_parser"),("arvexq.prediction.course_speed_baselines","arvexq.components.item_109.course_speed_baselines")]:
        assert importlib.import_module(src) is importlib.import_module(owned_path)
    assert _merge_result_fields is owned
    assert normalize_circuit is circuit_owner


def test_unknown_circuit_never_defaults_to_jra_or_nar():
    assert normalize_circuit("中央")=="jra"
    assert normalize_circuit("地方")=="nar"
    assert normalize_circuit("unknown") is None
