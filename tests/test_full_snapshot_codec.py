import copy
import json
import unittest
from arvexq.ingest.full_snapshot_codec import pack_raw, pack_detail, unpack_raw, unpack_detail, KEY


class FullSnapshotTests(unittest.TestCase):
    def test_exact_original_and_all_career_fields(self):
        value = {'id':'test', 'horses':[{'horseNumber':1,'name':'原本',
            'pastRuns':[{'distance':1800,'unknown':{'value':'保持'*100}} for _ in range(25)]}],
            'preRacePrediction':{'frozen':False,'horses':[{'horseNumber':1,'mark':'◎'}]},
            'preRaceBet':{'fixedBeforePost':True,'items':[{'kind':'馬連','combos':[[1,2]]}]},
            'result':{'order':[1,2]},'futureUnknown':{'preserved':True}}
        before = copy.deepcopy(value)
        raw = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
        packed = pack_raw(raw)
        self.assertEqual(unpack_raw(packed), raw)
        self.assertEqual(unpack_detail(packed), before)
        self.assertEqual(unpack_detail(pack_detail(packed)), before)
        self.assertEqual(value, before)
        self.assertLess(len(json.dumps(packed)), len(raw.encode()))
        self.assertFalse(packed['preRacePrediction']['frozen'])

    def test_stage64_compact_display_index_keeps_all_six_stages(self):
        stages = {name: {"status": "research-only", "value": {"1": 0.5}}
                  for name in ("ability", "runningStyle", "pace",
                               "probability", "marks", "tickets")}
        stages["tickets"]["value"] = {
            "hypotheticalTrifectaTop10": [[1, 2, 3]], "recommendedBets": None}
        original = {
            "id": "nar-2099-01-01-高知-01", "date": "2099-01-01",
            "startTime": "12:00", "fieldSize": 3,
            "horses": [{"horseNumber": i, "name": f"馬{i}",
                        "recentRaces": [{"finish": i}]} for i in range(1, 4)],
            "researchShadow": {
                "stage64": {"circuit": "nar", "stages": stages},
                "unrelatedResearch": {"rawData": ["preserved only in original"]}},
        }
        before = copy.deepcopy(original)
        packed = pack_detail(original)
        self.assertEqual(unpack_detail(packed), before)
        self.assertEqual(original, before)
        display = copy.deepcopy(packed)
        display.pop(KEY)
        self.assertEqual(display["researchShadow"]["stage64"]["stages"], stages)
        self.assertNotIn("unrelatedResearch", display["researchShadow"])
        self.assertNotIn("recentRaces", display["horses"][0])
        self.assertEqual(unpack_detail(pack_detail(packed)), before)

    def test_tampering_is_rejected(self):
        packed = pack_raw('{"id":"original","unknown":[1,2,3]}')
        for field, replacement in [('sha256','0'*64), ('bytes',1), ('version','other')]:
            damaged = copy.deepcopy(packed)
            damaged[KEY][field] = replacement
            with self.assertRaises(ValueError):
                unpack_raw(damaged)

    def test_sync_guard_protects_inside_compressed_original(self):
        from scripts.arvexq_protect_sync import guard, verify_published
        old = {'id':'protected','date':'2020-01-01','startTime':'13:00',
               'preRacePrediction':{'raceId':'protected','raceDate':'2020-01-01',
                   'capturedAtEpoch':1577830000,'frozen':True,
                   'horses':[{'horseNumber':1,'mark':'◎'},{'horseNumber':2,'mark':'○'}]},
               'preRaceBet':{'fixedAt':'2020-01-01T08:00:00+09:00','items':[],'decision':'見送り'}}
        candidate = {'id':old['id'],'date':old['date'],'startTime':old['startTime'],
                     'result':{'status':'確定'}}
        result = guard({'details':[pack_detail(candidate)]}, read=lambda base,rid:old, base='test')
        original = unpack_detail(result['details'][0])
        self.assertEqual(original['preRacePrediction'],old['preRacePrediction'])
        self.assertEqual(original['preRaceBet'],old['preRaceBet'])
        self.assertEqual(original['result'],candidate['result'])
        self.assertEqual(verify_published(result,read=lambda base,rid:original,base='test'),['protected'])


if __name__ == '__main__':
    unittest.main()
