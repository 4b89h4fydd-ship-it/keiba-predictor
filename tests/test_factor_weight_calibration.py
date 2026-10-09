import unittest
from arvexq.backtest.factor_weight_calibration import calibrate

class TemporalCalibrationTests(unittest.TestCase):
    def data(self):
        samples=[]
        for d in range(1,8):
            for i in range(20):
                date=f"2026-09-{d:02}"
                horses=[{"horseNumber":h,"families":{
                    "ability":h/5,"record":(6-h)/5,
                    "suitability":(h+i%2)/6,"support":.5}} for h in range(1,6)]
                samples.append({"source":"sealed-hash-verified-preoff-factor-shadow",
                  "raceId":date+f"-R{i}","date":date,"winner":5 if i%4 else 1,"rows":horses})
        return samples

    def test_future_labels_never_select_weights(self):
        data=self.data()
        a=calibrate(data,80,30)
        self.assertTrue(a["eligible"])
        changed=[dict(row,winner=1 if row["winner"]!=1 else 5)
                 if row["date"]>=a["splitDate"] else row for row in data]
        b=calibrate(changed,80,30)
        self.assertEqual(a["experimentalWeights"],b["experimentalWeights"])
        self.assertFalse(a["liveModelChange"])
        self.assertGreaterEqual(a["holdoutRaces"],30)

    def test_insufficient_is_unavailable(self):
        self.assertFalse(calibrate(self.data()[:10])["eligible"])
        self.assertNotIn("experimentalWeights",calibrate(self.data()[:10]))

if __name__=="__main__":
    unittest.main()
