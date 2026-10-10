"""Publish a tiny factual racecard-only backup independently of full D1 writes.

No odds, AI marks, predictions, results or post-off changes are published.
An existing racecard's original runners are immutable; later runs can only add
previously missing race IDs with verified runner names, never erase starts.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

HORSE_FIELDS = ("horseNumber","frameNumber","name","sex","age","jockey",
                "carriedWeight","weight","trainer","sexAge")
RACE_FIELDS = ("id","date","circuit","track","raceNumber","title","distance",
               "surface","startTime","scheduledStartTime","fieldSize")


def racecard_manifest(payload: dict[str, Any]) -> dict[str, Any] | None:
    summaries = [r for r in payload.get("summaries") or [] if isinstance(r,dict) and r.get("id")]
    if not summaries:
        return None
    days = {str(r.get("date") or "") for r in summaries}
    if len(days) != 1:
        return None
    date=next(iter(days))
    if not re.fullmatch(r"\d{4}-\d\d-\d\d",date):
        return None
    by_id = {str(r["id"]):r for r in summaries}
    cards=[]
    for d in payload.get("details") or []:
        if not isinstance(d,dict):
            continue
        rid=str(d.get("id") or "")
        if rid not in by_id:
            continue
        race=by_id[rid]
        if str(d.get("date") or race.get("date") or "")!=date:
            continue
        candidates=d.get("horses") or []
        if not isinstance(candidates,list):
            continue
        horses=[]
        numbers=set()
        for h in candidates:
            if not isinstance(h,dict):
                continue
            try:
                no=int(h.get("horseNumber") or 0)
            except (TypeError,ValueError):
                continue
            name=str(h.get("name") or "").strip()
            if no <= 0 or not name or no in numbers:
                continue
            numbers.add(no)
            horses.append({k:h[k] for k in HORSE_FIELDS if h.get(k) not in ("",None)})
        # Partial rosters are unsafe as a rescue card. Use source field size
        # where available, or require 2+ identified runners minimum.
        expected=int(race.get("fieldSize") or d.get("fieldSize") or 0)
        if len(horses)<2 or (expected>=2 and len(horses)<expected):
            continue
        horses.sort(key=lambda x:x["horseNumber"])
        card={k:d.get(k,race.get(k)) for k in RACE_FIELDS if d.get(k,race.get(k)) not in ("",None)}
        card["id"]=rid
        card["date"]=date
        card["horses"]=horses
        card["fieldSize"]=len(horses)
        # This is strictly a static roster, not an assessment or bet.
        cards.append(card)
    if not cards:
        return None
    cards.sort(key=lambda x:str(x["id"]))
    return {"version":"arvexq-static-entry-v1","date":date,
            "raceCount":len(cards),"races":cards}


def merge_manifest(existing: dict[str, Any] | None, fresh: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return fresh
    if existing.get("version")!=fresh.get("version") or existing.get("date")!=fresh.get("date"):
        raise ValueError("static racecard date/version mismatch")
    saved={r["id"]:r for r in existing.get("races") or []}
    for r in fresh["races"]:
        saved.setdefault(r["id"],r)  # first observed complete roster wins
    ordered=sorted(saved.values(),key=lambda x:str(x["id"]))
    return {"version":fresh["version"],"date":fresh["date"],"raceCount":len(ordered),"races":ordered}


def publish(payload: dict[str, Any], directory: Path) -> Path | None:
    manifest=racecard_manifest(payload)
    if manifest is None:
        print("STATIC_RACECARDS_NO_COMPLETE_ROSTERS")
        return None
    directory.mkdir(parents=True,exist_ok=True)
    destination=directory/(manifest["date"]+".json")
    original=json.loads(destination.read_text(encoding="utf-8")) if destination.is_file() else None
    combined=merge_manifest(original,manifest)
    if original!=combined:
        destination.write_text(json.dumps(combined,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("STATIC_RACECARDS_SAVED",destination,"races",len(combined["races"]),
          "added",len(combined["races"])-(len(original.get("races") or []) if original else 0))
    return destination


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output-dir",default="arvexq/ui/static/racecards")
    args=p.parse_args()
    return 0 if publish(json.loads(Path(args.input).read_text(encoding="utf-8")),
                        Path(args.output_dir)) is not None else 2


if __name__=="__main__":
    raise SystemExit(main())
