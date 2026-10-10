import unittest
from scripts.arvexq_saved_odds import saved_odds

class SavedActualOddsTest(unittest.TestCase):
    def test_only_acquired_prices_and_original_timestamp(self):
        d={'id':'race','date':'2026-10-10','oddsSource':'netkeiba','oddsUpdatedAt':'08:40:00',
           'horses':[{'horseNumber':1,'name':'原本','oddsSource':'netkeiba','winOdds':4.3,'popularity':2},
                     {'horseNumber':2,'name':'推定','oddsSource':'netkeiba','winOdds':3,'oddsForecast':True}]}
        result=saved_odds(d,'a'*64)
        self.assertEqual(result['oddsUpdatedAt'],'2026-10-10T08:40:00+09:00')
        self.assertEqual(result['oddsStatus'],'saved')
        self.assertEqual(result['odds'][0]['win_odds'],4.3)
        self.assertEqual(len(result['odds']),1)
        self.assertIsNone(saved_odds({**d,'oddsForecast':True},'a'*64))
        self.assertIsNone(saved_odds({**d,'oddsSource':'model'},'a'*64))
        self.assertIsNone(saved_odds({**d,'oddsUpdatedAt':''},'a'*64))
