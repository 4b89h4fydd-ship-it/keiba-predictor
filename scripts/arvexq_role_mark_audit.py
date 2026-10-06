#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))
MARKS = ("◎", "○", "▲", "☆+", "☆", "△", "注+", "注")


def iv(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def api_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"user-agent": "ARVEXQ-role-audit/1.0", "accept": "application/json"},
    )
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


def locked_marks(detail: dict[str, Any]) -> dict[int, str]:
    lock = detail.get("preRacePrediction") if isinstance(detail.get("preRacePrediction"), dict) else {}
    rows = lock.get("horses") if isinstance(lock.get("horses"), list) else []
    out: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        no = iv(row.get("horseNumber", row.get("number", row.get("horseNo"))))
        mark = str(row.get("mark") or "").strip()
        if no > 0 and mark:
            out[no] = mark
    return out


def empty_metrics() -> dict[str, Any]:
    return {
        "races": 0,
        "honmeiWin": 0,
        "honmeiTop2": 0,
        "honmeiTop3": 0,
        "maruSecond": 0,
        "maruTop2": 0,
        "maruTop3": 0,
        "triangleTop3": 0,
        "starPlusWin": 0,
        "starPlusTop3": 0,
        "starTop3": 0,
        "deltaTop3": 0,
        "notePlusTop3": 0,
        "noteTop3": 0,
        "podiumAllMarked": 0,
        "podiumAtLeast2Marked": 0,
        "winnerMarked": 0,
        "secondMarked": 0,
        "thirdMarked": 0,
        "firstSecondRoleExact": 0,
        "podiumMarkedSum": 0,
        "markSetSizeSum": 0,
        "finishMark1": Counter(),
        "finishMark2": Counter(),
        "finishMark3": Counter(),
    }


def horse_with_mark(marks: dict[int, str], target: str) -> int:
    return next((no for no, mark in marks.items() if mark == target), 0)


def add_race(m: dict[str, Any], order: list[int], marks: dict[int, str]) -> None:
    if len(order) < 3 or not marks:
        return
    top3 = order[:3]
    pos = {no: idx + 1 for idx, no in enumerate(order)}
    honmei = horse_with_mark(marks, "◎")
    maru = horse_with_mark(marks, "○")
    triangle = horse_with_mark(marks, "▲")
    star_plus = horse_with_mark(marks, "☆+")
    star = horse_with_mark(marks, "☆")
    delta = horse_with_mark(marks, "△")
    note_plus = horse_with_mark(marks, "注+")
    note = horse_with_mark(marks, "注")
    marked_top3 = sum(1 for no in top3 if bool(marks.get(no)))

    m["races"] += 1
    m["honmeiWin"] += int(pos.get(honmei, 999) == 1)
    m["honmeiTop2"] += int(pos.get(honmei, 999) <= 2)
    m["honmeiTop3"] += int(pos.get(honmei, 999) <= 3)
    m["maruSecond"] += int(pos.get(maru, 999) == 2)
    m["maruTop2"] += int(pos.get(maru, 999) <= 2)
    m["maruTop3"] += int(pos.get(maru, 999) <= 3)
    m["triangleTop3"] += int(pos.get(triangle, 999) <= 3)
    m["starPlusWin"] += int(pos.get(star_plus, 999) == 1)
    m["starPlusTop3"] += int(pos.get(star_plus, 999) <= 3)
    m["starTop3"] += int(pos.get(star, 999) <= 3)
    m["deltaTop3"] += int(pos.get(delta, 999) <= 3)
    m["notePlusTop3"] += int(pos.get(note_plus, 999) <= 3)
    m["noteTop3"] += int(pos.get(note, 999) <= 3)
    m["podiumAllMarked"] += int(marked_top3 == 3)
    m["podiumAtLeast2Marked"] += int(marked_top3 >= 2)
    m["winnerMarked"] += int(bool(marks.get(top3[0])))
    m["secondMarked"] += int(bool(marks.get(top3[1])))
    m["thirdMarked"] += int(bool(marks.get(top3[2])))
    m["firstSecondRoleExact"] += int(marks.get(top3[0]) == "◎" and marks.get(top3[1]) == "○")
    m["podiumMarkedSum"] += marked_top3
    m["markSetSizeSum"] += sum(1 for mark in marks.values() if mark in MARKS)
    m["finishMark1"][marks.get(top3[0], "無印")] += 1
    m["finishMark2"][marks.get(top3[1], "無印")] += 1
    m["finishMark3"][marks.get(top3[2], "無印")] += 1


