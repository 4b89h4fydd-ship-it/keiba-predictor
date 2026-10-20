#!/usr/bin/env python3
"""Wait for the existing local runtime without starting collectors or syncs."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.components.item_152.runtime_readiness import wait_ready


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid-file", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    pid = int(Path(args.pid_file).read_text().strip())
    attempts = wait_ready(args.url, pid=pid, timeout=args.timeout)
    print("ARVEXQ_RUNTIME_READY", "attempts=" + str(attempts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
