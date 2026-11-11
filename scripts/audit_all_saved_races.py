#!/usr/bin/env python3
"""Audit all MotherDuck races without treating postrace data as pre-off features."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

QUERY = """
SELECT race_id, CAST(race_date AS VARCHAR) AS race_date,
 json_extract_string(snapshot_json, '$.track') AS track,
 json_extract_string(snapshot_json, '$.result.status') AS result_status,
 json_exists(snapshot_json, '$.massFeatureArchive') AS has_archive,
 json_extract_string(snapshot_json, '$.massFeatureArchive.originStatus') AS archive_status,
 json_extract_string(snapshot_json, '$.massFeatureArchive.originHashVerified') AS hash_verified,
 COALESCE(json_array_length(snapshot_json->'horses'), 0) AS horse_count,
 COALESCE(json_array_length(snapshot_json->'result'->'finishers'), 0) AS finisher_count
FROM my_db.arvexq_analytics.race_snapshots
ORDER BY race_date, race_id
"""
FIELDS = ("race_id", "race_date", "track", "result_status", "has_archive",
          "archive_status", "hash_verified", "horse_count", "finisher_count",
          "bucket", "reason")

def categorize(item):
    if "帯広" in str(item["race_id"]) or item["track"] == "帯広":
        return "out_of_scope", "banei_excluded"
    if item["result_status"] != "確定" or not item["finisher_count"]:
        return "await_result", "unsettled_or_missing_finishers"
    if (item["has_archive"] and item["archive_status"] == "verified"
            and str(item["hash_verified"]).lower() == "true"):
        return "strict_export_candidate", "decoder_must_check_sha_and_complete_roster"
    if item["has_archive"]:
        return "archive_repair_review", "archive_not_origin_verified"
    return "historical_reconstruction_review", "no_verified_preoff_archive"

def audit(cursor, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    seen = set()
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        while True:
            batch = cursor.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                item = dict(zip(FIELDS[:9], row))
                if item["race_id"] in seen:
                    raise ValueError("duplicate race_id: " + str(item["race_id"]))
                seen.add(item["race_id"])
                item["bucket"], item["reason"] = categorize(item)
                counts["all_races"] += 1
                counts["horse_rows"] += int(item["horse_count"] or 0)
                counts[item["bucket"]] += 1
                writer.writerow(item)
    buckets = ("out_of_scope", "await_result", "strict_export_candidate",
               "archive_repair_review", "historical_reconstruction_review")
    if counts["all_races"] != sum(counts[b] for b in buckets):
        raise AssertionError("inventory count mismatch")
    return {"source": "my_db.arvexq_analytics.race_snapshots",
            "counts": dict(sorted(counts.items())),
            "status": "inventory_only; no training or production writes",
            "warning": "Candidate status does not certify leak-free training data."}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="md:my_db")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import duckdb
    con = duckdb.connect(args.database, read_only=True)
    try:
        result = audit(con.execute(QUERY), args.output)
    finally:
        con.close()
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
