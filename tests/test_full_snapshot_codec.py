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

    def test_tampering_is_rejected(self):
        packed = pack_raw('{"id":"original","unknown":[1,2,3]}')
        for field, replacement in [('sha256','0'*64), ('bytes',1), ('version','other')]:
            damaged = copy.deepcopy(packed)
            damaged[KEY][field] = replacement
            with self.assertRaises(ValueError):
                unpack_raw(damaged)


if __name__ == '__main__':
    unittest.main()
