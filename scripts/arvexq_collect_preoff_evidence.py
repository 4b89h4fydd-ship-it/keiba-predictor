#!/usr/bin/env python3
"""Offline, append-only capture from existing race data and independently reconciled roster.

Use a protected local DB. No network access, no old forecasts and no bets.
The roster must come from a separately verified source; JSON itself cannot
prove official provenance. Importing past races is forbidden by the time gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arvexq.components.item_125.preoff_capture import capture_preoff_features
from arvexq.components.item_125.preoff_evidence_store import open_store, append_capture


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-json", type=Path, required=True)
    parser.add_argument("--official-roster-json", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    args = parser.parse_args(argv)
    race = json.loads(args.race_json.read_text(encoding="utf-8"))
    roster = json.loads(args.official_roster_json.read_text(encoding="utf-8"))
    if not isinstance(roster, dict) or roster.get("raceId") != race.get("id"):
        parser.error("roster and race identity do not match")
    numbers = roster.get("activeHorseNumbers")
    if not isinstance(numbers, list):
        parser.error("independently verified activeHorseNumbers required")
    snapshot, receipt = capture_preoff_features(race, numbers)
    with open_store(args.store) as connection:
        cid = append_capture(connection, snapshot, receipt)
    print(json.dumps({"captureId": cid, "raceId": receipt["raceId"],
                      "researchOnly": True, "store": str(args.store),
                      "modelOrMarkPublished": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
