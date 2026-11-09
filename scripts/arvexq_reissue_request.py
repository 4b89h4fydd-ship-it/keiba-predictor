#!/usr/bin/env python3
"""File a slim reissue request and push it (the trigger is the push).

    python3 scripts/arvexq_reissue_request.py add \
        --race nar-2026-11-09-川崎-01 --kind env-repair-upgrade \
        --reason "surface fix landed after this race was computed"
    python3 scripts/arvexq_reissue_request.py add ... --mode dry-run
    python3 scripts/arvexq_reissue_request.py list

`add` reads the CURRENT remote requests.json through the GitHub API
(never trusting a possibly stale local copy), validates the entry
with the processor's own rules, appends it, and commits just that
file to main via the PAT Git Data API with read-back verification;
the local main copy is then updated to the exact pushed bytes.
Pushing requests.json is what fires .github/workflows/
arvexq-reissue.yml. Outcomes land in
arvexq/reissue_requests/results.json (committed back by the
workflow) and are shown by `list`.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import secrets
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
REQUESTS_REPO_PATH = "arvexq/reissue_requests/requests.json"
RESULTS_REPO_PATH = "arvexq/reissue_requests/results.json"

sys.path.insert(0, str(Path.home()
                       / "workspace/custom-connectors/custom.github-pat/bin"))
import ghpat  # noqa: E402

call, OWNER, REPO, MAIN_COPY = ghpat.call, ghpat.OWNER, ghpat.REPO, \
    ghpat.MAIN_COPY


def _load_processor():
    spec = importlib.util.spec_from_file_location(
        "arvexq_reissue_process", MAIN_COPY / "scripts"
        / "arvexq_reissue_process.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fetch_remote(path: str) -> tuple[dict, str]:
    entry = call("GET", f"/repos/{OWNER}/{REPO}/contents/{path}?ref=main")
    raw = base64.b64decode(entry["content"])
    return json.loads(raw.decode("utf-8")), entry["sha"]


def _commit_file(path: str, payload: dict, message: str) -> str:
    raw = (json.dumps(payload, ensure_ascii=False, indent=1)
           + "\n").encode("utf-8")
    ref = call("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
    head_sha = ref["object"]["sha"]
    base = call("GET", f"/repos/{OWNER}/{REPO}/git/commits/{head_sha}")
    blob = call("POST", f"/repos/{OWNER}/{REPO}/git/blobs",
                {"content": base64.b64encode(raw).decode(),
                 "encoding": "base64"})
    tree = call("POST", f"/repos/{OWNER}/{REPO}/git/trees", {
        "base_tree": base["tree"]["sha"],
        "tree": [{"path": path, "mode": "100644", "type": "blob",
                  "sha": blob["sha"]}]})
    new = call("POST", f"/repos/{OWNER}/{REPO}/git/commits", {
        "message": message, "tree": tree["sha"], "parents": [head_sha]})
    call("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main",
         {"sha": new["sha"], "force": False})
    remote, _ = _fetch_remote(path)
    remote_raw = (json.dumps(remote, ensure_ascii=False, indent=1)
                  + "\n").encode("utf-8")
    if hashlib.sha256(remote_raw).hexdigest() \
            != hashlib.sha256(raw).hexdigest():
        raise RuntimeError(f"read-back mismatch for {path}")
    (MAIN_COPY / path).write_bytes(raw)
    return new["sha"]


def cmd_add(args) -> int:
    proc = _load_processor()
    doc, _ = _fetch_remote(REQUESTS_REPO_PATH)
    results, _ = _fetch_remote(RESULTS_REPO_PATH)
    now = datetime.now(JST)
    entry = {
        "request_id": (f"req-{now.strftime('%Y%m%d%H%M%S')}-"
                       f"{secrets.token_hex(3)}"),
        "race_id": args.race,
        "revision_kind": args.kind,
        "reason": args.reason,
        "mode": args.mode,
        "requested_at": now.isoformat(timespec="seconds"),
        "requested_by": "arvexq_reissue_request.py",
    }
    error = proc.validate_entry(entry)
    if error is not None:
        print(f"invalid entry: {error}", file=sys.stderr)
        return 2
    pending = []
    for existing in doc.get("requests") or []:
        if not isinstance(existing, dict):
            continue
        recorded = (results.get("results") or {}).get(
            existing.get("request_id"))
        if isinstance(recorded, dict) \
                and recorded.get("status") in proc.TERMINAL:
            continue
        if existing.get("race_id") == args.race \
                and existing.get("revision_kind") == args.kind:
            pending.append(existing.get("request_id"))
    if pending and not args.force:
        print(f"a pending request for this race/kind already exists: "
              f"{pending}; pass --force to file another",
              file=sys.stderr)
        return 2
    doc.setdefault("requests", []).append(entry)
    sha = _commit_file(
        REQUESTS_REPO_PATH, doc,
        f"data: slim reissue request {entry['request_id']} "
        f"({args.kind} for {args.race})")
    print(f"filed {entry['request_id']}: {args.kind} for {args.race} "
          f"(mode {args.mode})")
    print(f"commit {sha[:12]} — the arvexq-reissue workflow fires on "
          "this push; outcomes land in "
          "arvexq/reissue_requests/results.json")
    return 0


def cmd_list(_args) -> int:
    doc, _ = _fetch_remote(REQUESTS_REPO_PATH)
    results, _ = _fetch_remote(RESULTS_REPO_PATH)
    outcomes = results.get("results") or {}
    for entry in doc.get("requests") or []:
        if not isinstance(entry, dict):
            continue
        outcome = outcomes.get(entry.get("request_id"))
        status = outcome.get("status") if isinstance(outcome, dict) \
            else "pending"
        detail = outcome.get("detail", "") if isinstance(outcome, dict) \
            else ""
        print(f"{entry.get('request_id')}  {entry.get('race_id')}  "
              f"{entry.get('revision_kind')}  "
              f"[{entry.get('mode', 'apply')}]  {status}"
              + (f" — {detail}" if detail else ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--race", required=True)
    add.add_argument("--kind", required=True)
    add.add_argument("--reason", required=True)
    add.add_argument("--mode", choices=("apply", "dry-run"),
                     default="apply")
    add.add_argument("--force", action="store_true")
    add.set_defaults(func=cmd_add)
    lst = sub.add_parser("list")
    lst.set_defaults(func=cmd_list)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
