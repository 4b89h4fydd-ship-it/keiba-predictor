"""Dedicated regression checks for app.py's extracted dependency-free modules."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from arvexq.ingest.pure_parsers import (
    decode_csv_bytes, _jra_decode, _decode_site, _json_horse_rows,
    _pick, _jra_run_key, _jra_run_value_present,
)
from arvexq.prediction.pure_diagnostics import (
    _central_detail_coverage, _diagnosis_history_quality,
    _audit_axes_from_eval, _learning_date_split, _pc_time_index,
    _prob_vector, _history_is_enough, _pc_season, _reference_weight_from_horse,
)
from arvexq.infra.pure_snapshots import (
    _bundle_quality, _racedb_snapshot_usable, _merge_official_result,
)

class ExtractedPureHelpersTest(unittest.TestCase):
    def test_api_file_imports_without_duplicate_definitions(self):
        src=Path("app.py").read_text(encoding="utf-8")
        tree=ast.parse(src)
        def_names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        extracted={"decode_csv_bytes","_jra_decode","_decode_site","_json_horse_rows",
            "_pick","_jra_run_key","_jra_run_value_present","_central_detail_coverage",
            "_diagnosis_history_quality","_audit_axes_from_eval","_learning_date_split",
            "_pc_time_index","_prob_vector","_history_is_enough","_pc_season",
            "_reference_weight_from_horse","_bundle_quality","_racedb_snapshot_usable",
            "_merge_official_result"}
        self.assertFalse(extracted & def_names)
        imported={alias.name for node in tree.body if isinstance(node,ast.ImportFrom)
                  and (node.module or "").startswith("arvexq")
                  for alias in node.names}
        self.assertTrue(extracted.issubset(imported))
        self.assertLess(Path("app.py").stat().st_size,400_000)

    def test_public_outputs_preserved_for_parsers(self):
        self.assertEqual(decode_csv_bytes("東京".encode("cp932")),"東京")
        self.assertEqual(_jra_decode("京都".encode("cp932")),"京都")
        self.assertEqual(_decode_site("園田".encode("euc_jp")),"園田")
        self.assertEqual(_json_horse_rows({"data":{"horses":[{"name":"A"}]}}),
                         [{"name":"A"}])
        self.assertEqual(_pick({"a":None,"b":7},"a","b"),7)
        self.assertEqual(_jra_run_key({"date":"2026-10-01","track":"東京","distance":1200}),
                         ("2026-10-01","東京",1200))
        self.assertTrue(_jra_run_value_present("finish",2))
        self.assertFalse(_jra_run_value_present("finish",0))

    def test_prediction_quality_observations(self):
        horse={"name":"A","recentRaces":[{"date":"2026-09-01","bodyWeight":502}]}
        detail={"horses":[horse]}
        cov=_central_detail_coverage(detail)
        self.assertEqual(cov["totalHorses"],1)
        self.assertEqual(cov["horsesWithHistory"],1)
        self.assertEqual(_diagnosis_history_quality({"horses":[]})["ready"],False)
        self.assertFalse(_history_is_enough(cov,10))
        self.assertEqual(_pc_season("2026-10-10"),"秋")
        self.assertAlmostEqual(sum(_prob_vector([1,2,3])),1.0)
        self.assertEqual(_reference_weight_from_horse(horse),(502,"2026-09-01"))
        self.assertIsNone(_pc_time_index({"timeSeconds":0},1200))
        self.assertAlmostEqual(_pc_time_index({"timeSeconds":72,"distance":1200},1200),1200/72)
        dates=_learning_date_split([{"date":f"2026-10-0{i}"} for i in range(1,7)])
        self.assertEqual(sorted(dates["dates"]),dates["dates"])
        self.assertEqual(_audit_axes_from_eval({})["evidence"],0.0)

    def test_result_merge_and_cache_quality(self):
        horse={"horseNumber":1,"name":"A","recentRaces":[]}
        d={"date":"2026-10-10","horses":[horse]}
        updated=_merge_official_result(d,{"result":{"finishers":[{"horseNumber":1,"name":"A","finish":1}]}})
        self.assertEqual(updated["result"]["finishers"][0]["finish"],1)
        self.assertEqual(len(updated["horses"]),1)
        self.assertTrue(_racedb_snapshot_usable(updated))
        self.assertEqual(_bundle_quality({"raceCount":3,"detailCount":2})[:2],(3,2))

if __name__=="__main__":
    unittest.main()
