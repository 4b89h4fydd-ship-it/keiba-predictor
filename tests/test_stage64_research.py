import copy
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from arvexq.research.stage63.forward import canonical, digest
from arvexq.research.stage64.circuits import CONFIGS
from arvexq.research.stage64.pipeline import predict
from arvexq.research.stage64.protocol import make_plan, snapshot, verify_local, freeze_batch
from arvexq.research.stage64.witness import read_witness, verify_batch, REPO, REPO_ID, LIMIT
from arvexq.research.stage64.evaluation import evaluate


def race(owner="nar"):
    return {"id":owner+"-2026-10-21-試験場-01","date":"2026-10-21","circuit":owner,
            "track":"試験場","surface":"芝" if owner=="jra" else "ダート",
            "analysisMode":"平地","startTime":"12:00","fieldSize":4,
            "horses":[{"horseNumber":n,"recentRaces":[
                {"date":"2026-10-15","finish":n,"fieldSize":4,"passing":[n],"track":"試験場"}]}
                for n in (1,2,3,4)]}


def local_receipt(owner="nar"):
    plan=make_plan(owner,["old-race"])
    with patch("arvexq.research.stage64.protocol.datetime") as dt:
        dt.now.return_value=datetime(2026,10,20,12,tzinfo=timezone.utc)
        dt.fromisoformat.side_effect=datetime.fromisoformat
        receipt=snapshot(race(owner),plan)
    return plan,receipt


class FakeArtifacts:
    """Synthetic tests only; cannot establish actual racing performance."""
    def __init__(self):
        plan,receipt=local_receipt()
        batch={"schema":"arvexq-stage64-batch-1","planSha256":digest(plan),
               "cohort":[receipt["snapshot"]["raceId"]],"receipts":[receipt]}
        self.plan=plan;self.batch=batch
        self.payloads={1:{"plan":plan},2:batch}
        self.metas={};self.runs={};self.archives={}
        for no,day in ((1,"2026-10-19"),(2,"2026-10-20")):
            b=io.BytesIO()
            with zipfile.ZipFile(b,"w") as z:z.writestr("bundle.json",canonical(self.payloads[no]))
            raw=b.getvalue()
            self.archives[no]=raw
            self.metas[no]={"id":no,"expired":False,"created_at":day+"T12:01:00Z",
                            "updated_at":day+"T12:01:00Z","digest":"sha256:"+sha256(raw).hexdigest(),
                            "workflow_run":{"id":no+100,"repository_id":REPO_ID,
                                            "head_repository_id":REPO_ID,"head_sha":"a"*40}}
            self.runs[no+100]={"id":no+100,"head_sha":"a"*40,"status":"completed","conclusion":"success",
                               "created_at":day+"T12:00:00Z","updated_at":day+"T12:02:00Z",
                               "repository":{"id":REPO_ID,"full_name":REPO}}
    def metadata(self,i):return self.metas[i]
    def run(self,i):return self.runs[i]
    def archive(self,i):return self.archives[i]


