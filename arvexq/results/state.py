from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any

JST = timezone(timedelta(hours=9))
TERMINAL_NO_PAYOUT = {"中止", "取止", "取消", "不成立"}
SCRATCH_MARKERS = ("出走取消", "競走除外", "欠場")
_RESULT_CNAME_DATE_RE = re.compile(r"(20\d{6})/[0-9A-Fa-f]{2}$")
_RESULT_CNAME_NO_RE = re.compile(
    r"pw01(?:d|s)de(?:00|01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/", re.I)


def _card_runner_count(detail: dict[str, Any]) -> int:
    """Active runners on the race card (scratches/withdrawals excluded)."""
    horses = detail.get("horses")
    if not isinstance(horses, list):
        return 0
    count = 0
    for horse in horses:
        if not isinstance(horse, dict):
            continue
        if horse.get("scratched") or horse.get("withdrawn"):
            continue
        status = str(horse.get("status") or "")
        if any(marker in status for marker in SCRATCH_MARKERS):
            continue
        count += 1
    return count


def _result_cname_conflicts(detail: dict[str, Any]) -> bool:
    """Whether the stored JRA result token names a different race.

    The token embeds the race identity (date in the tail, race number
    in the body). A token stored for another race means the result
    block that came with it is foreign, however final it reads.
    Fields that cannot be decoded are not judged.
    """
    cname = str(detail.get("resultCname") or "")
    if not cname:
        return False
    date_match = _RESULT_CNAME_DATE_RE.search(cname)
    if date_match:
        raw = date_match.group(1)
        token_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
        own_date = str(detail.get("date") or "")
        if own_date and token_date != own_date:
            return True
    no_match = _RESULT_CNAME_NO_RE.search(cname)
    if no_match:
        try:
            own_no = int(detail.get("raceNumber") or 0)
        except Exception:
            own_no = 0
        if own_no and int(no_match.group(1)) != own_no:
            return True
    return False


def start_minutes(row: dict[str, Any]) -> int:
    raw = str(row.get("startTime") or row.get("scheduledStartTime") or "")
    try:
        hh, mm = raw.split(":", 1)
        return int(hh) * 60 + int(mm[:2])
    except Exception:
        return 9999


def row_date(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("race_date") or row.get("raceDate") or "")


def podium_final(result: Any) -> bool:
    """Accept normal and dead-heat podiums once the source marks them final."""
    if not isinstance(result, dict) or str(result.get("status") or "") != "確定":
        return False
    finishes: list[int] = []
    for row in result.get("finishers") or []:
        if not isinstance(row, dict):
            continue
        try:
            finish = int(row.get("finish") or 0)
        except Exception:
            finish = 0
        if finish > 0:
            finishes.append(finish)
    return 1 in finishes and sum(1 for finish in finishes if finish <= 3) >= 3


# ---------------------------------------------------------------------------
# Named check: payout_combination_shape
#
# Every stored payout row must carry a combination whose shape matches
# its bet type: 単勝・複勝 are a single horse number (1..18), 枠連 a
# frame pair (1..8), 馬連・馬単・ワイド a horse pair, 3連複・3連単 a
# horse triple, and no (type, combination) pair may repeat. The JRA
# payout-parser defect repaired on 2026-11-08 stored popularity numbers
# and neighbouring amounts as combinations (複勝 "170", ワイド "133",
# a duplicated 複勝 number with two amounts); rows of that shape are
# not payouts, so a result carrying them is payout-incomplete and the
# result-repair lane re-fetches it. Unknown bet types are not judged.
# ---------------------------------------------------------------------------
_PAYOUT_COMBINATION_ARITY = {
    "単勝": 1, "複勝": 1,
    "枠連": 2, "馬連": 2, "馬単": 2, "ワイド": 2,
    "3連複": 3, "3連単": 3,
}


