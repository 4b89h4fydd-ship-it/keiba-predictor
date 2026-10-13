#!/usr/bin/env python3
"""Audit archived inputs without rewriting results or predictions."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from arvexq.research.preoff_coverage_audit import audit_races


def main():
    root=Path("arvexq/ui/static/saved-snapshots")
    races=[]
    for file in sorted(root.glob("*.json")):
        e=json.loads(file.read_text())
        if "gzipBase64" not in e:
            continue
        raw=gzip.decompress(base64.b64decode(e["gzipBase64"],validate=True))
        if hashlib.sha256(raw).hexdigest()!=e["sha256"]:
            raise ValueError("bad archived SHA256")
        races.append(json.loads(raw))
    result=audit_races(races)
    result["snapshotCount"]=len(races)
    result["provenance"]="historically archived snapshots; capture-time not uniformly authenticated"
    print("ARVEXQ_DATA_QUALITY="+json.dumps(result,ensure_ascii=False))
    Path("research-output").mkdir(exist_ok=True)
    Path("research-output/data-quality.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
