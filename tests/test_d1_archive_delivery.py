"""Prove server accepted feature archives, not merely an HTTP 200 response."""
from __future__ import annotations
import copy
import unittest
from scripts.arvexq_protect_sync import verify_published


def row():
    return {
        "id":"race-100",
        "horses":[{"horseNumber":1,"careerArchive":{
            "sha256":"horsehash","encoding":"arvexq-career-gzip-json-v2"}}],
        "massFeatureArchive":{
            "sha256":"masshash","featureHash":"features",
            "encoding":"arvexq-mass-feature-gzip-json-v1"},
    }


class D1ArchiveDeliveryTest(unittest.TestCase):
    def test_archive_delivery_and_no_seal_requirement(self):
        original=row()
        self.assertEqual(
            verify_published({"details":[original]},base="https://unit.invalid",
                             read=lambda base,rid:copy.deepcopy(original)),
            ["race-100"])

    def test_d1_discarding_feature_archive_fails(self):
        original=row()
        bad=copy.deepcopy(original)
        bad.pop("massFeatureArchive",None)
        with self.assertRaisesRegex(RuntimeError,"D1_MASS_ARCHIVE_POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="https://unit.invalid",retry_delays=(),
                             read=lambda base,rid:bad)

    def test_d1_discarding_horse_career_archive_fails(self):
        original=row()
        bad=copy.deepcopy(original)
        bad["horses"][0].pop("careerArchive",None)
        with self.assertRaisesRegex(RuntimeError,"D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="https://unit.invalid",retry_delays=(),
                             read=lambda base,rid:bad)

    def test_stale_d1_read_is_retried_without_disabling_integrity(self):
        original=row()
        missing=copy.deepcopy(original)
        missing["horses"][0].pop("careerArchive")
        attempts=[]
        delays=[]
        def read(base,rid):
            attempts.append(rid)
            return copy.deepcopy(missing if len(attempts)==1 else original)
        self.assertEqual(
            verify_published({"details":[original]},base="https://unit.invalid",
                             read=read,retry_delays=(.01,),sleeper=delays.append),
            ["race-100"])
        self.assertEqual(len(attempts),2)
        self.assertEqual(delays,[.01])

    def test_persistent_d1_data_loss_fails_after_bounded_retry(self):
        original=row()
        bad=copy.deepcopy(original)
        bad["horses"][0].pop("careerArchive")
        reads=[]
        with self.assertRaisesRegex(RuntimeError,"D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="https://unit.invalid",
                             read=lambda base,rid: (reads.append(rid),bad)[1],
                             retry_delays=(.01,.02),sleeper=lambda _:None)
        self.assertEqual(len(reads),3)

    def test_richer_concurrent_career_archive_is_verified(self):
        from arvexq.ingest.career_transport import pack_horse
        day="2026-10-10"
        def run(d, finish=3):
            return {"date":d,"finish":finish,"fieldSize":12,"cornerPositions":[2,2,2]}
        base={"horseNumber":1,"name":"horse","allPastRuns":[
            run("2026-09-01"),run("2026-09-10")]}
        expected={"id":"race-100","date":day,
                  "horses":[pack_horse(base,day)]}
        richer=copy.deepcopy(base)
        richer["allPastRuns"].append(run("2026-08-20"))
        actual={"id":"race-100","date":day,
                "horses":[pack_horse(richer,day)]}
        self.assertNotEqual(expected["horses"][0]["careerArchive"]["sha256"],
                            actual["horses"][0]["careerArchive"]["sha256"])
        self.assertEqual(
            verify_published({"details":[expected]},base="https://unit.invalid",
                             read=lambda _base,_rid:copy.deepcopy(actual)), ["race-100"])

    def test_concurrent_career_replacement_with_missing_or_rewritten_runs_fails(self):
        from arvexq.ingest.career_transport import pack_horse
        day="2026-10-10"
        def run(d, finish=3):
            return {"date":d,"finish":finish,"fieldSize":12}
        source={"horseNumber":1,"name":"horse","allPastRuns":[
            run("2026-09-01"),run("2026-09-10")]}
        expected={"id":"race-100","date":day,"horses":[pack_horse(source,day)]}
        for actual_runs in [
            [run("2026-09-10")],  # dropped a historical start
            [run("2026-09-01", 1),run("2026-09-10")],  # rewrote a finish
            [run("2026-09-01"),run("2026-09-10", 1),run("2026-08-20")],
        ]:
            actual={"id":"race-100","date":day,"horses":[pack_horse(
                {"horseNumber":1,"name":"horse","allPastRuns":actual_runs},day)]}
            with self.assertRaisesRegex(RuntimeError,
                                        "D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH"):
                verify_published({"details":[expected]},base="https://unit.invalid",retry_delays=(),
                                 read=lambda _base,_rid:copy.deepcopy(actual))

    def test_corrupted_richer_archive_never_passes_preservation_check(self):
        from arvexq.ingest.career_transport import pack_horse
        day="2026-10-10"
        old={"horseNumber":1,"name":"horse","allPastRuns":[
            {"date":"2026-09-01","finish":2,"fieldSize":10}]}
        expected={"id":"race-100","date":day,"horses":[pack_horse(old,day)]}
        richer=copy.deepcopy(old)
        richer["allPastRuns"].append({"date":"2026-09-05","finish":3,"fieldSize":10})
        current=pack_horse(richer,day)
        current["careerArchive"]["sha256"]="0"*64
        actual={"id":"race-100","date":day,"horses":[current]}
        with self.assertRaisesRegex(RuntimeError,"D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH"):
            verify_published({"details":[expected]},base="https://unit.invalid",retry_delays=(),
                             read=lambda _base,_rid:actual)

    def test_old_preoff_frozen_prediction_remains_requisite(self):
        original=row()
        original["modelMarkRevisions"]=[{"reason":"official track condition"}]
        changed=copy.deepcopy(original)
        changed["modelMarkRevisions"]=[]
        with self.assertRaisesRegex(RuntimeError,"D1_MODEL_MARK_REVISION_POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="https://unit.invalid",retry_delays=(),
                             read=lambda base,rid:changed)


if __name__=="__main__":
    unittest.main()
