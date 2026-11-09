# -*- coding: utf-8 -*-
"""env_repair_targets tests (2026-11-09 NAR surface repair).

The publish lane re-issues a 2026-11-09 NAR v9b forecast whose
probabilities were computed while the surface builders served ""
(fixed in main 2e01ec9e), but only from a stored detail that
already carries the real surface. Most stored details still carry
the "" baked in before the fix, so a qualifying race whose stored
detail still lacks its surface must be an explicit sync target —
its refreshed detail is what lets the publish lane's
env-repair-upgrade fire inside its own 30-minute guard.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "arvexq_live_sync", ROOT / "scripts" / "arvexq_live_sync.py")
live_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_sync)

env_repair_targets = live_sync.env_repair_targets

FIRST = "2026-11-08T21:55:37+09:00"


def row(rid, start, date="2026-11-09"):
    h, m = divmod(start, 60)
    return {"id": rid, "track": "川崎", "circuit": "地方",
            "date": date, "startTime": f"{h:02d}:{m:02d}"}


def detail(surface="", lane="v9b-cal-market", revision=None,
           first=FIRST, published=None, date="2026-11-09"):
    marker = {"abilityLane": lane, "blendApplied": True,
              "firstPublishedAt": first,
              "publishedAt": published or first}
    if revision is not None:
        marker["revision"] = revision
    return {"date": date, "surface": surface,
            "preparedMeta": {"rewritePublish": marker}}


def revision(kind, revised_at, with_kind=True):
    rev = {"reason": kind, "revisedAt": revised_at, "revisionCount": 1}
    if with_kind:
        rev["kind"] = kind
    return rev


class EnvRepairTargetsTest(unittest.TestCase):
    NOW = 14 * 60 + 40  # 14:40 JST

    def test_dead_surface_race_is_targeted(self):
        rid = "nar-2026-11-09-川崎-02"
        rows = [row(rid, 15 * 60 + 30)]
        details = {rid: detail(revision=revision(
            "blend-upgrade", "2026-11-09T02:29:01+09:00"))}
        self.assertEqual(env_repair_targets(rows, details, self.NOW),
                         [rid])

    def test_detail_already_carrying_surface_is_not_targeted(self):
        rid = "nar-2026-11-09-川崎-03"
        rows = [row(rid, 16 * 60)]
        details = {rid: detail(surface="ダート")}
        self.assertEqual(env_repair_targets(rows, details, self.NOW), [])

    def test_recomputed_after_fix_is_not_targeted(self):
        rid = "nar-2026-11-09-盛岡-11"
        rows = [row(rid, 17 * 60 + 40)]
        details = {rid: detail(revision=revision(
            "roster-change", "2026-11-09T14:02:33+09:00",
            with_kind=False))}
        self.assertEqual(env_repair_targets(rows, details, self.NOW), [])

    def test_surgical_revision_still_targeted(self):
        rid = "nar-2026-11-09-佐賀-02"
        rows = [row(rid, 16 * 60 + 55)]
        details = {rid: detail(revision=revision(
            "place-ev-upgrade", "2026-11-09T14:01:20+09:00"))}
        self.assertEqual(env_repair_targets(rows, details, self.NOW),
                         [rid])

    def test_already_repaired_is_not_targeted(self):
        rid = "nar-2026-11-09-川崎-01"
        rows = [row(rid, 16 * 60 + 30)]
        details = {rid: detail(surface="", revision=revision(
            "env-repair-upgrade", "2026-11-09T14:45:00+09:00"))}
        self.assertEqual(env_repair_targets(rows, details, self.NOW), [])

    def test_scope_date_lane_and_guard(self):
        rid = "nar-2026-11-09-川崎-04"
        rows = [row(rid, 16 * 60 + 30)]
        self.assertEqual(env_repair_targets(
            rows, {rid: detail(date="2026-11-10")}, self.NOW), [])
        self.assertEqual(env_repair_targets(
            rows, {rid: detail(lane="v8-elo-speed2")}, self.NOW), [])
        # 30 minutes out: inside the targeting lead (35).
        soon = "nar-2026-11-09-川崎-05"
        rows = [row(soon, self.NOW + 30)]
        self.assertEqual(env_repair_targets(
            rows, {soon: detail()}, self.NOW), [])


if __name__ == "__main__":
    unittest.main()
