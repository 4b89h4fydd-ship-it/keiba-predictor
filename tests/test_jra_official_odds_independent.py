"""The original JRA official race-card odds contract remains unchanged."""
from pathlib import Path

from arvexq.ingest.odds_fields.jra_official import parse_win_odds


def test_observed_jra_win_odds_and_rank_from_official_card_layout():
    info = "試験馬 6.5(3番人気) (0.0.0.0) 加藤 士津八"
    assert parse_win_odds(info, "試験馬") == (6.5, 3)
    assert parse_win_odds("試験馬 12 (10番人気)", "試験馬") == (12.0, 10)


def test_missing_jra_odds_are_not_fabricated_from_form_or_other_runners():
    assert parse_win_odds("試験馬 (0.0.0.0) 馬体重 450kg", "試験馬") == (0.0, 0)
    assert parse_win_odds("試験馬 単勝発売前", "試験馬") == (0.0, 0)
    assert parse_win_odds("", "試験馬") == (0.0, 0)


def test_jra_official_race_parser_is_wired_to_independent_module():
    source = Path("app.py").read_text()
    race = source.split("def _jra_parse_race(", 1)[1].split("\ndef _jra_parse_race_summary(", 1)[0]
    assert "from arvexq.ingest.odds_fields.jra_official import parse_win_odds as jra_observed_win_odds" in source
    assert "win_odds, popularity = jra_observed_win_odds(infot, name)" in race
    assert '"oddsSource":"JRA公式" if win_odds else ""' in race
