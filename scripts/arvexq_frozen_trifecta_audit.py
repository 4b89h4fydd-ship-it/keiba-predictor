"""Audit only frozen before-off trifecta tickets against official finishing order."""
import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def positive(value):
    try:
        n = int(value)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None

def evaluate(detail):
    bet = detail.get("preRaceBet") or {}
    result = detail.get("result") or {}
    if not isinstance(bet, dict) or not isinstance(result, dict):
        return "missing_record", None
    if bet.get("captureStatus") in ("failed", "engine-missing"):
        return "failed_capture", None
    if not bet.get("fixedAt"):
        return "missing_lock_time", None
    if bet.get("raceId") != detail.get("id"):
        return "race_identity_mismatch", None
    try:
        lock = datetime.fromisoformat(bet["fixedAt"].replace("Z", "+00:00"))
        start = datetime.fromisoformat(str(detail["date"]) + "T" + str(detail.get("scheduledStartTime") or detail.get("startTime") or "")[:5] + ":00+09:00")
        if lock.tzinfo is None or lock >= start:
            return "not_proven_preoff", None
    except (ValueError, TypeError, KeyError):
        return "unverifiable_off_time", None
    if result.get("status") not in ("確定", "official", "final") and detail.get("raceStatus") != "確定":
        return "unofficial_result", None
    positions = {}
    for row in result.get("finishers") or []:
        if not isinstance(row, dict):
            continue
        rank, no = positive(row.get("finish")), positive(row.get("horseNumber"))
        if rank in (1, 2, 3) and no is not None:
            if rank in positions:
                return "ambiguous_finish", None
            positions[rank] = no
    if len(positions) != 3 or len(set(positions.values())) != 3:
        return "incomplete_finish", None
    tickets = []
    for item in bet.get("items") or []:
        if isinstance(item, dict) and item.get("kind") == "3連単":
            for raw in item.get("combos") or []:
                if not isinstance(raw, list) or len(raw) != 3:
                    return "malformed_ticket", None
                combo = tuple(positive(x) for x in raw)
                if None in combo or len(set(combo)) != 3:
                    return "malformed_ticket", None
                tickets.append(combo)
    if not tickets:
        return "no_trifecta_ticket", None
    if len(tickets) != len(set(tickets)):
        return "duplicate_tickets", None
    if len(tickets) > 10:
        return "over_ten_tickets", None
    return "evaluated", {"hit": tuple(positions[x] for x in (1, 2, 3)) in set(tickets), "points": len(tickets), "circuit": detail.get("circuit") or "unknown"}

def summarize(details):
    coverage = Counter()
    groups = defaultdict(lambda: {"races": 0, "hits": 0, "points": 0})
    seen = set()
    for detail in details:
        if not isinstance(detail, dict):
            coverage["malformed_detail"] += 1
            continue
        rid = str(detail.get("id") or "")
        if not rid or rid in seen:
            coverage["missing_or_duplicate_id"] += 1
            continue
        seen.add(rid)
        status, record = evaluate(detail)
        coverage[status] += 1
        if record:
            group = groups[str(record["circuit"])]
            group["races"] += 1
            group["hits"] += int(record["hit"])
            group["points"] += record["points"]
    return {"coverage": dict(coverage), "byCircuit": {k: {**v, "observedHitRate": v["hits"]/v["races"], "averagePoints": v["points"]/v["races"]} for k,v in groups.items()}}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON with details array")
    parser.add_argument("--api-base", default="https://kraiz-api.4b89h4fydd.workers.dev")
    parser.add_argument("--end-date", default=(date.today()-timedelta(days=1)).isoformat())
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error("days must be 1..90")
    if args.input:
        with open(args.input, encoding="utf-8") as file:
            details = json.load(file)["details"]
    else:
        details = []
        end = date.fromisoformat(args.end_date)
        for offset in range(args.days):
            day = (end-timedelta(days=offset)).isoformat()
            url = args.api_base.rstrip("/") + "/api/day?" + urlencode({"date": day, "details": "1"})
            with urlopen(Request(url, headers={"User-Agent": "ARVEXQ-frozen-trifecta-audit/1"}), timeout=45) as response:
                payload = json.load(response)
            details.extend(payload.get("details") or [])
    report = {"version":"frozen-trifecta-audit-v1","periodEnd":args.end_date,"daysRequested":args.days,"totalDetails":len(details),**summarize(details)}
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
