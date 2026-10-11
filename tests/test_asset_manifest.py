"""Verify runtime serving actually delivers the extracted calculation modules."""
import unittest

from arvexq.ui.assets import read_asset


class AssetManifestIntegrationTest(unittest.TestCase):
    def test_api_serves_dependency_modules_before_screen_adapter(self):
        from fastapi.testclient import TestClient
        import app

        response = TestClient(app.app).get('/app-v329.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/javascript', response.headers['content-type'])
        self.assertEqual(response.text, read_asset('app.js'))
        for name in ('ARVEXQPaceSimulation', 'ARVEXQRelativeGrades'):
            declaration = response.text.index('global.' + name + '=')
            use = response.text.index('window.' + name + '.create(')
            self.assertLess(declaration, use)
        self.assertEqual(response.text.count('function scenarioPlan('), 1)
        self.assertEqual(response.text.count('function assignOverallGrades('), 1)


if __name__ == '__main__':
    unittest.main()
