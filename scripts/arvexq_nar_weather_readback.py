"""Read-only production NAR weather check; never writes D1.

The public API proves delivery, not the correctness of an independent provider.
Only counts an observed known weather value; absent data is a failure of coverage,
not an invitation to infer weather from going or results.
"""
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from arvexq.components.item_160.d1_day_readback import read_day

KNOWN = frozenset(("晴", "曇", "小雨", "雨", "小雪", "雪"))


def verify(bundle):
    nar = [race for race in bundle["details"]
           if str(race.get("id", "")).startswith("nar-")]
    bad = [{"id": race.get("id"), "weather": race.get("weather")}
           for race in nar if race.get("weather") not in KNOWN]
    expected = sum(str(row.get("id", "")).startswith("nar-")
                   for row in bundle.get("races", []))
    errors = [e for e in bundle.get("readErrors", [])
              if str(e.get("raceId", "")).startswith("nar-")]
    return {"date": bundle["date"], "expected": expected,
            "read": len(nar), "valid": len(nar) - len(bad),
            "missingOrInvalid": bad, "readErrors": errors,
            "ok": expected > 0 and len(nar) == expected
                  and not bad and not errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="https://kraiz-api.4b89h4fydd.workers.dev")
    parser.add_argument("--date", default=(datetime.now(ZoneInfo("Asia/Tokyo")).date()
                        - timedelta(days=1)).isoformat())
    args = parser.parse_args()
    import json
    report = verify(read_day(args.api_base, args.date))
    print("ARVEXQ_NAR_WEATHER_READBACK=" + json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
