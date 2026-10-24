"""Read-only inventory of previously saved, content-addressed ARVEXQ race snapshots.

Never requests another data provider, writes D1, re-labels predictions, or
pretends that a historical outcome was available before post time.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import base64, gzip, hashlib, json
import sys

def snapshots(directory: Path):
    seen=set()
    manifests=sorted(p for p in directory.glob('20??-??-??.json'))
    for path in manifests:
        m=json.loads(path.read_text(encoding='utf-8'))
        if m.get('date')!=path.stem or m.get('version')!='arvexq-saved-snapshots-v1':
            raise ValueError(f'invalid manifest: {path}')
        for rid, entry in (m.get('races') or {}).items():
            if (m['date'],rid) in seen:
                raise ValueError(f'duplicate race {rid}')
            seen.add((m['date'],rid))
            name=entry.get('file')
            if not name or Path(name).name!=name or not (directory/name).is_file():
                raise ValueError(f'missing envelope: {rid}')
            packed=json.loads((directory/name).read_text(encoding='utf-8'))
            raw=gzip.decompress(base64.b64decode(packed['gzipBase64'],validate=True))
            sha=hashlib.sha256(raw).hexdigest()
            if (sha!=packed['sha256'] or sha!=entry['sha256'] or len(raw)!=packed['bytes']
                    or len(raw)!=entry['bytes']):
                raise ValueError(f'historical snapshot corruption: {rid}')
            race=json.loads(raw)
            if race.get('id')!=rid or race.get('date')!=m['date']:
                raise ValueError(f'wrong race identity: {rid}')
            yield race

def inventory(directory:Path):
    counts=Counter()
    daily=defaultdict(Counter)
    examples={}
    fields=Counter()
    for race in snapshots(directory):
        day=race['date']; circuit=race.get('circuit','missing')
        result=race.get('result') or {}
        confirmed=result.get('status')=='確定'
        finishers=result.get('finishers') or []
        horses=race.get('horses') or []
        usable=(confirmed and len(finishers)>=3 and len(horses)>=3 and
                all(h.get('horseNumber') for h in horses) and
                len({h.get('horseNumber') for h in horses})==len(horses))
        counts['races']+=1
        counts['confirmed']+=int(confirmed)
        counts['readyForLabels']+=int(usable)
        counts['hasLapData']+=int(bool(race.get('laps') or race.get('lapTimes') or result.get('laps')))
        counts['withVideo']+=int(bool(race.get('_internalVideoFeatures')))
        counts['withPreoffTripleOdds']+=int(bool(race.get('_internalThreeWayOdds')))
        counts['horseRows']+=len(horses)
        counts['historyRows']+=sum(bool(h.get('allPastRuns') or h.get('recentRaces')) for h in horses)
        daily[day]['all']+=1
        daily[day]['labeled']+=int(usable)
        daily[day][circuit]+=int(usable)
        for k in race:
            fields[k]+=1
        if usable and circuit not in examples:
            examples[circuit]= {'raceId':race['id'],'finishersKeys':list(finishers[0]) if finishers else [],
                                'raceKeys':list(race),'horseKeys':list(horses[0]) if horses else []}
    return {'counts':dict(counts),'days':{k:dict(v) for k,v in sorted(daily.items())},
            'examples':examples,'fields':dict(fields)}

if __name__=='__main__':
    print('ARVEXQ_SAVED_SNAPSHOT_INVENTORY',json.dumps(inventory(
        Path(sys.argv[1] if len(sys.argv)>1 else 'arvexq/ui/static/saved-snapshots')
    ),ensure_ascii=False,separators=(',',':')))
