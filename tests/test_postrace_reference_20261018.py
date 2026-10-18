"""Prevent post-race reconstruction of rejected assistant predictions."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_retrospective_prediction_generator_is_deleted():
    assert not (ROOT/"scripts/arvexq_postrace_reference_20261018.py").exists()
    build=(ROOT/"build_static.py").read_text(encoding="utf-8")
    assert "produce_postrace_reference" not in build
    assert "arvexq_postrace_reference_20261018" not in build
    source=(ROOT/"arvexq/ui/static/app.js").read_text(encoding="utf-8")
    assert "/postrace-reference/" not in source
    assert "postraceReferenceArchive" not in source
    assert "r.postRaceReference=found" not in source

def test_historical_facts_remain_intact():
    assert (ROOT/"arvexq/ui/static/saved-snapshots/2026-10-18.json").exists()
    assert (ROOT/"arvexq/ui/static/racecards/2026-10-18.json").exists()
