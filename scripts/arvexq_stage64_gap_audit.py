#!/usr/bin/env python3
"""Read-only recheck of NAR gaps with the existing official CSV provider."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arvexq.databanks.nar_official_csv import NarOfficialArchive, normalize, item, date
from arvexq.research.stage64.circuits import discipline


def inspect(archive, race, horse):
    key=((normalize(race["track"]),race["date"],race["raceNumber"]),horse["horseNumber"])
    entry=archive.entry_rows.get(key)
    result={"raceId":race["id"],"horseNumber":horse["horseNumber"],"name":horse["name"],
            "status":"unresolved","validPriorRuns":0,"fullCareerVerified":False}
    if entry is None:
        return {**result,"reason":"target-official-entry-missing"}
    if normalize(item(entry,6))!=normalize(horse["name"]):
        return {**result,"reason":"target-name-conflict"}
    born=date(item(entry,10))
    if not born:
        return {**result,"reason":"target-birth-missing"}
    if horse.get("sex") and item(entry,7) and normalize(horse["sex"])!=normalize(item(entry,7)):
        return {**result,"reason":"target-sex-conflict"}
    if horse.get("age") is not None and item(entry,8) and str(horse["age"])!=item(entry,8):
        return {**result,"reason":"target-age-conflict"}
    history=archive.horse_history({**horse,"birthDate":born},race).get("allPastRuns",[])
    valid=[r for r in history if r.get("birthDate")==born and r.get("date","")<race["date"]
           and discipline(r)==discipline(race) and type(r.get("finish")) is int
           and type(r.get("fieldSize")) is int and 1<=r["finish"]<=r["fieldSize"] and r["fieldSize"]>=2]
    return {**result,"officialBirthDate":born,"targetIdentityMatch":"race/date/number/name/birth/available-sex-age",
            "validPriorRuns":len(valid),
            "status":"observed-prior-evidence" if valid else "unresolved",
            "reason":"valid-history-observed" if valid else "no-valid-prior-evidence-in-supplied-archives"}


def run(official_source, input_source, gaps_path, output):
    gaps=json.loads(Path(gaps_path).read_text())
    targets={r["raceId"]:{x["horseNumber"] for x in r["blockers"] if "horseNumber" in x}
             for r in gaps}
    with tempfile.TemporaryDirectory() as td:
        files=[]
        with zipfile.ZipFile(official_source) as z:
            for info in z.infolist():
                if info.filename.startswith("official-nar/") and info.filename.endswith(".zip"):
                    p=Path(td)/Path(info.filename).name
                    p.write_bytes(z.read(info));files.append(p)
        if not files:raise ValueError("no existing official NAR archives")
        archive=NarOfficialArchive(files)
        with zipfile.ZipFile(input_source) as z:races=json.loads(z.read("forward-inputs.json"))
        observations=[inspect(archive,race,h) for race in races if race["id"] in targets
                      for h in race["horses"] if h["horseNumber"] in targets[race["id"]]]
        result={"schema":"arvexq-stage64-official-gap-recheck-1",
                "officialSourceSha256":sha256(Path(official_source).read_bytes()).hexdigest(),
                "inputSourceSha256":sha256(Path(input_source).read_bytes()).hexdigest(),
                "officialArchiveCount":len(files),"targetRaces":len(targets),"targetHorses":len(observations),
                "withValidPriorEvidence":sum(r["validPriorRuns"]>0 for r in observations),
                "observations":observations,
                "limits":["2026 supplied NAR archives only; not JRA or pre-2026 full lifetime coverage.",
                          "Recheck made after target races; no independent preoff availability claim.",
                          "Static identity uses target-date official entry; target outcomes never enter scoring.",
                          "No original input, production store or prediction was modified.",
                          "No evidence does not establish a confirmed debut."]}
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("observations","limits")},indent=2))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-source",required=True);p.add_argument("--input-source",required=True)
    p.add_argument("--gaps",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();run(a.official_source,a.input_source,a.gaps,a.output)
