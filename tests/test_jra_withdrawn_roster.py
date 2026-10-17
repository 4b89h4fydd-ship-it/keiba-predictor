"""Regression for official card cancellation without a published numeric number."""
from unittest import TestCase
from unittest.mock import patch
import app

class JraWithdrawnRosterTests(TestCase):
    def test_unnumbered_cancellation_and_spaced_trainer(self):
        html='''<h2>新馬</h2><table><thead><tr><th>馬番</th><th>前走</th></tr></thead>
        <tr><td>枠1</td><td class="num">1</td><td class="horse"><p class="name"><a onclick="go('pw01dud123456789012/AB')">実馬</a></p><p class="trainer"><a>調教師 名</a>   <span>(美浦)</span></p></td><td>牡2 55.0kg <a>騎手</a></td></tr>
        <tr><td></td><td class="num">取消</td><td class="horse"><p class="name"><a onclick="go('pw01dud123456789013/AB')">取消馬</a></p></td><td>牡2</td></tr></table>'''
        with patch.object(app,'_jra_request',return_value=html),patch.object(app,'_jra_program_lookup',return_value={}):
            race=app._jra_parse_race('pw01dde0105202604010120261017/A0',supplement_profiles=False)
        self.assertEqual(len(race['horses']),1)
        self.assertEqual(race['horses'][0]['trainer'],'調教師 名')
        self.assertEqual(race['withdrawnEntries'][0]['name'],'取消馬')
        self.assertIsNone(race['withdrawnEntries'][0]['horseNumber'])
        self.assertTrue(race['withdrawnEntries'][0]['sourceHorseNumberMissing'])
