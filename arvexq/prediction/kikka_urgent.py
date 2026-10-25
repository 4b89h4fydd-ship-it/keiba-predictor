"""Urgent Kyoto 11R pre-off research candidate, without retired Stage64.

Only independently retrieved, D1-persisted race facts may produce this
date-bounded challenger output. Published mark candidates are explicitly
UNCALIBRATED, non-betting, and must not overwrite older sealed forecasts.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json

from arvexq.pipeline.persisted_inputs import may_create_prerace_prediction, verify_persisted_facts
from arvexq.prediction.new_forecast import build_forecast
from arvexq.prediction.learned_scenarios import VERSION as LEARNED_VERSION
from arvexq.prediction.prerace_archive import JST, post_at

RACE_ID = "jra-2026-10-25-京都-11"
RACE_DATE = "2026-10-25"
EXPECTED = (
    "エムズビギン", "コンジェスタス", "アウダーシア",
    "ショウナンガルフ", "ジャスティンシカゴ", "バステール",
    "ラージアンサンブル", "ロブチェン", "ゴーイントゥスカイ",
    "ダノンヒストリー", "アスクエジンバラ", "サノノグレーター",
    "キンググローリー", "マジョレルブルー", "シートゥサミット",
    "ショウナンハヤナミ", "チャリングクロス", "ナリタエスペランサ",
)
VERSION = "arvexq-kikka-urgent-learned-candidate-v1"
MARKS = frozenset(("◎", "○", "▲", "△", "☆", "注"))


def verified_entry(detail: dict, summary: dict, now=None) -> None:
    """Strict official-entry consistency and before-off check."""
    if (not isinstance(detail, dict) or not isinstance(summary, dict)
            or detail.get("id") != RACE_ID or summary.get("id") != RACE_ID
            or detail.get("date") != RACE_DATE or summary.get("date") != RACE_DATE
            or detail.get("track") != "京都" or summary.get("track") != "京都"
            or detail.get("circuit") != "中央"
            or int(detail.get("raceNumber") or 0) != 11
            or int(detail.get("distance") or 0) != 3000
            or "芝" not in str(detail.get("surface") or "")
            or detail.get("scheduledStartTime", detail.get("startTime"))[:5] != "15:40"):
        raise ValueError("JRA official Kyoto 11R identity/course/start mismatch")
    current = {
        h.get("horseNumber"): h.get("name")
        for h in detail.get("horses") or [] if isinstance(h, dict)
    }
    source = {
        h.get("horseNumber"): h.get("name")
        for h in summary.get("horses") or [] if isinstance(h, dict)
    }
    expected = {i: name for i, name in enumerate(EXPECTED, 1)}
    if len(current) != 18 or current != expected or (source and source != expected):
        raise ValueError("official 18-runner roster mismatch: no inferred runners")
    if detail.get("result") or str(detail.get("raceStatus") or "") in ("確定", "終了", "速報"):
        raise ValueError("race result already present: no retrospective preoff prediction")
    if not may_create_prerace_prediction(detail, now):
        raise ValueError("official 15:40 scheduled start passed")
    if post_at(detail) is None:
        raise ValueError("no trusted official post time")


def compact_candidate(detail: dict, summary: dict, trained: dict, now=None) -> dict:
    """Only original, earlier-trained challenger marks; NO imagined bet edges."""
    now = now or datetime.now(JST)
    verified_entry(detail, summary, now)
    trained_on = (trained.get("training") or {})
    if (trained.get("version") != LEARNED_VERSION or
            trained_on.get("circuit") != "中央" or
            trained_on.get("family") != "flat" or
            trained_on.get("lastDate", "9999") >= RACE_DATE):
        raise ValueError("earlier-dated JRA flat-trained model required")
    predicted = build_forecast(detail, trained)
    if (predicted.get("analysisType") != "preoff-candidate"
            or predicted.get("predictionStatus") != "candidate-analysis"
            or predicted.get("productionEligible") is not False):
        raise ValueError("eligible original preoff challenger not produced")
    by_no = {}
    for row in predicted.get("horses") or []:
        if not isinstance(row, dict):
            continue
        candidate = row.get("integratedEvaluation") or {}
        symbol = candidate.get("mark")
        if symbol not in MARKS:
            continue
        no = row.get("horseNumber")
        if type(no) is not int or not 1 <= no <= 18:
            raise ValueError("unrecognized forecast horse")
        by_no[no] = symbol
    if sum(m == "◎" for m in by_no.values()) != 1:
        raise ValueError("no unique learned ◎ candidate, not ready for display")
    if (predicted.get("recommendedBetPlan") or {}).get("items"):
        raise ValueError("uncalibrated betting advice must not be published")
    exact = sorted(by_no.items())
    source_hash = sha256(json.dumps(
        {"raceId": RACE_ID, "roster": EXPECTED, "modelHash": trained["modelHash"],
         "marks": exact}, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    # No whole-card histories/AI orders stored in the public preview.
    return {
        "version": VERSION, "raceId": RACE_ID, "raceDate": RACE_DATE,
        "capturedAt": now.isoformat(),
        "trainedThrough": trained_on["lastDate"],
        "trainingRaceCount": trained_on.get("races"),
        "modelVersion": trained["version"], "modelHash": trained["modelHash"],
        "sourceHash": source_hash,
        "provisional": True, "productionEligible": False,
        "verifiedWinRate": False, "verifiedTop3Rate": False,
        "probabilityCalibration": "unverified",
        "bettingRecommended": False,
        "marks": [{"horseNumber": no, "mark": mark} for no, mark in exact],
        "label": "菊花賞・発走前の新方式候補（学習済み／実測校正は未完了）",
    }


def overlay_preserving_facts(detail: dict, source: dict, summary: dict, candidate: dict,
                             now=None) -> dict:
    """Never modify official facts or replace an already existing pre-off seal."""
    from copy import deepcopy
    if any(key in source for key in ("preRacePrediction", "preRaceBet", "preRaceBetPlan")):
        raise ValueError("existing sealed pre-off evidence is immutable")
    verified_entry(detail, summary, now)
    if detail != source:
        raise ValueError("D1 readback changed since model inference")
    if candidate.get("version") != VERSION or candidate.get("raceId") != RACE_ID:
        raise ValueError("cross-race model candidate")
    out = deepcopy(source)
    out["kikkaCandidate"] = deepcopy(candidate)
    return out
