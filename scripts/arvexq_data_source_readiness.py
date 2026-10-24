"""Report ACTUALLY available ARVEXQ source inputs; no network or database writes.

This is a read-only readiness check of existing configurations. A reference
catalog entry is never an enabled provider, and a file on disk is never proof
of distribution rights. Missing assets are reported rather than invented.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from arvexq.databanks.source_catalog import discovery_inventory


def audit(env=None, archive_dir=None):
    env = dict(os.environ if env is None else env)
    configured = [x for x in env.get("ARVEXQ_NAR_OFFICIAL_CSV_ARCHIVES", "").split(os.pathsep) if x]
    found = set()
    for name in configured:
        path = Path(name)
        if path.is_file() and path.suffix.lower() == ".zip":
            found.add(path)
        elif path.is_dir():
            found.update(x for x in path.glob("*.zip") if x.is_file())
    if archive_dir:
        folder = Path(archive_dir)
        if folder.is_dir():
            found.update(x for x in folder.glob("*.zip") if x.is_file())
    nar_races = [p for p in found if re.fullmatch(
        r"(?:\d{6}|\d{8})(?:_\d+)?_race[.]zip|daily_race[.]zip", p.name, re.IGNORECASE)]
    nar_daily_odds = [p for p in found if re.fullmatch(
        r"\d{8}_\d{9,11}_odds[.]zip", p.name, re.IGNORECASE)]
    nar_final_odds = [p for p in found if re.fullmatch(
        r"\d{6}(?:_\d+)?_odds[.]zip", p.name, re.IGNORECASE)]
    inventory = discovery_inventory()
    return {
        "candidateSources": len(inventory),
        "candidateSourcesAreNotConnected": True,
        "centralSourceCandidates": sum(x["circuit"] in ("JRA", "both") for x in inventory),
        "localSourceCandidates": sum(x["circuit"] in ("NAR", "both") and x["id"]!="banei_official" for x in inventory),
        "localArchivePathsConfigured": len(configured),
        "localArchivePathsMissing": [p for p in configured if not Path(p).exists()],
        "localZipFilesFound": len(found),
        "localRaceZips": len(nar_races),
        "localDailyPreoffOddsZips": len(nar_daily_odds),
        "localFinalOddsZipsNotEligibleForPreoff": len(nar_final_odds),
        "videoVerified": False,
        "sourceAuthorizationVerified": False,
        "status": "inputs-observed-only-no-commercial-rights-or-history-coverage-claim",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive-dir", default="")
    args = p.parse_args()
    print("ARVEXQ_SOURCE_READINESS", json.dumps(audit(archive_dir=args.archive_dir),
          sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
