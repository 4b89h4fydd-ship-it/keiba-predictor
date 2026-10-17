from unittest import TestCase
from unittest.mock import patch
from scripts.arvexq_train_research_models import train_models


class ResearchTrainingModelsTests(TestCase):
    def test_only_prior_finalized_races_enter_training(self):
        older={'id':'old','date':'2026-10-16','circuit':'地方','result':{'status':'確定'}}
        same={'id':'same','date':'2026-10-17','circuit':'地方','result':{'status':'確定'}}
        unfinished={'id':'unfinal','date':'2026-10-16','circuit':'中央','result':{}}
        with patch('scripts.arvexq_train_research_models.fit_model',
                   return_value={'training':{'lastDate':'2026-10-16'}}) as fit:
            models,errors=train_models({'details':[older,same,unfinished]},'2026-10-17')
            self.assertEqual(sorted(models), ['地方'])
            self.assertEqual(fit.call_args.args[0],[older])
            self.assertIn('中央',errors)

    def test_empty_or_missing_corpus_is_not_success(self):
        with self.assertRaises(ValueError):
            train_models({},'2026-10-17')
        with patch('scripts.arvexq_train_research_models.fit_model',
                   side_effect=ValueError('insufficient labels')):
            models,errors=train_models({'details':[]},'2026-10-17')
            self.assertEqual(models,{})
            self.assertEqual(set(errors),{'中央','地方'})
