"""Only the new three-analysis forecasts qualify for D1 prediction repair."""
import unittest
from scripts.arvexq_select_prefetch_repairs import repair_reason

VERSION="arvexq-three-analysis-vnext-1"

def card(version=VERSION, mark="◎", status="ready"):
    return {
        "id":"jra-test", "date":"2026-10-20",
        "horses":[{"horseNumber":1,"name":"A","allPastRuns":[]},
                  {"horseNumber":2,"name":"B","allPastRuns":[]}],
        "preparedMeta":{"diagnosisReady":True},
        "predictionModelVersion":version,
        "predictionStatus":status,
        "predictionMarks":[{"horseNumber":1,"mark":mark}],
        "recommendedBets":[{"kind":"3連単","combos":[[1,2,3]],"points":1}],
    }

class D1NewForecastRepairTests(unittest.TestCase):
    def test_replace_saved_legacy_model_with_vnext(self):
        self.assertEqual(repair_reason(card(),card("old")),
                         "new_method_products_not_persisted")

    def test_changed_vnext_marks_are_not_skipped(self):
        self.assertEqual(repair_reason(card(mark="○"),card(mark="◎")),
                         "new_method_products_not_persisted")

    def test_incomplete_saved_forecast_is_not_treated_as_ready(self):
        self.assertEqual(repair_reason(card(),card(status="disabled")),
                         "new_method_products_not_persisted")

    def test_identical_vnext_product_is_not_rewritten(self):
        self.assertEqual(repair_reason(card(),card()),"")

    def test_fact_only_does_not_rewrite_for_prediction_fields(self):
        self.assertEqual(repair_reason(card(),card("old"),facts_only=True),"")

if __name__=="__main__":
    unittest.main()
