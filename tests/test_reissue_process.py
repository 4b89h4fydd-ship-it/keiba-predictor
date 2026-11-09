"""Slim reissue path (scripts/arvexq_reissue_process.py).

The slim path exists so a targeted re-issue no longer rides a full
publish cycle. Its safety-critical part is the exactly-once check:
the stored detail keeps only the LATEST revision stamp, and a
surgical stamp (place-EV, ticket-R24) replaces the revision dict
wholesale, erasing earlier stamps of other kinds — on 2026-11-09 a
place-ev stamp over an env-repair stamp caused a double repair.

These tests pin the request validation, the full-evidence
goal-state reads (never the latest stamp alone), the marks-block
goal state behind marksResync, and the ledger chain of record that
closes the overwrite hole once this path has observed a race.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from rewrite.analysis.tickets import formation_r24_selections
from scripts import arvexq_reissue_process as proc
from scripts import arvexq_rewrite_publish as pub

JST = ZoneInfo("Asia/Tokyo")
RACE = "nar-2026-11-09-川崎-01"
MARKS = ("◎", "○", "▲", "△", "☆")
ORDER = [3, 5, 1, 7, 9]


def _entry(**over):
    base = {"request_id": "req-test-1", "race_id": RACE,
            "revision_kind": "blend-upgrade", "reason": "test",
            "requested_at": "2026-11-09T16:00:00+09:00"}
    base.update(over)
    return base


def _detail(marker=None, revision=None, order=ORDER, uf_order=None,
            plan=None, date="2026-11-09"):
    if uf_order is None:
        uf_order = order
    unified = {"marks": [{"markSymbol": m, "horseNumber": n}
                         for m, n in zip(MARKS, uf_order)]}
    if plan is not None:
        unified["ticketPlan"] = plan
    detail = {
        "id": RACE, "date": date, "predictionStatus": "ready",
        "predictionMarks": [{"mark": m, "horseNumber": n}
                            for m, n in zip(MARKS, order)],
        "unifiedForecast": unified,
    }
    if marker is not None or revision is not None:
        full = dict(marker or {})
        if revision is not None:
            full["revision"] = revision
        detail["preparedMeta"] = {"rewritePublish": full}
    return detail


class ValidationTest(TestCase):
    def test_valid_entry(self):
        self.assertIsNone(proc.validate_entry(_entry()))

    def test_bad_race_id(self):
        self.assertIsNotNone(proc.validate_entry(
            _entry(race_id="kawasaki-01")))

    def test_unknown_kind(self):
        self.assertIsNotNone(proc.validate_entry(
            _entry(revision_kind="roster-change")))

    def test_missing_reason(self):
        self.assertIsNotNone(proc.validate_entry(_entry(reason="")))

    def test_unknown_mode(self):
        self.assertIsNotNone(proc.validate_entry(_entry(mode="yolo")))


class MarksAgreementTest(TestCase):
    def test_blocks_agree(self):
        self.assertTrue(proc.marks_blocks_agree(_detail()))

    def test_blocks_disagree(self):
        self.assertFalse(proc.marks_blocks_agree(
            _detail(uf_order=[9, 5, 1, 7, 3])))

    def test_unreadable(self):
        self.assertIsNone(proc.marks_blocks_agree({"id": RACE}))


class GoalStateTest(TestCase):
    def test_blend_via_marker_state(self):
        detail = _detail(marker={"blendApplied": True})
        self.assertIsNotNone(proc.goal_state(detail, "blend-upgrade",
                                             pub))

    def test_blend_not_applied(self):
        detail = _detail(marker={"blendApplied": False})
        self.assertIsNone(proc.goal_state(detail, "blend-upgrade",
                                          pub))

    def test_lane_via_ability_lane(self):
        detail = _detail(marker={"abilityLane": pub.V9B_LANE})
        self.assertIsNotNone(proc.goal_state(detail, "lane-upgrade",
                                             pub))

    def test_place_ev_via_product_state(self):
        detail = _detail(marker={},
                         plan={"placeExpectedValues": []})
        self.assertIsNotNone(proc.goal_state(detail, "place-ev-upgrade",
                                             pub))

    def test_ticket_r24_via_stored_shape(self):
        detail = _detail(marker={})
        detail["recommendedBets"] = [{
            "kind": "3連単",
            "combos": [list(c)
                       for c in formation_r24_selections(ORDER)]}]
        self.assertIsNotNone(proc.goal_state(
            detail, "ticket-r24-upgrade", pub))

    def test_env_via_latest_stamp(self):
        detail = _detail(marker={}, revision={
            "kind": "env-repair-upgrade",
            "revisedAt": "2026-11-09T14:22:58+09:00"})
        self.assertIsNotNone(proc.goal_state(
            detail, "env-repair-upgrade", pub))

    def test_env_stamp_overwritten_by_place_ev_is_not_claimed(self):
        # The 2026-11-09 hole: the env stamp is gone (a place-ev
        # stamp sits on top) and the probabilities date from BEFORE
        # the fix — the detail alone must NOT claim env applied.
        detail = _detail(marker={
            "firstPublishedAt": "2026-11-08T21:55:37+09:00"},
            revision={"kind": "place-ev-upgrade",
                      "revisedAt": "2026-11-09T15:05:00+09:00"})
        self.assertIsNone(proc.goal_state(
            detail, "env-repair-upgrade", pub))

    def test_env_claimed_when_probabilities_postdate_fix(self):
        # Same overwritten shape, but the probabilities themselves
        # were first computed after the surface fix went live.
        detail = _detail(marker={
            "firstPublishedAt": "2026-11-09T11:05:00+09:00"},
            revision={"kind": "place-ev-upgrade",
                      "revisedAt": "2026-11-09T15:05:00+09:00"})
        self.assertIsNotNone(proc.goal_state(
            detail, "env-repair-upgrade", pub))

    def test_env_claimed_via_recompute_revision_time(self):
        detail = _detail(marker={}, revision={
            "kind": "blend-upgrade",
            "revisedAt": "2026-11-09T12:00:00+09:00"})
        self.assertIsNotNone(proc.goal_state(
            detail, "env-repair-upgrade", pub))

    def test_env_out_of_scope_date(self):
        detail = _detail(marker={}, revision={
            "kind": "env-repair-upgrade",
            "revisedAt": "2026-11-09T14:22:58+09:00"},
            date="2026-11-10")
        detail["id"] = "nar-2026-11-10-川崎-01"
        self.assertIsNone(proc.goal_state(
            detail, "env-repair-upgrade", pub))

    def test_marks_resync_goal_is_agreement(self):
        self.assertIsNotNone(proc.goal_state(_detail(), "marksResync",
                                             pub))
        self.assertIsNone(proc.goal_state(
            _detail(uf_order=[9, 5, 1, 7, 3]), "marksResync", pub))


class AlreadyAppliedTest(TestCase):
    def test_ledger_outcome_wins(self):
        ledger = {"results": {"req-old": {
            "race_id": RACE, "revision_kind": "blend-upgrade",
            "status": "applied"}}, "observations": {}}
        found = proc.already_applied(RACE, "blend-upgrade",
                                     _detail(marker={}), ledger, pub)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "slim-ledger")

    def test_ledger_observation_closes_the_overwrite_hole(self):
        # The detail can no longer prove the env repair (stamp
        # overwritten, probabilities pre-fix) — but this path
        # OBSERVED the env stamp while it was on top, and that
        # observation is the chain of record.
        detail = _detail(marker={
            "firstPublishedAt": "2026-11-08T21:55:37+09:00"},
            revision={"kind": "place-ev-upgrade",
                      "revisedAt": "2026-11-09T15:05:00+09:00"})
        ledger = {"results": {}, "observations": {RACE: [{
            "observed_at": "2026-11-09T14:30:00+09:00",
            "request_id": "req-earlier",
            "applied_kinds": ["env-repair-upgrade"]}]}}
        found = proc.already_applied(RACE, "env-repair-upgrade",
                                     detail, ledger, pub)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "slim-ledger-observation")

    def test_nothing_applied(self):
        ledger = {"results": {}, "observations": {}}
        detail = _detail(marker={"blendApplied": False})
        self.assertIsNone(proc.already_applied(
            RACE, "blend-upgrade", detail, ledger, pub))

    def test_stamp_state_snapshots_revision(self):
        detail = _detail(marker={"blendApplied": True}, revision={
            "kind": "env-repair-upgrade", "revisionCount": 2,
            "revisedAt": "2026-11-09T14:22:58+09:00"})
        state = proc.stamp_state(detail)
        self.assertEqual(state["revision"]["kind"],
                         "env-repair-upgrade")
        self.assertTrue(state["marker"]["blendApplied"])
