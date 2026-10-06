#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from arvexq.prediction.final_marks import apply_core_marks

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))
MARK_ORDER = {"◎": 0, "○": 1, "▲": 2, "☆+": 3, "☆": 4, "△": 5, "注+": 6, "注": 7, "": 99}
PILLARS = ("ability", "record", "suitability", "pace", "support")


def iv(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def fv(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def api_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-unified-audit/1.1", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def finish_order(detail: dict[str, Any]) -> list[int]:
    result = detail.get("result") if isinstance(detail.get("result"), dict) else {}
    rows = result.get("finishers") or result.get("top5") or []
    found: list[tuple[int, int]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rank = iv(row.get("finish", row.get("rank", row.get("position"))))
        no = iv(row.get("horseNumber", row.get("number", row.get("horseNo"))))
        if rank > 0 and no > 0:
            found.append((rank, no))
    return [no for rank, no in sorted(found)]


def scrub_for_replay(detail: dict[str, Any], target_date: str) -> dict[str, Any]:
    """Best-effort retrospective replay base, never labelled exact historical."""
    d = copy.deepcopy(detail)
    for key in list(d):
        if key.lower() in {"result", "results", "payout", "payouts", "payoff", "finishers", "finishorder", "winner", "racestatus"}:
            d.pop(key, None)
    d.pop("preRacePrediction", None)
    for horse in d.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        for key in ("finishPosition", "resultTime", "currentFinish", "currentResult"):
            horse.pop(key, None)
        for key in ("allPastRuns", "recentRaces"):
            history = horse.get(key)
            if not isinstance(history, list):
                continue
            horse[key] = [
                run for run in history
                if isinstance(run, dict)
                and target_date not in str(run.get("date") or run.get("raceDate") or run.get("day") or "")
            ]
    return d


def mark_rows(rows: Any, *, lock: bool = False) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        no = iv(row.get("horseNumber", row.get("number", row.get("horseNo"))))
        if no <= 0:
            continue
        if lock:
            mark = str(row.get("mark") or "").strip()
            p = fv(row.get("decisionProbability", row.get("winnerProbability", row.get("p1Probability"))), -1.0)
        else:
            ev = row.get("integratedEvaluation") if isinstance(row.get("integratedEvaluation"), dict) else {}
            mark = str(ev.get("mark") or "").strip()
            p = fv(ev.get("winnerConsensusProbability", ev.get("winnerDecisionProbability", ev.get("p1Probability"))), -1.0)
        out.append({"no": no, "mark": mark, "p": p})
    return out


def replay_rank(detail: dict[str, Any]) -> list[int]:
    ranking = detail.get("factorRanking") if isinstance(detail.get("factorRanking"), list) else []
    out = [iv(x.get("horseNumber")) for x in ranking if isinstance(x, dict) and iv(x.get("horseNumber")) > 0]
    if out:
        return out
    rows = mark_rows(detail.get("horses"), lock=False)
    rows.sort(key=lambda x: (MARK_ORDER.get(str(x.get("mark") or ""), 98), -fv(x.get("p"), -1.0), x["no"]))
    return [x["no"] for x in rows]


def lock_rank(rows: list[dict[str, Any]]) -> list[int]:
    if any(fv(x.get("p"), -1.0) >= 0 for x in rows):
        return [x["no"] for x in sorted(rows, key=lambda x: (-fv(x.get("p"), -1.0), MARK_ORDER.get(x.get("mark", ""), 98), x["no"]))]
    return [x["no"] for x in sorted(rows, key=lambda x: (MARK_ORDER.get(x.get("mark", ""), 98), x["no"]))]


def init_metrics() -> dict[str, int]:
    return {"races": 0, "honmeiWin": 0, "honmeiTop2": 0, "honmeiTop3": 0, "winnerTop3": 0, "winnerTop5": 0, "winnerCoreMark": 0, "winnerAnyMark": 0}


def add_metrics(m: dict[str, int], order: list[int], rank: list[int], marks: dict[int, str]) -> None:
    if not order or not rank:
        return
    winner = order[0]
    honmei = next((no for no, mark in marks.items() if mark == "◎"), rank[0] if rank else 0)
    pos = order.index(honmei) + 1 if honmei in order else 999
    m["races"] += 1
    m["honmeiWin"] += int(pos == 1)
    m["honmeiTop2"] += int(pos <= 2)
    m["honmeiTop3"] += int(pos <= 3)
    m["winnerTop3"] += int(winner in rank[:3])
    m["winnerTop5"] += int(winner in rank[:5])
    wm = marks.get(winner, "")
    m["winnerCoreMark"] += int(wm in {"◎", "○", "▲"})
    m["winnerAnyMark"] += int(bool(wm))


def merge_metrics(dst: dict[str, int], src: dict[str, int]) -> None:
    for k, v in src.items():
        dst[k] = dst.get(k, 0) + int(v)


def rates(m: dict[str, int]) -> dict[str, Any]:
    n = max(0, int(m.get("races", 0)))
    out: dict[str, Any] = dict(m)
    for key in ("honmeiWin", "honmeiTop2", "honmeiTop3", "winnerTop3", "winnerTop5", "winnerCoreMark", "winnerAnyMark"):
        out[key + "Rate"] = round(m.get(key, 0) / n, 4) if n else None
    return out


def init_head_metrics() -> dict[str, int]:
    return {
        "races": 0,
        "coreHits": 0,
        "strengthHits": 0,
        "winHeadHits": 0,
        "coreWinAgree": 0,
        "coreWinAgreeHits": 0,
        "coreStrengthAgree": 0,
        "coreStrengthAgreeHits": 0,
        "allAgree": 0,
        "allAgreeHits": 0,
    }


def add_head_metrics(m: dict[str, int], order: list[int], detail: dict[str, Any]) -> tuple[int, int, int]:
    ranking = detail.get("factorRanking") if isinstance(detail.get("factorRanking"), list) else []
    if not order or not ranking:
        return 0, 0, 0
    winner = order[0]
    core = iv(ranking[0].get("horseNumber"))
    valid = [x for x in ranking if isinstance(x, dict) and iv(x.get("horseNumber")) > 0]
    strength_sorted = sorted(valid, key=lambda x: (iv((x.get("multiHead") or {}).get("strengthRank"), 999), iv((x.get("multiHead") or {}).get("winRank"), 999), iv(x.get("horseNumber"), 999)))
    strength = iv(strength_sorted[0].get("horseNumber")) if strength_sorted else 0
    mh = detail.get("multiHeadSummary") if isinstance(detail.get("multiHeadSummary"), dict) else {}
    win_head = iv(mh.get("winnerHorseNumber"))
    if not win_head:
        win_sorted = sorted(valid, key=lambda x: (iv((x.get("multiHead") or {}).get("winRank"), 999), iv((x.get("multiHead") or {}).get("strengthRank"), 999), iv(x.get("horseNumber"), 999)))
        win_head = iv(win_sorted[0].get("horseNumber")) if win_sorted else 0
    if not core or not strength or not win_head:
        return core, strength, win_head
    m["races"] += 1
    m["coreHits"] += int(core == winner)
    m["strengthHits"] += int(strength == winner)
    m["winHeadHits"] += int(win_head == winner)
    if core == win_head:
        m["coreWinAgree"] += 1
        m["coreWinAgreeHits"] += int(core == winner)
    if core == strength:
        m["coreStrengthAgree"] += 1
        m["coreStrengthAgreeHits"] += int(core == winner)
    if core == strength == win_head:
        m["allAgree"] += 1
        m["allAgreeHits"] += int(core == winner)
    return core, strength, win_head


def head_rates(m: dict[str, int]) -> dict[str, Any]:
    out = dict(m)
    n = m.get("races", 0)
    out["coreHitRate"] = round(m.get("coreHits", 0) / n, 4) if n else None
    out["strengthHitRate"] = round(m.get("strengthHits", 0) / n, 4) if n else None
    out["winHeadHitRate"] = round(m.get("winHeadHits", 0) / n, 4) if n else None
    for prefix in ("coreWinAgree", "coreStrengthAgree", "allAgree"):
        c = m.get(prefix, 0)
        out[prefix + "HitRate"] = round(m.get(prefix + "Hits", 0) / c, 4) if c else None
    return out


def init_pillar_miss() -> dict[str, int]:
    out = {"misses": 0, "winnerCoreTop3": 0, "winnerCoreTop5": 0, "winnerStrengthRank1": 0, "winnerWinRank1": 0}
    for p in PILLARS:
        out[f"winnerBetter_{p}"] = 0
        out[f"honmeiBetter_{p}"] = 0
        out[f"tie_{p}"] = 0
    return out


def add_pillar_miss(m: dict[str, int], order: list[int], detail: dict[str, Any], core: int) -> None:
    if not order or core == order[0]:
        return
    winner = order[0]
    ranking = detail.get("factorRanking") if isinstance(detail.get("factorRanking"), list) else []
    by_no = {iv(x.get("horseNumber")): x for x in ranking if isinstance(x, dict)}
    w = by_no.get(winner)
    h = by_no.get(core)
    if not w or not h:
        return
    m["misses"] += 1
    wrank = iv(w.get("rank"), 999)
    m["winnerCoreTop3"] += int(wrank <= 3)
    m["winnerCoreTop5"] += int(wrank <= 5)
    wm = w.get("multiHead") or {}
    m["winnerStrengthRank1"] += int(iv(wm.get("strengthRank"), 999) == 1)
    m["winnerWinRank1"] += int(iv(wm.get("winRank"), 999) == 1)
    wp = w.get("pillarRanks") or {}
    hp = h.get("pillarRanks") or {}
    for p in PILLARS:
        a = iv(wp.get(p), 999)
        b = iv(hp.get(p), 999)
        if a < b:
            m[f"winnerBetter_{p}"] += 1
        elif b < a:
            m[f"honmeiBetter_{p}"] += 1
        else:
            m[f"tie_{p}"] += 1


def resolved_end_date() -> date:
    if END_DATE:
        return datetime.strptime(END_DATE, "%Y-%m-%d").date()
    return date.today() - timedelta(days=1)


def main() -> None:
    end = resolved_end_date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    exact_total = init_metrics()
    replay_total = init_metrics()
    exact_by_circuit: dict[str, dict[str, int]] = defaultdict(init_metrics)
    replay_by_circuit: dict[str, dict[str, int]] = defaultdict(init_metrics)
    heads_total = init_head_metrics()
    heads_by_circuit: dict[str, dict[str, int]] = defaultdict(init_head_metrics)
    misses_by_circuit: dict[str, dict[str, int]] = defaultdict(init_pillar_miss)
    per_day: list[dict[str, Any]] = []
    changed = improved = worsened = equal = 0
    details_seen = finals_seen = exact_locks = replayed = 0

    for ds in dates:
        url = API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"})
        payload = api_json(url)
        details = payload.get("details") or []
        details_seen += len(details)
        day_exact = init_metrics()
        day_replay = init_metrics()
        day_finals = day_locks = day_replay_n = 0

        for detail in details:
            if not isinstance(detail, dict):
                continue
            order = finish_order(detail)
            if not order:
                continue
            finals_seen += 1
            day_finals += 1
            circuit = str(detail.get("circuit") or "unknown")

            lock = detail.get("preRacePrediction") if isinstance(detail.get("preRacePrediction"), dict) else {}
            locked_rows = mark_rows(lock.get("horses"), lock=True)
            locked_marks = {x["no"]: x["mark"] for x in locked_rows if x.get("mark")}
            locked_rank = lock_rank(locked_rows)
            locked_honmei = next((no for no, mark in locked_marks.items() if mark == "◎"), locked_rank[0] if locked_rank else 0)
            if locked_rows and locked_rank and locked_honmei:
                add_metrics(day_exact, order, locked_rank, locked_marks)
                add_metrics(exact_by_circuit[circuit], order, locked_rank, locked_marks)
                exact_locks += 1
                day_locks += 1

            replay = scrub_for_replay(detail, ds)
            try:
                apply_core_marks(replay)
            except Exception as exc:
                print("REPLAY_ERROR", ds, detail.get("id"), type(exc).__name__, str(exc)[:140])
                continue
            replay_rows = mark_rows(replay.get("horses"), lock=False)
            replay_marks = {x["no"]: x["mark"] for x in replay_rows if x.get("mark")}
            rr = replay_rank(replay)
            replay_honmei = next((no for no, mark in replay_marks.items() if mark == "◎"), rr[0] if rr else 0)
            if rr and replay_honmei:
                add_metrics(day_replay, order, rr, replay_marks)
                add_metrics(replay_by_circuit[circuit], order, rr, replay_marks)
                core, _, _ = add_head_metrics(heads_total, order, replay)
                add_head_metrics(heads_by_circuit[circuit], order, replay)
                add_pillar_miss(misses_by_circuit[circuit], order, replay, core)
                replayed += 1
                day_replay_n += 1

            if locked_honmei and replay_honmei and locked_honmei != replay_honmei:
                changed += 1
                old_pos = order.index(locked_honmei) + 1 if locked_honmei in order else 999
                new_pos = order.index(replay_honmei) + 1 if replay_honmei in order else 999
                if new_pos < old_pos:
                    improved += 1
                elif new_pos > old_pos:
                    worsened += 1
                else:
                    equal += 1

        merge_metrics(exact_total, day_exact)
        merge_metrics(replay_total, day_replay)
        per_day.append({"date": ds, "details": len(details), "finals": day_finals, "exactLocked": rates(day_exact), "currentReplay": rates(day_replay)})
        print("DAY", ds, "details", len(details), "finals", day_finals, "locked", day_locks, "replay", day_replay_n, "lockedHonmeiWin", rates(day_exact).get("honmeiWinRate"), "replayHonmeiWin", rates(day_replay).get("honmeiWinRate"))

    result = {
        "version": "arvexq-unified-prediction-audit-v2",
        "start": dates[0],
        "end": dates[-1],
        "days": DAYS,
        "detailsSeen": details_seen,
        "finalsSeen": finals_seen,
        "exactLockedRaces": exact_locks,
        "replayedRaces": replayed,
        "exactLocked": rates(exact_total),
        "currentFourPillarReplay": rates(replay_total),
        "exactByCircuit": {k: rates(v) for k, v in sorted(exact_by_circuit.items())},
        "replayByCircuit": {k: rates(v) for k, v in sorted(replay_by_circuit.items())},
        "decisionHeads": head_rates(heads_total),
        "decisionHeadsByCircuit": {k: head_rates(v) for k, v in sorted(heads_by_circuit.items())},
        "pillarMissesByCircuit": {k: dict(v) for k, v in sorted(misses_by_circuit.items())},
        "honmeiChanged": {"races": changed, "improved": improved, "worsened": worsened, "equal": equal},
        "perDay": per_day,
        "warning": "exactLocked is the only exact contemporaneous pre-race evaluation. currentFourPillarReplay and decision-head diagnostics are retrospective: result/payout and target-day history are scrubbed, but saved detail may contain later-mutated non-result fields.",
    }
    print("ARVEXQ_UNIFIED_AUDIT_JSON=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
