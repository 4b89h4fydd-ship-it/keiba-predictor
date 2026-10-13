"""Official odds source manifests: verified roster coverage and immutable precedence."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.arvexq_build_odds_sources import build_sources


DAY = "2026-10-14"


def race(no=1):
    rid = f"nar-{DAY}-園田-{no:02}"
    return {"id": rid, "date": DAY, "circuit": "地方", "track": "園田",
            "raceNumber": no, "horses": [
                {"horseNumber": 1, "name": "テスト一号"},
                {"horseNumber": 2, "name": "テスト二号"}]}


def card(rows):
    return {"version": "arvexq-static-entry-v1",
            "date": DAY, "raceCount": len(rows), "races": rows}


class VerifiedOddsManifestTest(unittest.TestCase):
    def write_card(self, root, data):
        directory = root / "racecards"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (DAY + ".json")
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return target

    def test_card_without_saved_snapshots_is_a_valid_source_not_fabricated_odds(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            static, dist = root / "static", root / "dist"
            file = self.write_card(static, card([race(1), race(2)]))
            build_sources(static, dist)
            manifest = json.loads((dist / "odds-sources" / file.name).read_text())
            self.assertEqual(len(manifest["races"]), 2)
            source = manifest["races"][race(1)["id"]]
            self.assertEqual(source["sourceRacecardSha256"],
                             hashlib.sha256(file.read_bytes()).hexdigest())
            self.assertEqual(source["sourceRosterKind"], "verified-static-racecard")
            self.assertEqual(source["horses"], race(1)["horses"])
            self.assertNotIn("odds", source)
            self.assertFalse((dist / "odds-backups" / file.name).exists())

    def test_saved_original_wins_and_missing_venue_is_augmented(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            static, dist = root / "static", root / "dist"
            self.write_card(static, card([race(1), race(2)]))
            sdir = static / "saved-snapshots"
            sdir.mkdir(parents=True)
            saved = race(1)
            saved["horses"][0]["name"] = "過去の固定原本"
            raw = json.dumps(saved, ensure_ascii=False).encode()
            digest = hashlib.sha256(raw).hexdigest()
            (sdir / (digest + ".json")).write_text(json.dumps({
                "gzipBase64": base64.b64encode(gzip.compress(raw)).decode()}))
            (sdir / (DAY + ".json")).write_text(json.dumps({
                "version": "arvexq-saved-snapshots-v1", "date": DAY,
                "races": {saved["id"]: {"file": digest + ".json", "sha256": digest}}}))
            build_sources(static, dist)
            manifest = json.loads((dist / "odds-sources" / (DAY + ".json")).read_text())
            self.assertEqual(len(manifest["races"]), 2)
            self.assertEqual(manifest["races"][saved["id"]]["sourceSnapshotSha256"], digest)
            self.assertEqual(manifest["races"][saved["id"]]["horses"][0]["name"], "過去の固定原本")
            self.assertEqual(manifest["races"][race(2)["id"]]["sourceRosterKind"],
                             "verified-static-racecard")

    def test_invalid_or_duplicate_race_identity_fails_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            static, dist = root / "static", root / "dist"
            for wrong in (card([race(1), race(1)]),
                          {"version": "arvexq-static-entry-v1", "date": DAY,
                           "raceCount": 9, "races": [race(1)]},
                          card([{**race(1), "track": "大井"}]),
                          card([{**race(1), "horses": [
                              {"horseNumber": 1, "name": "A"},
                              {"horseNumber": 1, "name": "B"}]}])):
                self.write_card(static, wrong)
                with self.assertRaises(ValueError):
                    build_sources(static, dist)

    def test_real_checked_in_day_is_covered(self):
        static = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"
        known = static / "racecards" / (DAY + ".json")
        if not known.is_file():
            self.skipTest("date-scoped checked-in source unavailable")
        doc = json.loads(known.read_text())
        with TemporaryDirectory() as td:
            dist = Path(td) / "dist"
            build_sources(static, dist)
            output = json.loads((dist / "odds-sources" / (DAY + ".json")).read_text())
            expected = {row["id"] for row in doc["races"]}
            self.assertTrue(expected)
            self.assertTrue(expected.issubset(set(output["races"])))
            self.assertEqual(doc["raceCount"], len(expected))


if __name__ == "__main__":
    unittest.main()