def merge(dst: dict[str, Any], src: dict[str, Any]) -> None:
    for k, v in src.items():
        if isinstance(v, Counter):
            dst[k].update(v)
        elif k != "races":
            dst[k] += v
    dst["races"] += src["races"]


def summarize(m: dict[str, Any]) -> dict[str, Any]:
    n = int(m.get("races", 0))
    out: dict[str, Any] = {"races": n}
    count_keys = (
        "honmeiWin", "honmeiTop2", "honmeiTop3", "maruSecond", "maruTop2", "maruTop3",
        "triangleTop3", "starPlusWin", "starPlusTop3", "starTop3", "deltaTop3",
        "notePlusTop3", "noteTop3", "podiumAllMarked", "podiumAtLeast2Marked",
        "winnerMarked", "secondMarked", "thirdMarked", "firstSecondRoleExact",
    )
    for key in count_keys:
        out[key] = int(m.get(key, 0))
        out[key + "Rate"] = round(out[key] / n, 4) if n else None
    out["avgPodiumMarked"] = round(m.get("podiumMarkedSum", 0) / n, 3) if n else None
    out["avgMarkSetSize"] = round(m.get("markSetSizeSum", 0) / n, 3) if n else None
    for key in ("finishMark1", "finishMark2", "finishMark3"):
        out[key] = dict(sorted(m[key].items(), key=lambda kv: (-kv[1], kv[0])))
    return out


def resolved_end_date() -> date:
    if END_DATE:
        return datetime.strptime(END_DATE, "%Y-%m-%d").date()
    return date.today() - timedelta(days=1)


def main() -> None:
    end = resolved_end_date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    total = empty_metrics()
    by_circuit: dict[str, dict[str, Any]] = defaultdict(empty_metrics)
    by_day: list[dict[str, Any]] = []
    details_seen = finals_seen = locked_seen = 0

    for ds in dates:
        payload = api_json(API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"}))
        details = payload.get("details") or []
        details_seen += len(details)
        day = empty_metrics()
        for detail in details:
            if not isinstance(detail, dict):
                continue
            order = finish_order(detail)
            if len(order) < 3:
                continue
            finals_seen += 1
            marks = locked_marks(detail)
            if not marks:
                continue
            locked_seen += 1
            circuit = str(detail.get("circuit") or "unknown")
            add_race(day, order, marks)
            add_race(by_circuit[circuit], order, marks)
        merge(total, day)
        s = summarize(day)
        by_day.append({"date": ds, **s})
        print("ROLE_DAY", ds, "locked", s["races"], "◎1着", s.get("honmeiWinRate"), "○2着", s.get("maruSecondRate"), "3頭印内", s.get("podiumAllMarkedRate"))

    result = {
        "version": "arvexq-exact-role-mark-audit-v1",
        "start": dates[0],
        "end": dates[-1],
        "days": DAYS,
        "detailsSeen": details_seen,
        "finalsSeen": finals_seen,
        "lockedRaces": locked_seen,
        "exactLocked": summarize(total),
        "byCircuit": {k: summarize(v) for k, v in sorted(by_circuit.items())},
        "perDay": by_day,
        "definitions": {
            "honmeiWin": "◎が1着",
            "maruSecond": "○が2着",
            "podiumAllMarked": "実着1〜3着の3頭すべてが何らかのAI印内",
            "firstSecondRoleExact": "1着が◎かつ2着が○",
        },
        "warning": "preRacePrediction が保存された確定レースだけを集計。結果後に作り直した予想は使わない。",
    }
    print("ARVEXQ_ROLE_AUDIT_JSON=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
