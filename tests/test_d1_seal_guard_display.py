"""Protect original D1 evidence even when the legacy read route is missing."""
from io import BytesIO
import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from scripts.arvexq_protect_sync import fetch_current


RACE = "jra-2026-10-18-京都-12"
BASE = "https://kraiz-api.4b89h4fydd.workers.dev"


class Response:
    def __init__(self, data):
        self.body = BytesIO(json.dumps(data).encode())
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def read(self):
        return self.body.read()


def test_existing_d1_display_detail_must_be_seen_before_absence():
    seen = []
    def fetch(req, timeout=25):
        url = req.full_url
        seen.append(url)
        if "view=display" in url:
            return Response({"ok":True,"detail":{"id":RACE,"horses":[{"horseNumber":1}],
                "massFeatureArchive":{"sha256":"unaltered"}}})
        if "/api/race/" in url:
            raise HTTPError(url, 404, "Not Found", {}, None)
        raise AssertionError("must not assume absent before checking display")
    with patch("scripts.arvexq_protect_sync.urllib.request.urlopen", side_effect=fetch):
        original = fetch_current(BASE, RACE)
    assert original["massFeatureArchive"]["sha256"] == "unaltered"
    assert len(seen) == 2


def test_mismatched_display_identity_fails_closed():
    def fetch(req, timeout=25):
        url = req.full_url
        if "view=display" in url:
            return Response({"ok":True,"detail":{"id":"another-race"}})
        raise HTTPError(url, 404, "Not Found", {}, None)
    with patch("scripts.arvexq_protect_sync.urllib.request.urlopen", side_effect=fetch):
        with pytest.raises(RuntimeError, match="mismatched race"):
            fetch_current(BASE, RACE)


def test_ambiguous_display_response_does_not_turn_into_absence():
    def fetch(req, timeout=25):
        url = req.full_url
        if "view=display" in url:
            return Response({"ok":True, "detail":None})
        raise HTTPError(url, 404, "Not Found", {}, None)
    with patch("scripts.arvexq_protect_sync.urllib.request.urlopen", side_effect=fetch):
        with pytest.raises(RuntimeError, match="no verifiable detail"):
            fetch_current(BASE, RACE)
