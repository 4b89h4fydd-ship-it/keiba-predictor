"""Read NAR's authoritative race-day change table (not the odds table).

NAR publishes scratched runners under 当日メニュー -> 変更情報, often before
odds/weight cells are populated.  Never infer a cancellation from a missing
odds quote; only explicit 取消/除外 rows are authoritative.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from bs4 import BeautifulSoup

SCRATCH_TYPES = ("競走除外", "出走取消", "競走取消", "除外", "取消", "欠場")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _type(value: str) -> str:
    value = _clean(value)
    if "除外" in value:
        return "競走除外"
    if "取消" in value:
        return "出走取消"
    if "欠場" in value:
        return "欠場"
    return ""


def parse_nar_changes(html: str) -> dict[int, dict[int, str]]:
    """Return {race_number: {horse_number: authoritative_status}}.

    A 変更情報 row is not a runner row: its first number is the RACE number
    and its second number is the HORSE number.  Do not confuse these.
    """
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    found: dict[int, dict[int, str]] = {}
    for table in soup.select("table"):
        rows = table.select("tr")
        header_index = -1
        positions: dict[str, int] = {}
        for idx, tr in enumerate(rows[:12]):
            cols = [_clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"], recursive=False)]
            keys = {k: next((i for i, value in enumerate(cols) if token in value), -1)
                    for k, token in (("race", "競走"), ("horse", "馬番"), ("status", "変更区分"))}
            if all(i >= 0 for i in keys.values()):
                header_index = idx
                positions = keys
                break
        if header_index < 0:
            continue
        for tr in rows[header_index + 1:]:
            cols = [_clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"], recursive=False)]
            if len(cols) <= max(positions.values()):
                continue
            race_cell, horse_cell, kind_cell = (cols[positions[k]] for k in ("race", "horse", "status"))
            race = re.search(r"(?<!\d)(\d{1,2})\s*(?:R|Ｒ|レース)?(?!\d)", race_cell, re.I)
            horse = re.fullmatch(r"\D*(\d{1,2})\D*", horse_cell)
            status = _type(kind_cell)
            if not race or not horse or not status:
                continue
            rn, no = int(race.group(1)), int(horse.group(1))
            if 1 <= rn <= 12 and 1 <= no <= 18:
                found.setdefault(rn, {})[no] = status
    return found


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8", "cp932", "shift_jis"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def fetch_track_changes(date: str, track: str, baba_code: str, timeout: float = 4.0) -> dict[int, dict[int, str]]:
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date) or not re.fullmatch(r"\d{2}", str(baba_code)):
        return {}
    query = urllib.parse.urlencode({
        "k_babaCode": baba_code,
        "k_raceDate": date.replace("-", "/"),
        "k_raceNo": 1,
    })
    urls = [
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList?" + query,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/RaceList_ipat?" + query,
    ]
    last_error = ""
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ARVEXQ-OfficialChanges/1)",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=timeout) as response:
                html = _decode(response.read())
            if "変更情報" in html or "変更区分" in html:
                changes = parse_nar_changes(html)
                print("OFFICIAL_CHANGES", track, date, "races=", len(changes),
                      "horses=", sum(len(h) for h in changes.values()))
                return changes
            last_error = "page has no change-table marker"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    print("OFFICIAL_CHANGES_UNAVAILABLE", track, date, last_error)
    return {}


def collect_nar_changes(date: str, tracks: dict[str, str]) -> dict[str, dict[int, str]]:
    """Fetch each venue independently; one unavailable source cannot stop others."""
    result: dict[str, dict[int, str]] = {}
    if not tracks:
        return result
    with ThreadPoolExecutor(max_workers=min(4, len(tracks))) as pool:
        futures = {pool.submit(fetch_track_changes, date, track, code): track
                   for track, code in tracks.items() if code}
        for future in as_completed(futures):
            track = futures[future]
            try:
                changes = future.result()
            except Exception as exc:
                print("OFFICIAL_CHANGES_ERROR", track, type(exc).__name__, str(exc))
                continue
            for race_no, horses in changes.items():
                result[f"nar-{date}-{track}-{race_no:02d}"] = horses
    return result
