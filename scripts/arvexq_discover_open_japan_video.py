#!/usr/bin/env python3
"""Find Japanese flat/jump horse-racing VIDEO metadata with explicit CC terms.

This is a source-catalog audit, not a downloader or rights clearance.
Wikimedia Commons category membership and licenses can change; the candidate
still requires independent assessment of racing venue, original authorship,
commercial reuse rights and actual race footage before any AI ingestion.
Ban'ei/Obihiro video is categorically EXCLUDED from ARVEXQ.
"""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API = "https://commons.wikimedia.org/w/api.php"
VERSION = "arvexq-japanese-open-video-source-audit-v1"
ROOTS = (
    "Category:Horse racing in Japan",
    "Category:Horseraces in Japan",
    "Category:Horseraces at Tokyo Racecourse",
    "Category:Sonoda Racecourse",
    "Category:Steeplechase in Japan",
)
BAD_TERMS = ("obihiro", "ban ei", "ban-ei", "ban'ei", "banei",
             "帯広", "ばんえい", "輓曳", "ばん馬")
VIDEO_SUFFIX = re.compile(r"\.(?:webm|ogv|ogg|mp4|mov|mkv)$", re.I)
CC_LICENSE = re.compile(r"^CC BY(?:-SA)? [234]\.0$", re.I)


def _bad(title: str) -> bool:
    flat = title.lower().replace("_", " ").replace("‐", "-").replace("’", "'")
    return any(bad in flat for bad in BAD_TERMS)


def _clean(value: object) -> str:
    raw = value.get("value", "") if isinstance(value, dict) else value
    return html.unescape(re.sub(r"<[^>]+>", "", str(raw or ""))).strip()[:500]


def _license(metadata: dict) -> tuple[str, str, str, bool]:
    short = _clean(metadata.get("LicenseShortName"))
    link = _clean(metadata.get("LicenseUrl"))
    artist = _clean(metadata.get("Artist"))
    u = urlsplit(link)
    if u.scheme != "https" or u.hostname not in ("creativecommons.org", "www.creativecommons.org"):
        return short, link, artist, False
    prefix = "/licenses/by-sa/" if "BY-SA" in short.upper() else "/licenses/by/"
    valid = CC_LICENSE.fullmatch(short) is not None and u.path.startswith(prefix)
    # Metadata alone does not independently verify commercial venue footage.
    return short, link, artist, valid


_LAST_API_CALL = 0.0


def commons_api(params: dict) -> dict:
    """Rate-limited Wikimedia API reader with bounded 429/5xx retries."""
    global _LAST_API_CALL
    query = urlencode({"action": "query", "format": "json",
                       "formatversion": "2", **params})
    req = Request(API + "?" + query, headers={
        "User-Agent": "ARVEXQ-source-audit/1.0 (https://github.com/4b89h4fydd-ship-it/keiba-predictor)",
        "Accept": "application/json"})
    for attempt in range(5):
        # Commons is a volunteer-hosted site. Avoid request bursts in CI.
        gap = time.monotonic() - _LAST_API_CALL
        if gap < 1.0:
            time.sleep(1.0 - gap)
        _LAST_API_CALL = time.monotonic()
        try:
            with urlopen(req, timeout=25) as response:
                if (hasattr(response, "geturl")
                        and urlsplit(response.geturl()).hostname != "commons.wikimedia.org"):
                    raise ValueError("Wikimedia API unexpected redirect")
                body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise ValueError("Wikimedia API oversized response")
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict) or data.get("error"):
                raise ValueError("Wikimedia API returned an error")
            return data
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            delay = [3, 6, 12, 18][attempt]
            requested = exc.headers.get("Retry-After") if exc.headers else None
            if requested is not None:
                try:
                    delay = max(delay, min(30, int(requested)))
                except ValueError:
                    pass
            time.sleep(delay)
    raise ValueError("Wikimedia retry budget exhausted")