class Pipeline(unittest.TestCase):
    def test_both_circuits_six_stages(self):
        for owner in ("jra","nar"):
            p=predict(race(owner),expected_circuit=owner)
            self.assertEqual(len(p["stages"]),6)
            self.assertTrue(all(s["value"] is not None for s in p["stages"].values()))
            v=p["stages"]["probability"]["value"]
            self.assertAlmostEqual(sum(v["win"].values()),1.)
            self.assertAlmostEqual(sum(v["top3"].values()),3.)
            self.assertTrue(all(0<=v<=1+1e-12 for v in v["top3"].values()))
            self.assertIsNone(p["stages"]["tickets"]["value"]["recommendedBets"])
            self.assertFalse(p["productionEligible"])

    def test_circuit_isolation(self):
        with self.assertRaises(ValueError):predict(race("jra"),expected_circuit="nar")

    def test_circuit_isolation_and_unverified_pace_cannot_move_ability_order(self):
        for owner in ("jra", "nar"):
            r=race(owner)
            # Every horse had a recorded first-corner position, but this
            # does not establish today's lead, an uncontested pace, or odds.
            p=predict(r,expected_circuit=owner)
            self.assertEqual(len(p["stages"]["pace"]["value"]),1)
            self.assertTrue(all(v==0 for v in p["stages"]["pace"]["value"][0].values()))
            self.assertFalse(p["paceEvidence"]["actualLeadVerified"])
            self.assertFalse(p["paceEvidence"]["actualPaceVerified"])
            self.assertEqual(p["stages"]["marks"]["value"]["orderedWinCandidates"][0],1)
            self.assertEqual(p["paceEvidence"]["observedPositionProfiles"][1],"前方")
        self.assertNotEqual(predict(race("jra"),expected_circuit="jra")["modelVersion"],
                            predict(race(),expected_circuit="nar")["modelVersion"])

    def test_all_front_position_does_not_fabricate_lead_competition(self):
        r=race()
        for h in r["horses"]:
            h["recentRaces"][0]["passing"]=[1]
        p=predict(r,expected_circuit="nar")
        self.assertTrue(all(v=="前方" for v in
                            p["paceEvidence"]["observedPositionProfiles"].values()))
        self.assertFalse(p["paceEvidence"]["actualPaceVerified"])
        self.assertEqual(p["stages"]["marks"]["value"]["orderedWinCandidates"][0],1)

    def test_status_only_scratch(self):
        r=race();r["horses"][0]["status"]="競走除外"
        p=predict(r,expected_circuit="nar")
        self.assertNotIn(1,p["stages"]["probability"]["value"]["win"])
        self.assertTrue(all(1 not in c for c in p["stages"]["tickets"]["value"]["hypotheticalTrifectaTop10"]))

    def test_unknown_style_not_filled(self):
        r=race();r["horses"][0]["recentRaces"][0]["passing"]=[]
        p=predict(r,expected_circuit="nar")
        self.assertIsNone(p["stages"]["probability"]["value"])
        self.assertIsNotNone(p["stages"]["ability"]["value"][1])

    def test_incompatible_banei_history(self):
        r=race();r["horses"][0]["recentRaces"][0]["track"]="帯広ば"
        p=predict(r,expected_circuit="nar")
        self.assertIsNone(p["stages"]["tickets"]["value"])
        self.assertIn("incompatible-history-discipline",[r["reason"] for r in p["blockers"]])

    def test_jumps_not_flat(self):
        r=race("jra");r["analysisMode"]="障害"
        self.assertIsNone(predict(r,expected_circuit="jra")["stages"]["tickets"]["value"])

    def test_labels_odds_and_input_mutation(self):
        r=race();base=copy.deepcopy(r);p=predict(r,expected_circuit="nar")
        self.assertEqual(r,base)
        r["result"]={"winner":4};r["horses"][0]["winOdds"]=999
        self.assertEqual(predict(r,expected_circuit="nar"),p)

    def test_plan_does_not_alias_config(self):
        plan=make_plan("nar",[]);plan["config"]["pace"]="neutral"
        self.assertEqual(CONFIGS["nar"]["pace"],"four")

    def test_local_roundtrip_and_no_external_claim(self):
        plan,receipt=local_receipt()
        result=verify_local(json.loads(canonical(receipt)),plan)
        self.assertTrue(result["localIntegrityVerified"])
        self.assertFalse(result["independentlyVerifiedPreoff"])

    def test_local_rehashed_forecast_fails(self):
        plan,receipt=local_receipt()
        receipt["snapshot"]["predictions"]["baseline"]["stages"]["tickets"]["value"]=None
        receipt["snapshotSha256"]=digest(receipt["snapshot"])
        with self.assertRaises(ValueError):verify_local(receipt,plan)

    def test_freeze_no_partial_or_overwrite(self):
        plan,receipt=local_receipt()
        with tempfile.TemporaryDirectory() as td, patch("arvexq.research.stage64.protocol.datetime") as dt:
            dt.now.return_value=datetime(2026,10,20,12,tzinfo=timezone.utc)
            dt.fromisoformat.side_effect=datetime.fromisoformat
            out=Path(td)/"bundle.json"
            bad=race();bad["id"]="nar-2026-10-20-試験場-02";bad["date"]="2026-10-20"
            with self.assertRaises(ValueError):freeze_batch(out,[race(),bad],plan)
            self.assertFalse(out.exists())
            freeze_batch(out,[race()],plan)
            with self.assertRaises(FileExistsError):freeze_batch(out,[race()],plan)


