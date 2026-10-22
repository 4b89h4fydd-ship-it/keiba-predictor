#!/usr/bin/env python3
"""Read-only D1 -> analytics source smoke test. Never prints race records or tokens."""
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("ARVEXQ_API_URL", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
TOKEN = os.environ.get("SYNC_TOKEN", "")
if not TOKEN:
    raise SystemExit("D1_SOURCE_PROBE_MISSING_SYNC_TOKEN")
url = BASE + "/api/admin/snapshot-export?table=race_summaries&limit=1&offset=0"
req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/json"}, method="GET")
try:
    with urllib.request.urlopen(req, timeout=30) as response:
        obj = json.loads(response.read(2_000_000))
except urllib.error.HTTPError as exc:
    raise SystemExit("D1_SOURCE_PROBE_HTTP_" + str(exc.code)) from None
except Exception as exc:
    raise SystemExit("D1_SOURCE_PROBE_ERROR_" + type(exc).__name__) from None
if obj.get("ok") is not True or obj.get("table") != "race_summaries" or not isinstance(obj.get("rows"), list):
    raise SystemExit("D1_SOURCE_PROBE_UNEXPECTED_SCHEMA")
print("D1_SNAPSHOT_EXPORT_READ_OK", "sample_row_count=" + str(len(obj["rows"])), "source_read_only=true")
