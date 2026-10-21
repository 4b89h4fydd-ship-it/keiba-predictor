import unittest
from scripts.arvexq_select_prefetch_repairs import repair_reason

def card(version='old', mark='◎', disabled=False):
    return {'id':'jra-test','horses':[
       {'horseNumber':1,'name':'A','allPastRuns':[],
        'integratedEvaluation':{'mark':mark}},
       {'horseNumber':2,'name':'B','allPastRuns':[]}],
      'preparedMeta':{'diagnosisReady':True},
      'predictionModelVersion':version,
      'predictionStatus':'new-model-unavailable' if disabled else 'ready',
      'legacyPresentationDisabled':disabled,
      'recommendedBetPlan':{'decision':'見送り','items':[]} if disabled else {'items':[1]}}

class D1NewForecastRepairTests(unittest.TestCase):
    def test_rewrite_rich_old_model(self):
        self.assertEqual(repair_reason(card('arvexq-learned-whole-career-scenarios-v2'),card()),'replacement_model_changed')
    def test_rewrite_same_model_changed_marks(self):
        name='arvexq-learned-whole-career-scenarios-v2'
        self.assertEqual(repair_reason(card(name,'○'),card(name,'◎')),'replacement_marks_changed')
    def test_remove_retired_marks(self):
        self.assertEqual(repair_reason(card(disabled=True),card()),'retired_forecast_still_published')
    def test_unchanged_new_model_is_not_rewritten(self):
        name='arvexq-learned-whole-career-scenarios-v2'
        self.assertEqual(repair_reason(card(name),card(name)),'')

class Stage64MissingForecastRepairTests(unittest.TestCase):
    def _future(self, owner="nar"):
        detail = card()
        detail["id"] = f"{owner}-2099-01-01-高知-01" if owner == "nar" else "jra-2099-01-01-京都-01"
        detail["date"] = "2099-01-01"
        detail["startTime"] = "12:00"
        detail["circuit"] = "地方" if owner == "nar" else "中央"
        detail["predictionModelVersion"] = "retired-model-should-not-matter"
        stages = {k: {"value": {"1": 1}} for k in
                  ("ability", "runningStyle", "pace", "probability", "marks", "tickets")}
        detail["researchShadow"] = {"stage64": {
            "raceId": detail["id"], "date": detail["date"], "circuit": owner,
            "modelVersion": f"{owner}-flat-shadow-v1", "stages": stages}}
        return detail

    def test_rich_d1_without_stage64_is_not_equivalent_to_latest_forecast(self):
        for owner in ("nar", "jra"):
            prepared = self._future(owner)
            existing = self._future(owner)
            existing.pop("researchShadow")
            self.assertEqual(repair_reason(prepared, existing),
                             "stage64_preoff_missing")

    def test_immutable_stage64_first_saved_snapshot_is_not_replaced(self):
        prepared = self._future()
        existing = self._future()
        existing["researchShadow"]["stage64"]["stages"]["marks"]["value"] = {"1": 2}
        self.assertEqual(repair_reason(prepared, existing), "")

    def test_postoff_never_creates_a_research_forecast_repair(self):
        prepared = self._future()
        prepared["date"] = "2020-01-01"
        prepared["id"] = "nar-2020-01-01-高知-01"
        trial = prepared["researchShadow"]["stage64"]
        trial["date"] = prepared["date"]
        trial["raceId"] = prepared["id"]
        existing = dict(prepared)
        existing.pop("researchShadow")
        self.assertEqual(repair_reason(prepared, existing), "")

    def test_wrong_owner_or_incomplete_stage_remains_blocked(self):
        prepared = self._future()
        existing = self._future()
        existing.pop("researchShadow")
        prepared["researchShadow"]["stage64"]["circuit"] = "jra"
        self.assertEqual(repair_reason(prepared, existing), "")
        prepared = self._future()
        prepared["researchShadow"]["stage64"]["stages"]["tickets"]["value"] = None
        self.assertEqual(repair_reason(prepared, existing), "")


if __name__=='__main__': unittest.main()
