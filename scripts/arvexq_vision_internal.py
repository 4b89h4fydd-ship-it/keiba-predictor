#!/usr/bin/env python3
"""Non-UI ARVEXQ video ingestion from an explicitly authorized provider.

The optional feed is a provider-owned HTTPS JSON manifest. No public race
website is scraped. Missing feed = documented no-data state; no false success.
This job only writes research-only compact observations to a private artifact;
production prediction activation requires separate out-of-sample validation.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request

from arvexq.vision.history import compact_video_evidence, write_evidence
from arvexq.vision.video_detector import collect_video


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("cross-origin video redirects are prohibited")


def _allowed(url: str, hosts: set[str]) -> None:
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname
            or parts.username or parts.password or parts.fragment
            or parts.port not in (None, 443)
            or parts.hostname not in hosts):
        raise ValueError("provider URL must use a trusted explicitly allowed HTTPS host")


def _download(url: str, target: Path, *, hosts: set[str], token: str,
              max_bytes: int, expected_sha256: str | None = None) -> None:
    _allowed(url, hosts)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token, "User-Agent": "ARVEXQ-Vision/1"})
    opener = urllib.request.build_opener(NoRedirect())
    digest = hashlib.sha256()
    read = 0
    with opener.open(req, timeout=60) as response, target.open("wb") as out:
        while True:
            data = response.read(1024 * 1024)
            if not data:
                break
            read += len(data)
            if read > max_bytes:
                raise ValueError("provider response exceeded permitted size")
            digest.update(data)
            out.write(data)
    if read == 0:
        raise ValueError("empty provider response")
    if expected_sha256:
        if (len(expected_sha256) != 64 or
                digest.hexdigest() != expected_sha256.lower()):
            raise ValueError("download SHA256 does not match authorized manifest")


def process_internal_feed(*, feed_url: str, token: str, allowed_hosts: set[str],
                          target_date: str, output_dir: Path) -> dict:
    if not token or not allowed_hosts:
        raise ValueError("provider token and allowlist required")
    datetime.strptime(target_date, "%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arvexq-vision-") as td:
        folder = Path(td)
        feed_path = folder / "feed.json"
        _download(feed_url, feed_path, hosts=allowed_hosts, token=token,
                  max_bytes=2_000_000)
        feed = json.loads(feed_path.read_text(encoding="utf-8"))
        if not isinstance(feed, dict) or not isinstance(feed.get("jobs"), list):
            raise ValueError("authorized provider feed requires jobs array")
        jobs = feed["jobs"]
        if len(jobs) > 12:
            raise ValueError("provider batch exceeds bounded daily video quota")
        result = {"date": target_date, "totalJobs": len(jobs),
                  "processed": 0, "skippedWrongDate": 0,
                  "failed": [], "evidence": [], "forecastUpdated": False}
        for i, job in enumerate(jobs):
            try:
                if not isinstance(job, dict):
                    raise ValueError("invalid job")
                config = job.get("config")
                if not isinstance(config, dict):
                    raise ValueError("race-specific video config required")
                if config.get("raceDate") != target_date:
                    result["skippedWrongDate"] += 1
                    continue
                if config.get("rightsVerified") is not True:
                    raise ValueError("provider must attest video processing rights")
                if not config.get("autoIdentifySaddlecloth") and not config.get("verifiedIdentityMap"):
                    raise ValueError("automated OCR or verified horse identity source required")
                ids = config.get("horseIdentityByNumber") or {}
                if (not isinstance(ids, dict)
                        or any(not str(ids.get(str(no)) or "").strip()
                               for no in config.get("horseNumbers") or [])):
                    raise ValueError("stable horse IDs for every runner required to link past video")
                for name in ("videoSha256", "weightsSha256"):
                    value = str(job.get(name) or "").lower()
                    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                        raise ValueError(name + " full provider SHA256 required")
                video = folder / ("race-%02d.mp4" % i)
                weights = folder / ("detector-%02d.pt" % i)
                _download(job.get("videoUrl", ""), video, hosts=allowed_hosts, token=token,
                          max_bytes=900_000_000,
                          expected_sha256=job.get("videoSha256"))
                _download(job.get("weightsUrl", ""), weights, hosts=allowed_hosts, token=token,
                          max_bytes=300_000_000,
                          expected_sha256=job.get("weightsSha256"))
                report = collect_video(video, config, model_path=weights)
                compact = compact_video_evidence(report, config)
                saved = write_evidence(output_dir, compact)
                result["processed"] += 1
                result["evidence"].append({"raceId": compact["raceId"],
                                           "sha256": compact["videoSha256"],
                                           "evidenceFile": saved.name,
                                           "measuredHorses": len(compact["runners"])})
            except Exception as exc:
                result["failed"].append({"jobIndex": i, "raceId": str(
                    (job.get("config") or {}).get("raceId") if isinstance(job, dict) else ""),
                    "error": type(exc).__name__ + ": " + str(exc)[:140]})
        report_path = output_dir / ("batch-" + target_date + ".json")
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)
                               + "\n", encoding="utf-8")
        return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output-dir", default=".arvexq-data/vision-evidence")
    args = parser.parse_args(argv)
    url = os.getenv("ARVEXQ_VIDEO_FEED_URL", "")
    token = os.getenv("ARVEXQ_VIDEO_FEED_TOKEN", "")
    hosts = {s.strip().lower() for s in os.getenv("ARVEXQ_VIDEO_ALLOWED_HOSTS", "").split(",") if s.strip()}
    if not url:
        print(json.dumps({"status": "blocked-no-authorized-video-provider",
                          "processed": 0, "forecastUpdated": False}))
        return 2
    try:
        result = process_internal_feed(feed_url=url, token=token,
                                       allowed_hosts=hosts, target_date=args.date,
                                       output_dir=Path(args.output_dir))
    except Exception as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)[:240],
                          "processed": 0, "forecastUpdated": False}))
        return 1
    print(json.dumps({"status": ("partial" if result["failed"] else "processed"),
                      "date": args.date, "processed": result["processed"],
                      "failed": len(result["failed"]),
                      "forecastUpdated": False}, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
