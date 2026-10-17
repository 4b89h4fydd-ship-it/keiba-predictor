"""Regression coverage for the independently owned ingestion normalizers."""
from arvexq.ingest.field_normalization import (
    _clean, _int, _float, _carried_weight, _iso_date, _start_time,
    _time_seconds, _normalize_sex, _scratch_status, _normalize_weather,
    _normalize_condition,
)

def test_numeric_and_weight_normalization():
    assert _clean("　馬　") == "馬"
    assert _int("1,234") == 1234
    assert _int("") == 0
    assert _float("1,234.5") == 1234.5
    assert _carried_weight("▲ 51.0") == 51.0
    assert _carried_weight("☆55.0") == 55.0

def test_race_fields_normalization():
    assert _iso_date("20261017") == "2026-10-17"
    assert _start_time("945") == "09:45"
    assert _time_seconds("2043") == 124.3
    assert _time_seconds("594") == 59.4
    assert _normalize_sex("騸") == "セ"
    assert _scratch_status("出走取消") == "出走取消"
    assert _normalize_weather("晴れ") == "晴"
    assert _normalize_condition("稍重") == "稍重"
