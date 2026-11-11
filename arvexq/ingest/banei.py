"""Obihiro banei exclusion: the single shared test for every route.

Banei (帯広ばんえい) is out of scope for the whole system: it must
never be collected, published, synced to D1 or displayed. Before
2026-11-11 each route spelled the exclusion on its own — the collect
stage used a dual track/id filter, the rewrite publisher checked
only the track string (and let a race through when the track was
missing), the D1 sync guard had no check at all, and the prefetch
analyze stage filtered its race rows but not its details dict.

Every route now asks this one function. A race counts as banei when
its track name starts with 帯広 OR its race id embeds -帯広- /
-帯広ば- (race ids always embed the venue, so the id check still
fires when the track field is absent). Identification is not
inclusion: affiliation lists such as NAR_TRACKS keep naming 帯広 so
historical records can be recognised and excluded, never served.
"""
from __future__ import annotations

from typing import Any, Optional


def is_banei(track: Optional[Any] = None, race_id: Optional[Any] = None) -> bool:
    name = str(track or "").strip()
    if name.startswith("帯広"):
        return True
    rid = str(race_id or "")
    return "-帯広-" in rid or "-帯広ば-" in rid or rid.startswith("帯広")
