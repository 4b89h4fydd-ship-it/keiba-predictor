"""Wikimedia rights metadata discovery is not a license to analyze race footage."""
from __future__ import annotations

from unittest import TestCase

from scripts.arvexq_discover_open_japan_video import (
    _bad, _info, _license, discover, ROOTS, VERSION,
)


def metadata(license_name="CC BY-SA 4.0"):
    return {"query": {"pages": [{"imageinfo": [{
        "mime": "video/webm",
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/11/race.webm",
        "extmetadata": {
            "LicenseShortName": {"value": license_name},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
            "Artist": {"value": "<a href='https://commons.wikimedia.org/'>Independent photographer</a>"},
        }
    }]}]}}


class CommonsClient:
    def __init__(self):
        self.calls = []

    def __call__(self, params):
        self.calls.append(params)
        if params.get("prop") == "imageinfo":
            return metadata()
        title = params["cmtitle"]
        if title == ROOTS[0]:
            return {"query": {"categorymembers": [
                {"ns": 6, "title": "File:Ban ei - obihiro - Oct 17 2020.webm"},
                {"ns": 6, "title": "File:Tokyo flat horse race.webm"},
                {"ns": 6, "title": "File:Japanese racing horse.jpg"},
                {"ns": 14, "title": "Category:帯広ばんえい競馬"},
            ]}}
        if title == ROOTS[1]:
            return {"query": {"categorymembers": [
                {"ns": 6, "title": "File:Tokyo flat horse race.webm"},
            ]}}
        return {"query": {"categorymembers": []}}


class OpenJapanSourceTests(TestCase):
    def test_research_crawl_excludes_obihiro_and_deduplicates(self):
        client = CommonsClient()
        report = discover(client=client)
        self.assertEqual(report["version"], VERSION)
        self.assertGreater(report["inspectedCategoryFiles"], 0)
        self.assertEqual(report["excludedObihiroBaneiVideoMentions"], 1)
        self.assertEqual(report["metadataVideoCandidates"], 1)
        self.assertEqual(report["ccMetadataCandidates"], 1)
        self.assertFalse(report["raceVideoActuallyDownloaded"])
        self.assertFalse(report["forecastChanged"])
        item = report["candidates"][0]
        self.assertEqual(item["artist"], "Independent photographer")
        self.assertTrue(item["commonsCcMetadataCandidate"])
        self.assertFalse(item["eligibleForProductionIngestion"])
        self.assertFalse(any("obihiro" in str(p).lower() for p in client.calls))

    def test_bad_venue_names_rejected(self):
        for value in ("File:Ban ei - obihiro.webm",
                      "Category:帯広ばんえい競馬",
                      "File:ばんえいrace.webm"):
            self.assertTrue(_bad(value))

    def test_no_license_or_nonmedia_is_not_rights_eligible(self):
        short, url, author, valid = _license({
            "LicenseShortName": {"value": "All rights reserved"},
            "LicenseUrl": {"value": "https://example.com/"},
            "Artist": {"value": "<b>Photographer</b>"}
        })
        self.assertFalse(valid)
        self.assertEqual(author, "Photographer")
        payload = metadata()
        payload["query"]["pages"][0]["imageinfo"][0]["mime"] = "image/jpeg"
        self.assertIsNone(_info(lambda _: payload, "File:Not video.webm"))

    def test_empty_catalog_expresses_nonexhaustive_not_false_rights(self):
        audit = discover(client=lambda _: {"query": {"categorymembers": []}})
        self.assertEqual(audit["metadataVideoCandidates"], 0)
        self.assertIn("no-eligible", audit["status"])
        self.assertIn("Not exhaustive", audit["caveat"])
        self.assertFalse(audit["rightsClearedForProduction"])

    def test_limit_and_source_failure_are_explicit(self):
        limited = discover(client=CommonsClient(), max_categories=1)
        self.assertTrue(limited["crawlTruncated"])
        self.assertEqual(limited["status"], "incomplete-source-audit")

        def broken(*args, **kwargs):
            raise RuntimeError("failed API")
        failing = discover(client=broken)
        self.assertGreater(len(failing["errors"]), 0)
        self.assertEqual(failing["status"], "incomplete-source-audit")
