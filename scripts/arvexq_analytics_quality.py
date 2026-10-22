#!/usr/bin/env python3
"""Read-only quality gates for ARVEXQ analytics race snapshots in MotherDuck."""
import json
import os
import duckdb

if not os.getenv("motherduck_token"):
    raise SystemExit("ANALYTICS_QUALITY_MOTHERDUCK_TOKEN_MISSING")
con=duckdb.connect("md:my_db",config={"access_mode":"READ_ONLY"})
try:
    base="my_db.arvexq_analytics.race_snapshots"
    report=con.execute(f"""
      SELECT COUNT(*) as rows, COUNT(DISTINCT race_id) as unique_ids,
             MIN(race_date)::VARCHAR AS first_day, MAX(race_date)::VARCHAR AS last_day,
             COUNT(DISTINCT race_date) AS days,
             SUM(CASE WHEN json_array_length(json_extract(snapshot_json,'$.horses')) >= 4 THEN 1 ELSE 0 END) AS adequate_fields,
             SUM(CASE WHEN json_array_length(json_extract(snapshot_json,'$.result.finishers')) >= 3 THEN 1 ELSE 0 END) AS final_results,
             SUM(CASE WHEN json_extract(snapshot_json,'$.result.payouts') IS NOT NULL THEN 1 ELSE 0 END) AS payout_fields,
             SUM(CASE WHEN sha256 IS NULL OR length(sha256)!=64 THEN 1 ELSE 0 END) AS missing_hash
      FROM {base}
    """).fetchone()
    names=["rows","unique_ids","first_day","last_day","days","adequate_fields","final_results","payout_fields","missing_hash"]
    data=dict(zip(names,report))
    data["incomplete_result_races"]=data["rows"]-data["final_results"]
    data["eligible_for_result_analysis"]=data["final_results"]
    data["ready_for_filtered_result_analysis"]=bool(
        data["rows"] and data["rows"]==data["unique_ids"]==data["adequate_fields"]
        and data["final_results"]>0 and data["missing_hash"]==0
    )
    print("ARVEXQ_ANALYTICS_DATA_QUALITY",json.dumps(data,ensure_ascii=False,default=str))
    if data["incomplete_result_races"]:
        print("::warning::Some races have no confirmed top-three finishers; exclude them from result metrics")
    if not data["ready_for_filtered_result_analysis"]:
        raise SystemExit("ANALYTICS_QUALITY_GATE_FAILED")
finally:
    con.close()
