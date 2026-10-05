from __future__ import annotations

from itertools import permutations
from typing import Any


def six_ticket_challenge(first: int, partners: list[int]) -> list[tuple[int, int, int]]:
    """Generate the fixed ARVEXQ six-ticket trifecta challenge.

    First place is fixed. Three partner horses rotate through second/third.
    """
    unique = []
    for no in partners:
        no = int(no or 0)
        if no > 0 and no != int(first) and no not in unique:
            unique.append(no)
    if int(first or 0) <= 0 or len(unique) != 3:
        return []
    return [(int(first), a, b) for a, b in permutations(unique, 2)]


def tickets_from_marks(rows: list[dict[str, Any]]) -> list[tuple[int, int, int]]:
    mark_map: dict[str, int] = {}
    for row in rows:
        mark = str(row.get("mark") or row.get("predMark") or "")
        horse = row.get("horse") or row
        no = int(horse.get("horseNumber") or 0)
        if no > 0 and mark:
            mark_map.setdefault(mark, no)
    first = mark_map.get("◎")
    partners = [mark_map.get("○"), mark_map.get("▲"), mark_map.get("☆+")]
    if not first or any(v is None for v in partners):
        return []
    return six_ticket_challenge(first, [int(v) for v in partners if v is not None])
