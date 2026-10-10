"""Fail-open static racecard backup, never invent runners or revise marks."""
from __future__ import annotations
import copy
import tempfile
import unittest
from pathlib import Path
from scripts.arvexq_publish_racecards_static import racecard_manifest, merge_manifest, publish


def sample(day="2026-10-10"):
    return {"summaries":[{"id":"jra-"+day+"-東京-01","date":day,"circuit":"中央",
             "track":"東京","raceNumber":1,"fieldSize":3,"title":"1R","startTime":"10:05"},
            {"id":"jra-"+day+"-東京-02","date":day,"circuit":"中央",
             "track":"東京","raceNumber":2,"fieldSize":3,"title":"2R"}],
        "details":[{"id":"jra-"+day+"-東京-01","date":day,
             "horses":[{"horseNumber":1,"name":"甲","jockey":"A","winOdds":2.4,
                        "recentRaces":[{"finish":1}],"prediction":{"mark":"◎"}},
                       {"horseNumber":2,"name":"乙","jockey":"B","scratched":False},
                       {"horseNumber":3,"name":"丙","carriedWeight":56}],
             "preRacePrediction":{"horses":[{"horseNumber":1,"mark":"◎"}]},
             "morningMarkSnapshot":{"fixedAt":"8:00"},
             "result":{"status":"確定","finishers":[{"horseNumber":3,"finish":1}]}}]}


class StaticRacecardTests(unittest.TestCase):
    def test_never_publish_predictions_odds_results_or_thin_card(self):
        src=sample()
        manifest=racecard_manifest(src)
        self.assertEqual(manifest["raceCount"],1)
        card=manifest["races"][0]
        self.assertEqual(len(card["horses"]),3)
        self.assertEqual([x["name"] for x in card["horses"]],["甲","乙","丙"])
        self.assertNotIn("result",card)
        self.assertNotIn("preRacePrediction",card)
        self.assertNotIn("morningMarkSnapshot",card)
        self.assertNotIn("winOdds",card["horses"][0])
        self.assertNotIn("recentRaces",card["horses"][0])
        src["details"][0]["horses"].pop()
        self.assertIsNone(racecard_manifest(src))

    def test_first_original_stays_and_new_race_can_be_added(self):
        first=racecard_manifest(sample())
        later=copy.deepcopy(first)
        later["races"][0]["horses"][0]["name"]="changed late"
        later["races"].append({**copy.deepcopy(first["races"][0]),
                               "id":"jra-2026-10-10-東京-02"})
        updated=merge_manifest(first,later)
        self.assertEqual(updated["raceCount"],2)
        self.assertEqual(updated["races"][0]["horses"][0]["name"],"甲")
        with self.assertRaises(ValueError):
            merge_manifest(first,{"version":"x","date":"2026-10-09","races":[]})

    def test_publish_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=sample()
            target=publish(source,root)
            self.assertTrue(target.is_file())
            previous=target.read_bytes()
            changed=copy.deepcopy(source)
            changed["details"][0]["horses"][0]["name"]="wrong update"
            publish(changed,root)
            self.assertEqual(target.read_bytes(),previous)


if __name__=="__main__":
    unittest.main()
