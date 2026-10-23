from app import normalize_central_race


def test_normalize_central_race_does_not_relabel_local_payload():
    assert normalize_central_race({
        "id": "nar-2026-10-23-大井-01",
        "circuit": "地方",
        "date": "2026-10-23",
        "track": "大井",
        "raceNumber": 1,
    }) is None


def test_normalize_central_race_keeps_source_missing_circuit_on_central_path():
    race = normalize_central_race({
        "id": "jra-2026-10-23-東京-01",
        "date": "2026-10-23",
        "track": "東京",
        "raceNumber": 1,
        "horses": [],
    })
    assert race["circuit"] == "中央"

