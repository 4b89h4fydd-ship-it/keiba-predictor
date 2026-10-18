"""Prevent retired prediction/mark handlers from returning to the shipped UI."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "arvexq/ui/static/app.js")
ARCHIVE = (Path(__file__).resolve().parents[1] / "arvexq/ui/static/saved-snapshots/2026-10-18.json")


def test_old_secondary_models_deleted_from_live_ui():
    source = APP.read_text(encoding="utf-8")
    for retired in (
        "function authorizedPreOffMarks(",
        "function latestOfficialMarkRevision(",
        "function latestUserApprovedModelMarkRevision(",
        "function latestAuthorizedMarkRevision(",
        "function latestSavedForecastRevision(",
        "function savedRevisionOriginalHtml(",
        "function revisionPercent(",
        "/api/forecast-revisions/",
    ):
        assert retired not in source, retired
    assert "function verifiedOriginalMarks(" in source
    assert "original:verifiedOriginalMarks" in source
    assert "var original=verifiedOriginalMarks(detail);" in source


def test_approved_forecast_and_immutable_evidence_remain():
    source = APP.read_text(encoding="utf-8")
    assert "ARVEXQProductionPrediction.build(r)" in source
    assert "window.ARVEXQProductionTickets.build(r,p)" in source
    assert "ARVEXQMorningEvidence" in source
    assert "function aiDailyOne(detail)" in source
    assert ARCHIVE.is_file(), "historical race originals must never be deleted"


def test_no_secondary_history_fetch_on_race_open():
    source = APP.read_text(encoding="utf-8")
    assert "return edgeFetchJson(url,9000).then(function(body){" in source
    assert "forecastRevisions=revisionBody.forecastRevisions" not in source
