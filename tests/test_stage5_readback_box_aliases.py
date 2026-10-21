"""Stage 5: shared readback boxes retain the original functions and contracts."""
import urllib.error

import pytest

from arvexq.ingest import d1_day_readback as original
from arvexq.components.item_160 import d1_day_readback as retry_box
from arvexq.components.item_175 import d1_day_readback as error_box


def test_readback_aliases_are_the_same_original_objects():
    assert retry_box.get_json is original.get_json
    assert retry_box.read_day is original.read_day
    assert error_box.read_day is original.read_day
    assert error_box.restore_race_response is original.restore_race_response


def test_retry_uses_existing_get_json_once_per_attempt():
    calls = []

    class Response:
        def __init__(self):
            self.unread = b'{"ok": true}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            chunk, self.unread = self.unread[:limit], self.unread[limit:]
            return chunk

    def opener(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 503, "temporary", {}, None)
        return Response()

    assert retry_box.get_json("https://example.invalid/api/day", attempts=2, opener=opener, sleeper=lambda _: None) == {"ok": True}
    assert len(calls) == 2


def test_existing_read_day_and_error_contract_no_network():
    day = "2026-10-21"
    def fetch(url):
        assert url.endswith("/api/day?date=2026-10-21&details=0")
        return {"ok": True, "date": day, "races": []}
    expected = original.read_day("https://example.invalid", day, fetch=fetch)
    assert retry_box.read_day("https://example.invalid", day, fetch=fetch) == expected
    assert error_box.read_day("https://example.invalid", day, fetch=fetch) == expected
    with pytest.raises(ValueError, match="successful object"):
        error_box.restore_race_response({"ok": False}, "id", day)
