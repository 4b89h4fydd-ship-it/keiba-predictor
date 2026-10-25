"""Post-cutoff production picks must never silently use obsolete learned models."""
from unittest.mock import patch
from scripts.arvexq_apply_learned_overlay import apply


def _race():
    return {
        "id": "nar-2026-10-26-園田-01",
        "date": "2026-10-26",
        "circuit": "地方",
        "track": "園田",
        "scheduledStartTime": "12:00",
        "horses": [
            {"horseNumber": i, "predMark": "◎" if i == 1 else "○"}
            for i in range(1, 7)
        ],
        "predictionStatus": "legacy-ready",
        "aiEvaluation": {"legacy": True},
        "prediction": {"modelVersion": "obsolete"},
        "predictionMarks": [{"horseNumber": 1, "mark": "◎"}],
        "recommendedBets": [{"kind": "単勝", "combo": [1]}],
    }


def test_preoff_without_fusion_never_builds_legacy_prediction():
    detail = _race()
    old_model = {"training": {"lastDate": "2026-10-20"}}
    with patch(
        "scripts.arvexq_apply_learned_overlay.may_create_prerace_prediction",
        return_value=True,
    ), patch(
        "scripts.arvexq_apply_learned_overlay.build_forecast",
        side_effect=AssertionError("legacy forecast executed"),
    ):
        result, report = apply({"details": [detail]}, {"地方": old_model})
    row = result["details"][0]
    assert report["overlaid"] == []
    assert report["fusionPublished"] == []
    assert report["skipped"][detail["id"]] == "fusion-inputs-unavailable"
    assert row["predictionStatus"] == "new-model-unavailable"
    assert "aiEvaluation" not in row
    assert "prediction" not in row
    assert "predictionMarks" not in row
    assert "recommendedBets" not in row
    assert all("predMark" not in horse for horse in row["horses"])
    assert detail["aiEvaluation"] == {"legacy": True}
    assert detail["horses"][0]["predMark"] == "◎"


def test_failed_fusion_does_not_promote_obsolete_model():
    detail = _race()
    with patch(
        "scripts.arvexq_apply_learned_overlay.may_create_prerace_prediction",
        return_value=True,
    ), patch(
        "scripts.arvexq_apply_learned_overlay.assemble_fusion_inputs",
        side_effect=ValueError("not enough real preoff evidence"),
    ), patch(
        "scripts.arvexq_apply_learned_overlay.build_forecast",
        side_effect=AssertionError("legacy fallback executed"),
    ):
        result, report = apply(
            {"details": [detail]},
            {"fusion": {"地方": {"models": {}, "calibration": {}}}},
        )
    assert result["details"][0]["predictionStatus"] == "new-model-unavailable"
    assert "predictionMarks" not in result["details"][0]
    assert "recommendedBets" not in result["details"][0]
    assert report["skipped"][detail["id"]] == "fusion-inputs-invalid"
    assert "not enough real preoff evidence" in report["fusionErrors"][detail["id"]]


def test_stage64_saved_original_is_not_promoted_into_active_public_projection():
    from arvexq.forecast.publication import public_race

    d = _race()
    d["date"] = "2026-10-24"
    d["predictionStatus"] = "ready"
    d["predictionModelVersion"] = "arvexq-stage64-product-v1"
    d["prediction"] = {
        "modelVersion": "arvexq-stage64-product-v1",
        "predictionStatus": "ready",
        "productionEligible": True,
        "raceId": d["id"],
        "date": d["date"],
    }
    d["predictionMarks"] = [
        {"horseNumber": n, "mark": mark}
        for n, mark in enumerate(("◎", "○", "▲", "△", "☆"), start=1)
    ]
    d["recommendedBets"] = []
    old = dict(d)
    projected = public_race(d)
    assert projected["predictionStatus"] == "disabled"
    assert "predictionMarks" not in projected
    assert "recommendedBets" not in projected
    assert d["predictionMarks"] == old["predictionMarks"]
