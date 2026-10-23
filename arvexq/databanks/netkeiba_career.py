"""Verified career runs and date-bound start-count evidence from netkeiba.

This provider returns acquisition evidence and same-page historical runs,
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

SOURCE = "netkeiba_verified_career"
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


def parse_verified_runs(html: str, cutoff: str, start_dates: list[str],
                        limit: int = 1000) -> list[dict[str, Any]]:
    """Performance rows from the *same* date-verified complete results listing.

    Source totals prove starts, but a row without track or distance is not
    usable as a speed/pace observation. Never invent measurements.
    """
    end = date_key(cutoff)
    allowed = set(start_dates)
    if not end or not allowed:
        return []
    for table in _soup(html).find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        headers = [re.sub(r"\s+", "", c.get_text(" ", strip=True))
                   for c in trs[0].find_all(["th", "td"])]
        if "日付" not in headers or "着順" not in headers:
            continue
        def col(*names: str) -> int:
            return next((i for i, h in enumerate(headers)
                         if any(n == h or n in h for n in names)), -1)
        i_date, i_fin = col("日付"), col("着順")
        i_track, i_dist = col("開催"), col("距離")
        if min(i_date, i_fin, i_track, i_dist) < 0:
            return []
        i_field, i_title = col("頭数"), col("レース名")
        i_time, i_corner = col("タイム"), col("通過")
        i_weight, i_jockey = col("斤量"), col("騎手")
        i_body, i_cond = col("馬体重"), col("馬場")
        i_last3f, i_margin = col("上り", "上がり"), col("着差")
        rows = []
        for tr in trs[1:]:
            vals = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            def value(i: int) -> str:
                return vals[i].strip() if 0 <= i < len(vals) else ""
            at = date_key(value(i_date))
            if not at or at >= end or at not in allowed:
                continue
            fin = value(i_fin)
            if not (re.match(r"^\d+", fin) or fin.startswith(_NON_FINISH)):
                continue
            dm = re.search(r"(芝|ダ|障)[^0-9]*(\d{3,4})", value(i_dist))
            track = re.sub(r"^\d+|\d+$", "", value(i_track)).strip()
            if not dm or not track:
                continue
            run = {
                "date": at, "track": track, "distance": int(dm.group(2)),
                "surface": ("障害" if dm.group(1) == "障" else
                            "芝" if dm.group(1) == "芝" else "ダート"),
                "source": "netkeiba verified career listing",
                "title": value(i_title),
            }
            fm = re.match(r"^(\d+)", fin)
            if fm:
                run["finish"] = int(fm.group(1))
            else:
                run["finish"] = 0
                run["resultStatus"] = fin
            field = re.search(r"\d+", value(i_field))
            if field: run["fieldSize"] = int(field.group())
            tm = re.search(r"(?:(\d+):)?(\d{1,2})\.(\d+)", value(i_time))
            if tm:
                run["timeSeconds"] = (int(tm.group(1) or 0) * 60 +
                                      int(tm.group(2)) + int(tm.group(3)) / (10 ** len(tm.group(3))))
            positions = re.search(r"\d{1,2}(?:-\d{1,2})+", value(i_corner))
            if positions:
                run["cornerPositions"] = [int(x) for x in positions.group().split("-")]
            weight = re.search(r"\d+(?:\.\d+)?", value(i_weight))
            if weight: run["carriedWeight"] = float(weight.group())
            if value(i_jockey): run["jockey"] = value(i_jockey)
            body = re.search(r"^\d{3,4}", value(i_body))
            if body: run["bodyWeight"] = int(body.group())
            if value(i_cond): run["condition"] = value(i_cond)
            # Preserve published finishing 3F time; never invent a rank.
            last3f_text = value(i_last3f).replace("．", ".").strip()
            if re.fullmatch(r"\d{1,2}\.\d{1,2}", last3f_text):
                last3f = float(last3f_text)
                if 15.0 <= last3f <= 90.0:
                    run["last3f"] = last3f
                    run["last3fSeconds"] = last3f
            # 着差 may denote lengths (ハナ/クビ/1/2), not seconds.
            margin_text = value(i_margin)
            if margin_text and margin_text not in ("-", "--", "－"):
                run["marginText"] = margin_text
            rows.append(run)
        return sorted(rows, key=lambda r: r["date"], reverse=True)[:max(1, int(limit))]
    return []


def fetch_verified_career(get: Callable[[str], str], horse: dict[str, Any],
                          race: dict[str, Any], limit: int = 1000) -> dict[str, Any]:
    """The single prefetch source of both full observed runs and career counts."""
    name = str(horse.get("name") or horse.get("horseName") or "").strip()
    cutoff = date_key(race.get("date") or race.get("raceDate"))
    if not name or not cutoff:
        return {}
    candidates = parse_search(get(search_url(name)), name)
    born = _birth_year(horse, cutoff)
    if born:
        candidates = [c for c in candidates if c["birthYear"] == born]
    known = {r["date"] for r in merge_career(
        horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)}
    matches = []
    for cand in candidates[:4]:
        listing_html = get(f"{BASE}/horse/result/{cand['id']}/")
        listing = parse_listing(listing_html)
        if listing is None or any(not r.get("date") or r.get("kind") == "unknown" for r in listing):
            continue
        dates = sorted({r["date"] for r in listing
                        if r["kind"] != "not-started" and r["date"] < cutoff})
        if not known <= set(dates):
            continue
        # The birth year or an observed prior start must independently verify
        # this exact-name candidate before partial performance is accepted.
        runs = parse_verified_runs(listing_html, cutoff, dates, limit)
        try:
            total = parse_total(get(f"{BASE}/horse/{cand['id']}/"))
        except Exception:
            total = None
        stats = build_stats(listing, total, cutoff, cand["id"])
        if stats is None and (not runs or not (born is not None or known)):
            continue
        matches.append((stats, runs))
    if len(matches) != 1:
        return {}
    stats, runs = matches[0]
    output = {"careerStartEvidence": stats} if stats else {}
    if runs:
        output["allPastRuns"] = runs
        output["recentRaces"] = runs[:5]
    return output


def _birth_year(horse: dict[str, Any], cutoff: str) -> int | None:
    try:
        age = int(re.sub(r"\D", "", str(horse.get("age") or "")) or 0)
    except ValueError:
        return None
    # JRA/NAR calendar racing age: a 2026 three-year-old was born in 2023.
    return int(cutoff[:4]) - age if age and cutoff else None


