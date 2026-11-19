"""Dual-source result merge: official primary, netkeiba secondary.

The user's standing rule (2026-11-19) is that race information is
taken from BOTH the official source (JRA / keiba.go.jp) and netkeiba,
never from one alone. For results the official parse stays
authoritative: a field the official result carries is never
overwritten. A field the official result leaves empty (None / "" /
[] / 0) is filled from the netkeiba parse of the same race — both
values are observed facts, nothing is estimated. Where both sources
carry a value and they disagree, the official value is kept and the
disagreement is recorded in the merged block's ``dualSource`` meta
(and counted), so a conflict is detectable instead of silent.

Finisher rows that exist only in the netkeiba parse are NOT added:
on real pages those rows are the scratched / excluded horses the
official table accounts for separately (nonFinishers), and adding
them as finishers would corrupt the finisher accounting. The merge
only fills fields of horses the official result itself lists, plus
the result-level payouts / raceLapTimes blocks.

No application dependency: callers fetch both parses and hand them
in, mirroring arvexq.ingest.odds_results_merge.
"""
from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any

# Finisher fields filled from the secondary when the primary leaves
# them empty. "finish" is deliberately absent: a placing is never
# granted from the secondary (see module docstring), it is only
# conflict-checked when both sources record one.
FILL_FIELDS = (
    "finishLabel", "frameNumber", "name", "sex", "age", "carriedWeight",
    "jockey", "trainer", "timeSeconds", "marginText", "bodyWeight",
    "bodyWeightChange", "popularity", "winOdds",
)

# The two spellings of the last-3F split are one logical field:
# official parses emit last3FSeconds, the netkeiba parse emits both.
LAST3F_KEYS = ("last3FSeconds", "last3fSeconds")

# Fields compared when both sources carry a value.
CONFLICT_FIELDS = (
    "finish", "timeSeconds", "marginText", "last3FSeconds",
    "cornerPositions", "popularity", "bodyWeight", "winOdds",
)

_FLOAT_TOL = 0.051
_CONFLICT_CAP = 20


def _empty(value: Any) -> bool:
    return value in (None, "", [], 0, 0.0)


def _norm_margin(value: Any) -> str:
    """Canonical margin text for comparison only (never stored).

    The two sources print the same margin with different spacing and
    fraction typography: the netkeiba smartphone layout loses the
    space inside "1 3/4" (stored as "1.3/4") and abbreviates 大差 as
    大. Those are notation variants, not disagreements.
    """
    s = unicodedata.normalize("NFKC", str(value or ""))
    # Compound margins first, while the separator is still visible:
    # "1 3/4", "1.3/4" and "1・3/4" are the same margin. (NFKC also
    # folds the official table's full-width digits — "３ 1/2",
    # "１／２" — onto the netkeiba half-width forms.)
    s = re.sub(r"(\d+)\s*[.・\s]\s*(\d+)\s*/\s*(\d+)", r"\1+\2/\3", s)
    s = s.replace(" ", "").replace("　", "").replace("・", "")
    if s == "大":
        s = "大差"
    return s


def _float_eq(a: Any, b: Any) -> bool:
    try:
        return abs(float(a) - float(b)) <= _FLOAT_TOL
    except (TypeError, ValueError):
        return a == b


def _last3f(finisher: dict) -> Any:
    for key in LAST3F_KEYS:
        value = finisher.get(key)
        if not _empty(value):
            return value
    return None


def result_gaps(result: dict | None) -> list[str]:
    """Gap keys present in a result block, for gap-triggered fetches.

    A block with no gaps gains nothing from a second source, so
    read-path callers can skip the extra fetch; the steady repair /
    refresh lanes fetch both sources regardless (the dual-source
    rule) and use this only for logging.
    """
    if not isinstance(result, dict):
        return ["result"]
    gaps: list[str] = []
    finishers = [f for f in (result.get("finishers") or []) if isinstance(f, dict)]
    if not finishers:
        return ["finishers"]
    if any(_last3f(f) is None for f in finishers):
        gaps.append("last3FSeconds")
    if any(not f.get("cornerPositions") for f in finishers):
        gaps.append("cornerPositions")
    if any(_empty(f.get("bodyWeight")) for f in finishers):
        gaps.append("bodyWeight")
    if any(_empty(f.get("winOdds")) for f in finishers):
        gaps.append("winOdds")
    if not result.get("raceLapTimes"):
        gaps.append("raceLapTimes")
    if not result.get("payouts"):
        gaps.append("payouts")
    return gaps


def _recompute_last3f_ranks(finishers: list[dict]) -> None:
    """Recompute last3FRank / last3FPercentile after fills.

    Same derivation as the JRA official parser: ranks over the
    distinct recorded splits. Only applied when the primary's rows
    already carry the rank fields (the JRA official shape); other
    shapes are left untouched.
    """
    if not any("last3FRank" in f for f in finishers):
        return
    sectionals = sorted({float(_last3f(f)) for f in finishers
                         if _last3f(f) is not None and float(_last3f(f)) > 0})
    for f in finishers:
        value = _last3f(f)
        try:
            s = float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            s = 0.0
        if s > 0 and sectionals:
            rk = sectionals.index(s) + 1
            f["last3FRank"] = rk
            f["last3FPercentile"] = 0.5 if len(sectionals) == 1 else 1.0 - (rk - 1) / (len(sectionals) - 1)
        else:
            f.pop("last3FRank", None)
            f.pop("last3FPercentile", None)


