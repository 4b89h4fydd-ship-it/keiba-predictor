"""No-network guarantees for lossless D1 circuit-breaker and retry policy."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import urllib.error

from scripts.arvexq_d1_capacity_guard import (
    post, classify, PERMANENT_CAPACITY, PERMANENT_WORKER_LIMIT,
    PERMANENT_TOO_LARGE, PERMANENT_AUTH, TRANSIENT,
)


class DummyResponse:
    status = 200
    def __init__(self, status: int = 200, body: bytes = b'{"ok":true}'):
        self.status = status
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, n: int):
        return self.body[:n]


class CapacityGuardTest(unittest.TestCase):
    def setUp(self):
        self.dir = TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "batch.json"
        self.path.write_text(json.dumps({"summaries": [], "details": [{"id": "race"}]}), encoding="utf-8")

    def test_cloudflare_error_classification(self):
        self.assertEqual(classify(500, b'{"ok":false,"error":"D1_ERROR: Exceeded maximum DB size"}'),
                         PERMANENT_CAPACITY)
        self.assertEqual(classify(503, b'error code: 1102'), PERMANENT_WORKER_LIMIT)
        self.assertEqual(classify(413, b'too large'), PERMANENT_TOO_LARGE)
        self.assertEqual(classify(401, b'bad token'), PERMANENT_AUTH)
        self.assertEqual(classify(503, b'upstream temporarily unavailable'), TRANSIENT)

    def test_database_full_never_retries(self):
        calls=[]
        def reply(req, timeout):
            calls.append(req)
            raise urllib.error.HTTPError(req.full_url,500,"full",None,
                                         __import__("io").BytesIO(b'D1_ERROR: Exceeded maximum DB size'))
        result=post(self.path,"https://example.invalid/api/sync","secret",opener=reply,
                    sleeper=lambda _: self.fail("must not retry permanent errors"),retries=5)
        self.assertEqual(result["reason"],PERMANENT_CAPACITY)
        self.assertEqual(result["attempts"],1)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.path.read_text(encoding="utf-8"),
                         json.dumps({"summaries":[],"details":[{"id":"race"}]}))

    def test_worker_limit_never_retries(self):
        calls=[]
        def reply(req, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url,503,"resource",None,
                                         __import__("io").BytesIO(b'error code: 1102'))
        result=post(self.path,"https://example.invalid/api/sync","secret",
                    opener=reply,sleeper=lambda _: self.fail("must not retry"),retries=4)
        self.assertEqual(result["reason"],PERMANENT_WORKER_LIMIT)
        self.assertEqual(len(calls),1)

    def test_transient_retries_at_most_twice(self):
        calls=[]
        def reply(req, timeout):
            calls.append(1)
            if len(calls)==1:
                raise urllib.error.HTTPError(req.full_url,503,"temporary",None,
                                             __import__("io").BytesIO(b"upstream unavailable"))
            return DummyResponse()
        result=post(self.path,"https://example.invalid/api/sync","secret",
                    opener=reply,sleeper=lambda _:None,retries=2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["attempts"],2)
        self.assertEqual(len(calls),2)

    def test_payload_limit_no_request(self):
        result=post(self.path,"https://example.invalid/api/sync","secret",
                    max_bytes=10,opener=lambda *_:self.fail("must not send"))
        self.assertEqual(result["reason"],PERMANENT_TOO_LARGE)
        self.assertEqual(result["attempts"],0)

    def test_json_error_with_http_200_not_success(self):
        result=post(self.path,"https://example.invalid/api/sync","secret",
                    opener=lambda req,timeout:DummyResponse(body=b'{"ok":false,"error":"D1_ERROR: Exceeded maximum DB size"}'),
                    sleeper=lambda _:self.fail("must not retry"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"],PERMANENT_CAPACITY)

if __name__=="__main__":
    unittest.main()
