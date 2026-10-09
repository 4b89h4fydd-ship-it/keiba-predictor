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
            verify_published({"details":[original]},base="https://unit.invalid",
                             read=lambda base,rid:bad)

    def test_d1_discarding_horse_career_archive_fails(self):
        original=row()
        bad=copy.deepcopy(original)
        bad["horses"][0].pop("careerArchive",None)
        with self.assertRaisesRegex(RuntimeError,"D1_CAREER_ARCHIVE_POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="https://unit.invalid",
                             read=lambda base,rid:bad)

    def test_old_preoff_frozen_prediction_remains_requisite(self):
        original=row()
        original["modelMarkRevisions"]=[{"reason":"official track condition"}]
        changed=copy.deepcopy(original)
        changed["modelMarkRevisions"]=[]
        with self.assertRaisesRegex(RuntimeError,"D1_MODEL_MARK_REVISION_POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="https://unit.invalid",
                             read=lambda base,rid:changed)


if __name__=="__main__":
    unittest.main()
