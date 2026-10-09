"""No post-off edits: user-approved model update is a separate pre-off revision."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import unittest

from arvexq.prediction.prerace_archive import JST
from arvexq.prediction.official_course_revision import latest_pre_off_marks
from arvexq.prediction.user_approved_model_revision import (
    APPROVAL_ID, MODEL, REVISION_VERSION, enabled, update_marks, valid_revision,
)
from scripts.arvexq_protect_sync import protect_detail

BASE_TIME = datetime(2026, 10, 9, 22, 12, tzinfo=JST)


def race():
    rid="nar-2026-10-09-園田-12"
    return {
        "id": rid, "date": "2026-10-09", "startTime": "23:40",
        "surface": "ダート", "track": "園田", "condition": "良",
        "horses": [{"horseNumber": i, "name": str(i)} for i in range(1,4)],
        "morningMarkSnapshot": {
            "version":"arvexq-morning-marks-v1","raceId":rid,
            "raceDate":"2026-10-09",
            "fixedAt":"2026-10-09T09:07:59+09:00",
            "horses":[{"horseNumber":1,"mark":"◎"},{"horseNumber":2,"mark":"○"},
                      {"horseNumber":3,"mark":"▲"}],
        },
    }


def recompute(_):
    return [{"horseNumber":1,"mark":"○"},{"horseNumber":2,"mark":"◎"},
            {"horseNumber":3,"mark":"▲"}]


class UserModelMarkRevisionTests(unittest.TestCase):
    def test_on_time_only_and_does_not_change_morning_original(self):
        old=race()
        new,status=update_marks(old,now=BASE_TIME,calculate=recompute)
        self.assertEqual(status,"changed:1,2")
        self.assertEqual(old["morningMarkSnapshot"],new["morningMarkSnapshot"])
        self.assertEqual(new["modelMarkRevisions"][0]["approvalId"],APPROVAL_ID)
        self.assertEqual(new["modelMarkRevisions"][0]["modelVersion"],MODEL)
        self.assertEqual(new["modelMarkRevisions"][0]["version"],REVISION_VERSION)
        self.assertTrue(valid_revision(new,new["modelMarkRevisions"][0]))
        self.assertEqual(latest_pre_off_marks(new)["horses"][1]["mark"],"◎")
        again,msg=update_marks(new,now=BASE_TIME,calculate=recompute)
        self.assertEqual(msg,"already-revised")
        self.assertEqual(again["modelMarkRevisions"],new["modelMarkRevisions"])

    def test_after_off_or_any_other_day_never_changes(self):
        for now in (datetime(2026,10,9,23,40,tzinfo=JST),
                    datetime(2026,10,10,0,10,tzinfo=JST),
                    datetime(2026,10,9,20,9,tzinfo=JST)):
            new,status=update_marks(race(),now=now,calculate=recompute)
            self.assertNotIn("modelMarkRevisions",new)
            self.assertFalse(status.startswith("changed:"))
        self.assertFalse(enabled(datetime(2026,10,10,11,tzinfo=JST)))

    def test_prior_bet_or_sealed_prediction_forbids_revision(self):
        original=race()
        original["preRaceBet"]={"raceId":original["id"],
            "fixedAt":"2026-10-09T22:11:00+09:00","decision":"見送り","items":[]}
        new,status=update_marks(original,now=BASE_TIME,calculate=recompute)
        self.assertEqual(status,"already-sealed-no-changes")
        self.assertNotIn("modelMarkRevisions",new)

    def test_unsupported_revision_is_never_used(self):
        d=race()
        new,_=update_marks(d,now=BASE_TIME,calculate=recompute)
        candidate=new["modelMarkRevisions"][0]
        for changed in (
            {**candidate,"revisedAt":"2026-10-09T23:41:00+09:00"},
            {**candidate,"revisedAt":"2026-10-09T20:09:00+09:00"},
            {**candidate,"approvalId":"unapproved"},
            {**candidate,"modelVersion":"unknown"},
            {**candidate,"horses":[{"horseNumber":5,"mark":"◎"}]},
        ):
            self.assertFalse(valid_revision(d,changed))
            self.assertEqual(latest_pre_off_marks({**d,"modelMarkRevisions":[changed]})["horses"][0]["mark"],"◎")

    def test_no_op_and_failures_keep_original(self):
        a,status=update_marks(race(),now=BASE_TIME,
                              calculate=lambda d:deepcopy(d["morningMarkSnapshot"]["horses"]))
        self.assertEqual(status,"no-mark-change")
        self.assertNotIn("modelMarkRevisions",a)
        b,status=update_marks(race(),now=BASE_TIME,calculate=lambda d:[])
        self.assertEqual(status,"invalid-preoff-revision")
        self.assertNotIn("modelMarkRevisions",b)

    def test_revised_mark_requires_actual_d1_readback(self):
        from scripts.arvexq_protect_sync import verify_published
        before=race()
        after,status=update_marks(before,now=BASE_TIME,calculate=recompute)
        self.assertTrue(status.startswith("changed:"),status)
        self.assertEqual(
            verify_published({"details":[after]},base="https://test.invalid",
                             read=lambda base,rid:deepcopy(after)), [before["id"]])
        with self.assertRaisesRegex(RuntimeError,"D1_MODEL_MARK_REVISION_POST_VERIFY_MISMATCH"):
            verify_published({"details":[after]},base="https://test.invalid",
                             read=lambda base,rid:deepcopy(before))

    def test_untrusted_revision_does_not_survive_write_guard(self):
        d=race()
        candidate={"version":REVISION_VERSION,"approvalId":"fake",
                   "modelVersion":MODEL,"raceId":d["id"],
                   "raceDate":d["date"],"revisedAt":BASE_TIME.isoformat(),
                   "horses":recompute(d)}
        got=protect_detail(d,{**d,"modelMarkRevisions":[candidate]})
        self.assertNotIn("modelMarkRevisions",got)


if __name__=="__main__":
    unittest.main()
