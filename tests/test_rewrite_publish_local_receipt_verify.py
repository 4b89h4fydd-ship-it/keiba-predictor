"""Local sealed-snapshot receipt verification (fix program B, 2026-11-23).

The rewrite publish lane's receipt gate used to read the published
race back through the D1-backed API (GET /api/race) and verify the
read-back copy.  It now seals the exact protected detail into a LOCAL
snapshot file — the saved-snapshots envelope, whose sha256 is the
SHA-256 of the raw snapshot string — and verifies against that file:
envelope sha256 re-hashed over the restored bytes, receipt string
(64-hex) equality, verified_unified() content re-hash, and marks
agreement.  These tests pin the round trip, every tamper shape, and
that publish_date (non-dry) performs NO API read-back after posting.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import urllib.parse
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.arvexq_protect_sync import protect_detail
from scripts.arvexq_rewrite_publish import (
    load_local_snapshot_detail, publish_date, seal_local_snapshot,
    verify_local_snapshot)
from tests.test_publish_mass_feature_archive import build, fresh_detail

JST = ZoneInfo("Asia/Tokyo")
DATE = "2026-11-04"
RACE_ID = "nar-2026-11-04-金沢-01"


def published_detail():
    detail = fresh_detail()
    new, receipt = build(detail)
    assert new is not None, receipt
    return protect_detail(detail, new), receipt, new


class LocalSnapshotSealTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "snapshots"

    def tearDown(self):
        self.tmp.cleanup()

    def test_seal_and_verify_round_trip(self):
        final, receipt, new = published_detail()
        path = seal_local_snapshot(final, DATE, self.root)
        env = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(env["version"], "arvexq-saved-snapshot-v1")
        # The envelope sha256 is the SHA-256 of the raw snapshot bytes.
        import base64, gzip
        restored = gzip.decompress(base64.b64decode(env["gzipBase64"]))
        self.assertEqual(hashlib.sha256(restored).hexdigest(),
                         env["sha256"])
        self.assertEqual(env["bytes"], len(restored))
        loaded = load_local_snapshot_detail(DATE, RACE_ID, self.root)
        # JSON round trip stringifies int dict keys; compare canonical
        # serializations (the same form the envelope hashes).
        self.assertEqual(
            json.dumps(loaded, ensure_ascii=False, sort_keys=True),
            json.dumps(final, ensure_ascii=False, sort_keys=True))
        ok, reason, sealed = verify_local_snapshot(
            DATE, RACE_ID, receipt, new, self.root)
        self.assertTrue(ok, reason)
        self.assertEqual(sealed["unifiedForecast"]["receiptSha256"],
                         receipt)

    def test_receipt_must_be_64hex_and_equal(self):
        final, receipt, new = published_detail()
        seal_local_snapshot(final, DATE, self.root)
        ok, reason, _ = verify_local_snapshot(
            DATE, RACE_ID, "b" * 64, new, self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "local-snapshot-receipt-mismatch")
        ok, reason, _ = verify_local_snapshot(
            DATE, RACE_ID, "not-a-hash", new, self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "receipt-not-64hex")

    def test_missing_snapshot_fails_closed(self):
        _, receipt, new = published_detail()
        ok, reason, _ = verify_local_snapshot(
            DATE, RACE_ID, receipt, new, self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "local-snapshot-missing-or-unverifiable")

    def test_envelope_sha_tamper_fails(self):
        final, receipt, new = published_detail()
        path = seal_local_snapshot(final, DATE, self.root)
        env = json.loads(path.read_text(encoding="utf-8"))
        env["sha256"] = "0" * 64
        path.write_text(json.dumps(env), encoding="utf-8")
        self.assertIsNone(
            load_local_snapshot_detail(DATE, RACE_ID, self.root))
        ok, _, _ = verify_local_snapshot(
            DATE, RACE_ID, receipt, new, self.root)
        self.assertFalse(ok)

    def test_content_tamper_fails_content_verify(self):
        # Re-seal a tampered detail under its own (honest) envelope:
        # the envelope sha verifies, but the unified content no longer
        # re-hashes to the receipt — the 256-ticket failure mode.
        final, receipt, new = published_detail()
        tampered = json.loads(json.dumps(final))
        tampered["unifiedForecast"]["marks"][0]["winProbability"] += 0.01
        seal_local_snapshot(tampered, DATE, self.root)
        ok, reason, _ = verify_local_snapshot(
            DATE, RACE_ID, receipt, new, self.root)
        self.assertFalse(ok)
        self.assertEqual(reason, "local-snapshot-content-mismatch")

    def test_marks_mismatch_fails(self):
        final, receipt, new = published_detail()
        seal_local_snapshot(final, DATE, self.root)
        built = json.loads(json.dumps(new))
        marks = built.get("predictionMarks") or []
        if len(marks) == 5:
            marks[0]["horseNumber"], marks[1]["horseNumber"] = (
                marks[1]["horseNumber"], marks[0]["horseNumber"])
            ok, reason, _ = verify_local_snapshot(
                DATE, RACE_ID, receipt, built, self.root)
            self.assertFalse(ok)
            self.assertIn("marks-mismatch", reason)


FIXED_NOW = datetime(2026, 11, 4, 10, 5, tzinfo=JST)


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW


class PublishDateLocalVerifyTests(TestCase):
    def test_publish_uses_no_api_readback(self):
        detail = fresh_detail()
        summaries = [{"race_id": RACE_ID, "id": RACE_ID, "track": "金沢"}]
        get_calls = []

        def fake_get(url: str):
            get_calls.append(url)
            if url.startswith("/api/races"):
                return {"races": summaries}
            rid = urllib.parse.unquote(url.rsplit("/", 1)[-1])
            assert rid == RACE_ID
            return {"detail": detail}

        tmp = tempfile.TemporaryDirectory()
        cwd = os.getcwd()
        os.chdir(tmp.name)
        stdout = io.StringIO()
        try:
            with patch("scripts.arvexq_rewrite_publish._get",
                       side_effect=fake_get), \
                    patch("scripts.arvexq_rewrite_publish._post_sync",
                          return_value={"ok": True}) as post, \
                    patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                          return_value={RACE_ID: {
                              "segment": "nar",
                              "extras": {str(n): {"elo": 1500.0}
                                         for n in (1, 2, 3, 4, 5)}}}), \
                    patch("scripts.arvexq_rewrite_publish.datetime",
                          _FixedDateTime), \
                    redirect_stdout(stdout):
                counts = publish_date(DATE, "token", False)
        finally:
            os.chdir(cwd)
        out = stdout.getvalue()
        self.assertEqual(counts["published"], 1, out)
        self.assertEqual(counts["failed"], 0, out)
        self.assertEqual(post.call_count, 1)
        # Exactly one API fetch of the race: the pre-publish input
        # fetch.  No /api/race read-back happens after posting.
        race_fetches = [u for u in get_calls if u.startswith("/api/race/")]
        self.assertEqual(len(race_fetches), 1, get_calls)
        # The local sealed snapshot exists in the working directory.
        manifest = Path(tmp.name) / "rewrite-publish-snapshots" / DATE \
            / "manifest.json"
        self.assertTrue(manifest.exists())
        entry = json.loads(manifest.read_text(encoding="utf-8")) \
            ["races"][RACE_ID]
        self.assertEqual(len(entry["sha256"]), 64)
        tmp.cleanup()


if __name__ == "__main__":
    import unittest
    unittest.main()
