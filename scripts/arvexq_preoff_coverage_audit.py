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
    referenced = set()
    for manifest_file in sorted(root.glob("????-??-??.json")):
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if manifest.get("version") != "arvexq-saved-snapshots-v1":
            continue
        for race_id, entry in sorted((manifest.get("races") or {}).items()):
            name = str(entry.get("file") or "")
            if not name or Path(name).name != name:
                raise ValueError(f"invalid snapshot filename: {race_id}")
            file = root / name
            if not file.is_file():
                raise FileNotFoundError(f"missing archived snapshot: {race_id}: {name}")
            referenced.add(name)
            e = json.loads(file.read_text(encoding="utf-8"))
            raw = gzip.decompress(base64.b64decode(e["gzipBase64"], validate=True))
            digest = hashlib.sha256(raw).hexdigest()
            if digest != e["sha256"] or digest != entry.get("sha256"):
                raise ValueError(f"bad archived SHA256: {race_id}")
            race = json.loads(raw)
            if str(race.get("id") or "") != str(race_id):
                raise ValueError(f"archive identity mismatch: {race_id}")
            races.append(race)
    # The manifest is the immutable source of record; ignore unreferenced
    # blobs rather than silently treating them as additional saved races.
    result=audit_races(races)
    result["snapshotCount"]=len(races)
    result["provenance"]="historically archived snapshots; capture-time not uniformly authenticated"
    print("ARVEXQ_DATA_QUALITY="+json.dumps(result,ensure_ascii=False))
    Path("research-output").mkdir(exist_ok=True)
    Path("research-output/data-quality.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
