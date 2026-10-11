"""Keep known archive fields when a later CSV row lacks them."""
import json
from dataclasses import replace


def retain_archive_rows(conn, races, entries):
    retained=[]
    for race in races:
        old=conn.execute('SELECT * FROM races WHERE track=? AND date=? AND race_no=?',
                         (race.track,race.date,race.race_no)).fetchone()
        changes={}
        if old:
            for key in ('start_time','title','distance','field_size'):
                if getattr(race,key) in (None,'',0):changes[key]=old[key]
            if not any(race.prize):changes['prize']=tuple(old['prize'+str(i)] for i in range(1,6))
            if not race.corners:
                changes['corners']=[{int(k):v for k,v in corner.items()} for corner in json.loads(old['corners_json'] or '[]')]
        retained.append(replace(race,**changes) if changes else race)
    cards=[]
    for entry in entries:
        old=conn.execute('SELECT * FROM entries WHERE track=? AND date=? AND race_no=? AND horse_no=?',
                         (entry.track,entry.date,entry.race_no,entry.horse_no)).fetchone()
        changes={}
        if old:
            for key in ('frame_no','name','sex','age','carried_weight','jockey','trainer','finish','time_seconds'):
                if getattr(entry,key) in (None,'',0):changes[key]=old[key]
        cards.append(replace(entry,**changes) if changes else entry)
    return retained,cards
