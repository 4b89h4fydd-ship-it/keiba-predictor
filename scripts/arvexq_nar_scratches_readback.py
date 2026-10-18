"""Read-only production NAR scratch-map schema check; never writes D1."""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from arvexq.ingest.d1_day_readback import read_day

KNOWN = frozenset(("出走取消", "競走取消", "除外", "競走除外", "欠場"))


def verify(bundle):
    nar = [race for race in bundle.get("details", [])
           if str(race.get("id", "")).startswith("nar-")]
    invalid = []
    for race in nar:
        mapping = race.get("scratchMap", {})
        if not isinstance(mapping, dict):
            invalid.append({"id": race.get("id"), "scratchMap": mapping})
            continue
        for number, status in mapping.items():
            try:
                valid_number = 1 <= int(number) <= 18
            except (TypeError, ValueError):
                valid_number = False
            if not valid_number or status not in KNOWN:
                invalid.append({"id": race.get("id"), "horseNumber": number,
                                "status": status})
    expected = sum(str(row.get("id", "")).startswith("nar-")
                   for row in bundle.get("races", []))
    errors = [e for e in bundle.get("readErrors", [])
              if str(e.get("raceId", "")).startswith("nar-")]
    return {"date": bundle.get("date"), "expected": expected,
            "read": len(nar), "valid": len(nar) - len(invalid),
            "invalid": invalid, "readErrors": errors,
            "ok": expected > 0 and len(nar) == expected
                  and not invalid and not errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="https://kraiz-api.4b89h4fydd.workers.dev")
    parser.add_argument("--date", default=(datetime.now(ZoneInfo("Asia/Tokyo")).date()
                        - timedelta(days=1)).isoformat())
    args = parser.parse_args()
    import json
    report = verify(read_day(args.api_base, args.date))
    print("ARVEXQ_NAR_SCRATCH_READBACK=" + json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
