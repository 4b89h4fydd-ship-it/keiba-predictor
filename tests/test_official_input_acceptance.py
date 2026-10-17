from unittest import TestCase
from scripts.arvexq_official_input_acceptance import summarize_jra, official_jra_roster_size


class OfficialInputAcceptanceTests(TestCase):
    def test_fieldsize_from_same_parser_is_not_independent_proof(self):
        race={'id':'jra-test','date':'2026-10-17','fieldSize':1,'horses':[{'horseNumber':1,'name':'馬'}]}
        report=summarize_jra([race],race['date'])
        self.assertFalse(report['sourceRosterVerified'])
        self.assertIsNone(report['entryCoveragePercent'])
        report=summarize_jra([race],race['date'],{'jra-test':2})
        self.assertEqual(report['fieldMismatches'],['jra-test'])
        self.assertEqual(report['entryCoveragePercent'],50)

    def test_official_profile_identity_count_is_deduplicated(self):
        html='''<table><thead><tr><th>馬番</th><th>前走</th></tr></thead>
          <tr><td><a onclick="go('pw01dud123456789012/AB')">馬</a></td></tr>
          <tr><td><a onclick="go('pw01dud123456789012/AB')">同じ馬</a></td></tr>
          <tr><td><a onclick="go('pw01dud123456789013/AC')">別馬</a></td></tr></table>'''
        self.assertEqual(official_jra_roster_size(html),2)
        self.assertIsNone(official_jra_roster_size('<h1>Access Denied</h1>'))
