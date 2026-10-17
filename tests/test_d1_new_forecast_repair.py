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
if __name__=='__main__': unittest.main()
