"""Named result audit checks (item 2, 2026-11-08).

The Result Repair workflow's final verify step used to be one
monolithic inline gate: it lumped the repair report's
result_missing / payout_missing lists and a podium-only read-back
probe into a single ``raise SystemExit('result repair incomplete:
...')``.  When it failed, nobody could tell WHICH race failed WHICH
condition — the failure state was normalised (observed 2026-11-08
06:21Z / 07:13Z / 07:19Z, every write green).  This module replaces
that gate with independent named checks.  Each check returns failure
records of one shape::

    {check, race_id, failure_class, expected, actual,
     timestamp, retry_state, ...check-specific fields}

Named checks
------------
- ``result_fetch``          a result block was actually obtained:
                            present, a dict, carrying a status and
                            at least one finisher row (or a terminal
                            no-payout status).
- ``race_identity``         the detail is the race it claims to be:
                            id matches the expected race id, the
                            embedded date/track/raceNumber match the
                            expected identity when supplied, and the
                            stored JRA result token (resultCname)
                            does not name a different race (the
                            2026-11-08 Fukushima 7R foreign-result
                            defect).
- ``finisher_completeness`` the finisher list accounts for the whole
                            active roster.  The expected count is
                            ``state._card_runner_count`` — the exact
                            scratch handling of ``result_state``
                            (出走取消・競走除外・欠場 and
                            scratched/withdrawn flags excluded from
                            the roster), imported, never re-implemented,
                            so this check can never drift from the
                            repair lane's own completeness judgement.
                            Horses accounted as non-finishers (a
                            finish<=0 finisher row, a result-level
                            ``nonFinishers`` entry, or a card status
                            carrying a non-finisher marker such as
                            中止・失格） count as accounted, not as
                            finishers.  A podium shape is also required
                            (1st present, at least three finish<=3).
- ``payout_cross_check``    payouts are present for a final result
                            and every stored row passes the standing
                            ``payout_combination_shape`` check
                            (``state.payout_combination_violations``,
                            item 1, behaviour unchanged; its violations
                            surface here with failure_class
                            ``payout_combination_shape``).
- ``save_read_back``        the detail read back from storage is the
                            detail that was supposed to be saved:
                            present, and its result status / finisher
                            count / payout count agree with the source
                            detail.

Kochi 5R, 2026-11-07 (the counting question this module settles):
the card lists 10 horses and no scratch marker — horse 2 ゲクウ is
not marked 出走取消・競走除外・欠場 anywhere in the stored detail —
while the stored result lists 9 finishers.  The old workflow verify
(podium-only) passed this race; ``result_state`` failed it
(9 < 10 active runners).  The two sides disagreed because the verify
side had no roster counting at all.  Aligned here to result_state:
expected = 10, accounted = 9, failure_class ``finisher_count_short``,
missing horse [2].  The official NAR result (keiba.go.jp
RaceMarkTable, baba 31, 2026/11/07, race 5) accounts for horse 2 as
中止 (stopped, no placing): the 9 stored finishers and all 12 stored
payouts match the official page exactly, so the stored *finishers*
are the full official finisher list — what the stored record lacks
is any accounting of the non-finisher.  A stored detail that carries
that accounting (finish<=0 row or ``nonFinishers`` entry marked
中止） passes this check; one that silently drops the horse does
not.  ``result_state`` itself is unchanged (not weakened).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .state import (
    JST,
    TERMINAL_NO_PAYOUT,
    _card_runner_count,
    _result_cname_conflicts,
    payout_combination_violations,
    podium_final,
)

CHECK_RESULT_FETCH = "result_fetch"
CHECK_RACE_IDENTITY = "race_identity"
CHECK_FINISHER_COMPLETENESS = "finisher_completeness"
CHECK_PAYOUT_CROSS_CHECK = "payout_cross_check"
CHECK_SAVE_READ_BACK = "save_read_back"

ALL_CHECKS = (
    CHECK_RESULT_FETCH,
    CHECK_RACE_IDENTITY,
    CHECK_FINISHER_COMPLETENESS,
    CHECK_PAYOUT_CROSS_CHECK,
    CHECK_SAVE_READ_BACK,
)

# Markers that account for a horse that started but did not finish.
# （出走取消・競走除外・欠場 are pre-start scratches: state._card_runner_count
# already removes those horses from the active roster, so they never
# reach this list.)
NON_FINISHER_MARKERS = ("中止", "競走中止", "失格", "落馬", "競走中止", "転倒")


def _timestamp(now: datetime | None) -> str:
    moment = now if isinstance(now, datetime) else datetime.now(JST)
    return moment.isoformat()


def _failure(check: str, race_id: str, failure_class: str,
             expected: Any, actual: Any, *,
             now: datetime | None = None, retry_state: str = "",
             **extra: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "check": check,
        "race_id": str(race_id or ""),
        "failure_class": failure_class,
        "expected": expected,
        "actual": actual,
        "timestamp": _timestamp(now),
        "retry_state": retry_state,
    }
    record.update(extra)
    return record


def _result_of(detail: Any) -> dict[str, Any]:
    d = detail if isinstance(detail, dict) else {}
    result = d.get("result")
    return result if isinstance(result, dict) else {}


def _placed_finishers(result: dict[str, Any]) -> list[dict[str, Any]]:
    placed = []
    for row in result.get("finishers") or []:
        if not isinstance(row, dict):
            continue
        try:
            finish = int(row.get("finish") or 0)
        except Exception:
            finish = 0
        if finish > 0:
            placed.append(row)
    return placed


def _non_finisher_numbers(detail: dict[str, Any]) -> set[int]:
    """Horse numbers accounted for as started-but-did-not-finish."""
    numbers: set[int] = set()
    result = _result_of(detail)
    candidates: list[Any] = []
    candidates.extend(result.get("finishers") or [])
    for key in ("nonFinishers", "non_finishers", "didNotFinish"):
        value = result.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    for row in candidates:
        if not isinstance(row, dict):
            continue
        try:
            finish = int(row.get("finish") or 0)
        except Exception:
            finish = 0
        text = " ".join(str(row.get(k) or "") for k in
                        ("finishLabel", "status", "marginText", "note"))
        if finish <= 0 and any(m in text for m in NON_FINISHER_MARKERS):
            try:
                no = int(row.get("horseNumber") or 0)
            except Exception:
                no = 0
            if no:
                numbers.add(no)
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        status = str(horse.get("status") or "")
        if any(m in status for m in NON_FINISHER_MARKERS):
            try:
                no = int(horse.get("horseNumber") or 0)
            except Exception:
                no = 0
            if no:
                numbers.add(no)
    return numbers


def audit_detail(detail: dict[str, Any] | None, *,
                 expected_race_id: str = "",
                 expected_identity: dict[str, Any] | None = None,
                 fetched: bool = True,
                 fetch_error: str = "",
                 now: datetime | None = None,
                 retry_state: str = "") -> list[dict[str, Any]]:
    """Run checks (a)-(d) over one race detail.

    ``expected_identity`` may carry date/track/raceNumber values the
    detail must match.  Returns failure records (empty = all pass).
    """
    race_id = str(expected_race_id or
                  (detail.get("id") if isinstance(detail, dict) else "") or "")
    failures: list[dict[str, Any]] = []

    def fail(check, failure_class, expected, actual, **extra):
        failures.append(_failure(check, race_id, failure_class, expected,
                                 actual, now=now, retry_state=retry_state,
                                 **extra))

    d = detail if isinstance(detail, dict) else {}
    result = _result_of(d)
    status = str(result.get("status") or "")
    terminal = status in TERMINAL_NO_PAYOUT

    # (a) result_fetch -------------------------------------------------
    if not fetched or not d:
        fail(CHECK_RESULT_FETCH, "result_not_fetched",
             "detail fetched from result source / storage",
             fetch_error or "no detail returned")
        return failures
    if not result:
        fail(CHECK_RESULT_FETCH, "result_missing",
             "result block present", "result block absent")
    elif not status:
        fail(CHECK_RESULT_FETCH, "result_status_missing",
             "result status present", "")
    elif not terminal and not (result.get("finishers") or []):
        fail(CHECK_RESULT_FETCH, "finishers_missing",
             "at least one finisher row", 0)

    # (b) race_identity -------------------------------------------------
    if expected_race_id and str(d.get("id") or "") != expected_race_id:
        fail(CHECK_RACE_IDENTITY, "race_id_mismatch",
             expected_race_id, str(d.get("id") or ""))
    if expected_identity:
        for key, detail_key in (("date", "date"), ("track", "track"),
                                ("raceNumber", "raceNumber")):
            want = expected_identity.get(key)
            if want in (None, ""):
                continue
            got = d.get(detail_key)
            if got in (None, ""):
                # A field the detail does not carry is not judged
                # (same rule as _result_cname_conflicts).
                continue
            if str(got) != str(want):
                fail(CHECK_RACE_IDENTITY, "race_identity_mismatch",
                     f"{key}={want}", f"{key}={got}")
    if _result_cname_conflicts(d):
        fail(CHECK_RACE_IDENTITY, "result_cname_identity_conflict",
             "resultCname naming this race (date/raceNumber)",
             str(d.get("resultCname") or ""))

    if terminal or not result:
        # A terminal no-payout race (中止・取止・取消・不成立 as the
        # race status itself) has no finishers/payouts to judge, the
        # same contract as result_state.
        return failures

    # (c) finisher_completeness ----------------------------------------
    placed = _placed_finishers(result)
    finishes = []
    for row in placed:
        try:
            finishes.append(int(row.get("finish") or 0))
        except Exception:
            pass
    if status == "確定" and not (1 in finishes and
                                 sum(1 for f in finishes if f <= 3) >= 3):
        fail(CHECK_FINISHER_COMPLETENESS, "podium_incomplete",
             "finish 1 present and at least 3 finishers in top 3",
             sorted(finishes)[:5])
    runners = _card_runner_count(d)
    if runners:
        placed_numbers = set()
        for row in placed:
            try:
                no = int(row.get("horseNumber") or 0)
            except Exception:
                no = 0
            if no:
                placed_numbers.add(no)
        accounted_numbers = placed_numbers | _non_finisher_numbers(d)
        card_numbers = set()
        for horse in d.get("horses") or []:
            if not isinstance(horse, dict):
                continue
            try:
                no = int(horse.get("horseNumber") or 0)
            except Exception:
                no = 0
            if no:
                card_numbers.add(no)
        # Missing = on the card, not placed, not accounted as a
        # non-finisher, and not a scratch (scratches are already out
        # of `runners`; a card number beyond the roster count cannot
        # be named individually, so fall back to the count compare).
        missing = sorted(n for n in card_numbers
                         if n not in accounted_numbers) \
            if len(card_numbers) == runners else []
        accounted = len(placed) + len(_non_finisher_numbers(d))
        if accounted < runners:
            fail(CHECK_FINISHER_COMPLETENESS, "finisher_count_short",
                 runners, accounted, missing_horse_numbers=missing)

    # (d) payout_cross_check --------------------------------------------
    payouts = result.get("payouts") if isinstance(result.get("payouts"), list) else []
    if status == "確定" and not payouts:
        fail(CHECK_PAYOUT_CROSS_CHECK, "payout_missing",
             "payout rows present for a final result", 0)
    for violation in payout_combination_violations(d):
        fail(CHECK_PAYOUT_CROSS_CHECK, "payout_combination_shape",
             f"valid {violation.get('type') or ''} combination "
             f"({violation.get('reason') or ''})",
             str(violation.get("combination") or ""),
             type=str(violation.get("type") or ""),
             reason=str(violation.get("reason") or ""))
    return failures


def audit_read_back(source_detail: dict[str, Any] | None,
                    read_back_detail: dict[str, Any] | None, *,
                    expected_race_id: str = "",
                    read_back_error: str = "",
                    now: datetime | None = None,
                    retry_state: str = "") -> list[dict[str, Any]]:
    """Check (e): the stored read-back is the detail meant to be saved."""
    race_id = str(expected_race_id or
                  (source_detail.get("id") if isinstance(source_detail, dict)
                   else "") or "")
    failures: list[dict[str, Any]] = []

    def fail(failure_class, expected, actual, **extra):
        failures.append(_failure(CHECK_SAVE_READ_BACK, race_id,
                                 failure_class, expected, actual,
                                 now=now, retry_state=retry_state, **extra))

    if not isinstance(read_back_detail, dict) or not read_back_detail:
        fail("save_read_back_missing",
             "detail read back from storage after save",
             read_back_error or "no detail returned")
        return failures
    if expected_race_id and str(read_back_detail.get("id") or "") != expected_race_id:
        fail("save_read_back_identity_mismatch",
             expected_race_id, str(read_back_detail.get("id") or ""))
    if isinstance(source_detail, dict) and source_detail:
        src = _result_of(source_detail)
        got = _result_of(read_back_detail)
        comparisons = (
            ("status", str(src.get("status") or ""), str(got.get("status") or "")),
            ("finishers", len(src.get("finishers") or []),
             len(got.get("finishers") or [])),
            ("payouts", len(src.get("payouts") or []),
             len(got.get("payouts") or [])),
        )
        for field, want, have in comparisons:
            if want != have:
                fail("save_read_back_mismatch",
                     f"{field}={want}", f"{field}={have}", field=field)
    return failures


def audit_race(source_detail: dict[str, Any] | None,
               read_back_detail: dict[str, Any] | None, *,
               expected_race_id: str = "",
               expected_identity: dict[str, Any] | None = None,
               fetched: bool = True,
               fetch_error: str = "",
               read_back_error: str = "",
               now: datetime | None = None,
               retry_state: str = "") -> list[dict[str, Any]]:
    """All five named checks for one race.

    Checks (a)-(d) judge the read-back detail when one was obtained
    (that is what users are served); otherwise they judge the source
    detail so the failure is still named.  Check (e) compares the two.
    """
    judged = read_back_detail if isinstance(read_back_detail, dict) \
        and read_back_detail else source_detail
    failures = audit_detail(
        judged, expected_race_id=expected_race_id,
        expected_identity=expected_identity, fetched=fetched,
        fetch_error=fetch_error, now=now, retry_state=retry_state)
    failures.extend(audit_read_back(
        source_detail, read_back_detail, expected_race_id=expected_race_id,
        read_back_error=read_back_error, now=now, retry_state=retry_state))
    return failures


def summarise(failures: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-check failure counts + the failing race ids, by check."""
    by_check: dict[str, dict[str, Any]] = {
        name: {"failure_count": 0, "race_ids": []} for name in ALL_CHECKS}
    for record in failures:
        bucket = by_check.setdefault(
            str(record.get("check") or ""),
            {"failure_count": 0, "race_ids": []})
        bucket["failure_count"] += 1
        rid = str(record.get("race_id") or "")
        if rid and rid not in bucket["race_ids"]:
            bucket["race_ids"].append(rid)
    return by_check
