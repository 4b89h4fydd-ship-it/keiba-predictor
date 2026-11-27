"""Pro-index term tests (2026-11-27, nk-materials-v18):
netkeiba's pro-forecast Maria index (マリア指数) and
track-aptitude index (馬場適正指数), carried per horse as
mariaIndex / babaIndex, and the adapter's pro-index terms
(maria_index / baba_index).

Covered here:
  - the parser carries both fields as numbers and drops
    unreadable values (never guessed);
  - both terms fire as post-integrate logit shifts when
    their material exists, moving probability toward the
    higher-index horses, and stamp the trial marker, the
    weights label and the coverage counts;
  - a horse carrying no index is never shifted by that
    term;
  - with neither index present the terms stay inert;
  - both families join the materials fingerprint.

The frozen integrated_eval is untouched; the pro-index
terms are adapter-level post-integrate logit shifts (see
rewrite/analysis/nk_materials.py).
"""
from __future__ import annotations

from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    NK_INDEX_LABEL, NK_INDEX_TRIAL, apply_nk_materials,
    materials_fingerprint, parse_materials_payload)

NK_ID = "202648112708"
RACE_ID = "nar-2026-11-27-名古屋-08"
DATE = "2026-11-27"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
STRENGTHS = {n: 0.20 for n in NAMES}


def _forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def _parsed(per_horse):
    payload = {"version": "nk-materials-v18", "date": DATE,
               "races": {RACE_ID: {
                   "netkeibaRaceId": NK_ID,
                   "horses": {str(n): dict(
                       {"nk_best": None, "nk_avg5": 60,
                        "nk_dist": None, "nk_course": None,
                        "nk_recent": None},
                       **per_horse.get(n, {}))
                       for n in NAMES},
                   "courseAnalysis": None,
                   "paceLabel": None}}}
    return parse_materials_payload(payload)[RACE_ID]


class ProIndexParserTests(TestCase):
    def test_parser_carries_numbers_and_drops_unreadable(self):
        entry = _parsed({
            1: {"mariaIndex": 64.25, "babaIndex": 67.57},
            2: {"mariaIndex": 44.09, "babaIndex": None},
            3: {"mariaIndex": "x", "babaIndex": 32.9},
        })
        horses = entry["horses"]
        self.assertEqual(horses[1]["mariaIndex"], 64.25)
        self.assertEqual(horses[1]["babaIndex"], 67.57)
        self.assertEqual(horses[2]["mariaIndex"], 44.09)
        self.assertIsNone(horses[2]["babaIndex"])
        self.assertIsNone(horses[3]["mariaIndex"])
        self.assertEqual(horses[3]["babaIndex"], 32.9)


class ProIndexTermTests(TestCase):
    def _apply(self, per_horse):
        return apply_nk_materials(_forecast(), _parsed(per_horse))

    def test_maria_index_fires_and_shifts_toward_the_top(self):
        per_horse = {
            1: {"mariaIndex": 80.0},
            2: {"mariaIndex": 60.0},
            3: {"mariaIndex": 50.0},
            4: {"mariaIndex": 40.0},
            5: {"mariaIndex": 30.0},
        }
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("maria_index", info["terms"])
        self.assertNotIn("baba_index", info["terms"])
        self.assertEqual(info["proIndexTrial"], NK_INDEX_TRIAL)
        self.assertIn(NK_INDEX_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["maria_index"], 5)
        moved = {r.number: r.p_win for r in adjusted.runners}
        self.assertGreater(moved[1], 0.20)
        self.assertLess(moved[5], 0.20)
        self.assertAlmostEqual(sum(moved.values()), 1.0, places=3)

    def test_baba_index_fires_alone(self):
        per_horse = {
            1: {"babaIndex": 30.0},
            2: {"babaIndex": 40.0},
            3: {"babaIndex": 50.0},
            4: {"babaIndex": 60.0},
            5: {"babaIndex": 70.0},
        }
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("baba_index", info["terms"])
        self.assertNotIn("maria_index", info["terms"])
        moved = {r.number: r.p_win for r in adjusted.runners}
        self.assertGreater(moved[5], 0.20)
        self.assertLess(moved[1], 0.20)

    def test_unlisted_horse_is_never_shifted(self):
        per_horse = {
            1: {"mariaIndex": 80.0},
            2: {"mariaIndex": 60.0},
            3: {"mariaIndex": 50.0},
            4: {"mariaIndex": 40.0},
            # horse 5 carries no index
        }
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertEqual(info["coverage"]["maria_index"], 4)
        moved = {r.number: r.p_win for r in adjusted.runners}
        origin = {r.number: r.p_win for r in _forecast().runners}
        # Horse 5's probability moves only through the
        # renormalisation (down, since others gained) — it
        # receives no shift of its own: its share relative
        # to the unshifted baseline ordering is unchanged
        # in log terms, i.e. it never gains.
        self.assertLessEqual(moved[5], origin[5])

    def test_no_indices_stays_inert(self):
        adjusted, info = self._apply({})
        self.assertNotIn("maria_index", info.get("terms") or [])
        self.assertNotIn("baba_index", info.get("terms") or [])
        self.assertNotIn("proIndexTrial", info)

    def test_flat_indices_shift_nothing(self):
        # A flat field's z-scores are all zero: the vector
        # must come back exactly as the no-index application
        # produced it, and neither term may join the record.
        baseline, _ = self._apply({})
        per_horse = {n: {"mariaIndex": 50.0, "babaIndex": 50.0}
                     for n in NAMES}
        adjusted, info = self._apply(per_horse)
        self.assertNotIn("maria_index", info.get("terms") or [])
        self.assertNotIn("baba_index", info.get("terms") or [])
        self.assertEqual(
            {r.number: r.p_win for r in adjusted.runners},
            {r.number: r.p_win for r in baseline.runners})

    def test_fingerprint_counts_both_families(self):
        entry = _parsed({
            1: {"mariaIndex": 64.25, "babaIndex": 67.57},
            2: {"mariaIndex": 44.09},
            3: {"babaIndex": 32.9},
        })
        fp = materials_fingerprint(entry)
        self.assertEqual(fp["maria_index"], 2)
        self.assertEqual(fp["baba_index"], 2)