def _info(client, title: str) -> dict | None:
    payload = client({"prop": "imageinfo", "titles": title,
                      "iiprop": "mime|extmetadata|url"})
    for page in (payload.get("query") or {}).get("pages") or []:
        for info in page.get("imageinfo") or []:
            if not str(info.get("mime") or "").lower().startswith("video/"):
                continue
            media_url = info.get("url") or ""
            parts = urlsplit(media_url)
            if parts.scheme != "https" or parts.hostname != "upload.wikimedia.org":
                return None
            license_name, license_url, artist, cc_candidate = _license(info.get("extmetadata") or {})
            return {
                "file": title, "descriptionPage": "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_"),
                "videoUrl": media_url, "mime": info["mime"],
                "artist": artist, "license": license_name, "licenseUrl": license_url,
                "commonsCcMetadataCandidate": cc_candidate,
                "racecourseAndAuthorPermissionsIndependentlyReviewed": False,
                "jraNarFlatOrJumpIndependentlyConfirmed": False,
                "eligibleForProductionIngestion": False,
            }
    return None


def discover(*, client=commons_api, max_categories: int = 20,
             max_items: int = 1500) -> dict:
    if not 1 <= max_categories <= 200 or not 1 <= max_items <= 10_000:
        raise ValueError("bounded crawl budgets required")
    queue = deque((root, 0) for root in ROOTS)
    seen, file_seen = set(), set()
    candidates, skipped_banei, errors = [], 0, []
    inspected_files = 0
    limit_hit = False
    while queue:
        if len(seen) >= max_categories or inspected_files >= max_items:
            limit_hit = True
            break
        category, depth = queue.popleft()
        if category in seen or _bad(category):
            continue
        seen.add(category)
        continuation = None
        while True:
            try:
                params = {"list": "categorymembers", "cmtitle": category,
                          "cmtype": "file|subcat", "cmlimit": "100"}
                if continuation:
                    params["cmcontinue"] = continuation
                data = client(params)
                items = (data.get("query") or {}).get("categorymembers") or []
                if not isinstance(items, list):
                    raise ValueError("bad Wikimedia category response")
                for item in items:
                    title = str(item.get("title") or "")
                    namespace = item.get("ns")
                    if _bad(title):
                        if VIDEO_SUFFIX.search(title):
                            skipped_banei += 1
                        continue
                    if namespace == 14 and depth < 2 and not _bad(title):
                        queue.append((title, depth + 1))
                    elif namespace == 6 and title not in file_seen:
                        if inspected_files >= max_items:
                            limit_hit = True
                            break
                        inspected_files += 1
                        file_seen.add(title)
                        if VIDEO_SUFFIX.search(title):
                            try:
                                fact = _info(client, title)
                                if fact:
                                    # One source file may have multiple category references.
                                    fact["foundInCategory"] = category
                                    candidates.append(fact)
                            except Exception as exc:
                                errors.append({"category": category, "file": title,
                                               "reason": type(exc).__name__})
                if limit_hit:
                    break
                continuation = (data.get("continue") or {}).get("cmcontinue")
                if not continuation:
                    break
            except Exception as exc:
                errors.append({"category": category, "reason": type(exc).__name__,
                               "httpStatus": getattr(exc, "code", None)})
                break
        if limit_hit:
            break
    candidates.sort(key=lambda row: row["file"])
    cc = sum(c["commonsCcMetadataCandidate"] for c in candidates)
    return {
        "version": VERSION,
        "auditedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": "Wikimedia Commons categorymembers/imageinfo read-only API",
        "rootCategories": list(ROOTS),
        "visitedCategories": len(seen),
        "inspectedCategoryFiles": inspected_files,
        "excludedObihiroBaneiVideoMentions": skipped_banei,
        "metadataVideoCandidates": len(candidates),
        "ccMetadataCandidates": cc,
        "candidates": candidates,
        "crawlTruncated": limit_hit,
        "errors": errors,
        "rightsClearedForProduction": False,
        "raceVideoActuallyDownloaded": False,
        "fullHorseTrackingPerformed": False,
        "forecastChanged": False,
        "status": ("incomplete-source-audit" if limit_hit or errors
                   else "metadata-candidates-await-rights-review" if candidates
                   else "no-eligible-japanese-flat-jump-video-found-in-scanned-categories"),
        "caveat": "Not exhaustive across Wikimedia/Internet. CC metadata is not a venue-use clearance."
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path,
                   default=Path(".arvexq-data/japan-video-source-audit.json"))
    p.add_argument("--max-categories", type=int, default=20)
    p.add_argument("--max-items", type=int, default=1500)
    args = p.parse_args(argv)
    report = discover(max_categories=args.max_categories, max_items=args.max_items)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("status", "visitedCategories", "inspectedCategoryFiles",
                       "excludedObihiroBaneiVideoMentions", "metadataVideoCandidates",
                       "ccMetadataCandidates", "crawlTruncated", "errors")},
                     ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
