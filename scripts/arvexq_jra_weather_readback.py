"""Read-only production JRA weather check; no inference from going or results."""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from arvexq.ingest.d1_day_readback import read_day

KNOWN = frozenset(("晴", "曇", "小雨", "雨", "小雪", "雪"))


def verify(bundle):
    jra = [race for race in bundle.get("details", [])
           if str(race.get("id", "")).startswith("jra-")]
    invalid = [{"id": race.get("id"), "weather": race.get("weather")}
               for race in jra if race.get("weather") not in KNOWN]
    expected = sum(str(row.get("id", "")).startswith("jra-")
                   for row in bundle.get("races", []))
    errors = [e for e in bundle.get("readErrors", [])
              if str(e.get("raceId", "")).startswith("jra-")]
    return {"date": bundle.get("date"), "expected": expected,
            "read": len(jra), "valid": len(jra) - len(invalid),
            "missingOrInvalid": invalid, "readErrors": errors,
            "ok": expected > 0 and len(jra) == expected
                  and not invalid and not errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="https://kraiz-api.4b89h4fydd.workers.dev")
    parser.add_argument("--date", default=(datetime.now(ZoneInfo("Asia/Tokyo")).date()
                        - timedelta(days=1)).isoformat())
    args = parser.parse_args()
    import json
    report = verify(read_day(args.api_base, args.date))
    print("ARVEXQ_JRA_WEATHER_READBACK=" + json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
