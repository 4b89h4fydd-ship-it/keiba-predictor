import ast
import inspect
import textwrap
import unittest
from unittest.mock import Mock
import app
from arvexq.databanks.legacy_bridge import _jra_official_prior_result_adapter

class JraMarginPathRegression(unittest.TestCase):
    def test_jra_result_parser_has_no_unbound_margin_text(self):
        tree=ast.parse(textwrap.dedent(inspect.getsource(app._jra_parse_result)))
        reads=[n for n in ast.walk(tree) if isinstance(n,ast.Name)
               and n.id=="margin_text" and isinstance(n.ctx,ast.Load)]
        self.assertFalse(reads,"undefined margin_text causes every JRA official result parse to fail")

    def test_existing_jra_result_link_without_profile_cname(self):
        import base64
        link="jraresult-"+base64.urlsafe_b64encode(b"official-result").decode().rstrip("=")
        result=Mock(return_value={"date":"2026-10-01","track":"東京",
             "result":{"finishers":[{"name":"勝ち馬","finish":1,"timeSeconds":95.0},
                                    {"name":"対象馬","finish":3,"timeSeconds":95.7,
                                     "last3FSeconds":34.2}]}})
        fetch=_jra_official_prior_result_adapter({
             "_jra_profile_runs":Mock(return_value=[]),"_jra_parse_result":result})
        output=fetch({"name":"対象馬","recentRaces":[{"date":"2026-10-01",
                         "track":"東京","raceId":link,"fieldSize":12,"finish":3}]},
                     {"date":"2026-10-12"},200)
        self.assertAlmostEqual(output["recentRaces"][0]["timeBehindWinner"],0.7)
        self.assertEqual(output["recentRaces"][0]["last3fSeconds"],34.2)

if __name__=="__main__":
    unittest.main()
