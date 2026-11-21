#!/usr/bin/env python3
"""Direct public-page collection for the nk-materials inputs that
no forward collection produced (2026-11-21 audit, items B4 / B7).

Two materials are collected here, both from netkeiba pages that are
served to any visitor (no sign-in, no saved session — this script
never touches the browser session and never attempts a login):

  --barometer   the 調子偏差値 (form deviation) table at
                race.sp.netkeiba.com/barometer/score.html — the
                per-horse 今回偏差値 becomes the builder's
                nk-judgements input (nkFormDev). JRA-side only:
                the NAR host serves no barometer page (404), so
                NAR targets are reported as skipped, never filled.
                The AI総合スコア (nkAiScore) lives on the
                ai_summary page, which netkeiba gates behind its
                Master course; it is NOT collected here (the plan
                boundary recorded 2026-11-16: master-only material
                is out of scope).

  --comments    the 厩舎コメント (stable comments) page at
                race.sp.netkeiba.com/?pid=comment — published for
                新馬戦 / 特別レース only. A race whose page has no
                comment table is recorded with "published": false
                and an empty horse map: "no comments published" is
                the correct state for such a race, not a failure.
                The public page shows only the first few horses'
                comments to signed-out visitors; the file records
                exactly what the page served, and the coverage block
                says how many horses that was. A signed-in browser
                collection writing the same file shape can supply
                the rest later — the builder merges by (race, horse
                number) either way.

Outputs land in --out-dir under the exact names the materials
builder auto-discovers next to its other inputs:

  nk-judgements.json    {"races": {<nk race_id>: {"horses":
                        {<number>: {"nkFormDev": number}}}}}
  stable-comments.json  {"races": {<nk race_id>: {"horses":
                        {<number>: {"comment": text}},
                        "published": bool}}}

A material counts as collected only when real values were parsed
and written to the file; the printed coverage is counted from the
written payload, never from pages merely fetched.

Usage:
  python3 scripts/arvexq_nk_page_collect.py --date 2026-11-22 \
      --targets <course-analysis-targets.json> \
      --out-dir <netkeiba-forward/2026-11-22> --barometer --comments
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
      "Mobile/15E148 Safari/604.1")
BAROMETER_URL = ("https://race.sp.netkeiba.com/barometer/"
                 "score.html?race_id={nk}")
COMMENT_URL = "https://race.sp.netkeiba.com/?pid=comment&race_id={nk}"


def _fetch_curl(url: str) -> str:
    """GET via curl — the route that answers reliably from the
    collection environment (the SP host drops urllib connections
    mid-body often enough to fail whole race batches)."""
    proc = subprocess.run(
        ["curl", "-sL", "--compressed", "--retry", "3",
         "--retry-all-errors", "--max-time", "45",
         "-A", UA, url],
        capture_output=True, timeout=180)
    text = proc.stdout.decode("utf-8", errors="replace")
    if len(text) <= 1000:
        raise ValueError(f"empty/short body ({len(text)} bytes)")
    return text


def _fetch_urllib(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=30) as res:
        body = res.read()
        if res.headers.get("Content-Encoding") == "gzip" \
                or body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
    text = body.decode("utf-8", errors="replace")
    if len(text) <= 1000:
        raise ValueError(f"empty/short body ({len(text)} bytes)")
    return text


def fetch(url: str, attempts: int = 4) -> str:
    """GET a public page, curl first with a urllib fallback.
    The SP host intermittently answers with an empty body or
    drops the connection mid-body; retry those, then give up
    with an exception the caller records as a failed race (never
    as empty data). A truncated body is never parsed: both
    routes raise on one and it lands here."""
    last: Exception | None = None
    for i in range(attempts):
        for route in (_fetch_curl, _fetch_urllib):
            try:
                return route(url)
            except Exception as exc:  # noqa: BLE001 - try next route
                last = exc
        time.sleep(2 + i)
    raise RuntimeError(f"fetch failed for {url}: {last}")


_DEVIATION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)")


def parse_barometer(html: str) -> dict:
    """{horse number (str): nkFormDev} from a barometer page.

    The score table's header names the 馬番 and 今回偏差値 columns;
    column positions are taken from the header, not assumed. The
    deviation cell reads like "59 (5位)" — the leading number is
    the deviation value. Rows whose cells do not parse are skipped,
    never repaired."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        header = [c.get_text(" ", strip=True)
                  for c in rows[0].find_all(["td", "th"])]
        try:
            no_idx = next(i for i, h in enumerate(header)
                          if "馬番" in h)
            dev_idx = next(i for i, h in enumerate(header)
                           if "偏差値" in h)
        except StopIteration:
            continue
        out: dict = {}
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) <= max(no_idx, dev_idx):
                continue
            no_text = cells[no_idx].get_text(" ", strip=True)
            if not re.fullmatch(r"\d{1,2}", no_text):
                continue
            m = _DEVIATION_RE.match(
                cells[dev_idx].get_text(" ", strip=True))
            if not m:
                continue
            out[no_text] = float(m.group(1))
        if out:
            return out
    return {}


