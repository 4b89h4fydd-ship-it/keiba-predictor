#!/usr/bin/env python3
"""Shadow-only prospective forecasts from the existing verified Prefetch artifact.

No new data collection, D1 writes, production marks, tickets, or deployment.
The resulting artifact is not independently pre-off until GitHub upload and
successful workflow completion are externally witnessed before each start.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage64.circuits import circuit
from arvexq.research.stage64.protocol import check_plan, freeze_batch, post_at, JST
from arvexq.research.stage64.witness import GitHubArtifacts, read_witness, instant

INDEX = Path(__file__).resolve().parents[1] / "docs/research/stage64-results/preregistration_readback.json"
LEAD = timedelta(minutes=30)


def select_future(source, owner, plan, now):
    if now.tzinfo is None or owner not in ("jra", "nar"):
        raise ValueError("invalid circuit or naive current time")
    rows = source.get("details") if isinstance(source, dict) else None
    if not isinstance(rows, list):
        raise ValueError("saved input details missing")
    # The existing Prefetch bundle contains a day race index AND full details.
    # A partial detail fetch must not silently shrink the pre-off cohort.
    # Keep accepting detail-only test/research inputs without claiming calendar coverage.
    if "races" in source:
        listed = source["races"]
        if not isinstance(listed, list) or any(
            not isinstance(r, dict) or not isinstance(r.get("id"), str) or not r["id"]
            for r in listed
        ):
            raise ValueError("saved input race index invalid")
        if any(not isinstance(r, dict) or not isinstance(r.get("id"), str)
               or not r["id"] for r in rows):
            raise ValueError("saved input detail identity invalid")
        listed_ids = [r["id"] for r in listed]
        detail_ids = [r["id"] for r in rows]
        if (len(set(listed_ids)) != len(listed_ids)
                or len(set(detail_ids)) != len(detail_ids)
                or set(listed_ids) != set(detail_ids)):
            raise ValueError("saved input races/details identity mismatch")
    if not rows:
        # Full Prefetch explicitly emits both empty arrays when no races exist.
        # Missing details with a nonempty/unknown race roster remain a hard error.
        # Do not invent a zero-race calendar claim from this supplied artifact.
        if source.get("races") != []:
            raise ValueError("saved input details empty")
        return [], {"circuit": owner, "sourceRows": 0, "circuitRaces": 0,
                    "selected": [], "excluded": [],
                    "fullCalendarVerified": False,
                    "independentlyVerifiedPreoff": False}
    chosen, excluded, observed = [], [], set()
    for row in rows:
        rid = row.get("id") if isinstance(row, dict) else None
        try:
            owner_of_row = circuit(row)
        except (ValueError, TypeError, AttributeError):
            excluded.append({"raceId": rid, "reason": "invalid-race-identity"})
            continue
        if owner_of_row != owner:
            continue
        if rid in observed:
            raise ValueError("duplicate race identity")
        observed.add(rid)
        day = row.get("date")
        if not isinstance(day, str) or not plan["startDate"] <= day <= plan["endDate"] or rid in plan["developmentIds"]:
            excluded.append({"raceId": rid, "reason": "outside-fixed-cohort"})
            continue
        try:
            start = post_at(row)
        except (ValueError, TypeError, KeyError):
            excluded.append({"raceId": rid, "reason": "no-verified-start-time"})
            continue
        if start <= now + LEAD:
            excluded.append({"raceId": rid, "reason": "already-started-or-insufficient-lead"})
            continue
        chosen.append(row)
    chosen.sort(key=lambda r: (r["date"], r["startTime"], r["id"]))
    return chosen, {"circuit": owner, "sourceRows": len(rows), "circuitRaces": len(observed),
                    "selected": [r["id"] for r in chosen], "excluded": excluded,
                    "fullCalendarVerified": False, "independentlyVerifiedPreoff": False}


def source_artifact(client, run_id):
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("invalid prefetch run")
    run = client.run(run_id)
    if (run.get("name") != "ARVEXQ Full Prefetch" or
            run.get("head_branch") != "main" or
            run.get("status") != "completed" or run.get("conclusion") != "success"):
        raise ValueError("source not a successful main Full Prefetch")
    with urlopen(client._request(f"actions/runs/{run_id}/artifacts?per_page=100"), timeout=30) as response:
        items = json.load(response)["artifacts"]
    name = f"arvexq-stage64-source-facts-{run_id}"
    matched = [a for a in items if a["name"] == name and a.get("expired") is False
               and a.get("workflow_run", {}).get("id") == run_id]
    if len(matched) != 1:
        raise ValueError("missing/ambiguous immutable saved source artifact")
    return matched[0]["id"]


def registered_plan(client, owner, now):
    entries = json.loads(INDEX.read_text(encoding="utf-8"))["plans"]
    matches = [row for row in entries if row["circuit"] == owner]
    if len(matches) != 1:
        raise ValueError("missing/ambiguous preregistration")
    entry = matches[0]
    bundle, anchor = read_witness(client, entry["artifactId"], before=now)
    if (anchor["artifactDigest"] != entry["artifactDigest"] or
            anchor["runId"] != entry["runId"] or anchor["headSha"] != entry["headSha"]):
        raise ValueError("plan preregistration identity mismatch")
    plan = bundle["plan"]
    check_plan(plan)
    if plan["circuit"] != owner:
        raise ValueError("cross-circuit plan")
    opening = datetime.fromisoformat(plan["startDate"] + "T00:00:00").replace(tzinfo=JST)
    if instant(anchor["serverObservedBy"]) >= opening:
        raise ValueError("late plan registration")
    return plan, anchor


def capture(client, run_id, owner, output, audit):
    plan, plan_anchor = registered_plan(client, owner, datetime.now(timezone.utc))
    artifact_id = source_artifact(client, run_id)
    source, anchor = read_witness(client, artifact_id, before=datetime.now(timezone.utc),
                                  source_member="persisted-facts.json")
    if anchor["runId"] != run_id:
        raise ValueError("source artifact run mismatch")
    chosen, report = select_future(source, owner, plan, datetime.now(timezone.utc))
    report.update({"sourceRunId": run_id, "sourceArtifactId": artifact_id,
                   "sourceDigest": anchor["artifactDigest"], "planArtifactId": plan_anchor["artifactId"],
                   "status": "awaiting-upload-witness" if chosen else "no-preoff-eligible-races",
                   "productionChanged": False})
    if chosen:
        batch = freeze_batch(output, chosen, plan)
        if len(batch["cohort"]) != len(chosen):
            raise ValueError("incomplete prospective cohort")
    Path(audit).parent.mkdir(parents=True, exist_ok=True)
    Path(audit).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-run", type=int, required=True)
    p.add_argument("--circuit", choices=("jra", "nar"), required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--audit", required=True)
    a = p.parse_args()
    print(json.dumps(capture(GitHubArtifacts(), a.source_run, a.circuit, a.output, a.audit),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
