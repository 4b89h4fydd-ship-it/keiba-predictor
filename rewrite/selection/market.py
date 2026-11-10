"""Append-only actual market observations. Fetch time never makes old odds fresh."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from hashlib import sha256
from html.parser import HTMLParser
import json
import math
import re
import sqlite3

JST = timezone(timedelta(hours=9))
VERSION = "arvexq-selection-market-v1"


def timestamp(value):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return t if t.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def off_time(detail):
    raw = detail.get("scheduledStartTime") or detail.get("startTime") or ""
    return timestamp(raw) if "T" in raw else timestamp(
        f"{detail.get('date')}T{str(raw)[:5]}:00+09:00")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def active_numbers(detail):
    horses = [h for h in detail.get("horses", []) if not (
        h.get("scratched") or h.get("withdrawn") or
        re.search("取消|除外|欠場", str(h.get("status", ""))))]
    numbers = [h.get("horseNumber") for h in horses]
    if (len(numbers) < 3 or len(set(numbers)) != len(numbers)
            or any(type(n) is not int or n < 1 for n in numbers)):
        raise ValueError("invalid-active-roster")
    return sorted(numbers)


def observation(detail, quotes, *, observed_at, fetched_at, source, source_url,
                source_body_sha256, kind):
    """Validate acquisition before post; original provider timestamp is retained."""
    observed, fetched, off = timestamp(observed_at), timestamp(fetched_at), off_time(detail)
    if not observed or not fetched or not off or not observed <= fetched < off:
        raise ValueError("unverified-preoff-market-time")
    if (detail.get('result') or {}).get('status') in ('確定','結果確定','finished'):
        raise ValueError('result-already-published')
    if detail.get("track") in ("帯広", "帯広ば", "帯広ばんえい"):
        raise ValueError("excluded-banei")
    roster = active_numbers(detail)
    if not source or not source_url or not re.fullmatch(r"[0-9a-f]{64}", source_body_sha256):
        raise ValueError("market-provenance-missing")
    width = {"win": 1, "place": 1, "wide": 2, "quinella": 2}.get(kind)
    if width is None:
        raise ValueError("unsupported-market-kind")
    cleaned, seen = [], set()
    for q in quotes:
        combo = tuple(sorted(q.get("combo", [])))
        low, high = q.get("oddsLow"), q.get("oddsHigh", q.get("oddsLow"))
        if (len(combo) != width or len(set(combo)) != width or combo in seen
                or any(type(n) is not int or n not in roster for n in combo)
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       for v in (low, high)) or not 1 <= low <= high
                or q.get("forecast") is True):
            raise ValueError("invalid-or-predicted-market-quote")
        seen.add(combo)
        cleaned.append({"combo": list(combo), "oddsLow": low, "oddsHigh": high})
    if not cleaned:
        raise ValueError("market-unavailable")
    uf = detail.get("unifiedForecast") or {}
    record = {"version": VERSION, "raceId": detail["id"], "raceDate": detail["date"],
              "roster": roster, "kind": kind, "observedAt": observed.isoformat(),
              "fetchedAt": fetched.isoformat(), "scheduledStartAt": off.isoformat(),
              "source": source, "sourceUrl": source_url, "sourceBodySha256": source_body_sha256,
              "forecastCapturedAt": uf.get("capturedAt"), "forecastModel": uf.get("modelVersion"),
              "forecastReceipt": uf.get("receiptSha256"),
              "forecastVectorSha256": digest(uf.get("diagnosis") or []),
              "quotes": sorted(cleaned, key=lambda q: q["combo"])}
    record["contentSha256"] = digest(record)
    return record


def open_store(path):
    db = sqlite3.connect(path)
    db.executescript("""
      CREATE TABLE IF NOT EXISTS market_observations (
        digest TEXT PRIMARY KEY, race_id TEXT NOT NULL, kind TEXT NOT NULL,
        observed_at TEXT NOT NULL, body TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS market_race ON market_observations(race_id,observed_at);
      CREATE TRIGGER IF NOT EXISTS market_no_update BEFORE UPDATE ON market_observations
      BEGIN SELECT RAISE(ABORT,'append-only market evidence'); END;
      CREATE TRIGGER IF NOT EXISTS market_no_delete BEFORE DELETE ON market_observations
      BEGIN SELECT RAISE(ABORT,'append-only market evidence'); END;
    """)
    return db


def append_observation(db, record):
    unsigned = {k: v for k, v in record.items() if k != "contentSha256"}
    if record.get("contentSha256") != digest(unsigned):
        raise ValueError("market-hash-mismatch")
    db.execute("INSERT OR IGNORE INTO market_observations VALUES (?,?,?,?,?)",
               (record["contentSha256"], record["raceId"], record["kind"],
                record["observedAt"], json.dumps(record, ensure_ascii=False, allow_nan=False)))
    db.commit()


class _TableRows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.row = None; self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.row = []
        if tag in ("td", "th"): self.cell = []

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            if self.row is not None: self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row); self.row = None


def parse_nar_wide(html):
    """Only displayed combo + odds rows; missing combinations are not filled."""
    parser = _TableRows(); parser.feed(html)
    quotes = []
    for row in parser.rows:
        if len(row) != 3 or not re.fullmatch(r"\d+\s*[-－]\s*\d+", row[0]):
            continue
        values = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[-－〜～]\s*(\d+(?:\.\d+)?)\s*", row[1])
        if values:
            quotes.append({"combo": [int(n) for n in re.findall(r"\d+", row[0])],
                           "oddsLow": float(values[1]), "oddsHigh": float(values[2])})
    return quotes
