"""Configured, licensed provider tests (no actual third-party network calls)."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from arvexq.databanks.authorized_feeds import (
    configured_feeds, register_authorized_history_feeds,
)
from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.orchestrator import fetch_domain
from arvexq.ingest.fallback_enrichment import enrich_race_missing
from arvexq.databanks.source_catalog import discovery_inventory, NAR_VENUES


def spec(name="partner_jra", circuit="JRA", url="https://example.com/history", token_env="ARVEXQ_FAKE_TOKEN"):
    return {"name": name, "circuit": circuit, "url": url, "token_env": token_env, "priority": 25}


def runner(day, first):
    return {"date": day, "track": "東京", "distance": 1400, "raceNumber": 3,
            "fieldSize": 14, "cornerPositions": [first, first, first]}


class HttpResponse:
    def __init__(self, data):
        self._data = json.dumps(data, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, _size):
        return self._data


class AuthorizedFeedConfigTests(unittest.TestCase):
    def test_disabled_by_default_no_implicit_scrapers(self):
        self.assertEqual(configured_feeds(environ={}), [])
        reg = DataBankRegistry()
        self.assertEqual(register_authorized_history_feeds(reg, environ={}), [])
        self.assertEqual(reg.providers("horse_history"), [])

    def test_any_number_sources_and_circuits(self):
        items = [spec(name="partner_1", circuit="JRA"),
                 spec(name="partner_2", circuit="NAR"),
                 spec(name="partner_3", circuit="both", token_env="")]
        env = {"ARVEXQ_FAKE_TOKEN": "secret"}
        reg = DataBankRegistry()
        registered = register_authorized_history_feeds(
            reg, config=json.dumps(items), environ=env
        )
        self.assertEqual(len(registered), 3)
        self.assertEqual(len(reg.providers("horse_history", circuit="JRA")), 2)
        self.assertEqual(len(reg.providers("horse_history", circuit="NAR")), 2)

    def test_disabled_without_token(self):
        reg = DataBankRegistry()
        self.assertEqual(register_authorized_history_feeds(reg,
            config=json.dumps([spec()]), environ={}), [])

    def test_invalid_or_unlicensed_style_endpoints_not_implicitly_used(self):
        for uri in ("http://example.com", "https://localhost/api",
                    "https://user:secret@example.com/api", "file:///tmp/races.json"):
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    configured_feeds(json.dumps([spec(url=uri)]),
                                     environ={"ARVEXQ_FAKE_TOKEN": "ok"})

    def test_discovery_does_not_claim_connected(self):
        inventory = discovery_inventory()
        self.assertGreaterEqual(len(inventory), 20)
        self.assertGreaterEqual(len(NAR_VENUES), 15)
        self.assertTrue(all(row["enabledForExtraction"] is False for row in inventory))


class AuthorizedHistoryRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_identity_and_future_cutoff(self):
        reg = DataBankRegistry()
        c = json.dumps([spec()])
        env = {"ARVEXQ_FAKE_TOKEN": "secret"}
        register_authorized_history_feeds(reg, config=c, environ=env)
        horse = {"horseId": "horse-100", "name": "sample"}
        race = {"date": "2026-10-08", "circuit": "中央", "track": "東京"}
        def respond(request, timeout):
            self.assertEqual(timeout, 8)
            self.assertEqual(request.headers["Authorization"], "Bearer secret")
            self.assertIn("horseId=horse-100", request.full_url)
            self.assertIn("raceDate=2026-10-08", request.full_url)
            return HttpResponse({
                "horseId": "horse-100",
                "recentRaces": [
                    runner("2026-09-20", 2), runner("2026-10-09", 1),
                ],
            })
        with patch.dict(os.environ, env), patch(
            "urllib.request.urlopen", side_effect=respond
        ):
            results = await fetch_domain("horse_history", horse, race, 5,
                circuit="JRA", bank_registry=reg)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)
        self.assertEqual(len(results[0].data["recentRaces"]), 1)
        self.assertEqual(results[0].data["recentRaces"][0]["cornerPositions"][0], 2)

    async def test_measured_horse_3f_enriches_full_corner_history_without_refetching_official(self):
        reg = DataBankRegistry()
        called = []
        def official(*args):
            called.append("official")
            return {"recentRaces": []}
        reg.register(DataSource(
            name="jra_official", circuit="JRA", priority=10,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": official},
        ))
        partner = spec()
        partner["horse_first3f"] = True
        register_authorized_history_feeds(
            reg, config=json.dumps([partner]),
            environ={"ARVEXQ_FAKE_TOKEN": "secret"},
        )
        past = [runner(f"2026-09-{d:02}", 2) for d in (30, 24, 18, 12, 6)]
        h = {"horseId": "horse-100", "name": "sample", "recentRaces": past}
        observations = [dict(past[0], first3FSeconds=36.8),
                        dict(past[1], first3FSeconds=36.5)]
        with patch.dict(os.environ, {"ARVEXQ_FAKE_TOKEN": "secret"}), patch(
            "urllib.request.urlopen",
            return_value=HttpResponse({"horseId":"horse-100", "recentRaces": observations}),
        ):
            detail = {"date": "2026-10-08", "circuit": "中央", "horses": [h]}
            done = await enrich_race_missing(detail, bank_registry=reg)
        self.assertEqual(called, [], "official source must not refetch complete corners")
        rows = done["horses"][0]["recentRaces"]
        self.assertAlmostEqual(rows[0]["horseFirst3FSeconds"], 36.8)
        self.assertAlmostEqual(rows[1]["horseFirst3FSeconds"], 36.5)
        meta = done["preparedMeta"]["supplementalSearch"]
        self.assertEqual(meta["measuredHorseFirst3FReadyHorses"], 1)
        self.assertEqual(meta["measuredHorseFirst3FProviderCount"], 1)
        self.assertNotIn("horseFirst3FSeconds", h["recentRaces"][0], "input is unchanged")

    async def test_bad_provider_is_isolated_and_no_wrong_horse_merge(self):
        reg = DataBankRegistry()
        reg.register(DataSource(
            name="official_jra", circuit="JRA", priority=10,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": lambda horse, race, limit: {
                "recentRaces": [runner("2026-09-25", 3)]
            }},
        ))
        register_authorized_history_feeds(reg,
            config=json.dumps([spec()]),
            environ={"ARVEXQ_FAKE_TOKEN": "secret"})
        with patch.dict(os.environ, {"ARVEXQ_FAKE_TOKEN": "secret"}), patch(
            "urllib.request.urlopen",
            return_value=HttpResponse({
                "horseId": "WRONG_HORSE",
                "recentRaces": [runner("2026-09-25", 1)],
            }),
        ):
            detail = {
                "date": "2026-10-08", "circuit": "中央", "horses": [
                    {"horseId": "horse-100", "name": "sample", "recentRaces": []},
                ],
            }
            enriched = await enrich_race_missing(detail, bank_registry=reg)
        self.assertEqual(enriched["horses"][0]["recentRaces"][0]["cornerPositions"][0], 3)
        self.assertIn("official_jra", enriched["horses"][0]["_supplementalSources"])
        failed = enriched["preparedMeta"]["supplementalSearch"]["failures"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["source"], "partner_jra")


if __name__ == "__main__":
    unittest.main()
