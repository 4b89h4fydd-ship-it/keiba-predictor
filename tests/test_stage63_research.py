import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arvexq.research.stage63.ability import prior_runs, score_field
from arvexq.research.stage63.running_style import style_field
from arvexq.research.stage63.probability import distribution
from arvexq.research.stage63.experiment import ARMS, predict
from arvexq.research.stage63.forward import protocol, freeze, verify, digest, write_once
from arvexq.research.stage63.tickets import top10


def race():
    return {"id":"nar-2026-10-21-名古屋-01","date":"2026-10-21","circuit":"地方",
            "startTime":"12:00","fieldSize":4,
            "horses":[{"horseNumber":n,"recentRaces":[
                {"date":"2026-10-15","finish":n,"fieldSize":4,"passing":[n]}]}
                for n in range(1,5)]}


class Research(unittest.TestCase):
    def test_date_filter(self):
        h={"recentRaces":[{"date":d} for d in ("2026-10-15","2026-10-21","2026-10-22","2026-02-30","2026-1-1")]}
        self.assertEqual(prior_runs(h,"2026-10-21"),[{"date":"2026-10-15"}])

    def test_duplicate_conflict(self):
        h={"recentRaces":[{"date":"2026-01-01","finish":1},{"date":"2026-01-01","finish":2}]}
        with self.assertRaises(ValueError):prior_runs(h,"2026-10-21")

    def test_exact_duplicate(self):
        row={"date":"2026-01-01","finish":1}
        self.assertEqual(prior_runs({"recentRaces":[row,row]},"2026-10-21"),[row])

    def test_unknown_ability(self):
        self.assertEqual(score_field({1:[]},"recent5_shrunk"),{1:None})

    def test_invalid_finish(self):
        for finish in (True,float("nan"),float("inf"),0,8):
            self.assertIsNone(score_field({1:[{"fieldSize":4,"finish":finish}]})[1])

    def test_recent_weights(self):
        h={1:[{"finish":f,"fieldSize":2} for f in (1,2,2,2,2,1)]}
        self.assertAlmostEqual(score_field(h,"recent5")[1],1/3)

    def test_shrink(self):
        h={1:[{"finish":1,"fieldSize":2}],2:[{"finish":2,"fieldSize":2}]}
        self.assertEqual(score_field(h,"recent5_shrunk"),{1:.625,2:.375})

    def test_unknown_style(self):
        self.assertIsNone(style_field({1:[{"finish":1,"fieldSize":4}]})[1])

    def test_style_window(self):
        h={1:[{"passing":[1],"fieldSize":4}]*5+[{"passing":[4],"fieldSize":4}]}
        self.assertEqual(style_field(h,5)[1],[1.,0.,0.,0.])
        self.assertAlmostEqual(style_field(h)[1][3],1/6)

    def test_normalization(self):
        for arm in ARMS:
            p=predict(race(),arm)
            self.assertAlmostEqual(sum(p["probabilities"].values()),1.)
            self.assertAlmostEqual(p["trifectaMass"],1.)
            self.assertEqual(len(p["tickets"]),10)
            self.assertEqual(len(set(p["tickets"])),10)
            self.assertIsNone(p["marks"])

    def test_extreme_stability(self):
        d=distribution({1:1000.,2:0.,3:-1000.},[{1:0.,2:0.,3:0.}])
        self.assertAlmostEqual(sum(d["trifecta"].values()),1.)

    def test_invalid_temperature(self):
        for t in (0,-1,True,float("nan")):
            with self.assertRaises(ValueError):distribution({1:1,2:2,3:3},[{1:0,2:0,3:0}],t)

    def test_roster_mismatch(self):
        with self.assertRaises(ValueError):distribution({1:1,2:2,3:3},[{1:0,2:0}])

    def test_tie_breaking(self):
        d=distribution({i:0 for i in (1,2,3,4)},[{i:0 for i in (1,2,3,4)}])
        self.assertEqual(top10(d)[0],(1,2,3))

    def test_labels_cannot_change_forecast(self):
        r=race();before=predict(r)
        r.update(result={"actual":[4,3,2]},payouts={"trifecta":999999})
        for h in r["horses"]:h.update(actualFinish=1,winOdds=.1,mark="◎")
        self.assertEqual(predict(r),before)

    def test_input_immutable(self):
        r=race();before=copy.deepcopy(r);predict(r)
        self.assertEqual(r,before)

    def test_circuit_isolation(self):
        r=race();r.update(circuit="中央",id="jra-2026-10-21-東京-01")
        with self.assertRaises(ValueError):predict(r)

    def test_missing_not_imputed(self):
        r=race();r["horses"][0]["recentRaces"]=[]
        p=predict(r)
        self.assertIsNone(p["tickets"]);self.assertEqual(p["missingAbility"],[1])

    def test_duplicate_roster(self):
        r=race();r["horses"][0]["horseNumber"]=2
        with self.assertRaises(ValueError):predict(r)

    def test_field_size_mismatch(self):
        r=race();r["fieldSize"]=5
        with self.assertRaises(ValueError):predict(r)


