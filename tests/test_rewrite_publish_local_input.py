"""Local input mode for the rewrite publish lane (GitHub-only).

With --local-input the lane reads its stored state from the
collection lane's day file (fresh facts) plus the committed static
packs (prior published state) instead of the D1-backed API, and
posts nothing.  The stored detail the build consumes is the same
merge the retired D1 facts sync produced server-side:
protect_detail(prior pack detail, fresh facts detail).

The load-bearing subtlety these tests pin: pack details pass
through the delivery projection, which renames a published race's
predictionStatus to "unified-reference-ready".  The freeze
decision keys on the stored spelling, so a projected pack read
left as-is would make a frozen race look never-published.  The
de-projection restores the stored spelling only when the detail
carries this lane's marker and its receipt chain verifies.
"""
from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from zoneinfo import ZoneInfo

from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    _active_roster, _deproject_pack_detail, _freeze_decision,
    _load_local_day, _load_protect, _local_input_for_date,
    _local_pack_detail, build_publish_detail, load_local_input_detail)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
RID = "nar-2099-01-01-高知-12"
DAY = "2099-01-01"
FORECAST_KEYS = ("unifiedForecast", "prediction", "predictionMarks",
                 "recommendedBets", "forecastText", "predictionStatus",
                 "predictionModelVersion", "preRaceBet", "masterAnalysis")


def published_detail(status: str = "ready") -> dict:
    """A detail this lane has published, in the stored spelling
    (status="ready") or as the pack projection serves it
    (status="unified-reference-ready")."""
    return {
        "id": RID,
        "date": DAY,
        "scheduledStartTime": "20:50",
        "predictionStatus": status,
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": {
            "modelVersion": MODEL_VERSION,
            "publishedAt": "2026-11-01T08:00:00+09:00",
            "receiptSha256": RECEIPT,
            "abilityLane": "v8-elo-speed2"}},
        "unifiedForecast": {
            "receiptSha256": RECEIPT,
            "roster": [{"horseNumber": 1, "name": "アアア"},
                       {"horseNumber": 2, "name": "イイイ"},
                       {"horseNumber": 3, "name": "ウウウ"}]},
        "predictionMarks": [{"horseNumber": 1, "mark": "◎"}],
        "horses": [{"horseNumber": 1, "name": "アアア"},
                   {"horseNumber": 2, "name": "イイイ"},
                   {"horseNumber": 3, "name": "ウウウ"}],
        "weather": "晴",
    }


def facts_detail() -> dict:
    """The same race as a fresh facts detail: no forecast-owned
    blocks, no lane marker, and a facts-side change (weather) so a
    test can prove the facts form the merge base."""
    detail = published_detail()
    for key in FORECAST_KEYS:
        detail.pop(key, None)
    detail["preparedMeta"] = {}
    detail["weather"] = "雨"
    return detail


