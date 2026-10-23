"""Regression for repair transport of immutable mass feature evidence."""
from scripts.arvexq_select_prefetch_repairs import retain_frozen_mass_context


def _detail():
    return {
        "id": "nar-2026-10-23-園田-07", "date": "2026-10-23",
        "massFeatureSnapshot": {
            "raceId": "nar-2026-10-23-園田-07", "date": "2026-10-23",
            "featureHash": "frozen-evidence",
            "rows": [{"horseNumber": 1}],
        },
    }


def test_existing_matching_original_preserved_for_transport():
    prepared = _detail()
    original = {**_detail(), "preRacePrediction": {"frozen": "unmodified"}}
    out = retain_frozen_mass_context(prepared, original)
    assert out["preRacePrediction"] is original["preRacePrediction"]
    assert out["massFeatureSnapshot"] is prepared["massFeatureSnapshot"]
    assert "preRacePrediction" not in prepared


def test_unknown_or_conflicting_mass_is_never_used_for_repair():
    prepared = _detail()
    original = {**_detail(), "preRacePrediction": {"frozen": "unmodified"}}
    assert retain_frozen_mass_context(prepared, None) is None
    assert retain_frozen_mass_context(prepared, {}) is None
    assert retain_frozen_mass_context(prepared, {**original, "id": "other"}) is None
    changed = _detail()
    changed["massFeatureSnapshot"] = {**changed["massFeatureSnapshot"], "featureHash": "different"}
    assert retain_frozen_mass_context(changed, original) is None
    assert retain_frozen_mass_context(prepared, {**original, "preRacePrediction": None}) is None
    assert retain_frozen_mass_context({**prepared, "preRacePrediction": {"original": True}}, None) == {
        **prepared, "preRacePrediction": {"original": True}
    }
