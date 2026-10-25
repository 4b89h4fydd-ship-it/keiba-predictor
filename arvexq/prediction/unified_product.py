"""ARVEXQ unified, race-specific, single-source pre-off forecast product.

Every visible mark, race-pace observation and candidate ticket must originate
from the SAME previously trained, date-isolated model prediction. The video
channel stays unavailable until independently reviewed horse identities exist.
No after-off materialization and no Stage64 or subjective override.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite

from arvexq.forecast.engine import _has_result_evidence
from arvexq.prediction.learned_scenarios import VERSION as MODEL_VERSION, race_family
from arvexq.prediction.new_forecast import build_forecast
from arvexq.prediction.prerace_archive import JST, post_at
from arvexq.core.runner_status import is_inactive_runner

VERSION = "arvexq-unified-live-v1"
SYMBOLS = ("◎", "○", "▲", "△", "☆", "注")
BET_KINDS = {"馬連", "ワイド", "馬単", "3連複", "3連単"}


def _timestamp(stamp):
    try:
        v = datetime.fromisoformat(str(stamp))
        return v.astimezone(JST) if v.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def _core_valid(race, source):
    if not isinstance(race, dict) or not isinstance(source, dict):
        return False
    if source.get("version") != VERSION or source.get("raceId") != race.get("id"):
        return False
    if source.get("raceDate") != race.get("date") or source.get("circuit") != race.get("circuit"):
        return False
    if source.get("modelVersion") != MODEL_VERSION or source.get("modelFamily") != race_family(race):
        return False
    if source.get("researchOnly") is not True or source.get("probabilitiesCalibrated") is not False:
        return False
    capture, off = _timestamp(source.get("capturedAt")), post_at(race)
    if not capture or not off or capture >= off or source.get("trainedThrough", "9999") >= race.get("date", ""):
        return False
    actual = {h.get("horseNumber"): h.get("name") for h in race.get("horses") or []
              if isinstance(h, dict) and not is_inactive_runner(h)}
    expected = {row.get("horseNumber"): row.get("name") for row in source.get("roster") or []
                if isinstance(row, dict)}
    if len(actual) < 3 or actual != expected:
        return False
    marks = source.get("marks")
    if not isinstance(marks, list) or not marks:
        return False
    seen, count = set(), 0
    for row in marks:
        if not isinstance(row, dict):
            return False
        no, symbol = row.get("horseNumber"), row.get("markSymbol")
        if type(no) is not int or no not in actual or no in seen or symbol not in SYMBOLS:
            return False
        seen.add(no)
        count += symbol == "◎"
    if count != 1:
        return False
    return True


def verified(race):
    """Revalidate immutable receipt and its hash, not only claimed IDs."""
    candidate = (race or {}).get("unifiedForecast")
    if not _core_valid(race, candidate):
        return None
    canonical = {k: v for k, v in candidate.items() if k != "receiptSha256"}
    digest = sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return candidate if candidate.get("receiptSha256") == digest else None


def generate(race, model, *, now=None):
    now = now or datetime.now(JST)
    if now.tzinfo is None:
        raise ValueError("timezone-aware time required")
    now = now.astimezone(JST)
    off = post_at(race)
    if not off or now >= off or race.get("date") != now.date().isoformat() or _has_result_evidence(race.get("result")):
        raise ValueError("only truly upcoming, date-matched races may be predicted")
    if race.get("circuit") not in ("中央", "地方") or race_family(race) == "banei":
        raise ValueError("central/local only, Obihiro banei disabled")
    training = model.get("training") if isinstance(model, dict) else None
    if (not isinstance(training, dict) or model.get("version") != MODEL_VERSION
            or training.get("lastDate", "9999") >= race["date"]
            or training.get("circuit") != race["circuit"]
            or training.get("family") != race_family(race)):
        raise ValueError("matching earlier-trained central/local/family model required")
    # Reject nonempty results, but do not convert an empty pending placeholder
    # into artificial retrospective evidence.
    detail = deepcopy(race)
    if not _has_result_evidence(detail.get("result")):
        detail.pop("result", None)
    prediction = build_forecast(detail, model, compare_research_tickets=False)
    if (prediction.get("predictionStatus") != "candidate-analysis"
            or prediction.get("analysisType") != "preoff-candidate"
            or prediction.get("productionEligible") is not False):
        raise ValueError("unified before-off model not available")
    rows = prediction.get("scenarioAnalysis", {}).get("reports") or []
    scenarios = prediction.get("scenarioAnalysis", {}).get("scenarios") or []
    marks = []
    for horse in prediction.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        evaluation = horse.get("integratedEvaluation") or {}
        symbol = evaluation.get("mark")
        if symbol not in SYMBOLS:
            continue
        no = int(horse["horseNumber"])
        probs = evaluation.get("modelProbabilities") or {}
        def pair(label):
            p = probs.get(label)
            return [round(float(x), 6) for x in p] if isinstance(p, list) and len(p) == 2 else None
        marks.append({"horseNumber": no, "markSymbol": symbol,
                      "winProbabilityRange": pair("win"), "top3ProbabilityRange": pair("top3"),
                      "reason": str(evaluation.get("markReason") or "")})
    if sum(row["markSymbol"] == "◎" for row in marks) != 1:
        raise ValueError("unique unified ◎ must exist")
    active = [h for h in race.get("horses") or [] if isinstance(h, dict)
              and h.get("horseNumber") and not is_inactive_runner(h)]
    roster = [{"horseNumber": int(h["horseNumber"]), "name": str(h.get("name") or "")}
              for h in active]
    if len(set(x["horseNumber"] for x in roster)) != len(roster) or any(not x["name"] for x in roster):
        raise ValueError("observed complete horse roster required")
    head = next(m["horseNumber"] for m in marks if m["markSymbol"] == "◎")
    # A relative early position is not proof of start speed, tactical intent or
    # the actual race outcome. This is only observed past corner position.
    positioned = [r for r in rows if r.get("featureValues", {}).get("early_position") is not None]
    leaders = sorted(positioned, key=lambda r: (-r["featureValues"]["early_position"],
                                                 r["horseNumber"]))[:4]
    scenario_ids = [s["id"] for s in scenarios]
    pace = {
        "status": "past-corner-evidence-scenario-sensitivity",
        "likelyForwardNumbers": [r["horseNumber"] for r in leaders],
        "observedPositionCoverage": len(positioned),
        "activeRunners": len(roster),
        "testedScenarios": scenario_ids,
        "scenarioFrequencyMeasured": False,
        "firstCornerMetersOfficial": race.get("firstCornerMetersOfficial"),
        "text": ("過去走の初角位置から前に行く候補は"
                 + "、".join(str(r["horseNumber"]) + "番" for r in leaders)
                 + "。前争い・控える想定を比較。発生頻度は未検証。"
                 if leaders else "過去走の初角順位が不足。隊列を断定せず、通常展開のみ評価。")
    }
    # Tickets are derived exclusively from the same model's finishing-order
    # distribution and the same marks. Never fabricate odds, or recommend
    # unknown expected returns to a user who may spend real money.
    bets = {"status": "見送り", "items": [],
            "reason": "未検証確率または発走前の券種別実オッズ不足。買い目を捏造しない",
            "sameModelAndMarks": True, "maximumPoints": 5}
    market = race.get("preOffMarket") or {}
    if (market.get("provenanceVerified") is True
            and isinstance(market.get("odds"), dict)
            and isinstance(race.get("availableBetTypes"), list)
            and scenarios):
        from arvexq.betting.scenario_tickets import compare_tickets
        source = deepcopy(prediction)
        source["preOffMarket"] = deepcopy(market)
        source["availableBetTypes"] = list(race["availableBetTypes"])
        source["placePlaces"] = race.get("placePlaces")
        try:
            compared = compare_tickets(source, scenarios, model_version=MODEL_VERSION,
                                       max_points=5)
            choices = compared.get("comparisons") or compared.get("ticketComparisons") or []
            candidates = []
            for row in choices:
                if (row.get("kind") not in BET_KINDS or
                        not row.get("expectedReturnRange") or
                        min(row["expectedReturnRange"]) < 1.05):
                    continue
                for combo in row.get("combos") or []:
                    if len(candidates) == 5:
                        break
                    if head not in combo:
                        continue
                    candidates.append({"kind": row["kind"], "combo": list(combo),
                                       "modelledReturnRange": row["expectedReturnRange"]})
            if candidates:
                bets = {"status": "研究候補・購入推奨ではない",
                        "items": candidates, "maximumPoints": 5,
                        "sameModelAndMarks": True,
                        "reason": "同一モデルの条件付き順序分布と実オッズによる参考候補。実測校正・ROI保証なし"}
        except (KeyError, ValueError, TypeError, OverflowError):
            pass
    product = {
        "version": VERSION, "raceId": race["id"], "raceDate": race["date"],
        "circuit": race["circuit"], "modelFamily": race_family(race),
        "specialHandling": ("新馬・既走ゼロを欠損として分離" if "新馬" in str(race.get("title") or "")
                            else "障害専用" if race_family(race) == "jumps" else "通常"),
        "capturedAt": now.isoformat(), "trainedThrough": training["lastDate"],
        "modelVersion": MODEL_VERSION, "modelHash": model["modelHash"],
        "roster": roster, "marks": marks, "honmeiHorseNumber": head,
        "pace": pace, "ticketPlan": bets,
        "researchOnly": True, "probabilitiesCalibrated": False,
        "videoIdentityValidated": False, "humanOverrides": False,
        "source": "date-held-out-per-circuit-learned-whole-career-model",
    }
    product["receiptSha256"] = sha256(json.dumps(product, ensure_ascii=False,
                                                sort_keys=True, separators=(",", ":"),
                                                allow_nan=False).encode()).hexdigest()
    if not _core_valid(race, product) or verified(dict(race, unifiedForecast=product)) is None:
        raise ValueError("unified product source/marks/roster self-check failed")
    return product
