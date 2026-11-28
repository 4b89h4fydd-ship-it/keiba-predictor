"""Canonical entry (racecard) reconciliation: one clean route for horse
identity (name / horseNumber / frameNumber).

Principle (user directive, 2026-11-28): the official card and the
netkeiba card describe the SAME real racecard, so a disagreement
between two readings is a bug in one of the readings — never a reason
to stop, and never something to paper over by mixing the two.  This
module is the single place that

  * decides, per horse, which reading of the identity is right
    (the side whose numbering is internally consistent wins; the
    standard frame map is the cross-check),
  * corrects the losing reading and records every correction,
  * merges materials strictly by horse NAME, and
  * refuses to mix one horse's materials when the two sides disagree
    on that horse's number (a disagreement means one side's identity
    is scrambled, so the materials cannot be trusted to belong
    together until reconciliation has run).

Everything here is pure: no network, no persistence, no forecasts.
Callers keep their own transports; identity is owned here.
"""
from __future__ import annotations

import copy
from typing import Any, Callable

IDENTITY_FIELDS = ("horseNumber", "frameNumber")


def _no(row: Any) -> int:
    try:
        return int((row or {}).get("horseNumber") or 0)
    except (TypeError, ValueError):
        return 0


def _frame(row: Any) -> int:
    try:
        return int((row or {}).get("frameNumber") or 0)
    except (TypeError, ValueError):
        return 0


def _name(row: Any) -> str:
    return str((row or {}).get("name") or "").strip()


def _meaningful(value: Any) -> bool:
    return value not in (None, "", [], {})


def frame_for_number(number: int, field_size: int) -> int:
    """Standard frame (枠) for a horse number in a field of N.

    Frames hold either floor(N/8) or ceil(N/8) horses; the larger
    frames are the highest-numbered ones.  Returns 0 when the inputs
    cannot describe a frame.
    """
    try:
        number = int(number)
        field_size = int(field_size)
    except (TypeError, ValueError):
        return 0
    if number <= 0 or field_size <= 0 or number > field_size:
        return 0
    if field_size <= 8:
        return number
    base, rem = divmod(field_size, 8)
    small_frames = 8 - rem
    small_horses = small_frames * base
    if number <= small_horses:
        return (number - 1) // base + 1
    return small_frames + (number - small_horses - 1) // (base + 1) + 1


def numbering_report(rows: Any) -> dict[str, Any]:
    """Internal-consistency report for one reading of a roster.

    ``clean``: the numbers are exactly 1..N.  ``frameMatches`` counts
    rows whose stated frame equals the standard frame for their
    number — a permuted reading keeps ``clean`` true while its frames
    (read from a different page feature) betray it, which is exactly
    the 2026-11-28 failure shape.
    """
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    numbers = [_no(r) for r in rows]
    clean = bool(numbers) and all(n > 0 for n in numbers) and \
        sorted(numbers) == list(range(1, len(numbers) + 1))
    frame_matches = 0
    frame_known = 0
    for r in rows:
        frame = _frame(r)
        if frame > 0:
            frame_known += 1
            if frame == frame_for_number(_no(r), len(rows)):
                frame_matches += 1
    seen: set[str] = set()
    dup_names: list[str] = []
    for r in rows:
        name = _name(r)
        if name and name in seen and name not in dup_names:
            dup_names.append(name)
        seen.add(name)
    return {
        "size": len(rows),
        "clean": clean,
        "frameMatches": frame_matches,
        "frameKnown": frame_known,
        "duplicateNames": dup_names,
    }


def _consistency_key(report: dict[str, Any]) -> tuple[int, int, int]:
    return (1 if report["clean"] else 0,
            report["frameMatches"],
            -len(report["duplicateNames"]))