class Witness(unittest.TestCase):
    def setUp(self):
        self.client=FakeArtifacts()
        self.clock=patch("arvexq.research.stage64.witness.datetime")
        self.dt=self.clock.start()
        self.dt.now.return_value=datetime(2026,10,23,tzinfo=timezone.utc)
        self.dt.fromisoformat.side_effect=datetime.fromisoformat
        self.deadline=datetime(2026,10,21,tzinfo=timezone.utc)

    def tearDown(self):self.clock.stop()

    def test_verified_complete_batch(self):
        self.assertTrue(verify_batch(self.client,1,2)["independentlyVerifiedPreoff"])

    def test_digest_mismatch(self):
        self.client.archives[1]+=b"x"
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_missing_digest(self):
        self.client.metas[1]["digest"]=None
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_expired(self):
        self.client.metas[1]["expired"]=True
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_fork(self):
        self.client.metas[1]["workflow_run"]["head_repository_id"]=1
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_wrong_repo(self):
        self.client.runs[101]["repository"]["full_name"]="other/repo"
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_wrong_run_head(self):
        self.client.runs[101]["head_sha"]="b"*40
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_running_workflow(self):
        self.client.runs[101]["status"]="in_progress"
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_postoff_completion_even_if_created_before(self):
        self.client.runs[102]["updated_at"]="2026-10-21T04:00:00Z"
        with self.assertRaises(ValueError):verify_batch(self.client,1,2)

    def test_plan_registration_after_cohort_opens(self):
        self.client.runs[101]["updated_at"]="2026-10-21T00:00:00Z"
        with self.assertRaises(ValueError):verify_batch(self.client,1,2)

    def test_artifact_duplicate_member_rejected(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            z.writestr("bundle.json","{}")
            z.writestr("other.json","{}")
        self.client.archives[1]=b.getvalue()
        self.client.metas[1]["digest"]="sha256:"+sha256(b.getvalue()).hexdigest()
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)

    def test_bad_source_member(self):
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline,source_member="../file.json")

    def test_chronology_inconsistent(self):
        self.client.metas[1]["created_at"]="2026-10-19T11:00:00Z"
        with self.assertRaises(ValueError):read_witness(self.client,1,before=self.deadline)


class Scoring(unittest.TestCase):
    def setUp(self):
        plan,receipt=local_receipt()
        self.receipt=receipt
        self.batch={"cohort":[receipt["snapshot"]["raceId"]],"receipts":[receipt]}
        combo=list(receipt["snapshot"]["predictions"]["baseline"]["stages"]["tickets"]["value"]["hypotheticalTrifectaTop10"][0])
        self.results=[{"raceId":race()["id"],"circuit":"nar","date":race()["date"],
                       "status":"confirmed","orders":[combo],"payouts":[{"order":combo,"amount":2000}]}]

    def test_ticket_scoring_and_no_independence_upgrade(self):
        report=evaluate(self.batch,self.results)
        m=report["byCircuit"]["nar"]["baseline"]
        self.assertEqual(m["trifectaHits"],1)
        self.assertEqual(m["roiPct"],200.)
        self.assertFalse(report["independentlyVerifiedPreoff"])

    def test_missing_payout_unknown_roi(self):
        self.results[0]["payouts"][0]["amount"]=None
        m=evaluate(self.batch,self.results)["byCircuit"]["nar"]["baseline"]
        self.assertEqual(m["trifectaHits"],1)
        self.assertIsNone(m["roiPct"])

    def test_unscored_retained(self):
        for p in self.receipt["snapshot"]["predictions"].values():
            p["stages"]["tickets"]["value"]=None
        m=evaluate(self.batch,self.results)["byCircuit"]["nar"]["baseline"]
        self.assertEqual(m["cohortRaces"],1)
        self.assertEqual(m["unscoredRaces"],1)
        self.assertEqual(m["trifectaHitRateAllCohort"],0.)
        self.assertIsNone(m["trifectaHitRateScored"])

    def test_missing_or_extra_result_rejected(self):
        with self.assertRaises(ValueError):evaluate(self.batch,[])
        with self.assertRaises(ValueError):evaluate(self.batch,self.results*2)

    def test_cross_circuit_result(self):
        self.results[0]["circuit"]="jra"
        with self.assertRaises(ValueError):evaluate(self.batch,self.results)

    def test_unknown_podium_horse(self):
        self.results[0]["orders"]=[[9,2,3]]
        with self.assertRaises(ValueError):evaluate(self.batch,self.results)

    def test_zero_payout_invalid(self):
        self.results[0]["payouts"][0]["amount"]=0
        with self.assertRaises(ValueError):evaluate(self.batch,self.results)

    def test_dead_heat_separate_payouts_and_proper_scores(self):
        self.results[0]["orders"]=[[1,2,3],[2,1,3]]
        self.results[0]["payouts"]=[{"order":[1,2,3],"amount":2000},{"order":[2,1,3],"amount":3000}]
        m=evaluate(self.batch,self.results)["byCircuit"]["nar"]["baseline"]
        self.assertEqual(m["probabilityMetricRaces"],0)
        self.assertIsNone(m["meanLogloss"])
        self.assertGreaterEqual(m["returnYen"],2000)

    def test_result_labels_do_not_mutate_receipt(self):
        before=copy.deepcopy(self.batch)
        evaluate(self.batch,self.results)
        self.assertEqual(self.batch,before)

if __name__=="__main__":unittest.main()
