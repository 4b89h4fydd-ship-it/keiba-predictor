"""Career start-count evidence from the netkeiba horse database.

This provider returns *only* acquisition evidence (``careerStartEvidence``), never runs,
so prediction inputs are unchanged.  Evidence is emitted only when:

* the horse identity is unambiguous (exact name, and known pre-race start
  dates / birth year agree), and
* the source's own career total ("通算成績 N戦") equals the number of starts
  listed in its results table, i.e. the listing itself is proven complete.

The pre-race start dates are then derived from that complete listing, so the
total is bound to the target race date rather than to the fetch date.
"""
from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable
from typing import Any

from bs4 import BeautifulSoup

from arvexq.ingest.full_career import date_key, merge_career

SOURCE = "netkeiba_career_totals"
BASE = "https://db.netkeiba.com"
_ID = re.compile(r"db\.netkeiba\.com/+horse/(\d{10})/")
_NOT_STARTED = ("取", "除")          # 出走取消・競走除外: not a start
_NON_FINISH = ("中", "失")           # 競走中止・失格: a start without a placing


def search_url(name: str) -> str:
    # netkeiba expects EUC-JP query bytes; UTF-8 returns an empty result page.
    return BASE + "/?" + urllib.parse.urlencode({"pid": "horse_list", "word": name}, encoding="euc-jp")


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "html.parser")


def parse_search(html: str, name: str) -> list[dict[str, Any]]:
    """Exact-name candidates from a search page, or the horse page itself."""
    s = _soup(html)
    canonical = s.find("link", rel="canonical")
    href = canonical.get("href") if canonical else ""
    m = _ID.search(str(href or ""))
    if m:  # unique hits redirect straight to the horse page
        title = s.title.get_text(" ", strip=True) if s.title else ""
        if title.split(" ")[0].strip() == name:
            return [{"id": m.group(1), "birthYear": int(m.group(1)[:4])}]
        return []
    out: list[dict[str, Any]] = []
    for tr in s.find_all("tr"):
        link = tr.find("a", href=_ID)
        if not link or link.get_text(strip=True) != name:
            continue
        hid = _ID.search(link["href"]).group(1)
        if all(c["id"] != hid for c in out):
            out.append({"id": hid, "birthYear": int(hid[:4])})
    return out


def parse_total(html: str) -> int | None:
    text = _soup(html).get_text(" ", strip=True)
    m = re.search(r"通算成績\s*(\d+)\s*戦", text)
    return int(m.group(1)) if m else None


def parse_listing(html: str) -> list[dict[str, Any]] | None:
    """Every row of the results table. None when the table cannot be read."""
    for table in _soup(html).find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        headers = [re.sub(r"\s+", "", c.get_text(" ", strip=True)) for c in trs[0].find_all(["th", "td"])]
        if "日付" not in headers or "着順" not in headers:
            continue
        i_date, i_fin = headers.index("日付"), headers.index("着順")
        rows = []
        for tr in trs[1:]:
            vals = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(vals) <= max(i_date, i_fin):
                continue
            at = date_key(vals[i_date])
            fin = vals[i_fin].strip()
            if re.match(r"^\d+", fin):
                kind = "finished"
            elif fin.startswith(_NOT_STARTED):
                kind = "not-started"
            elif fin.startswith(_NON_FINISH):
                kind = "non-finish"
            else:
                kind = "unknown"
            rows.append({"date": at, "kind": kind})
        return rows
    return None


def build_stats(listing: list[dict[str, Any]] | None, total: int | None,
                cutoff: str, horse_id: str) -> dict[str, Any] | None:
    end = date_key(cutoff)
    if listing is None or total is None or not end:
        return None
    if any(r["kind"] == "unknown" or not r["date"] for r in listing):
        return None
    starts = [r for r in listing if r["kind"] != "not-started"]
    if len(starts) != total or len({r["date"] for r in starts}) != len(starts):
        return None
    pre = sorted(r["date"] for r in starts if r["date"] < end)
    return {
        "starts": len(pre),
        "asOfRaceDate": end,
        "startDates": pre,
        "nonFinishStarts": sum(r["kind"] == "non-finish" and r["date"] < end for r in starts),
        "source": SOURCE,
        "sourceHorseId": horse_id,
        "basis": "source-total-equals-listed-starts",
        "sourceTotalStarts": total,
        "listedStarts": len(starts),
    }


def _birth_year(horse: dict[str, Any], cutoff: str) -> int | None:
    try:
        age = int(re.sub(r"\D", "", str(horse.get("age") or "")) or 0)
    except ValueError:
        return None
    return int(cutoff[:4]) - age if age and cutoff else None


def fetch_career_totals(get: Callable[[str], str], horse: dict[str, Any],
                        race: dict[str, Any]) -> dict[str, Any]:
    name = str(horse.get("name") or horse.get("horseName") or "").strip()
    cutoff = date_key(race.get("date") or race.get("raceDate"))
    if not name or not cutoff:
        return {}
    candidates = parse_search(get(search_url(name)), name)
    born = _birth_year(horse, cutoff)
    if born:
        candidates = [c for c in candidates if c["birthYear"] == born]
    known = {r["date"] for r in merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)}
    matches = []
    for cand in candidates[:4]:
        stats = build_stats(parse_listing(get(f"{BASE}/horse/result/{cand['id']}/")),
                            parse_total(get(f"{BASE}/horse/{cand['id']}/")), cutoff, cand["id"])
        if stats is not None and known <= set(stats["startDates"]):
            matches.append(stats)
    # Ambiguous identity is not evidence.
    return {"careerStartEvidence": matches[0]} if len(matches) == 1 else {}
