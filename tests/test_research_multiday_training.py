"""Historical training sources can contain NAR yesterday and JRA last weekend."""
import unittest
from unittest.mock import patch
from scripts.arvexq_train_research_models import train_models


class MultiDayTrainingTests(unittest.TestCase):
    def test_circuit_models_accept_prior_distinct_dates_not_target(self):
        prior_nar = {'id': 'nar-old', 'date': '2026-10-16', 'circuit': '地方', 'result': {'status': '確定'}}
        prior_jra = {'id': 'jra-old', 'date': '2026-10-11', 'circuit': '中央', 'result': {'status': '確定'}}
        target_jra = {'id': 'jra-today', 'date': '2026-10-17', 'circuit': '中央', 'result': {'status': '確定'}}
        seen = {}
        def fake_fit(details, *, circuit):
            seen[circuit] = [row['id'] for row in details]
            return {'circuit': circuit}
        with patch('scripts.arvexq_train_research_models.fit_model', side_effect=fake_fit):
            models, errors = train_models({'details': [prior_nar, prior_jra, target_jra]}, '2026-10-17')
        self.assertEqual(set(models), {'中央', '地方'})
        self.assertEqual(seen['中央'], ['jra-old'])
        self.assertEqual(seen['地方'], ['nar-old'])
        self.assertEqual(errors, {})


if __name__ == '__main__':
    unittest.main()
