"""The compact-tombstone result-only exception (2026-11-09).

The D1 nightly compact replaced the stored details of 13 finished
2026-10-31 JRA races with summary stubs stamped
predictionStatus="disabled" / predictionModelVersion=
"arvexq-prediction-removed" — the tombstone stamps live IN STORAGE
(the compact envelope unpacks to the stub; the originals are gone,
and there is no preoffStage64Archive).  protect_detail failed closed
on them, which also blocked the history payout repair: those races'
stored payout combinations violate the official shape and could not
be rewritten by any lane.

These tests pin the narrow exception in
scripts/arvexq_protect_sync.py:

- a RESULT-ONLY write (result / resultCname / payouts) over a
  compact tombstone — compact provenance present, no card, no
  forecast blocks, no archive — is admitted;
- any wider write is refused;
- an archive or any forecast block disables the exception (the
  archive-restore / fail-closed behaviour is unchanged);
- a projection tombstone without the compact markers (a read of a
  live race) still fails closed, and the 2026-11-05 regression
  scenarios keep their behaviour (see
  tests/test_protect_projection_seam.py).
"""
from __future__ import annotations

import io
import json
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from scripts import arvexq_protect_sync as protect_sync
from scripts.arvexq_protect_sync import fetch_current, protect_detail

RID = "jra-2026-10-31-京都-01"
TOKEN = "pw01sde1008202604100120261031/AB"


def _stub() -> dict:
    """The stored shape of a nightly-compact tombstone (Kyoto 01)."""
    return {
        "id": RID, "date": "2026-10-31", "track": "京都",
        "raceNumber": 1, "raceName": "2歳新馬", "startTime": "09:50",
        "status": "確定", "_summaryOnly": True,
        "compactedAt": "2026-11-01T19:12:00+09:00",
        "compactedFrom": {"bytes": 17863},
        "predictionStatus": "disabled",
        "predictionModelVersion": "arvexq-prediction-removed",
        "forecastText": "",
        "result": {
            "status": "確定", "source": "JRA公式",
            "finishers": [{"horseNumber": 3, "name": "勝馬",
                           "finish": 1}],
            "payouts": [{"type": "三連複", "combination": "3",
                         "amount": 1000}],
        },
    }


def _result_only_write(stub: dict) -> dict:
    """The stub with only its result fields replaced (official fix)."""
    out = deepcopy(stub)
    out["result"] = {
        "status": "確定", "source": "JRA公式",
        "finishers": [{"horseNumber": 3, "name": "勝馬", "finish": 1}],
        "payouts": [{"type": "三連複", "combination": "3-5-7",
                     "amount": 1000}],
    }
    out["resultCname"] = TOKEN
    return out


class CompactTombstoneExceptionTests(TestCase):
    def test_result_only_write_over_compact_tombstone_passes(self):
        old = _stub()
        incoming = _result_only_write(old)
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["result"], incoming["result"])
        self.assertEqual(out["resultCname"], TOKEN)
        # Everything else is the stored stub, verbatim.
        for key, value in old.items():
            if key in ("result", "resultCname"):
                continue
            self.assertEqual(out[key], value)
        self.assertEqual(out["predictionStatus"], "disabled")
        self.assertNotIn("unifiedForecast", out)
        self.assertNotIn("predictionMarks", out)

    def test_payouts_only_write_passes(self):
        old = _stub()
        incoming = deepcopy(old)
        incoming["payouts"] = [{"type": "三連複", "combination": "3-5-7",
                                "amount": 1000}]
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["payouts"], incoming["payouts"])

    def test_write_touching_another_field_is_refused(self):
        old = _stub()
        incoming = _result_only_write(old)
        incoming["raceName"] = "書き換え"
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))

    def test_write_adding_the_card_is_refused(self):
        old = _stub()
        incoming = _result_only_write(old)
        incoming["horses"] = [{"horseNumber": 1, "name": "H1"}]
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))

    def test_publish_shaped_write_is_refused(self):
        # A genuine-publish-shaped write over a compact tombstone
        # changes far more than the result fields; the exception must
        # not become a publish door and the "ready" gate is untouched.
        old = _stub()
        incoming = _result_only_write(old)
        incoming["predictionStatus"] = "ready"
        incoming["predictionModelVersion"] = "arvexq-rewrite-v3-v9b"
        incoming["predictionMarks"] = [
            {"horseNumber": 3, "mark": "◎", "winProbability": 0.4}]
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))

    def test_archive_present_disables_the_exception(self):
        old = _stub()
        # An archive that cannot verify: the pre-existing behaviour
        # (fail closed) must win over the new exception.
        old["preoffStage64Archive"] = {"raceId": RID, "bogus": True}
        incoming = _result_only_write(old)
        del incoming["preoffStage64Archive"]
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))

    def test_forecast_block_present_disables_the_exception(self):
        for key, value in (
                ("unifiedForecast", {"modelVersion": "x"}),
                ("prediction", {"predictionStatus": "ready"}),
                ("predictionMarks", [{"horseNumber": 1, "mark": "◎"}]),
                ("recommendedBets", [{"kind": "三連単"}])):
            old = _stub()
            old[key] = value
            incoming = _result_only_write(old)
            del incoming[key]
            with self.assertRaises(RuntimeError, msg=key):
                protect_detail(deepcopy(old), deepcopy(incoming))

    def test_projection_tombstone_without_compact_markers_refused(self):
        # A tombstoned READ of a live race: stamps present, but no
        # compact provenance. Even a result-only write fails closed.
        old = _stub()
        incoming = _result_only_write(old)
        for detail in (old, incoming):
            del detail["compactedAt"]
            del detail["compactedFrom"]
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))

    def test_card_present_disables_the_exception(self):
        old = _stub()
        old["horses"] = [{"horseNumber": 1, "name": "H1"}]
        incoming = _result_only_write(old)
        incoming["horses"] = deepcopy(old["horses"])
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _json_response(payload: dict) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload).encode("utf-8"))


class FetchCurrentCompactStubTests(TestCase):
    def test_display_compact_stub_is_returned_as_stored_state(self):
        stub = _stub()
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            return _json_response({"ok": True, "detail": stub})

        with patch.object(protect_sync.urllib.request, "urlopen",
                          fake_urlopen):
            got = fetch_current("https://example.invalid", RID)
        self.assertEqual(got, stub)
        self.assertEqual(len(calls), 2)

    def test_display_projection_tombstone_still_fails_closed(self):
        tombstone = _stub()
        del tombstone["compactedAt"]
        del tombstone["compactedFrom"]
        tombstone["horses"] = [{"horseNumber": 1, "name": "H1"}]

        def fake_urlopen(req, timeout=None):
            return _json_response({"ok": True, "detail": tombstone})

        with patch.object(protect_sync.urllib.request, "urlopen",
                          fake_urlopen):
            with self.assertRaises(RuntimeError):
                fetch_current("https://example.invalid", RID)
