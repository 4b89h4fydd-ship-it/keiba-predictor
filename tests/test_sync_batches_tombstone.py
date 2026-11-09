"""sync_batches must ship a compact-tombstone repair write verbatim.

The result-repair payload for a nightly-compact tombstone is the
stored stub plus a result-only overlay. protect_detail admits that
write only when nothing beyond result/payout differs from the stored
stub. The career-transport normalisation in
``arvexq_sync_batches.prepare_detail`` would materialise
``horses: []`` and stamp ``preparedMeta.careerTransportVersion`` onto
the detail — field differences that make the write inadmissible
(workflow runs of 2026-11-09 failed exactly there). For a detail
matching protect's compact-tombstone predicate, sync_batches
therefore skips the transport normalisation; the batch still carries
the detail in the lossless full-snapshot envelope, whose unpacked
content is the payload detail byte-for-byte.

Normal details are unaffected: they still receive the transport
stamp.
"""
from __future__ import annotations

import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest import TestCase

from arvexq.ingest.full_snapshot_codec import unpack_detail as unpack_full

RID = "jra-2026-10-31-京都-01"


def _stub() -> dict:
    return {
        "id": RID, "date": "2026-10-31", "track": "京都",
        "raceNumber": 1, "startTime": "09:50", "_summaryOnly": True,
        "compactedAt": "2026-11-01T19:12:00+09:00",
        "compactedFrom": {"bytes": 17863},
        "predictionStatus": "disabled",
        "predictionModelVersion": "arvexq-prediction-removed",
        "result": {"status": "確定", "source": "JRA公式",
                   "finishers": [{"horseNumber": 3, "finish": 1}],
                   "payouts": [{"type": "三連複", "combination": "3-5-7",
                                "amount": 1000}]},
        "resultCname": "pw01sde1008202604100120261031/ED",
    }


def _run_batches(payload: dict) -> list[dict]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import arvexq_sync_batches
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "payload.json"
        out = Path(tmp) / "batches"
        src.write_text(json.dumps(payload, ensure_ascii=False),
                       encoding="utf-8")
        argv = sys.argv
        sys.argv = ["arvexq_sync_batches.py", "--input", str(src),
                    "--out-dir", str(out)]
        try:
            arvexq_sync_batches.main()
        finally:
            sys.argv = argv
        return [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(out.glob("batch-*.json"))]


class SyncBatchesTombstoneTests(TestCase):
    def test_tombstone_detail_shipped_verbatim(self):
        detail = _stub()
        payload = {"summaries": [], "details": [deepcopy(detail)],
                   "meta": {"source": "test"}}
        batches = _run_batches(payload)
        shipped = [b for b in batches if b.get("details")]
        self.assertEqual(len(shipped), 1)
        unpacked = unpack_full(shipped[0]["details"][0])
        self.assertEqual(unpacked, detail)
        self.assertNotIn("preparedMeta", unpacked)
        self.assertNotIn("horses", unpacked)

    def test_normal_detail_still_gets_transport_stamp(self):
        detail = {
            "id": "jra-2026-11-08-東京-01", "date": "2026-11-08",
            "track": "東京", "raceNumber": 1,
            "predictionStatus": "ready",
            "horses": [{"horseNumber": 1, "name": "テスト"}],
            "result": {"status": "確定", "finishers": []},
        }
        payload = {"summaries": [], "details": [deepcopy(detail)],
                   "meta": {"source": "test"}}
        batches = _run_batches(payload)
        shipped = [b for b in batches if b.get("details")]
        self.assertEqual(len(shipped), 1)
        unpacked = unpack_full(shipped[0]["details"][0])
        self.assertIn("careerTransportVersion",
                      (unpacked.get("preparedMeta") or {}))
