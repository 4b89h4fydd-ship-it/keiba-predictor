#!/usr/bin/env python3
"""Read-only ARVEXQ research commands; never re-create missing past predictions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arvexq.verification.trust_report import build_trust_report
from arvexq.vision.observations import analyze_tracking


def main(argv=None):
    parser = argparse.ArgumentParser(description="ARVEXQ auditable prediction research")
    sub = parser.add_subparsers(dest="command", required=True)

    history = sub.add_parser("history", help="audit frozen predictions and official results")
    history.add_argument("--races", type=Path, required=True, help="JSON array of complete race details")
    history.add_argument("--output", type=Path, required=True)

    video = sub.add_parser("tracking", help="measure already identified video ground-plane observations")
    video.add_argument("--manifest", type=Path, required=True)
    video.add_argument("--roster", type=Path, required=True, help="JSON array of horse numbers")
    video.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "history":
        data = json.loads(args.races.read_text(encoding="utf-8"))
        output = build_trust_report(data)
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        roster = json.loads(args.roster.read_text(encoding="utf-8"))
        output = analyze_tracking(manifest, roster)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False,
                                      sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"command": args.command, "version": output["version"],
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