class Forward(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"receipt.json"
        self.plan=protocol(["nar-2026-10-16-名古屋-01"])
        self.clock=patch("arvexq.research.stage63.forward.datetime")
        self.dt=self.clock.start()
        self.dt.now.return_value=datetime(2026,10,20,tzinfo=timezone.utc)
        self.dt.fromisoformat.side_effect=datetime.fromisoformat

    def tearDown(self):
        self.clock.stop();self.tmp.cleanup()

    def test_roundtrip_stays_unverified(self):
        receipt=freeze(self.path,race(),self.plan)
        result=verify(json.loads(self.path.read_text()),self.plan)
        self.assertTrue(result["localIntegrityVerified"])
        self.assertFalse(result["independentEvaluationEligible"])
        receipt["independentlyVerifiedPreoff"]=True
        self.assertFalse(verify(receipt,self.plan)["independentlyVerifiedPreoff"])

    def test_no_overwrite(self):
        freeze(self.path,race(),self.plan)
        with self.assertRaises(FileExistsError):freeze(self.path,race(),self.plan)

    def test_protocol_fixed(self):
        self.plan["ticketLimit"]=20
        with self.assertRaises(ValueError):freeze(self.path,race(),self.plan)

    def test_postoff_rejected(self):
        self.dt.now.return_value=datetime(2026,10,22,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):freeze(self.path,race(),self.plan)

    def test_development_rejected(self):
        r=race();r.update(date="2026-10-16",id="nar-2026-10-16-名古屋-01")
        with self.assertRaises(ValueError):freeze(self.path,r,self.plan)

    def test_tamper_rejected(self):
        receipt=freeze(self.path,race(),self.plan)
        receipt["snapshot"]["input"]["horses"][0]["horseNumber"]=9
        with self.assertRaises(ValueError):verify(receipt,self.plan)

    def test_rehashed_forecast_rejected(self):
        receipt=freeze(self.path,race(),self.plan)
        receipt["snapshot"]["predictions"]["baseline"]["tickets"]=[]
        receipt["snapshotSha256"]=digest(receipt["snapshot"])
        with self.assertRaises(ValueError):verify(receipt,self.plan)

    def test_target_labels_excluded_from_receipt(self):
        r=race();r["horses"][0]["actualFinish"]=4
        receipt=freeze(self.path,r,self.plan)
        self.assertNotIn("result",receipt["snapshot"]["input"])
        self.assertNotIn("actualFinish",receipt["snapshot"]["input"]["horses"][0])

    def test_postrace_input_rejected(self):
        r=race();r["result"]={"winner":4}
        with self.assertRaises(ValueError):freeze(self.path,r,self.plan)

if __name__=="__main__":unittest.main()
