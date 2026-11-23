#!/usr/bin/env python3
"""Build the live relay's asset bundle (odds-sources/ + odds-backups/ only).

Thin wrapper around the exact same generator the main build uses
(scripts/arvexq_build_odds_sources.build_sources), pointed at the relay's
own asset directory so the detached relay worker carries the verified
manifests it needs and nothing else. No new generation logic.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.arvexq_build_odds_sources import build_sources

STATIC = ROOT / "arvexq" / "ui" / "static"
OUT = ROOT / "dist-live-relay"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    build_sources(STATIC, OUT)
    files = sorted(p.name for p in OUT.glob("*/*.json"))
    print(f"live relay assets: {len(files)} files in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
