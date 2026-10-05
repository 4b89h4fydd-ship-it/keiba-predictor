#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any

from arvexq.prediction.final_marks import apply_core_marks

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
TARGET_DATE = os.environ.get("ARVEXQ_DATE", "2026-10-05")
MARKS = ("◎", "○", "▲", "☆+", "☆", "△", "注", "注+")


def iv(v: Any, d: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def fv(v: Any, d: float = -1e18) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def api_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-old-new-audit/1.0", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def finish_order(detail: dict[str, Any]) -> list[int]:
    result = detail.get("result") or {}
    rows = result.get("finishers") or result.get("top5") or []
    out: list[tuple[int, int]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        f = iv(row.get("finish", row.get("rank", row.get("position"))))
        n = iv(row.get("horseNumber", row.get("number", row.get("horseNo"))))
        if f > 0 and n > 0:
            out.append((f, n))
    return [n for f, n in sorted(out)]


def mark_from_obj(obj: dict[str, Any]) -> str:
    ev = obj.get("integratedEvaluation") if isinstance(obj.get("integratedEvaluation"), dict) else {}
    for source in (obj, ev):
        for key in ("aiMark", "mark", "predictionMark", "symbol", "predictionSymbol"):
            value = source.get(key)
            if isinstance(value, str) and value.strip() in MARKS:
                return value.strip()
    return ""


def marks_from_horses(rows: Any) -> dict[int, str]:
    if not isinstance(rows, list):
        return {}
    out: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        n = iv(row.get("horseNumber", row.get("number", row.get("horseNo"))))
        m = mark_from_obj(row)
        if n > 0 and m:
            out[n] = m
    return out


def walk_candidates(obj: Any, path: str = "root"):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from walk_candidates(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_candidates(v, f"{path}[{i}]")


def find_prerace_snapshot(detail: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for path, obj in walk_candidates(detail):
        low = path.lower()
        if not any(token in low for token in ("lock", "prerace", "pre_race", "snapshot", "frozen", "prediction")):
            continue
        horses = obj.get("horses")
        if isinstance(horses, list) and len(horses) >= 2:
            marks = marks_from_horses(horses)
            score = len(marks) * 100 + len(horses)
            if "lock" in low or "frozen" in low:
                score += 1000
            if "prerace" in low or "pre_race" in low:
                score += 500
            candidates.append((score, path, obj))
    if not candidates:
        return None, ""
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0][2], candidates[0][1]


def legacy_marks(detail: dict[str, Any], snapshot: dict[str, Any] | None) -> tuple[dict[int, str], str]:
    if snapshot:
        marks = marks_from_horses(snapshot.get("horses"))
        if marks:
            return marks, "frozen/prerace snapshot"

    # The final-mark wrapper saves the mark produced immediately before the new core
    # marks replace it. This is the strongest fallback when a frozen snapshot is not
    # exposed by the public day payload.
    legacy: dict[int, str] = {}
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        n = iv(horse.get("horseNumber"))
        ev = horse.get("integratedEvaluation") or {}
        m = str(ev.get("legacyComputedMark") or "").strip()
        if n > 0 and m in MARKS:
            legacy[n] = m
    if legacy:
        return legacy, "legacyComputedMark fallback"

    current = marks_from_horses(detail.get("horses"))
    engine = str(detail.get("markEngineVersion") or "")
    if current and "four-pillar" not in engine:
        return current, "stored old mark"

    # Last-resort legacy P1 order: label explicitly so it is never misrepresented as
    # the historical displayed mark.
    scored: list[tuple[float, int]] = []
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        n = iv(horse.get("horseNumber"))
        ev = horse.get("integratedEvaluation") or {}
        if n > 0 and ev.get("p1Score") is not None:
            scored.append((fv(ev.get("p1Score")), n))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = {n: m for (_, n), m in zip(scored, MARKS)}
    return out, "legacy p1Score fallback"


def scrub_postrace(detail: dict[str, Any]) -> dict[str, Any]:
    d = copy.deepcopy(detail)
    for key in list(d):
        low = key.lower()
        if low in {"result", "results", "payout", "payouts", "payoff", "finishers", "finishorder", "winner"}:
            d.pop(key, None)

    # A horse cannot legitimately have the same race in its pre-race history. Remove
    # target-day history rows when dates are present. This is conservative and avoids
    # obvious result leakage during retrospective replay.
    for horse in d.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        for key in ("allPastRuns", "recentRaces"):
            rows = horse.get(key)
            if not isinstance(rows, list):
                continue
            kept = []
            for run in rows:
                if not isinstance(run, dict):
                    continue
                date_text = str(run.get("date") or run.get("raceDate") or run.get("day") or "")
                if TARGET_DATE in date_text:
                    continue
                kept.append(run)
            horse[key] = kept
    return d


def replay_base(detail: dict[str, Any], snapshot: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    if snapshot and isinstance(snapshot.get("horses"), list):
        base = copy.deepcopy(snapshot)
        # Fill immutable race context if the lock stores only the horse snapshot.
        for key in ("id", "date", "circuit", "track", "venue", "raceNumber", "distance", "surface", "condition", "going", "weather", "bias", "trackBias"):
            if base.get(key) in (None, "") and detail.get(key) not in (None, ""):
                base[key] = copy.deepcopy(detail.get(key))
        return scrub_postrace(base), "prerace snapshot"
    return scrub_postrace(detail), "current saved detail (post-race fields scrubbed)"


def pct(hit: int, n: int) -> str:
    return "—" if not n else f"{hit}/{n} ({100.0*hit/n:.1f}%)"


def main() -> None:
    url = API_BASE + "/api/day?" + urllib.parse.urlencode({"date": TARGET_DATE, "details": "1"})
    payload = api_json(url)
    details = payload.get("details") or []
    rows: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    replay_counts: Counter[str] = Counter()

    for detail in details:
        if not isinstance(detail, dict):
            continue
        order = finish_order(detail)
        if not order:
            continue
        winner = order[0]
        snapshot, snapshot_path = find_prerace_snapshot(detail)
        old, old_source = legacy_marks(detail, snapshot)
        base, replay_source = replay_base(detail, snapshot)
        apply_core_marks(base)
        new = marks_from_horses(base.get("horses"))
        if not old or not new:
            continue
        source_counts[old_source] += 1
        replay_counts[replay_source] += 1
        old_best = next((n for n, m in old.items() if m == "◎"), 0)
        new_best = next((n for n, m in new.items() if m == "◎"), 0)
        old_pos = order.index(old_best) + 1 if old_best in order else 999
        new_pos = order.index(new_best) + 1 if new_best in order else 999
        rows.append({
            "id": str(detail.get("id") or ""),
            "circuit": str(detail.get("circuit") or ""),
            "track": str(detail.get("track") or detail.get("venue") or ""),
            "raceNo": iv(detail.get("raceNumber", detail.get("raceNo"))),
            "winner": winner,
            "oldBest": old_best,
            "newBest": new_best,
            "oldBestPos": old_pos,
            "newBestPos": new_pos,
            "oldWinnerMark": old.get(winner, ""),
            "newWinnerMark": new.get(winner, ""),
            "oldSource": old_source,
            "replaySource": replay_source,
            "snapshotPath": snapshot_path,
        })

    def metrics(which: str) -> dict[str, int]:
        best_pos = f"{which}BestPos"
        winner_mark = f"{which}WinnerMark"
        return {
            "races": len(rows),
            "bestWin": sum(r[best_pos] == 1 for r in rows),
            "bestTop2": sum(r[best_pos] <= 2 for r in rows),
            "bestTop3": sum(r[best_pos] <= 3 for r in rows),
            "winnerCore": sum(r[winner_mark] in {"◎", "○", "▲"} for r in rows),
            "winnerAnyMark": sum(bool(r[winner_mark]) for r in rows),
        }

    old_m, new_m = metrics("old"), metrics("new")
    changed = [r for r in rows if r["oldBest"] != r["newBest"]]
    improved = sum(r["newBestPos"] < r["oldBestPos"] for r in changed)
    worsened = sum(r["newBestPos"] > r["oldBestPos"] for r in changed)
    equal = sum(r["newBestPos"] == r["oldBestPos"] for r in changed)

    print(f"ARVEXQ OLD vs NEW {TARGET_DATE}")
    print(f"API={url}")
    print(f"details={len(details)} evaluable={len(rows)}")
    print("OLD_SOURCE", json.dumps(source_counts, ensure_ascii=False, sort_keys=True))
    print("NEW_REPLAY_SOURCE", json.dumps(replay_counts, ensure_ascii=False, sort_keys=True))
    print("metric\tOLD\tNEW")
    for label, key in (("◎1着", "bestWin"), ("◎連対", "bestTop2"), ("◎3着内", "bestTop3"), ("勝ち馬=◎○▲", "winnerCore"), ("勝ち馬=全印内", "winnerAnyMark")):
        print(f"{label}\t{pct(old_m[key], len(rows))}\t{pct(new_m[key], len(rows))}")
    print(f"◎変更={len(changed)} 改善={improved} 悪化={worsened} 着順同等={equal}")
    print("RACES")
    for r in rows:
        print(
            f"{r['circuit'] or '-'} {r['track'] or '-'} {r['raceNo']}R "
            f"勝={r['winner']} 旧◎={r['oldBest']}({r['oldBestPos']}着) "
            f"新◎={r['newBest']}({r['newBestPos']}着) "
            f"勝馬印 旧={r['oldWinnerMark'] or '無'} 新={r['newWinnerMark'] or '無'}"
        )
    out = {
        "date": TARGET_DATE,
        "evaluable": len(rows),
        "old": old_m,
        "new": new_m,
        "changed": len(changed),
        "improved": improved,
        "worsened": worsened,
        "equal": equal,
        "oldSource": dict(source_counts),
        "newReplaySource": dict(replay_counts),
        "rows": rows,
    }
    print("ARVEXQ_COMPARISON_JSON=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
