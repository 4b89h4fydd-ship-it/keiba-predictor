"""Independent canonical identity validation, without synthesizing facts."""
from arvexq.ingest.race_identity import observed_detail_identity_error
from arvexq.quality.fact_audit import audit_day


def test_correct_jra_and_nar_identity_acceptance():
    for circuit, prefix, track in (("JRA", "jra", "京都"), ("NAR", "nar", "大井")):
        detail = dict(id=f"{prefix}-2026-10-18-{track}-02", circuit=circuit,
                      date="2026-10-18", track=track, raceNumber=2, horses=[])
        assert observed_detail_identity_error(detail) is None


def test_observed_race_mismatch_detected_without_rewriting():
    detail = {"id": "jra-2026-10-18-京都-05", "circuit": "JRA",
              "date": "2026-10-18", "track": "京都",
              "raceNumber": 2, "horses": []}
    before = dict(detail)
    error = observed_detail_identity_error(detail)
    assert error == {"raceId": detail["id"], "expectedRaceId": "jra-2026-10-18-京都-02",
                     "error": "race detail identity mismatch"}
    assert detail == before
    bundle = {"date": "2026-10-18", "races": [{"id": detail["id"]}],
              "details": [detail], "readErrors": []}
    assert audit_day(bundle)["validationErrors"] == [error]


def test_missing_identity_does_not_fabricate_error_or_race():
    detail = {"id": "jra-2026-10-18-京都-05", "date": "2026-10-18",
              "horses": []}
    assert observed_detail_identity_error(detail) is None
    assert audit_day({"date": "2026-10-18", "races": [{"id": detail["id"]}],
                      "details": [detail], "readErrors": []})["validationErrors"] == []
