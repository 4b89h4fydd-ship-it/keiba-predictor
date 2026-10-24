"""Adapter for the replacement three-analysis forecast. No legacy scorer is called."""
from datetime import datetime
from zoneinfo import ZoneInfo
from .new_method import VERSION, load_model, predict

JST=ZoneInfo("Asia/Tokyo")


def _has_result_evidence(value):
    """Exclude posted outcomes; permit empty pre-off result placeholders."""
    if not value:
        return False
    if not isinstance(value, dict):
        return True
    if set(value) - {"status", "finishers", "payouts"}:
        return True
    if value.get("finishers") or value.get("payouts"):
        return True
    return str(value.get("status") or "").strip() not in {
        "", "未確定", "未取得", "発走前", "未発走"
    }


def build_prediction(facts, now=None):
    if not isinstance(facts, dict) or facts.get("circuit") not in ("中央", "地方", "jra", "nar"):
        return None
    if _has_result_evidence(facts.get("result")) or facts.get("raceStatus") in ("速報", "確定", "終了"):
        return None
    if not isinstance(facts.get("date"), str):
        return None
    post=facts.get("scheduledStartTime") or facts.get("startTime")
    if not isinstance(post, str) or len(post)<5:
        return None
    try:
        scheduled=datetime.fromisoformat(facts["date"]+"T"+post[:5]+":00").replace(tzinfo=JST)
        current=now or datetime.now(JST)
        current=current.replace(tzinfo=JST) if current.tzinfo is None else current.astimezone(JST)
        if current>=scheduled:
            return None
    except (ValueError, TypeError):
        return None
    circuit={"jra":"中央", "nar":"地方"}.get(facts["circuit"],facts["circuit"])
    model=load_model(circuit)
    if model is None:
        return None
    race=dict(facts)
    race["circuit"]=circuit
    # Pre-off placeholders are not finish evidence and must not block
    # the scorer's explicit "no result data" leakage guard.
    race.pop("result", None)
    videos=race.pop("_internalVideoFeatures",None)
    quoted=race.pop("_internalThreeWayOdds",None)
    try:
        return predict(race,model,videos=videos,quoted_odds=quoted)
    except (ValueError,KeyError,TypeError,OverflowError):
        # Uncalibrated, missing, mismatched or damaged data MUST NOT silently
        # trigger legacy scoring or produce made-up probabilities.
        return None
