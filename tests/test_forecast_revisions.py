from copy import deepcopy
from unittest import TestCase
from arvexq.prediction.forecast_revisions import append_revision, latest_revision, originals_hash, preserve_revisions
from arvexq.prediction.learned_scenarios import fit_model
from test_learned_scenarios import target, training_race


class ForecastRevisionTests(TestCase):
    def test_replace_latest_view_without_replacing_originals(self):
        race=target('地方');race['preRacePrediction']={'horses':[{'horseNumber':6,'mark':'◎'}]}
        race['preRaceBet']={'items':[{'kind':'単勝','combos':[[6]]}]}
        original=deepcopy(race);model=fit_model([training_race('地方')],circuit='地方')
        updated=append_revision(race,model,at='2026-10-17T00:00:00Z')
        self.assertEqual(race,original)
        self.assertEqual(originals_hash(updated),originals_hash(race))
        revision=latest_revision(updated)
        self.assertEqual(revision['analysisType'],'retrospective')
        self.assertEqual(revision['honmeiDecision']['horseNumber'],1)
        self.assertEqual(updated['preRacePrediction']['horses'][0]['horseNumber'],6)
        again=append_revision(updated,model,at='2026-10-17T00:00:01Z')
        self.assertEqual(len(again['forecastRevisions']),1)

    def test_refresh_preserves_revision_chain_and_rejects_rewrites(self):
        race=target('地方');updated=append_revision(race)
        preserved=preserve_revisions(updated,race)
        self.assertEqual(latest_revision(preserved),latest_revision(updated))
        changed=deepcopy(updated);changed['forecastRevisions'][0]['forecastText']='改変'
        with self.assertRaisesRegex(ValueError,'prefix'):
            preserve_revisions(updated,changed)
        broken=deepcopy(updated);broken['currentForecastRevisionId']='wrong'
        with self.assertRaisesRegex(ValueError,'pointer'):
            preserve_revisions(updated,broken)
