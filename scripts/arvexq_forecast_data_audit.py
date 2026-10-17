"""Read-only audit of checked-in ARVEXQ facts vs trainable pre-off evidence.

Never reconstruct training features from post-race details. The audit only
reports coverage and does not claim time-provenance from a stored JSON body.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import base64
import gzip
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1] / "arvexq/ui/static"


def _read_snapshot(path):
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    if "gzipBase64" not in wrapper:
        return wrapper
    raw = gzip.decompress(base64.b64decode(wrapper["gzipBase64"]))
    if wrapper.get("sha256") and hashlib.sha256(raw).hexdigest() != wrapper["sha256"]:
        raise ValueError("saved snapshot sha256 mismatch")
    return json.loads(raw)


def audit_date(day):
    result = {"date": day, "staticRacecards": {}, "savedSnapshots": {}}
    path = ROOT / "racecards" / (day + ".json")
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        cards = data.get("races") or []
        horses = [h for r in cards for h in r.get("horses") or [] if isinstance(h, dict)]
        result["staticRacecards"] = {
            "races": len(cards), "horses": len(horses),
            "horsesWithPastRuns": sum(bool(h.get("allPastRuns") or h.get("recentRaces")) for h in horses),
            "frozenFeatureRaces": sum(bool(r.get("massFeatureSnapshot")) for r in cards),
            "circuits": dict(Counter(str(r.get("circuit")) for r in cards)),
        }
    manifest = ROOT / "saved-snapshots" / (day + ".json")
    if manifest.exists():
        index = json.loads(manifest.read_text(encoding="utf-8")).get("races") or {}
        stats = Counter()
        examples = []
        for rid, item in index.items():
            stats["listed"] += 1
            try:
                detail = _read_snapshot(ROOT / "saved-snapshots" / item["file"])
                if not isinstance(detail, dict):
                    raise ValueError("not a JSON race mapping")
                horses = detail.get("horses") or []
                stats["decoded"] += 1
                stats["horses"] += len(horses)
                stats["horsesWithPastRuns"] += sum(bool(
                    h.get("allPastRuns") or h.get("recentRaces")) for h in horses if isinstance(h, dict))
                stats["racesWithFrozenFeatures"] += int(bool(detail.get("massFeatureSnapshot")))
                stats["racesWithArchivedFeatures"] += int(bool(detail.get("massFeatureArchive")))
                stats["racesWithFinalResult"] += int(
                    isinstance(detail.get("result"), dict)
                    and str(detail["result"].get("status") or "") == "確定")
                stats["racesWithIndependentPreoffReceipt"] += int(
                    isinstance(detail.get("preoffAcquisitionReceipt"), dict))
                if len(examples) < 2:
                    examples.append({"raceId": rid, "fields": sorted(detail.keys())[:30]})
            except (OSError, ValueError, TypeError, KeyError, gzip.BadGzipFile):
                stats["readErrors"] += 1
        result["savedSnapshots"] = {**dict(stats), "examples": examples}
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("dates", nargs="*", default=["2026-10-17", "2026-10-18"])
    args = parser.parse_args()
    print(json.dumps([audit_date(d) for d in args.dates],
                     ensure_ascii=False, indent=2, sort_keys=True))