def merge_result_sources(primary: dict | None, secondary: dict | None,
                         *, skip_fields: tuple = ()) -> dict | None:
    """Merge two parses of the same race's result, official first.

    ``primary`` is the authoritative (official) result block,
    ``secondary`` the netkeiba one. Returns the merged block (a deep
    copy; inputs are not mutated). With either side missing, the
    other is returned unchanged — a single-source result is still a
    result, it just carries no dualSource meta. ``skip_fields``
    names finisher fields a caller must not take from the secondary
    at all (the central read path strips win odds from result
    finishers by policy, so it skips winOdds).
    """
    skip = set(skip_fields or ())
    if not isinstance(primary, dict) or not primary.get("finishers"):
        return primary if isinstance(primary, dict) and primary else secondary
    if not isinstance(secondary, dict) or not secondary.get("finishers"):
        return primary

    merged = copy.deepcopy(primary)
    sec_by_no = {}
    for f in secondary.get("finishers") or []:
        if isinstance(f, dict):
            no = int(f.get("horseNumber") or 0)
            if no:
                sec_by_no[no] = f

    filled: dict[str, int] = {}
    conflicts: list[dict[str, Any]] = []
    conflict_count = 0
    corner_coverage_diffs = 0

    def note_fill(field: str) -> None:
        filled[field] = filled.get(field, 0) + 1

    def note_conflict(no: int, field: str, official: Any, netkeiba: Any) -> None:
        nonlocal conflict_count
        conflict_count += 1
        if len(conflicts) < _CONFLICT_CAP:
            conflicts.append({
                "horseNumber": no, "field": field,
                "official": official, "netkeiba": netkeiba,
            })

    for f in merged.get("finishers") or []:
        if not isinstance(f, dict):
            continue
        no = int(f.get("horseNumber") or 0)
        sec = sec_by_no.get(no)
        if not sec:
            continue
        # Plain field fills.
        for key in FILL_FIELDS:
            if key in skip:
                continue
            if _empty(f.get(key)) and not _empty(sec.get(key)):
                f[key] = copy.deepcopy(sec.get(key))
                note_fill(key)
        # Last 3F: one logical field behind two key spellings. Fill
        # both spellings so every downstream consumer sees the value.
        if skip.intersection(LAST3F_KEYS):
            pass
        elif _last3f(f) is None and _last3f(sec) is not None:
            value = _last3f(sec)
            for key in LAST3F_KEYS:
                f[key] = value
            note_fill("last3FSeconds")
        # Corner positions: fill an empty list wholesale; with equal
        # lengths fill only the slots the primary left as None. A
        # length difference is a coverage difference between the two
        # pages' corner tables (they do not always enumerate the same
        # passing points), recorded as such, never as a conflict.
        mine = f.get("cornerPositions") or []
        theirs = sec.get("cornerPositions") or []
        if "cornerPositions" in skip:
            mine, theirs = [], []
        if not mine and theirs:
            f["cornerPositions"] = copy.deepcopy(theirs)
            note_fill("cornerPositions")
        elif mine and theirs and len(mine) == len(theirs):
            slots = 0
            for i, (a, b) in enumerate(zip(mine, theirs)):
                if a is None and b is not None:
                    mine[i] = b
                    slots += 1
            if slots:
                f["cornerPositions"] = mine
                note_fill("cornerPositions")
        elif mine and theirs and len(mine) != len(theirs):
            corner_coverage_diffs += 1
        # Conflicts: both sources carry a value and they disagree.
        for key in CONFLICT_FIELDS:
            if key in skip or (key == "last3FSeconds" and skip.intersection(LAST3F_KEYS)):
                continue
            if key == "cornerPositions":
                a, b = f.get("cornerPositions") or [], sec.get("cornerPositions") or []
                if a and b and len(a) == len(b):
                    if any(x is not None and y is not None and x != y
                           for x, y in zip(a, b)):
                        note_conflict(no, key, a, b)
                continue
            if key == "last3FSeconds":
                a, b = _last3f(f), _last3f(sec)
            elif key == "finish":
                a, b = f.get("finish") or 0, sec.get("finish") or 0
                if not a or not b:
                    continue
            else:
                a, b = f.get(key), sec.get(key)
            if _empty(a) or _empty(b):
                continue
            if key == "marginText":
                same = _norm_margin(a) == _norm_margin(b)
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                same = _float_eq(a, b)
            else:
                same = a == b
            if not same:
                note_conflict(no, key, a, b)

    # Result-level fills: payouts and race laps are whole blocks.
    if not merged.get("payouts") and secondary.get("payouts"):
        merged["payouts"] = copy.deepcopy(secondary["payouts"])
        note_fill("payouts")
    if not merged.get("raceLapTimes") and secondary.get("raceLapTimes"):
        merged["raceLapTimes"] = copy.deepcopy(secondary["raceLapTimes"])
        note_fill("raceLapTimes")
    if _empty(merged.get("status")) and not _empty(secondary.get("status")):
        merged["status"] = secondary["status"]
        note_fill("status")

    _recompute_last3f_ranks(merged.get("finishers") or [])

    merged["dualSource"] = {
        "version": "result-dual-source-v1",
        "primary": primary.get("source") or "",
        "secondary": secondary.get("source") or "",
        "filled": filled,
        "filledTotal": sum(filled.values()),
        "conflicts": conflicts,
        "conflictCount": conflict_count,
        "cornerCoverageDiffs": corner_coverage_diffs,
    }
    return merged