def parse_stable_comments(html: str) -> dict | None:
    """{horse number (str): comment text} from a 厩舎コメント page,
    or None when the page carries no comment table at all (the
    race has no published comments — a state, not an error).

    The Stable_Comment table alternates a header row (枠 cell =
    horse number, Horse_Info cell = name / trainer) with a single-
    cell comment row. The comment text is carried verbatim."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="Stable_Comment")
    if table is None:
        return None
    out: dict = {}
    current: str | None = None
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) >= 2:
            no_text = cells[0].get_text(" ", strip=True)
            current = no_text if re.fullmatch(r"\d{1,2}", no_text) \
                else None
        elif len(cells) == 1 and current is not None:
            text = cells[0].get_text(" ", strip=True)
            if text:
                out[current] = text
            current = None
    return out


def _targets(path: str | None, race_ids: str | None) -> list:
    """[(netkeiba race_id, is_jra)] from a targets file (the
    course-analysis-targets.json shape, whose arvexq ids carry the
    circuit prefix) or a bare comma-separated id list (JRA assumed,
    as documented in the module docstring)."""
    out: list = []
    if path:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for target in payload.get("targets") or []:
            nk = str(target.get("netkeiba_race_id") or "")
            aq = str(target.get("arvexq_race_id") or "")
            if nk:
                out.append((nk, aq.startswith("jra-")))
    for nk in (race_ids or "").split(","):
        nk = nk.strip()
        if nk:
            out.append((nk, True))
    return out


def _existing_races(path: Path) -> dict:
    """Races already saved in an output file, so a re-run fills
    the races it failed on before without dropping the ones it
    collected earlier (collected data is never lost to a retry)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    races = payload.get("races") if isinstance(payload, dict) else None
    return races if isinstance(races, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--targets")
    parser.add_argument("--race-ids")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--barometer", action="store_true")
    parser.add_argument("--comments", action="store_true")
    parser.add_argument("--delay-sec", type=float, default=1.0)
    args = parser.parse_args()
    if not (args.barometer or args.comments):
        parser.error("nothing to do: pass --barometer and/or --comments")

    targets = _targets(args.targets, args.race_ids)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {}

    if args.barometer:
        races = _existing_races(out_dir / "nk-judgements.json")
        skipped_nar = failed = 0
        for nk, is_jra in targets:
            if not is_jra:
                skipped_nar += 1
                continue
            try:
                values = parse_barometer(fetch(BAROMETER_URL.format(nk=nk)))
            except Exception as exc:  # noqa: BLE001
                print(f"barometer {nk}: {exc}")
                failed += 1
                continue
            if values:
                races[nk] = {"horses": {
                    no: {"nkFormDev": v} for no, v in values.items()}}
            time.sleep(args.delay_sec)
        payload = {
            "date": args.date, "material": "nk_judgements",
            "source": "race.sp.netkeiba.com/barometer/score.html "
                      "(public page, no sign-in)",
            "races": races,
            "coverage": {
                "races": len(races),
                "horses": sum(len(r["horses"]) for r in races.values()),
                "skippedNarRaces": skipped_nar,
                "failedRaces": failed,
            },
        }
        path = out_dir / "nk-judgements.json"
        path.write_text(json.dumps(payload, ensure_ascii=False,
                                   indent=1) + "\n", encoding="utf-8")
        summary["nk-judgements"] = payload["coverage"]
        print(f"wrote {path}: {payload['coverage']}")

    if args.comments:
        races = _existing_races(out_dir / "stable-comments.json")
        failed = 0
        for nk, is_jra in targets:
            if not is_jra:
                # The NAR host serves no stable-comment page; the
                # race is recorded as unpublished only when a JRA
                # page said so. NAR races are left out entirely so
                # the file never claims a state it did not read.
                continue
            try:
                comments = parse_stable_comments(
                    fetch(COMMENT_URL.format(nk=nk)))
            except Exception as exc:  # noqa: BLE001
                print(f"comments {nk}: {exc}")
                failed += 1
                continue
            # The comment page exists for every race; one with no
            # comment rows (an empty Stable_Comment table, or no
            # table at all) has nothing published — that is the
            # correct state for a non-新馬/特別 race, recorded as
            # published: false, never as a failure.
            if comments:
                races[nk] = {
                    "horses": {no: {"comment": text}
                               for no, text in comments.items()},
                    "published": True,
                }
            else:
                races[nk] = {"horses": {}, "published": False}
            time.sleep(args.delay_sec)
        payload = {
            "date": args.date, "material": "stable_comments",
            "source": "race.sp.netkeiba.com/?pid=comment "
                      "(public page, no sign-in; signed-out view "
                      "may show only the first horses)",
            "races": races,
            "coverage": {
                "racesChecked": len(races),
                "racesPublished": sum(
                    1 for r in races.values() if r["published"]),
                "horses": sum(len(r["horses"]) for r in races.values()),
                "failedRaces": failed,
            },
        }
        path = out_dir / "stable-comments.json"
        path.write_text(json.dumps(payload, ensure_ascii=False,
                                   indent=1) + "\n", encoding="utf-8")
        summary["stable-comments"] = payload["coverage"]
        print(f"wrote {path}: {payload['coverage']}")

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
