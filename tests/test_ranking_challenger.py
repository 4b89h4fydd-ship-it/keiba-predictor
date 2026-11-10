"""Safety and task semantics for isolated race-group ranking research."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from arvexq.research.ranking_challenger import (
    _features, _relevance, feature_manifest, metrics, prepare_races, split_races, train_one,
)


def sample(day, circuit="中央", horse_count=6, *, popularity=True):
    race_id = f"{circuit}-{day}-01"
    rows = []
    for no in range(1, horse_count + 1):
        feats = {"history::all::w8::finish::mean": no * .3,
                 "static::age": no + 2,
                 "market::popularity": no if popularity else None,
                 "result::finish": no * 100,
                 "relative::market::popularity::percentile": no / 10}
        rows.append({"raceId": race_id, "circuit": circuit, "date": day,
                     "featureHash": f"freeze-{race_id}", "snapshotVersion": "v1",
                     "horseNumber": no, "finish": no, "features": feats})
    return rows


class RankingChallengerSafety(unittest.TestCase):
    def test_targets_and_only_podium_longshots(self):
        self.assertEqual([_relevance(i, i + 2, "ability") for i in range(1, 5)], [3, 2, 1, 0])
        self.assertEqual([_relevance(i, 7, "ana") for i in range(1, 5)], [3, 3, 3, 0])
        self.assertEqual(_relevance(1, 1, "ana"), 0)

    def test_market_excluded_from_ability_and_result_never_features(self):
        row = sample("2026-10-01")[0]
        f = _features(row, "ability")
        self.assertNotIn("market::popularity", f)
        self.assertNotIn("relative::market::popularity::percentile", f)
        self.assertNotIn("result::finish", f)
        self.assertIn("history::all::w8::finish::mean", f)
        self.assertIn("market::popularity", _features(row, "ana"))

    def test_market_missing_excludes_whole_ana_race(self):
        rows = sample("2026-10-01")
        rows[0]["features"]["market::popularity"] = None
        self.assertEqual(prepare_races(rows, "jra", "ana"), [])
        self.assertEqual(len(prepare_races(rows, "jra", "ability")), 1)

    def test_frozen_hash_conflict_fails_closed(self):
        rows = sample("2026-10-01")
        rows[1]["featureHash"] = "different"
        with self.assertRaisesRegex(ValueError, "inconsistent frozen"):
            prepare_races(rows, "jra", "ability")

    def test_race_group_date_split_and_train_only_features(self):
        rows = []
        for n in range(10):
            day = f"2026-10-{n+1:02d}"
            extra = sample(day)
            if n >= 8:
                for item in extra:
                    item["features"]["static::only_after_train"] = item["horseNumber"]
            rows.extend(extra)
        races = prepare_races(rows, "jra", "ability")
        groups = split_races(races)
        all_dates = [{r["date"] for r in group} for group in groups.values()]
        self.assertFalse(all_dates[0] & all_dates[1] or all_dates[0] & all_dates[2]
                         or all_dates[1] & all_dates[2])
        self.assertNotIn("static::only_after_train", feature_manifest(groups["train"]))
        self.assertEqual(sum(map(len, groups.values())), 10)

    def test_different_circuits_never_pooled(self):
        rows = sample("2026-10-01", "中央") + sample("2026-10-01", "地方")
        self.assertEqual(len(prepare_races(rows, "jra", "ability")), 1)
        self.assertEqual(len(prepare_races(rows, "nar", "ability")), 1)

    def test_rank_metrics_market_baseline(self):
        race = prepare_races(sample("2026-10-01"), "jra", "ability")
        m = metrics(race, [6, 5, 4, 3, 2, 1])
        self.assertEqual(m["winHitAt1"], 1)
        self.assertEqual(m["winnerHitAt3"], 1)
        self.assertIsNone(m["roi"])
        with self.assertRaises(ValueError):
            metrics(race, [1])

    @unittest.skipUnless(importlib.util.find_spec("lightgbm") and importlib.util.find_spec("sklearn"), "optional ranking deps")
    def test_small_fit_and_sealed_report(self):
        rows = []
        for n in range(12):
            day = f"2026-10-{n+1:02d}"
            group = sample(day)
            # Change winners and market ranks across race days.
            for entry in group:
                no = entry["horseNumber"]
                entry["finish"] = 1 + (no + n - 1) % 6
                entry["features"]["static::age"] = (no * 2 + n) % 11
                entry["features"]["market::popularity"] = 1 + (no + n * 2 - 1) % 6
            rows.extend(group)
        with tempfile.TemporaryDirectory() as tmp:
            report = train_one(rows, "jra", "ability", Path(tmp), min_train_races=3)
            self.assertEqual(report["testRaces"], 2)
            self.assertFalse(report["productionEligible"])
            self.assertIsNone(report["metrics"]["roi"])
            self.assertTrue((Path(tmp) / "jra" / "ability" / "ranker.txt").exists())


if __name__ == "__main__":
    unittest.main()