class LocalDayFileTests(TestCase):
    def test_loads_and_indexes_by_date(self):
        payload = {"date": DAY, "races": [{"id": RID}],
                   "details": [{"id": RID, "horses": []}]}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "persisted-facts.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            day = _load_local_day(path)
        ctx = _local_input_for_date(day, DAY, Path(td) / "packs")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["summaries"], [{"id": RID}])
        self.assertEqual(list(ctx["facts_by_id"]), [RID])

    def test_other_dates_file_is_refused(self):
        day = {"date": "2099-01-02", "races": [], "details": []}
        self.assertIsNone(_local_input_for_date(day, DAY, Path("packs")))

    def test_malformed_day_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text('{"details": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_local_day(path)


class PackDetailTests(TestCase):
    def _packs(self, td: str, body) -> Path:
        packs = Path(td) / "packs"
        (packs / "race").mkdir(parents=True)
        if body is not None:
            (packs / "race" / f"{RID}.json").write_text(
                json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return packs

    def test_reads_detail_member(self):
        with tempfile.TemporaryDirectory() as td:
            packs = self._packs(td, {"detail": {"id": RID}})
            self.assertEqual(_local_pack_detail(packs, RID), {"id": RID})

    def test_missing_or_malformed_pack_is_absent(self):
        with tempfile.TemporaryDirectory() as td:
            packs = self._packs(td, None)
            self.assertIsNone(_local_pack_detail(packs, RID))
            (packs / "race" / f"{RID}.json").write_text(
                "{not json", encoding="utf-8")
            self.assertIsNone(_local_pack_detail(packs, RID))
            (packs / "race" / f"{RID}.json").write_text(
                '{"ok": true}', encoding="utf-8")
            self.assertIsNone(_local_pack_detail(packs, RID))


class DeprojectionTests(TestCase):
    def test_verified_publication_status_is_restored(self):
        pack = published_detail(status="unified-reference-ready")
        restored = _deproject_pack_detail(pack)
        self.assertEqual(restored["predictionStatus"], "ready")
        # The input is not mutated; the caller decides what to use.
        self.assertEqual(pack["predictionStatus"],
                         "unified-reference-ready")

    def test_broken_receipt_chain_is_untouched(self):
        pack = published_detail(status="unified-reference-ready")
        pack["unifiedForecast"]["receiptSha256"] = "b" * 64
        self.assertEqual(
            _deproject_pack_detail(pack)["predictionStatus"],
            "unified-reference-ready")

    def test_tombstone_is_untouched(self):
        pack = published_detail(status="disabled")
        pack["predictionModelVersion"] = "arvexq-prediction-removed"
        restored = _deproject_pack_detail(pack)
        self.assertEqual(restored["predictionStatus"], "disabled")
        self.assertEqual(restored["predictionModelVersion"],
                         "arvexq-prediction-removed")

    def test_unpublished_detail_is_untouched(self):
        pack = facts_detail()
        pack["predictionStatus"] = "unified-reference-ready"
        self.assertEqual(
            _deproject_pack_detail(pack)["predictionStatus"],
            "unified-reference-ready")


class LocalInputConstructionTests(TestCase):
    def setUp(self):
        self.protect = _load_protect()
        self._td = tempfile.TemporaryDirectory()
        packs = Path(self._td.name) / "packs"
        (packs / "race").mkdir(parents=True)
        self.packs = packs

    def tearDown(self):
        self._td.cleanup()

    def _write_pack(self, detail: dict) -> None:
        (self.packs / "race" / f"{RID}.json").write_text(
            json.dumps({"detail": detail}, ensure_ascii=False),
            encoding="utf-8")

    def _ctx(self, facts: dict | None) -> dict:
        return {"summaries": [],
                "facts_by_id": {RID: facts} if facts is not None else {},
                "packs_dir": self.packs}

    def test_first_publish_input_is_the_facts(self):
        facts = facts_detail()
        built = load_local_input_detail(self._ctx(facts), RID, self.protect)
        self.assertEqual(built["weather"], "雨")
        self.assertNotIn("unifiedForecast", built)

    def test_frozen_state_survives_the_merge(self):
        self._write_pack(published_detail(
            status="unified-reference-ready"))
        built = load_local_input_detail(
            self._ctx(facts_detail()), RID, self.protect)
        # Facts form the base ...
        self.assertEqual(built["weather"], "雨")
        # ... and the publication survives verbatim, in the stored
        # spelling the freeze decision keys on.
        self.assertEqual(built["predictionStatus"], "ready")
        self.assertEqual(built["unifiedForecast"]["receiptSha256"],
                         RECEIPT)
        self.assertEqual(
            built["preparedMeta"]["rewritePublish"]["receiptSha256"],
            RECEIPT)
        self.assertEqual(_freeze_decision(built), ("frozen", RECEIPT))

    def test_projected_pack_alone_would_not_freeze(self):
        # The trap the construction closes: the raw pack read does
        # not classify as this lane's frozen publication.
        self.assertIsNone(_freeze_decision(
            published_detail(status="unified-reference-ready")))

    def test_prior_without_facts_is_used_as_is(self):
        self._write_pack(published_detail())
        built = load_local_input_detail(self._ctx(None), RID, self.protect)
        self.assertEqual(built["predictionStatus"], "ready")
        self.assertEqual(_freeze_decision(built), ("frozen", RECEIPT))

    def test_neither_source_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            load_local_input_detail(self._ctx(None), RID, self.protect)

    def test_pack_scratch_reaches_the_merged_detail(self):
        # The 2026-11-27 Sonoda 8R shape: the realtime sync lane
        # has written an official withdrawal into the pack, but
        # the facts (built at the collection lane's last slot)
        # still carry the runner as active. The publisher's input
        # must show the scratch, or the roster never changes and
        # no re-issue can fire.
        pack = published_detail(status="unified-reference-ready")
        pack["horses"][1]["status"] = "出走取消"
        pack["horses"][1]["scratched"] = True
        pack["horses"][1]["withdrawn"] = True
        self._write_pack(pack)
        facts = facts_detail()
        facts["horses"][1]["winOdds"] = 5.5
        built = load_local_input_detail(
            self._ctx(facts), RID, self.protect)
        horse = built["horses"][1]
        self.assertEqual(horse["status"], "出走取消")
        self.assertIs(horse["scratched"], True)
        self.assertIsNone(horse["winOdds"])
        self.assertEqual([n for n, _ in _active_roster(built)], [1, 3])
        decision = _freeze_decision(built)
        self.assertEqual(decision[0], "reissue")

    def test_no_scratch_in_pack_leaves_the_merge_frozen(self):
        self._write_pack(published_detail(
            status="unified-reference-ready"))
        built = load_local_input_detail(
            self._ctx(facts_detail()), RID, self.protect)
        self.assertEqual([n for n, _ in _active_roster(built)],
                         [1, 2, 3])
        self.assertEqual(_freeze_decision(built), ("frozen", RECEIPT))

    def test_unstatused_pack_flag_does_not_carry(self):
        # A stray scratched flag without an official scratch
        # status is not an authoritative withdrawal; the overlay
        # must not invent one.
        pack = published_detail(status="unified-reference-ready")
        pack["horses"][1]["scratched"] = True
        self._write_pack(pack)
        built = load_local_input_detail(
            self._ctx(facts_detail()), RID, self.protect)
        self.assertEqual([n for n, _ in _active_roster(built)],
                         [1, 2, 3])

    def test_build_gate_keeps_the_frozen_forecast(self):
        self._write_pack(published_detail(
            status="unified-reference-ready"))
        built = load_local_input_detail(
            self._ctx(facts_detail()), RID, self.protect)
        new, reason = build_publish_detail(
            built, {"race_id": RID, "id": RID},
            datetime(2099, 1, 1, 9, 0, tzinfo=JST))
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)


if __name__ == "__main__":
    import unittest
    unittest.main()
