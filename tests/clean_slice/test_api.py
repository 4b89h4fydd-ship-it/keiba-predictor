import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
from rewrite.slice.analyze import analyze
from rewrite.slice.server import handler
from rewrite.slice.store import Store


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.path=Path(self.directory.name)/'research.db'
        store=Store(self.path)
        fixture=next((Path(__file__).resolve().parents[1]/'fixtures/clean_slice').glob('jra*.json'))
        self.race=json.loads(fixture.read_text())
        self.expected=store.save(self.race,analyze(self.race));store.close()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.path))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.directory.cleanup()

    def get(self,path):
        try:
            response=urllib.request.urlopen(self.base+path)
        except urllib.error.HTTPError as error:
            response=error
        return response.status,json.load(response)

    def test_api_exact_saved_payload_filters_and_404(self):
        code,health=self.get('/api/v1/health')
        self.assertEqual((code,health['verified_saved_races']),(200,1))
        code,document=self.get('/api/v1/races/'+urllib.parse.quote(self.race['id']))
        self.assertEqual(code,200);self.assertEqual(document,self.expected)
        code,document=self.get('/api/v1/races?date=1900-01-01')
        self.assertEqual((code,document['races']),(200,[]))
        code,document=self.get('/api/v1/races/missing')
        self.assertEqual(code,404);self.assertFalse(document['ok'])

    def test_corrupt_artifact_cannot_return_success_even_health(self):
        store=Store(self.path)
        with store.db:
            store.db.execute('DROP TRIGGER runs_no_update')
            store.db.execute("UPDATE runs SET output_sha256='corrupt'")
        store.close()
        for route in ('/api/v1/health','/api/v1/races','/api/v1/races/'+urllib.parse.quote(self.race['id'])):
            code,document=self.get(route)
            self.assertEqual(code,500);self.assertFalse(document['ok'])


if __name__=='__main__':unittest.main()
