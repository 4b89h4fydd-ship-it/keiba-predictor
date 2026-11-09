#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe for the 7 result-missing NAR races (2026-11-10).

Runs inside GitHub Actions (healthy network). For each requested
race: fetches the official keiba.go.jp RaceMarkTable (both variants
app.py uses) and the nar.netkeiba.com result page; records status /
length / content flags, extracts the netkeiba result-table rows and
payout rows as text, and writes everything to
arvexq/nar_missing_probe_requests/results/ for commit-back.
Read-only against the web; writes only its own results directory.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402  (production parsers / code maps)

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
      "Mobile/15E148 Safari/604.1")
OUT = ROOT / "arvexq" / "nar_missing_probe_requests" / "results"


def fetch(url: str, timeout: float = 25.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja-JP,ja;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, app._jra_decode(res.read())
    except Exception as exc:  # noqa: BLE001
        return 0, f"ERROR {type(exc).__name__}: {exc}"


def table_texts(html: str) -> list[str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True)
                     for c in tr.find_all(["th", "td"], recursive=False)]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            out.append("\n".join(rows))
    return out


def main() -> int:
    req = json.loads((ROOT / "arvexq" / "nar_missing_probe_requests"
                      / "requests.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for race in req["races"]:
        rid = race["id"]
        date = race["date"]
        track = race["track"]
        no = int(race["raceNumber"])
        entry: dict = {"id": rid}
        code = app.NAR_BABA_CODES.get(track)
        q = (f"k_babaCode={code}&k_raceDate={date.replace('-', '/')}"
             f"&k_raceNo={no}")
        for label, url in (
            ("official", "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?" + q),
            ("official_ipat", "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/RaceMarkTable_ipat?" + q),
        ):
            status, html = fetch(url)
            entry[label] = {
                "status": status, "length": len(html),
                "has_result_table": ("着順" in html and "馬体重" in html),
                "no_info": "情報がありません" in html,
            }
        nk_id = app._nar_netkeiba_race_id(date, track, no)
        entry["netkeiba_race_id"] = nk_id
        status, html = fetch(
            f"https://nar.netkeiba.com/race/result.html?race_id={nk_id}")
        entry["netkeiba"] = {
            "status": status, "length": len(html),
            "has_result_table": ("着順" in html),
            "no_data": ("データがありません" in html
                        or "レース結果はありません" in html),
        }
        if status and len(html) > 2000:
            tables = table_texts(html)
            (OUT / f"{rid}.tables.txt").write_text(
                "\n\n==== TABLE ====\n\n".join(tables), encoding="utf-8")
            entry["netkeiba_tables"] = len(tables)
        summary[rid] = entry
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
