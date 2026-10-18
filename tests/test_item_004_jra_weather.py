"""Item 004 contracts for observed JRA weather fallback."""

import app


def test_historical_jra_weather_uses_official_result(monkeypatch):
    monkeypatch.setattr(app, "_jra_find_cname", lambda *args: "")
    monkeypatch.setattr(
        app,
        "_jra_prior_result_cnames",
        lambda date, track: ["pw01sde1005202604060120261017/6B"],
    )
    monkeypatch.setattr(app, "_jra_any_race_no", lambda cname: 1)
    monkeypatch.setattr(
        app,
        "_jra_parse_result",
        lambda *args, **kwargs: {
            "weather": "晴", "condition": "良",
        },
    )
    monkeypatch.setattr(
        app,
        "_netkeiba_race_meta",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("secondary source must not be needed")
        ),
    )

    result = app._jra_fetch_environment({
        "date": "2026-10-17",
        "track": "東京",
        "raceNumber": 1,
        "surface": "ダート",
    })

    assert result["weather"] == "晴"
    assert result["condition"] == "良"
    assert result["source"] == "JRA公式優先"


def test_jra_weather_fallback_does_not_infer_from_going(monkeypatch):
    monkeypatch.setattr(app, "_jra_find_cname", lambda *args: "")
    monkeypatch.setattr(app, "_jra_prior_result_cnames", lambda *args: [])
    monkeypatch.setattr(
        app,
        "_netkeiba_race_meta",
        lambda *args: {"condition": "良"},
    )

    result = app._jra_fetch_environment({
        "date": "2026-10-17",
        "track": "東京",
        "raceNumber": 1,
        "surface": "ダート",
    })

    assert result.get("weather") in (None, "", "不明")
    assert result["condition"] == "良"
