import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from arvexq_merge_morning_output import merge  # noqa: E402
from arvexq.prediction.mass_feature_transport import _feature_hash, pack_mass_detail  # noqa: E402


def _snapshot():
    snap = {"raceId": "R1", "date": "2026-10-10", "rows": [
        {"horseNumber": 1, "name": "A", "featureCount": 2, "features": {"f1": 1.0, "f2": 0.25}}]}
    snap["featureHash"] = _feature_hash(snap)
    return snap


def _payload():
    snap = _snapshot()
    detail = {"id": "R1", "date": "2026-10-10", "preRacePrediction": {"x": 1},
              "massFeatureSnapshot": snap, "massFeatureHash": snap["featureHash"],
              "volatility": {"other": 2.0}}
    return {"summaries": [{"id": "R1", "volatility": {"other": 2.0}}], "details": [detail], "meta": {}}


def _through_node(tmp_path, payload):
    src = tmp_path / "in.json"
    src.write_text(json.dumps(payload))
    out = tmp_path / "node.json"
    js = ("const fs=require('fs');const p=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
          "for(const r of [...p.summaries,...p.details]){r.morningSelected=true;"
          "r.volatility={...(r.volatility||{}),morningPicks:{selected:true}}}"
          "p.details[0].morningMarkSnapshot={version:'arvexq-morning-marks-v1'};"
          "fs.writeFileSync(process.argv[2],JSON.stringify(p))")
    subprocess.run(["node", "-e", js, str(src), str(out)], check=True)
    return json.loads(out.read_text())


def test_node_roundtrip_breaks_frozen_hash_without_merge(tmp_path):
    node = _through_node(tmp_path, _payload())
    with pytest.raises(ValueError, match="origin hash mismatch"):
        pack_mass_detail(node["details"][0])


def test_merge_keeps_python_bytes_and_morning_fields(tmp_path):
    original = _payload()
    node = _through_node(tmp_path, original)
    merged = merge(original, node)
    d = merged["details"][0]
    assert d["massFeatureSnapshot"] == original["details"][0]["massFeatureSnapshot"]
    assert isinstance(d["massFeatureSnapshot"]["rows"][0]["features"]["f1"], float)
    assert d["morningSelected"] is True
    assert d["morningMarkSnapshot"]["version"] == "arvexq-morning-marks-v1"
    assert d["volatility"] == {"other": 2.0, "morningPicks": {"selected": True}}
    assert merged["summaries"][0]["morningSelected"] is True
    packed = pack_mass_detail(d)
    assert packed["massFeatureArchive"]["originHashVerified"] is not False
