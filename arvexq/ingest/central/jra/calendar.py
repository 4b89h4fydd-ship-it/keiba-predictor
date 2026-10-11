"""central/jra/calendar: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from concurrent.futures import ThreadPoolExecutor
import os


from arvexq.ingest.central.jra.state import JRA_CNAME_RE

def fetch_jra_official(iso_date: str, lightweight: bool=False, *, _jra_parse_race, _jra_parse_race_summary, _jra_program_summaries, _jra_race_no_from_cname, _jra_request, _jra_track_from_cname) -> list[dict]:
    if lightweight:return _jra_program_summaries(iso_date)
    token=iso_date.replace("-","")
    try:
        home=_jra_request("https://www.jra.go.jp/",None,120)
    except Exception:
        return []
    seeds=[]
    for c in JRA_CNAME_RE.findall(home):
        if token in c and c not in seeds:
            seeds.append(c)
    if not seeds:
        return []

    # v48: a race page contains links to the other active venue(s) too.
    # v47 filtered those links to the first venue, which could leave only Nakayama.
    # Discover one seed per track first, then expand each venue to all race-number links.
    track_seed={}
    for c in seeds:
        tr=_jra_track_from_cname(c)
        if tr and tr not in track_seed:
            track_seed[tr]=c

    discovered=[]
    processed_tracks=set()
    queue=list(track_seed.items())
    guard=0
    while queue and guard<12:
        guard+=1
        track,seed=queue.pop(0)
        if track in processed_tracks:
            continue
        processed_tracks.add(track)
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",seed,180)
        except Exception:
            continue
        links=[]
        for c in JRA_CNAME_RE.findall(html):
            if token not in c:
                continue
            if c not in links:
                links.append(c)
            if c not in discovered:
                discovered.append(c)
        # Important: do NOT restrict to the current track. Any newly linked venue
        # becomes a seed and is expanded on its own page.
        for c in links:
            tr=_jra_track_from_cname(c)
            if tr and tr not in processed_tracks and all(q[0]!=tr for q in queue):
                queue.append((tr,c))

    for c in seeds:
        if c not in discovered:
            discovered.append(c)

    # prefer detailed 01 variant and deduplicate by venue/race number
    chosen={}
    for c in discovered:
        key=(_jra_track_from_cname(c),_jra_race_no_from_cname(c))
        if not key[0] or not key[1]:
            continue
        if key not in chosen or c.startswith("pw01dde01"):
            chosen[key]=c

    def one(c):
        try:
            return _jra_parse_race_summary(c) if lightweight else _jra_parse_race(c, supplement_profiles=True)
        except Exception as exc:
            print("JRA official race parse failed",c,exc)
            return None
    workers=max(4,min(16,int(os.getenv("JRA_SUMMARY_WORKERS","12") if lightweight else os.getenv("JRA_RACE_WORKERS","6"))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        races=[x for x in pool.map(one,chosen.values()) if x]
    races.sort(key=lambda r:(r.get("track") or "",int(r.get("raceNumber") or 0)))
    return races
