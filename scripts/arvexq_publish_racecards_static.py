"""Publish a tiny factual racecard-only backup independently of full D1 writes.

No odds, AI marks, predictions, results or post-off changes are published.
Later runs can add previously missing race IDs with verified runner names
and never erase starts.  A later roster for an already-published race
replaces the stored one only when it is the same set of horses read
more consistently (or a fuller set): the earlier "first complete
roster wins, immutable forever" rule locked a permuted roster into
this file on 2026-11-28 and the prefetch recovery then read it back
as verified truth.
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


def _roster_quality(card: dict[str, Any]) -> tuple[int, int, int]:
    """(frame-map matches, runners, numbers are a clean 1..N) for one
    roster, judged against the standard frame map.  The frame is read
    from a different page feature than the number, so a permuted
    roster scores below the true one even though both look complete.
    """
    horses=[h for h in (card.get("horses") or []) if isinstance(h,dict)]
    numbers=[]
    matches=0
    for h in horses:
        try:
            no=int(h.get("horseNumber") or 0)
            frame=int(h.get("frameNumber") or 0)
        except (TypeError,ValueError):
            no,frame=0,0
        numbers.append(no)
        if frame>0 and frame==_frame_for_number(no,len(horses)):
            matches+=1
    clean=1 if numbers and all(n>0 for n in numbers) and \
        sorted(numbers)==list(range(1,len(numbers)+1)) else 0
    return (matches,len(horses),clean)


def _frame_for_number(number: int, field_size: int) -> int:
    """Standard frame for a horse number (same rule as
    arvexq.ingest.entry_reconcile.frame_for_number, inlined so this
    rescue publisher stays dependency-free)."""
    if number<=0 or field_size<=0 or number>field_size:
        return 0
    if field_size<=8:
        return number
    base,rem=divmod(field_size,8)
    small_frames=8-rem
    small_horses=small_frames*base
    if number<=small_horses:
        return (number-1)//base+1
    return small_frames+(number-small_horses-1)//(base+1)+1


def merge_manifest(existing: dict[str, Any] | None, fresh: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return fresh
    if existing.get("version")!=fresh.get("version") or existing.get("date")!=fresh.get("date"):
        raise ValueError("static racecard date/version mismatch")
    saved={r["id"]:r for r in existing.get("races") or []}
    for r in fresh["races"]:
        rid=r["id"]
        old=saved.get(rid)
        if old is None:
            saved[rid]=r
            continue
        # The old rule ("first observed complete roster wins") locked
        # the 2026-11-28 garble in permanently: the first roster was
        # form-complete but permuted, and no later correct roster
        # could ever replace it — while the prefetch recovery read
        # the file back as verified truth.  Two rosters of the same
        # race are two readings of the same card: when they name the
        # same horses, the internally consistent reading (standard
        # frame map) replaces the scrambled one; when they name
        # different horses, the fuller reading wins; ties keep the
        # existing roster.
        old_names={str(h.get("name") or "").strip() for h in old.get("horses") or []}
        new_names={str(h.get("name") or "").strip() for h in r.get("horses") or []}
        if old_names==new_names:
            if _roster_quality(r)>_roster_quality(old):
                print("STATIC_RACECARDS_ROSTER_CORRECTED",rid)
                saved[rid]=r
        elif len(new_names)>len(old_names):
            print("STATIC_RACECARDS_ROSTER_CORRECTED",rid)
            saved[rid]=r
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
