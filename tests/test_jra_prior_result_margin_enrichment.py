import unittest
from unittest.mock import Mock
from arvexq.databanks.legacy_bridge import _jra_official_prior_result_adapter

class JraOfficialPriorResult(unittest.TestCase):
    def test_verified_winner_relative_seconds(self):
        import base64
        rid="jraresult-"+base64.urlsafe_b64encode(b"linked-official-race").decode().rstrip("=")
        profile=Mock(return_value=[{"date":"2026-10-01","track":"東京","raceId":rid,
                                    "fieldSize":10,"finish":2,"cornerPositions":[]}])
        results=Mock(return_value={"date":"2026-10-01","track":"東京",
                                   "result":{"finishers":[
                                       {"name":"勝馬","finish":1,"timeSeconds":95.1},
                                       {"name":"対象馬","finish":2,"timeSeconds":95.5,
                                        "last3FSeconds":34.7,"cornerPositions":[4,3]}]}})
        fetch=_jra_official_prior_result_adapter({"_jra_profile_runs":profile,
                                                   "_jra_parse_result":results})
        out=fetch({"name":"対象馬","_jraHorseCname":"official-horse"},
                  {"date":"2026-10-13"},200)
        self.assertEqual(out["recentRaces"][0]["timeBehindWinner"],0.4)
        self.assertEqual(out["recentRaces"][0]["last3fSeconds"],34.7)
        self.assertEqual(out["recentRaces"][0]["cornerPositions"],[4,3])

    def test_future_unmatched_and_race_identity_rejected(self):
        import base64
        rid="jraresult-"+base64.urlsafe_b64encode(b"linked").decode().rstrip("=")
        profile=lambda *args:[{"date":"2026-10-14","track":"東京","raceId":rid}]
        fetch=_jra_official_prior_result_adapter({"_jra_profile_runs":profile,
                      "_jra_parse_result":lambda *args:{}})
        self.assertEqual(fetch({"name":"対象馬","_jraHorseCname":"horse"},{"date":"2026-10-13"},200),{})

if __name__=="__main__":unittest.main()
