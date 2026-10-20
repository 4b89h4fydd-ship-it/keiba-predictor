import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("gap_audit",Path(__file__).parents[1]/"scripts/arvexq_stage64_gap_audit.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class Provider:
    def __init__(self):
        row=[""]*36
        for i,v in ((6,"対象馬"),(7,"牡"),(8,"3"),(10,"20230404")):row[i]=v
        self.entry_rows={(("名古屋","2026-10-16",1),1):row}
        self.runs=[]
    def horse_history(self,horse,race):
        assert horse["birthDate"]=="2023-04-04"
        return {"allPastRuns":self.runs}


class GapAudit(unittest.TestCase):
    def setUp(self):
        self.p=Provider()
        self.r={"id":"nar-2026-10-16-名古屋-01","date":"2026-10-16","track":"名古屋","raceNumber":1}
        self.h={"horseNumber":1,"name":"対象馬","sex":"牡","age":3}

    def test_identity_conflict(self):
        self.h["name"]="別馬"
        self.assertEqual(module.inspect(self.p,self.r,self.h)["reason"],"target-name-conflict")

    def test_age_conflict(self):
        self.h["age"]=4
        self.assertEqual(module.inspect(self.p,self.r,self.h)["reason"],"target-age-conflict")

    def test_future_wrong_birth_and_banei_never_fill(self):
        base={"birthDate":"2023-04-04","date":"2026-10-15","track":"名古屋","finish":1,"fieldSize":10}
        self.p.runs=[{**base,"date":"2026-10-16"},{**base,"birthDate":"2022-04-04"},{**base,"track":"帯広ば"}]
        self.assertEqual(module.inspect(self.p,self.r,self.h)["validPriorRuns"],0)

    def test_observed_strict_prior(self):
        self.p.runs=[{"birthDate":"2023-04-04","date":"2026-10-15","track":"名古屋","finish":1,"fieldSize":10}]
        self.assertEqual(module.inspect(self.p,self.r,self.h)["validPriorRuns"],1)
        self.assertFalse(module.inspect(self.p,self.r,self.h)["fullCareerVerified"])

if __name__=="__main__":unittest.main()
