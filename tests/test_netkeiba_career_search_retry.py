"""netkeiba verified-career provider: the first horse-search GET retries.

Regression for 2026-11-26 (Urawa 3R, ニシノトップダノン): the search
GET in ``paginated_search`` had no failure handling at all, and the
GET itself takes ~5.5s live against the adapter's per-attempt
timeout, so one transient timeout failed the whole
``netkeiba_verified_career`` provider and the horse's career
resolved to nothing.  The search GET is idempotent, so it now
retries up to two more times with short pauses; if every attempt
fails, the last error still propagates so the provider audit records
the failure instead of a silent empty result.  No other GET in the
provider is retried, and the adapter's default per-attempt timeout
rose from 6s to 10s for headroom over the measured search time.
"""
from __future__ import annotations

import unittest
from unittest import mock

from arvexq.databanks import netkeiba_career as nk

NAME = "テスト馬"
HID = "2022100001"
RACE = {"date": "2026-10-11", "circuit": "地方", "track": "大井"}

HEADERS = ["日付", "開催", "レース名", "頭 数", "着 順", "騎手", "斤量",
           "距離", "馬場", "タイム", "通過", "馬体重"]


def _row(date):
    values = [date, "1大井2", "C2", "12", "2", "テスト", "55",
              "ダ1200", "良", "1:15.5", "3-4-4-3", "480(+0)"]
    return "<tr>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>"


def _listing(count=3):
    dates = [f"2026/08/{i:02d}" for i in range(1, count + 1)]
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in HEADERS) +
            "</tr>" + "".join(_row(d) for d in dates) + "</table>")


def _search_page():
    return ('<html><head><title>' + NAME + ' (Test) | netkeiba</title>'
            '<link rel="canonical" href="https://db.netkeiba.com/horse/' +
            HID + '/" /></head></html>')


def _site(fail_search_times=0, fail_listing=False):
    calls = {"search": 0, "listing": 0}

    def get(url):
        if "pid=horse_list" in url:
            calls["search"] += 1
            if calls["search"] <= fail_search_times:
                raise TimeoutError("simulated transient search timeout")
            return _search_page()
        if url.endswith(f"/horse/result/{HID}/"):
            calls["listing"] += 1
            if fail_listing:
                raise TimeoutError("simulated listing timeout")
            return _listing(3)
        if url.endswith(f"/horse/{HID}/"):
            return "<p>通算成績 3戦</p>"
        raise AssertionError(url)

    return get, calls


class SearchGetRetryTests(unittest.TestCase):
    def test_transient_search_timeout_recovers_on_retry(self):
        get, calls = _site(fail_search_times=1)
        with mock.patch.object(nk, "time") as fake_time:
            fake_time.sleep.return_value = None
            actual = nk.fetch_verified_career(get, {"name": NAME}, RACE, 200)
        self.assertEqual(calls["search"], 2)
        self.assertEqual(actual["careerStartEvidence"]["starts"], 3)
        self.assertEqual(actual["careerStartEvidence"]["sourceHorseId"], HID)
        self.assertEqual(len(actual["allPastRuns"]), 3)

    def test_search_get_stops_after_three_attempts_and_propagates(self):
        get, calls = _site(fail_search_times=99)
        with mock.patch.object(nk, "time") as fake_time:
            fake_time.sleep.return_value = None
            with self.assertRaises(TimeoutError):
                nk.fetch_verified_career(get, {"name": NAME}, RACE, 200)
        self.assertEqual(calls["search"], nk._SEARCH_GET_ATTEMPTS)
        self.assertEqual(nk._SEARCH_GET_ATTEMPTS, 3)

    def test_successful_search_is_not_retried(self):
        get, calls = _site()
        actual = nk.fetch_verified_career(get, {"name": NAME}, RACE, 200)
        self.assertEqual(calls["search"], 1)
        self.assertEqual(actual["careerStartEvidence"]["starts"], 3)

    def test_listing_get_is_not_retried(self):
        get, calls = _site(fail_listing=True)
        with self.assertRaises(TimeoutError):
            nk.fetch_verified_career(get, {"name": NAME}, RACE, 200)
        self.assertEqual(calls["search"], 1)
        self.assertEqual(calls["listing"], 1)


class AdapterTimeoutTests(unittest.TestCase):
    def test_adapter_default_timeout_has_headroom(self):
        import os

        from arvexq.databanks import legacy_bridge

        seen = []

        def getter(url, timeout, max_age):
            seen.append(timeout)
            if "pid=horse_list" in url:
                return _search_page()
            if url.endswith(f"/horse/result/{HID}/"):
                return _listing(3)
            if url.endswith(f"/horse/{HID}/"):
                return "<p>通算成績 3戦</p>"
            raise AssertionError(url)

        fetch = legacy_bridge._netkeiba_verified_career_adapter(
            {"_netkeiba_get": getter})
        self.assertIsNotNone(fetch)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NETKEIBA_CAREER_TOTALS_TIMEOUT_SEC", None)
            fetch = legacy_bridge._netkeiba_verified_career_adapter(
                {"_netkeiba_get": getter})
            actual = fetch({"name": NAME}, RACE, 200)
        self.assertEqual(actual["careerStartEvidence"]["starts"], 3)
        self.assertTrue(seen)
        self.assertTrue(all(t == 10.0 for t in seen), seen)


if __name__ == "__main__":
    unittest.main()
