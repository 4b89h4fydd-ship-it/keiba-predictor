"""Contracts for separate external feed and environment parsing."""
from arvexq.ingest.enrichment_transport import _format_feed_url
from arvexq.ingest.environment_values import (
    _env_clean_weather, _env_clean_condition, _safe_float, _safe_int,
)

def test_format_feed_url_replaces_race_fields():
    race = {"date":"2026-10-17","track":"園田","raceNumber":8,"circuit":"地方","id":"nar-8"}
    assert _format_feed_url("https://example.test/{track}/{race}", race).endswith("/%E5%9C%92%E7%94%B0/8")
    query = _format_feed_url("https://example.test/api",race)
    assert "date=2026-10-17" in query and "race=8" in query

def test_environment_and_external_numeric_values():
    assert _env_clean_weather("小雨") == "小雨"
    assert _env_clean_condition("稍重") == "稍重"
    assert _safe_float("1,234.50") == 1234.5
    assert _safe_int("12.9") == 12
    assert _safe_int("不明") is None
