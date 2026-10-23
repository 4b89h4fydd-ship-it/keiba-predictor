"""JRA official live runner weights are separate, observed-only facts."""
from pathlib import Path

from arvexq.ingest.jra_fields.body_weight import extract as body_weight
from arvexq.ingest.jra_fields.body_weight_change import extract as weight_change


def test_weight_from_published_kg_with_optional_change():
    assert body_weight("サンプル 490kg (+4)") == 490
    assert body_weight("サンプル 490 kg（-4）") == 490
    assert body_weight("サンプル 490kg") == 490
    assert body_weight("サンプル 5.4kg") == 0
    assert body_weight("体重未発表") == 0


def test_weight_change_never_assumes_previous_or_current_race_weight():
    assert weight_change("サンプル 490kg (+4)") == 4
    assert weight_change("サンプル 490kg (-4)") == -4
    assert weight_change("サンプル 490kg (+0)") == 0
    assert weight_change("サンプル 490kg") is None
    assert weight_change("体重未発表") is None


def test_existing_jra_card_uses_independent_weight_and_delta_modules():
    app_source = Path("app.py").read_text()
    card = app_source.split("def _jra_parse_race(", 1)[1].split("\ndef _jra_parse_race_summary(", 1)[0]
    assert "body_weight=jra_observed_body_weight(infot)" in card
    assert "body_change=jra_observed_body_weight_change(infot)" in card
    assert "from arvexq.ingest.jra_fields.body_weight import extract as jra_observed_body_weight" in app_source
    assert "from arvexq.ingest.jra_fields.body_weight_change import extract as jra_observed_body_weight_change" in app_source
