"""Safety and task semantics for isolated race-group ranking research."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from arvexq.research.ranking_feature_signals import enrich_frozen_features, history_coverage, HISTORY_RELATIVE

from arvexq.research.ranking_challenger import (
    _features, _relevance, feature_manifest, metrics, prepare_races, split_races, train_one, paired_report, _ndcg_at_3,
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

    def test_ndcg_matches_sklearn_ties_when_available(self):
        values = [3, 0, 2, 1, 0]
        scores = [0.9, 0.8, 0.8, 0.2, 0.1]
        estimate = _ndcg_at_3(values, scores)
        self.assertGreater(estimate, 0)
        if importlib.util.find_spec("sklearn"):
            from sklearn.metrics import ndcg_score
            self.assertAlmostEqual(estimate, float(ndcg_score([values], [scores], k=3)), places=10)

    def test_common_ndcg_does_not_depend_on_head_labels(self):
        rows = sample("2026-10-01")
        for row in rows:
            row["features"]["market::popularity"] = 7-row["horseNumber"]
        a = prepare_races(rows, "jra", "ability")
        b = prepare_races(rows, "jra", "ana")
        scores = [6, 5, 4, 3, 2, 1]
        self.assertEqual(metrics(a, scores)["ndcgAt3"], metrics(b, scores)["ndcgAt3"])
        self.assertEqual(metrics(b, scores)["winnerHitAt5"], 1)

    def test_ingested_corner_positions_are_used_without_inventing_missing(self):
        from arvexq.prediction.mass_feature_factory import _position, _corner_at, _late_speed
        self.assertEqual(_corner_at({"cornerPositions": "1-2-3-4"}, 3), 3)
        self.assertIsNone(_corner_at({"cornerPositions": "2-4"}, 3))
        self.assertEqual(_late_speed({"last3fRank": 1, "fieldSize": 10}), 1)
        self.assertEqual(_position({"cornerPositions": "2-3-4"}), 4)
        self.assertEqual(_position({"cornerPositions": [2, 3, 4]}), 4)
        self.assertIsNone(_position({"cornerPositions": ""}))
        self.assertEqual(_position({"corner4": 2, "cornerPositions": "3-4"}), 2)

    def test_manifest_preserves_bounded_hypotheses(self):
        key = HISTORY_RELATIVE["form"]
        races = [{"rows": [{"features": {key: n/10, "static::prize": n*1000000}}
                           for n in range(5)]}]
        self.assertEqual(feature_manifest(races, limit=1), [key])

    def test_development_run_never_reuses_consumed_test_dates(self):
        import json
        rows = []
        for day in ("2026-10-21", "2026-10-22", "2026-10-24", "2026-10-25", "2026-10-26", "2026-10-27"):
            for suffix in ("a", "b"):
                extra = sample(day)
                for row in extra:
                    row["raceId"] += suffix
                rows.extend(extra)
        with tempfile.TemporaryDirectory() as tmp:
            report = train_one(rows, "jra", "ability", Path(tmp), min_train_races=2,
                               development_only=True)
            self.assertEqual(report["testRaces"], 0)
            self.assertIsNone(report["testFrom"])
            self.assertEqual(report["trainThrough"], "2026-10-24")
            cards = json.loads((Path(tmp)/"jra/ability/holdout_scores.json").read_text())
            self.assertEqual(cards["test"], [])
            self.assertTrue(all(c["date"] == "2026-10-25" for c in cards["validation"]))

    def test_matrix_distinguishes_missing_from_observed_zero(self):
        import math
        from sklearn.feature_extraction import DictVectorizer
        from arvexq.research.ranking_challenger import make_matrix
        v = DictVectorizer().fit([{ "static::age": 1 }])
        x, _, _ = make_matrix([{"rows": [{"features": {"static::age": 0}, "label": 0},
                                        {"features": {}, "label": 0}]}], v)
        self.assertEqual(x[0, 0], 0)
        self.assertTrue(math.isnan(x[1, 0]))

    def test_rank_metrics_market_baseline(self):
        race = prepare_races(sample("2026-10-01"), "jra", "ability")
        m = metrics(race, [6, 5, 4, 3, 2, 1])
        self.assertEqual(m["winHitAt1"], 1)
        self.assertEqual(m["winnerHitAt3"], 1)
        self.assertIsNone(m["roi"])
        with self.assertRaises(ValueError):
            metrics(race, [1])

    def test_relative_postrace_injection_cannot_enter_training(self):
        entry = sample("2026-10-01")[0]
        entry["features"]["relative::result::finish::percentile"] = 1.0
        entry["features"]["relative::history::all::w5::position_quality::mean::percentile"] = .75
        f = _features(entry, "ana")
        self.assertNotIn("relative::result::finish::percentile", f)
        self.assertIn("relative::history::all::w5::position_quality::mean::percentile", f)

    def test_derived_market_gap_uses_frozen_preoff_features_only(self):
        inp = {"market::popularity": 5.0, HISTORY_RELATIVE["position"]: .85,
               HISTORY_RELATIVE["form"]: .65, HISTORY_RELATIVE["speed"]: .7}
        ana = enrich_frozen_features(inp, head="ana", mode="enhanced", field_size=8)
        ability = enrich_frozen_features({k:v for k,v in inp.items() if not k.startswith("market::")},
                                         head="ability", mode="enhanced", field_size=8)
        self.assertAlmostEqual(ana["research::position_minus_market"], .85-(1-4/7))
        self.assertIn("research::position_x_form", ability)
        self.assertFalse(any("market" in k for k in ability))
        self.assertNotIn("research::opponent_minus_market", ana)
        self.assertEqual(inp[HISTORY_RELATIVE["position"]], .85)

    def test_feature_ablation_does_not_change_podium_labels(self):
        rows = sample("2026-10-01")
        for entry in rows:
            entry["features"].update({HISTORY_RELATIVE["position"]: entry["horseNumber"]/6,
                                      HISTORY_RELATIVE["form"]: 1-entry["horseNumber"]/6})
        full = prepare_races(rows, "jra", "ana", mode="enhanced")
        no_position = prepare_races(rows, "jra", "ana", mode="no-position")
        no_gap = prepare_races(rows, "jra", "ana", mode="no-market-gap")
        self.assertEqual([r["label"] for r in full[0]["rows"]],
                         [r["label"] for r in no_position[0]["rows"]])
        self.assertFalse(any("position" in k for e in no_position[0]["rows"]
                             for k in e["features"]))
        self.assertFalse(any(k.endswith("_minus_market") for e in no_gap[0]["rows"]
                             for k in e["features"]))
        self.assertIn("research::position_minus_market", full[0]["rows"][0]["features"])

    def test_banei_is_excluded_without_changing_other_nar(self):
        banei = sample("2026-10-01", "地方")
        for item in banei:
            item["raceId"] = item["raceId"].replace("-01", "-帯広-01")
        self.assertEqual(prepare_races(banei, "nar", "ability"), [])
        self.assertEqual(len(prepare_races(sample("2026-10-01", "地方"), "nar", "ability")), 1)

    def test_coverage_does_not_impute_missing_history(self):
        rows = sample("2026-10-01")
        rows[0]["features"][HISTORY_RELATIVE["position"]] = .5
        races = prepare_races(rows, "jra", "ability")
        coverage = history_coverage(races)
        self.assertEqual(coverage["horses"], 6)
        self.assertEqual(coverage["availability"]["position"]["observed"], 1)
        self.assertEqual(coverage["availability"]["opponent"]["observed"], 0)

    def test_paired_comparison_blend_is_selected_on_validation_only(self):
        def card(day, ability_good, ana_good):
            a, b = [], []
            for no in range(1, 5):
                baseline = {"horseNumber": no, "finish": no,
                            "popularity": no, "label": max(0, 4-no)}
                a.append({**baseline, "score": (5-no) if ability_good else no})
                b.append({**baseline, "score": (5-no) if ana_good else no})
            return {"raceId": day, "date": day, "rows": a}, {"raceId": day, "date": day, "rows": b}
        val = [card("2026-10-03", True, False), card("2026-10-04", True, False)]
        test = [card("2026-10-05", False, True), card("2026-10-06", False, True)]
        a = {"trainThrough": "2026-10-02", "validation": [x[0] for x in val],
             "test": [x[0] for x in test]}
        b = {"trainThrough": "2026-10-02", "validation": [x[1] for x in val],
             "test": [x[1] for x in test]}
        result = paired_report(a, b)
        self.assertEqual(result["blendAbilityWeight"], 1.0)
        self.assertEqual(result["ability"]["winHitAt1"], 0)
        self.assertEqual(result["ana"]["winHitAt1"], 1)
        self.assertEqual(result["blended"]["winHitAt1"], 0)
        self.assertFalse(result["productionEligible"])

    def test_paired_refuses_leaky_date_or_mismatched_roster(self):
        ref = {"trainThrough": "2026-10-05", "validation": [], "test": []}
        self.assertEqual(paired_report(ref, ref)["status"], "insufficient-paired-races")
        with self.assertRaisesRegex(ValueError, "training period"):
            paired_report(ref, {**ref, "trainThrough": "2026-10-07"})

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