"""Publishing must not classify a mere ticket-kind label as purchasable selected."""
from __future__ import annotations
import copy
import unittest
from scripts.arvexq_publish_morning_static import morning_manifest


def prepared():
    date="2026-10-11"
    rid=f"nar-{date}-高知-07"
    fixed="2026-10-11T06:30:00+09:00"
    marks=[{"horseNumber":i,"mark":"◎" if i==1 else "○"} for i in range(1,7)]
    evidence={"version":"arvexq-morning-ticket-evidence-v1",
              "raceId":rid,"raceDate":date,"fixedAt":fixed,
              "axisStatus":"honmei","axisHorseNumber":1,"marks":marks,
              "items":[{"kind":"ワイド","level":"本線","combos":[[1,2],[1,3]]}],
              "ticketKinds":["ワイド"]}
    return {"summaries":[{"id":rid,"date":date,"startTime":"17:45",
             "morningPickFixedAt":fixed,"morningPickVersion":"v1",
             "morningPickScope":1,"morningSelected":True,
             "morningSpecial":False,"morningPrimaryType":"的中重視型",
             "morningSelectedTypes":["的中重視型"],"morningTicketKinds":["ワイド"],
             "morningTicketEvidence":evidence}],
            "details":[{"id":rid,"date":date,"horses":[{"horseNumber":i} for i in range(1,7)]}]}


class MorningPublishEvidenceTest(unittest.TestCase):
    def test_publish_saves_precise_original_and_axis(self):
        p=prepared()
        original=copy.deepcopy(p)
        manifest=morning_manifest(p)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["races"][0]["ticketEvidence"],p["summaries"][0]["morningTicketEvidence"])
        self.assertEqual(manifest["races"][0]["ticketEvidence"]["axisHorseNumber"],1)
        self.assertEqual(manifest["races"][0]["ticketEvidence"]["items"][0]["combos"],[[1,2],[1,3]])
        self.assertEqual(p,original)

    def test_kind_only_is_not_purchasable(self):
        p=prepared()
        p["summaries"][0].pop("morningTicketEvidence")
        self.assertIsNone(morning_manifest(p))

    def test_late_wrong_race_and_fake_combo_are_rejected(self):
        for changed in ("late","wrong","ghost","empty"):
            p=prepared()
            e=p["summaries"][0]["morningTicketEvidence"]
            if changed=="late":
                e["fixedAt"]="2026-10-11T18:00:00+09:00"
            if changed=="wrong":
                e["raceId"]="another"
            if changed=="ghost":
                e["items"][0]["combos"]=[[1,999]]
            if changed=="empty":
                e["items"]=[]
            with self.subTest(changed=changed):
                self.assertIsNone(morning_manifest(p))

    def test_unselected_day_never_requires_ticket(self):
        p=prepared()
        p["summaries"][0]["morningSelected"]=False
        p["summaries"][0].pop("morningTicketEvidence")
        self.assertIsNotNone(morning_manifest(p))

if __name__=="__main__":
    unittest.main()