def _by_name(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in (rows or []):
        if not isinstance(r, dict):
            continue
        name = _name(r)
        if name and name not in out:
            out[name] = r
    return out


def identity_map(rows: Any) -> dict[str, int]:
    """name -> horseNumber for a roster (first row wins per name)."""
    return {name: _no(r) for name, r in _by_name(rows).items()}


def reconcile_rosters(primary_rows: Any, secondary_rows: Any, *,
                      primary_label: str = "primary",
                      secondary_label: str = "secondary",
                      ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the one canonical roster from two readings of it.

    Identity (horseNumber/frameNumber) for every shared horse comes
    from the internally consistent side; when both sides are equally
    consistent the primary (official) side wins.  Other fields are
    merged with the primary side winning conflicts and the secondary
    side filling gaps.  Horses seen by only one side are kept with
    that side's identity and flagged ``singleSource`` in the report —
    the two readings are of the same racecard, so a one-sided horse
    is a gap in the other reading, not a fabrication.

    Returns (rows sorted by horseNumber, report) where the report
    lists every identity correction that was applied.
    """
    primary_rows = [r for r in (primary_rows or []) if isinstance(r, dict)]
    secondary_rows = [r for r in (secondary_rows or []) if isinstance(r, dict)]
    p_map = _by_name(primary_rows)
    s_map = _by_name(secondary_rows)
    p_rep = numbering_report(primary_rows)
    s_rep = numbering_report(secondary_rows)
    primary_wins = _consistency_key(p_rep) >= _consistency_key(s_rep)
    winner_label = primary_label if primary_wins else secondary_label

    corrections: list[dict[str, Any]] = []
    single_source: list[str] = []
    out: list[dict[str, Any]] = []
    for name in dict.fromkeys([*p_map, *s_map]):
        prow = p_map.get(name)
        srow = s_map.get(name)
        if prow is None or srow is None:
            only = prow if prow is not None else srow
            out.append(copy.deepcopy(only))
            single_source.append(name)
            continue
        merged = copy.deepcopy(srow)
        for key, value in prow.items():
            if _meaningful(value) or key not in merged:
                merged[key] = copy.deepcopy(value)
        winner = prow if primary_wins else srow
        loser = srow if primary_wins else prow
        for field in IDENTITY_FIELDS:
            merged[field] = winner.get(field)
        if _no(prow) != _no(srow) or _frame(prow) != _frame(srow):
            corrections.append({
                "name": name,
                "primaryNumber": _no(prow), "primaryFrame": _frame(prow),
                "secondaryNumber": _no(srow), "secondaryFrame": _frame(srow),
                "chosenNumber": _no(winner), "chosenFrame": _frame(winner),
                "chosenFrom": winner_label,
                "correctedSide": secondary_label if primary_wins else primary_label,
            })
        out.append(merged)
    out.sort(key=lambda r: (_no(r) <= 0, _no(r), _name(r)))
    report = {
        "primary": p_rep, "secondary": s_rep,
        "identitySource": winner_label,
        "corrections": corrections,
        "singleSource": single_source,
    }
    return out, report


def merge_rows_by_name(base_rows: Any, fresh_rows: Any, *,
                       field_merger: Callable[[dict, dict], None] | None = None,
                       disagreements: list | None = None,
                       ) -> list[dict[str, Any]]:
    """Merge fresh materials onto a base roster, keyed by horse NAME.

    The replacement for every horseNumber-keyed merge:

    * identity fields are never taken from the fresh side — a merge
      can never renumber or reframe a horse;
    * materials follow the NAME: a fresh row's fields were read from
      the same source row as its name, so they belong to that horse
      even when the row's number was misread.  A number disagreement
      is recorded in ``disagreements`` (never silently absorbed) and
      the identity itself is left for reconcile_rosters to settle;
    * a fresh horse the base does not know is appended with its own
      identity intact.

    Document-to-document grafts of computed blocks (research
    evidence, career history) use the stricter graft_field_by_name:
    there the donor document's own name<->materials pairing may
    already have been scrambled by a number-keyed assembly, so a
    number disagreement means the block does not move.
    """
    out = [copy.deepcopy(h) for h in (base_rows or []) if isinstance(h, dict)]
    by_name = _by_name(out)
    for raw in (fresh_rows or []):
        if not isinstance(raw, dict):
            continue
        name = _name(raw)
        if not name:
            continue
        row = by_name.get(name)
        if row is None:
            row = copy.deepcopy(raw)
            out.append(row)
            by_name[name] = row
            continue
        base_no, fresh_no = _no(row), _no(raw)
        if base_no > 0 and fresh_no > 0 and base_no != fresh_no \
                and disagreements is not None:
            disagreements.append({
                "name": name, "baseNumber": base_no,
                "freshNumber": fresh_no})
        if field_merger is not None:
            field_merger(row, raw)
        else:
            for key, value in raw.items():
                if key in IDENTITY_FIELDS:
                    continue
                if _meaningful(value) or key not in row:
                    row[key] = copy.deepcopy(value)
    return out


def graft_field_by_name(target_rows: Any, donor_rows: Any, field: str, *,
                        disagreements: list | None = None) -> int:
    """Copy one per-horse field from donor rows onto target rows,
    matched by name, only where the target lacks it and the two
    sides agree on the horse's number.  Returns the graft count."""
    donors = _by_name(donor_rows)
    moved = 0
    for horse in (target_rows or []):
        if not isinstance(horse, dict):
            continue
        if isinstance(horse.get(field), (dict, list)) and horse.get(field):
            continue
        if horse.get(field) not in (None, "", [], {}):
            continue
        name = _name(horse)
        donor = donors.get(name) if name else None
        if donor is None or donor.get(field) in (None, "", [], {}):
            continue
        t_no, d_no = _no(horse), _no(donor)
        if t_no > 0 and d_no > 0 and t_no != d_no:
            if disagreements is not None:
                disagreements.append({
                    "name": name, "targetNumber": t_no,
                    "donorNumber": d_no, "field": field})
            continue
        horse[field] = copy.deepcopy(donor[field])
        moved += 1
    return moved


def dedupe_roster_by_name(rows: Any, *,
                          report: list | None = None,
                          ) -> list[dict[str, Any]]:
    """Collapse phantom duplicates: the same horse name twice in one
    roster is one horse.  The surviving identity is the row whose
    frame matches the standard frame for its number (the frame is
    read from a different page feature than the number, so it is the
    independent witness); if no row's frame witnesses its number,
    the first row survives.  Materials from the dropped rows are
    merged in by name (identity fields excluded)."""
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    total = len(rows)
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for r in rows:
        name = _name(r)
        key = name or f"\0id{id(r)}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)
    out: list[dict[str, Any]] = []
    for key in order:
        group = groups[key]
        if len(group) == 1:
            out.append(copy.deepcopy(group[0]))
            continue
        keeper = None
        for r in group:
            if _frame(r) > 0 and _frame(r) == frame_for_number(_no(r), total):
                keeper = r
                break
        if keeper is None:
            keeper = group[0]
        merged = copy.deepcopy(keeper)
        for r in group:
            if r is keeper:
                continue
            for k, value in r.items():
                if k in IDENTITY_FIELDS:
                    continue
                if _meaningful(value) and not _meaningful(merged.get(k)):
                    merged[k] = copy.deepcopy(value)
        if report is not None:
            report.append({
                "name": key,
                "keptNumber": _no(keeper),
                "droppedNumbers": [_no(r) for r in group if r is not keeper],
            })
        out.append(merged)
    out.sort(key=lambda r: (_no(r) <= 0, _no(r), _name(r)))
    return out
