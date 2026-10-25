import math,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from engine import predict

class KeirinTests(unittest.TestCase):
    def test_probabilities_and_marks(self):
        entries=[{"umaban":i,"name":f"選手{i}","score":90+i,"win_rate":i+3,"top3_rate":i+25,"style":"逃" if i in (1,4) else "追","comment":"自力。" if i==1 else "選手1君。" if i==2 else "単騎。"} for i in range(1,8)]
        p=predict({"venue":"川崎","entries":entries})
        self.assertIsNotNone(p)\n        self.assertIn("ability",p["stages"])\n        self.assertEqual(p["stages"]["video"]["status"],"unavailable")
        self.assertAlmostEqual(sum(x["p1"] for x in p["riders"]),1,places=7)
        self.assertAlmostEqual(sum(x["p3"] for x in p["riders"]),3,places=7)
        self.assertEqual(len(set(p["marks"].values())),5)
        self.assertEqual(p["model"],"keirin-ability-video-development-v3-uncalibrated")
        self.assertTrue(any(set(x)=={1,2} for x in p["lines"]))
        self.assertGreater(len(p["trifecta"]),0)
    def test_reject_missing_inputs(self):
        self.assertIsNone(predict({"entries":[{"umaban":1}]}))
    def test_9_car(self):
        entries=[{"umaban":i,"score":90+i,"win_rate":5,"top3_rate":25,"style":"両","comment":"単騎。"} for i in range(1,10)]
        p=predict({"venue":"青森","entries":entries})
        self.assertEqual(len(p["riders"]),9)
        self.assertTrue(all(x["p"]>0 for x in p["trifecta"]))
if __name__=="__main__":unittest.main()
