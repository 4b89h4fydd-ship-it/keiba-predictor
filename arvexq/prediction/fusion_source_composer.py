"""Compose the five genuinely trained preoff methods on the EXISTING D1 card.

No second API, scraping path or product pipeline is introduced. Inputs are
computed from already collected prior-run histories and previously fitted
artifacts, then sent to the existing forecast.engine/publication/seal steps.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.prediction.empirical_fusion import VERSION as FUSION_VERSION, _arms
from arvexq.prediction.fusion_method_models import predict_observed_methods, METHODS
from arvexq.prediction.fusion_ai_models import predict_logistic, predict_bayes

JST = ZoneInfo("Asia/Tokyo")


def _off(detail):
    from arvexq.prediction.prerace_archive import post_at
    post = post_at(detail)
    if post is None:
        raise ValueError("official scheduled off unavailable")
    return post.astimezone(JST)


def assemble_fusion_inputs(detail, model_artifacts, fitted_calibration, *, now=None):
    """Produce 5 full runner-order distributions and a frozen input receipt.

    Three methods are transparent public-method implementations, not the
    actual personal picks of Mineta or another paid forecaster. Two different
    independently trained machine-learning architectures supply the AI arms.
    """
    if not isinstance(detail, dict) or not isinstance(model_artifacts, dict):
        raise ValueError("full preoff race card and fitted artifacts required")
    circuit, day = detail.get("circuit"), detail.get("date")
    if circuit not in ("中央","地方") or not isinstance(day,str):
        raise ValueError("separate central/local model required")
    if (detail.get("result") or {}).get("finishers") or (detail.get("result") or {}).get("payouts"):
        raise ValueError("result evidence present before opinion calculation")
    now = now or datetime.now(JST)
    if now.tzinfo is None:
        raise ValueError("timezone-aware model capture required")
    clock = now.astimezone(JST)
    scheduled = _off(detail)
    if clock >= scheduled or day != clock.date().isoformat():
        raise ValueError("current scheduled-race-day preoff capture required")
    if not isinstance(fitted_calibration, dict) or fitted_calibration.get("version") != FUSION_VERSION:
        raise ValueError("actual heldout calibration required")
    if fitted_calibration.get("circuit") != circuit or fitted_calibration.get("targetDate") != day:
        raise ValueError("calibration circuit and target date mismatch")
    experts = model_artifacts.get("methods")
    ai = model_artifacts.get("ai")
    if not isinstance(experts, dict) or set(experts) != set(METHODS):
        raise ValueError("three earlier trained method artifacts required")
    if not isinstance(ai, dict) or set(ai) != {"ai:learned","ai:bayes"}:
        raise ValueError("two different earlier fitted AI architectures required")
    at, off = clock.isoformat(), scheduled.isoformat()
    opinions = predict_observed_methods(detail, experts, captured_at=at, scheduled_off_at=off)
    opinions["ai:learned"] = predict_logistic(
        detail, ai["ai:learned"], captured_at=at, scheduled_off_at=off)
    opinions["ai:bayes"] = predict_bayes(
        detail, ai["ai:bayes"], captured_at=at, scheduled_off_at=off)
    _arms(opinions)
    if fitted_calibration.get("methodVersions") != {
            name: opinion["modelVersion"] for name, opinion in opinions.items()}:
        raise ValueError("model versions changed after empirical evaluation")
    starters = [int(h["horseNumber"]) for h in detail["horses"] if isinstance(h,dict) and
                not any(h.get(k) for k in ("scratched","withdrawn","cancelled")) and
                str(h.get("status") or "") not in ("取消","出走取消","除外")]
    if len(starters)<5 or len(set(starters))!=len(starters):
        raise ValueError("invalid active runner field")
    return {
        "raceId": detail["id"], "raceDate": day, "circuit": circuit,
        "capturedAt": at, "scheduledOffAt": off,
        "sourceKind": "original-frozen-preoff-method-opinions",
        "roster": starters, "opinions": opinions,
        "sourceVersions": {name: arm["modelVersion"] for name,arm in opinions.items()},
        "calibration": deepcopy(fitted_calibration),
        "odds": deepcopy(detail.get("officialPreoffTicketOdds")),
        "methodProvenance": {
            "mineta": "transparent public position/pace technique, not a published pick",
            "expert:form": "independent trained recent-form method",
            "expert:course": "independent trained course-distance method",
            "ai:learned": "existing pairwise logistic learner",
            "ai:bayes": "independent categorical Bayesian learner",
        },
    }
