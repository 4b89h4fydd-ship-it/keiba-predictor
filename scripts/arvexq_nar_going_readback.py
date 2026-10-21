"""Read-only production NAR going check, preserving Banei moisture separately."""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from arvexq.components.item_175.d1_day_readback import read_day

KNOWN_GOING = frozenset(("良", "稍重", "重", "不良"))


def _is_banei(race):
    return "帯広" in str(race.get("track") or race.get("venue") or race.get("id") or "")


def verify(bundle):
    nar = [race for race in bundle.get("details", [])
           if str(race.get("id", "")).startswith("nar-")]
    invalid = []
    for race in nar:
        if _is_banei(race):
            moisture = race.get("goingMoisture")
            if not isinstance(moisture, str) or not moisture.strip():
                invalid.append({"id": race.get("id"), "goingMoisture": moisture})
        elif race.get("condition") not in KNOWN_GOING:
            invalid.append({"id": race.get("id"), "condition": race.get("condition")})
    expected = sum(str(row.get("id", "")).startswith("nar-")
                   for row in bundle.get("races", []))
    errors = [e for e in bundle.get("readErrors", [])
              if str(e.get("raceId", "")).startswith("nar-")]
    return {"date": bundle.get("date"), "expected": expected,
            "read": len(nar), "valid": len(nar) - len(invalid),
            "missingOrInvalid": invalid, "readErrors": errors,
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
    print("ARVEXQ_NAR_GOING_READBACK=" + json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