def payout_combination_violations(detail: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Shape violations in a detail's stored payout rows.

    Returns one record per offending row: race_id (the detail id),
    bet type, the stored combination, and the reason. An empty list
    means every judged row is well-formed (or there are no payouts).
    """
    d = detail if isinstance(detail, dict) else {}
    result = d.get("result") if isinstance(d.get("result"), dict) else {}
    payouts = result.get("payouts") if isinstance(result.get("payouts"), list) else []
    race_id = str(d.get("id") or "")
    violations: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for row in payouts:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("type") or "")
        arity = _PAYOUT_COMBINATION_ARITY.get(kind)
        if arity is None:
            continue
        raw = str(row.get("combination") or "")
        numbers = [int(x) for x in re.findall(r"\d+", raw)]
        reason = ""
        if len(numbers) != arity:
            reason = f"combination has {len(numbers)} numbers, expected {arity}"
        else:
            limit = 8 if kind == "枠連" else 18
            if any(n < 1 or n > limit for n in numbers):
                reason = f"combination number outside 1..{limit}"
            elif (kind, tuple(numbers)) in seen:
                reason = "duplicate combination for bet type"
        if reason:
            violations.append({
                "race_id": race_id,
                "type": kind,
                "combination": raw,
                "reason": reason,
            })
        seen.add((kind, tuple(numbers)))
    return violations


def result_state(detail: dict[str, Any] | None) -> tuple[bool, bool, str]:
    d = detail if isinstance(detail, dict) else {}
    result = d.get("result") if isinstance(d.get("result"), dict) else {}
    status = str(result.get("status") or "")
    if status in TERMINAL_NO_PAYOUT:
        return True, True, status
    payouts = result.get("payouts") if isinstance(result.get("payouts"), list) else []
    final = podium_final(result)
    if final:
        # A podium-shaped block is not complete when the card says
        # more horses ran than the block lists: an interim (速報)
        # table parsed early freezes as "final" otherwise, and the
        # repair lane never revisits it (2026-11-08 Fukushima 9R was
        # stored with only its first five finishers).
        runners = _card_runner_count(d)
        finishers = result.get("finishers")
        if runners and isinstance(finishers, list) and len(finishers) < runners:
            final = False
        # A result block whose source token names another race is
        # foreign data, not a final result for this race.
        if _result_cname_conflicts(d):
            final = False
    # Payout rows whose combination shape is impossible for their bet
    # type (payout_combination_shape check above) are corrupt data,
    # not a completed payout set: the repair lane must re-fetch them.
    payout_ok = bool(payouts) and not payout_combination_violations(d)
    return final, payout_ok, status


def started(summary: dict[str, Any], now: datetime) -> bool:
    race_date = row_date(summary)
    today = now.strftime("%Y-%m-%d")
    if race_date:
        if race_date < today:
            return True
        if race_date > today:
            return False
    sm = start_minutes(summary)
    now_minutes = now.hour * 60 + now.minute
    return sm < 9999 and now_minutes >= sm + 2


def merge_result(old: Any, new: Any) -> dict[str, Any]:
    old_r = copy.deepcopy(old) if isinstance(old, dict) else {}
    new_r = new if isinstance(new, dict) else {}
    if not new_r:
        return old_r
    old_final = podium_final(old_r)
    new_final = podium_final(new_r)
    out = old_r
    for key, value in new_r.items():
        if value in (None, "", [], {}):
            continue
        if old_final and not new_final and key in {"status", "finishers"}:
            continue
        # A partial refresh cannot shrink an already known official result.
        if key in {"payouts", "finishers"} and isinstance(value, list):
            previous = old_r.get(key)
            if isinstance(previous, list) and len(previous) > len(value):
                continue
        out[key] = copy.deepcopy(value)
    return out


def merge_detail(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
    """Merge refreshed result data without degrading a precomputed rich card."""
    if not old:
        return copy.deepcopy(new or {})
    if not new:
        return copy.deepcopy(old)

    out = copy.deepcopy(old)
    protected = {
        "horses",
        "preparedMeta",
        "preRacePrediction",
        "predictionAudit",
        "aiEvaluation",
        "pace",
        "pacePrediction",
        "volatility",
    }
    for key, value in new.items():
        if key in protected or key == "result":
            continue
        if value not in (None, "", [], {}):
            out[key] = copy.deepcopy(value)

    if isinstance(new.get("result"), dict) and new.get("result"):
        out["result"] = merge_result(old.get("result"), new.get("result"))

    for key in protected:
        if key in old:
            out[key] = copy.deepcopy(old[key])
    return out
