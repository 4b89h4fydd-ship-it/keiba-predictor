"""Behavior and dependency regressions for the first domain extraction stage."""
import ast
import copy
import hashlib
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from arvexq.normalize.scalars import _carried_weight, _time_seconds, _scratch_status
from arvexq.normalize.central_feed import normalize_central_race
from arvexq.normalize.measurements import _sanitize_horse_measurements
from arvexq.ingest.history.run_merge import _jra_merge_runs, _jra_history_complete
from arvexq.ingest.parsers.nar_archive import parse_corner_order
from arvexq.prediction.metrics.past_runs import _pc_sectional_score

ROOT = Path(__file__).resolve().parents[1]


class DomainExtractionTest(unittest.TestCase):
    def test_calculation_bodies_and_signatures_match_reviewed_main(self):
        manifest = json.loads((ROOT / 'docs/refactor/extracted-functions.json').read_text())
        for record in manifest:
            with self.subTest(function=record['name']):
                tree = ast.parse((ROOT / record['after']).read_text())
                node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == record['name'])
                digest = hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
                self.assertEqual(digest, record['ast_sha256'])
                module = importlib.import_module(record['after'][:-3].replace('/', '.'))
                self.assertTrue(callable(getattr(module, record['name'])))

    def test_modules_import_without_network_storage_or_app_initialization(self):
        manifest = json.loads((ROOT / 'docs/refactor/extracted-functions.json').read_text())
        modules = sorted({r['after'][:-3].replace('/', '.') for r in manifest})
        code = ('import importlib,sys,urllib.request,sqlite3\n'
                'def fail(*a,**k): raise AssertionError("unexpected I/O")\n'
                'urllib.request.urlopen=fail\nsqlite3.connect=fail\n'
                f'for name in {modules!r}: importlib.import_module(name)\n'
                'assert "app" not in sys.modules\n')
        subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True, timeout=20)

    def test_model_outputs_match_original_main_across_race_categories(self):
        from arvexq.prediction.legacy.role_utilities import _v213_role_utilities
        golden = json.loads((ROOT / "tests/fixtures/legacy-model-main-c025fea.json").read_text())
        for case in golden["cases"]:
            with self.subTest(race=case["race"]):
                actual = _v213_role_utilities(copy.deepcopy(case["race"]), copy.deepcopy(case["horses"]))
                self.assertEqual(json.loads(json.dumps(actual)), case["expected"])

    def test_nar_normalization_and_tied_corner_order(self):
        self.assertEqual(_carried_weight('▲ 51.0'), 51)
        self.assertEqual(_time_seconds('2043'), 124.3)
        self.assertEqual(_scratch_status('競走除外'), '除外')
        self.assertEqual(parse_corner_order('1,(2,7),3-4'), {1: 1, 2: 2, 7: 2, 3: 4, 4: 5})

    def test_central_debut_jump_and_full_history_are_not_truncated(self):
        for title, surface in [('新馬', '芝'), ('障害未勝利', '障害'), ('地方交流', 'ダート')]:
            rows = [{'date': f'2026-09-{i:02}', 'finish': i} for i in range(1, 13)]
            raw = {'date': '2026-10-11', 'track': '東京', 'raceNumber': 1,
                   'title': title, 'surface': surface,
                   'horses': [{'name': 'A', 'allPastRuns': rows, 'recentRaces': rows[:5]}]}
            race = normalize_central_race(raw)
            self.assertEqual(race['surface'], surface)
            self.assertEqual(len(race['horses'][0]['allPastRuns']), 12)
            self.assertEqual(len(race['horses'][0]['recentRaces']), 5)

    def test_history_merge_preserves_career_limit_and_source_evidence(self):
        rows = [{'date': f'2026-09-{i:02}', 'track': '東京', 'distance': 1600,
                 'finish': 2, 'fieldSize': 12, 'source': 'official'} for i in range(1, 13)]
        extra = dict(rows[-1], agari3f=33.5, source='backup')
        full = _jra_merge_runs(rows, [extra], limit=100000)
        self.assertEqual(len(full), 12)
        self.assertEqual(full[0]['agari3f'], 33.5)
        self.assertEqual(full[0]['source'], 'official + backup')
        self.assertEqual(len(_jra_merge_runs(rows, [extra])), 5)
        self.assertTrue(_jra_history_complete(rows))
        self.assertTrue(_jra_history_complete([], career_complete=True))
        self.assertFalse(_jra_history_complete([]))

    def test_sectional_analysis_uses_career_when_display_runs_have_no_evidence(self):
        run = {'date': '2026-09-01', 'distance': 1600, 'timeSeconds': 95,
               'agari3f': 34, 'track': '東京', 'fieldSize': 12}
        horse = {'allPastRuns': [run] * 12, 'recentRaces': [{'finish': 9}] * 5}
        score, count = _pc_sectional_score(horse, {'distance': 1600, 'track': '東京'})
        self.assertEqual(count, 8)  # Existing evidence window, not a new career cap.
        self.assertGreater(score, 0)
        self.assertEqual(len(horse['allPastRuns']), 12)

    def test_measurement_cleanup_keeps_frozen_prediction_and_tickets(self):
        horse = {'bodyWeight': '480kg', 'carriedWeight': '▲ 54.0',
                 'preRacePrediction': {'mark': '◎'}, 'preRaceBet': {'nums': [1, 2, 3]},
                 'morningPicks': {'selected': True, 'fixedAt': 123}}
        frozen = {k: horse[k].copy() for k in ('preRacePrediction', 'preRaceBet', 'morningPicks')}
        result = _sanitize_horse_measurements(horse)
        for key, value in frozen.items():
            self.assertEqual(result[key], value)


if __name__ == '__main__':
    unittest.main()
