# -*- coding: utf-8 -*-
"""Unit tests for scripts/arvexq_pack_bundle.py (Cloudflare-exit lane).

The bundle builder is the GitHub-native counterpart of
arvexq_fetch_d1_bundle.py: it must reproduce that fetcher's output
contract ({date, races, details} + report) from the committed static
packs alone, exclude retired Banei, and never invent a detail for a
race whose pack is absent.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "arvexq_pack_bundle", ROOT / "scripts" / "arvexq_pack_bundle.py")
pack_bundle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pack_bundle)


def _write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


def _race_row(rid: str, track: str) -> dict:
    return {
        "id": rid, "date": "2026-11-23", "circuit": "地方", "track": track,
        "raceNumber": 1, "startTime": "10:00", "scheduledStartTime": "10:00",
        "title": "テスト", "surface": "ダート", "distance": 1400,
        "weather": "晴", "condition": "良",
        "volatility": {"label": "", "score": None}, "raceStatus": "",
        "updatedAtEpoch": 1,
    }


class PackBundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.packs = Path(self._tmp.name) / "api-static"
        rows = [
            _race_row("nar-2026-11-23-金沢-01", "金沢"),
            _race_row("nar-2026-11-23-金沢-02", "金沢"),
            _race_row("nar-2026-11-23-帯広ば-01", "帯広ば"),
        ]
        _write(self.packs / "day" / "2026-11-23.json", {
            "version": "arvexq-static-api-v1", "source": "static-json",
            "ok": True, "date": "2026-11-23", "races": rows, "details": [],
            "raceCount": 3, "detailCount": 0,
        })
        # Race 01 has a pack detail; race 02 deliberately has none.
        _write(self.packs / "race" / "nar-2026-11-23-金沢-01.json", {
            "version": "arvexq-static-api-v1", "source": "static-json",
            "ok": True, "race_id": "nar-2026-11-23-金沢-01",
            "summary": {"id": "nar-2026-11-23-金沢-01", "date": "2026-11-23",
                        "track": "金沢", "raceNumber": 1},
            "detail": {"id": "nar-2026-11-23-金沢-01", "date": "2026-11-23",
                       "track": "金沢", "raceNumber": 1, "horses": []},
            "analysis_ready": False, "detail_updated_at": None, "odds": [],
        })

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bundle_shape_and_banei_exclusion(self) -> None:
        bundle, report = pack_bundle.build_bundle(self.packs, "2026-11-23")
        self.assertEqual(bundle["date"], "2026-11-23")
        self.assertEqual(
            [r["id"] for r in bundle["races"]],
            ["nar-2026-11-23-金沢-01", "nar-2026-11-23-金沢-02"],
        )
        self.assertEqual(report["retired_banei_excluded_count"], 1)
        self.assertEqual(report["race_count"], 2)

    def test_missing_pack_is_reported_not_invented(self) -> None:
        bundle, report = pack_bundle.build_bundle(self.packs, "2026-11-23")
        self.assertEqual(
            [d["id"] for d in bundle["details"]], ["nar-2026-11-23-金沢-01"])
        self.assertEqual(report["detail_count"], 1)
        self.assertEqual(report["missing_detail_count"], 1)
        self.assertEqual(
            report["missing_details"][0]["race_id"], "nar-2026-11-23-金沢-02")

    def test_missing_day_pack_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            pack_bundle.build_bundle(self.packs, "2026-11-24")


if __name__ == "__main__":
    unittest.main()
