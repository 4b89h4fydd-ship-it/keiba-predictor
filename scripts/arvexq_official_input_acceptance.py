"""Acquire official inputs through existing app routes, without production writes.

This checks observed entry delivery, not lifetime completeness or prediction
accuracy. A successful racecard gate must not promote a forecast to production.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import os


def official_jra_roster_size(html):
    from bs4 import BeautifulSoup
    import re
    soup=BeautifulSoup(html,'html.parser')
    for table in soup.find_all('table'):
        heading=table.find('thead') or table
        if '馬番' not in heading.get_text() or '前走' not in heading.get_text():
            continue
        entries=[]
        for row in table.find_all('tr'):
            # Count official horse-profile identities in source rows independently
            # of the racecard parser's horse-name and fieldSize output.
            ids=re.findall(r'pw01dud[0-9]{12,}(?:/|%2F)[0-9A-Fa-f]{2}',str(row))
            if ids:entries.append(ids[0].replace('%2F','/'))
        return len(set(entries)) if entries else None
    return None


def summarize_jra(races, target_date, source_rosters=None):
    from arvexq.prediction.past_performance import observed_runs
    by_id = {}
    invalid = []
    for race in races:
        rid = race.get('id')
        if not rid or rid in by_id or race.get('date') != target_date:
            invalid.append(rid)
        else:
            by_id[rid] = race
    rows = []
    for rid, race in by_id.items():
        horses = [h for h in race.get('horses', []) if isinstance(h, dict)]
        numbers = [h.get('horseNumber') for h in horses]
        histories = [len(observed_runs(h,race,limit=None)) for h in horses]
        rows.append({'raceId':rid, 'reportedFieldSize':race.get('fieldSize'),
                     'acquiredEntries':len(horses), 'sourceRosterEntries':(source_rosters or {}).get(rid), 'uniqueHorseNumbers':len(set(numbers)),
                     'invalidHorseNumbers':sum(type(n) is not int or n<=0 for n in numbers),
                     'observedPriorRuns':sum(histories),
                     'horsesWithPriorRuns':sum(n>0 for n in histories),
                     'horsesWithoutPriorRuns':sum(n==0 for n in histories),
                     'explicitDebutHorses':sum(bool(h.get('debutNoHistory')) for h in horses),
                     'missingFields':{key:sum(h.get(key) in (None,'',0) for h in horses)
                                      for key in ('name','jockey','trainer','carriedWeight')},
                     'lifetimeCompleteProven':False})
    horses = sum(r['acquiredEntries'] for r in rows)
    verified=all(r['sourceRosterEntries'] is not None for r in rows) and bool(rows)
    expected=sum(r['sourceRosterEntries'] or 0 for r in rows) if verified else None
    return {'targetDate':target_date, 'races':len(rows), 'acquiredEntries':horses,
            'officialSourceRosterTotal':expected, 'sourceRosterVerified':verified,
            'entryCoveragePercent':100*horses/expected if expected else None,
            'invalidRaceIds':invalid,
            'fieldMismatches':[r['raceId'] for r in rows if not r['acquiredEntries']
                               or r['acquiredEntries'] != r['reportedFieldSize']
                               or r['acquiredEntries'] != r['uniqueHorseNumbers'] or r['invalidHorseNumbers']
                               or (r['sourceRosterEntries'] is not None and r['sourceRosterEntries'] != r['acquiredEntries'])],
            'observedPriorRuns':sum(r['observedPriorRuns'] for r in rows),
            'horsesWithPriorRuns':sum(r['horsesWithPriorRuns'] for r in rows),
            'horsesWithoutPriorRuns':sum(r['horsesWithoutPriorRuns'] for r in rows),
            'perRace':rows}


def acquire(output, target_date, min_races=30, nar_months=3):
    # Import only after the caller has selected a disposable local data root.
    import app
    from scripts.arvexq_nar_csv_coverage import audit
    output.mkdir(parents=True,exist_ok=True)
    report = {'startedAt':datetime.now(timezone.utc).isoformat(),'targetDate':target_date,
              'minimumRacesPerCircuit':min_races,'productionWrites':False,
              'stageOneComplete':False,'errors':[]}
    try:
        races = app.fetch_jra_official(target_date)
        from arvexq.databanks.legacy_bridge import _jra_history_adapter
        from arvexq.ingest.full_career import merge_career
        fetch_history=_jra_history_adapter(vars(app))
        history_errors=[]
        def full_history(pair):
            horse,race=pair
            try:
                payload=fetch_history(horse,race,500) if fetch_history else {}
                merged=merge_career(horse.get('allPastRuns'),
                    [*(horse.get('recentRaces') or []),*(payload.get('allPastRuns') or [])],target_date)
                horse['allPastRuns']=merged
                horse['recentRaces']=merged[:5]
                horse['_careerHistoryAudit']={'complete':False,'status':'official-profile-observed-not-lifetime-certified',
                    'requestedAtRaceDate':target_date,'observedRuns':len(merged),'requestedLimit':500}
            except Exception as exc:
                history_errors.append({'raceId':race.get('id'),'horseNumber':horse.get('horseNumber'),'error':str(exc)})
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(full_history,[(h,r) for r in races for h in r.get('horses',[])]))
        sources=output/'jra-official-html';sources.mkdir(exist_ok=True)
        source_rosters={}
        for race in races:
            cname=race.get('jraCname') or ''
            cache=app._jra_text_cache.get('https://www.jra.go.jp/JRADB/accessD.html|'+cname)
            if cache:
                source_rosters[race['id']]=official_jra_roster_size(cache[1])
        source_index=[]
        for key,(_,html) in app._jra_text_cache.items():
            name=sha256(key.encode()).hexdigest()+'.html'
            (sources/name).write_text(html)
            source_index.append({'requestKey':key,'file':name,'sha256':sha256(html.encode()).hexdigest()})
        (sources/'index.json').write_text(json.dumps(source_index,ensure_ascii=False,indent=2))
        data = json.dumps(races,ensure_ascii=False).encode()
        (output/'jra-official-racecards.json').write_bytes(data)
        report['JRA'] = summarize_jra(races,target_date,source_rosters)
        report['JRA']['fullHistoryErrors']=history_errors
        report['JRA']['profileHistoryLimit']=500
        report['JRA']['savedOfficialHtmlResponses']=len(source_index)
        report['JRA']['racecardsSha256'] = sha256(data).hexdigest()
    except Exception as exc:
        report['errors'].append({'circuit':'JRA','type':type(exc).__name__,'error':str(exc)})
        report['JRA'] = summarize_jra([],target_date)
    # Do not use a production DB or D1. NarSync uses KEIBA_DATA_DIR selected by
    # this process, and the existing official daily/monthly archive downloader.
    try:
        sync = app.NarSync()
        day = datetime.fromisoformat(target_date).date()
        imports = [sync.sync_daily(force=True),sync.sync_month(day.year,day.month,force=True)]
        for year, month in app.iter_months_back(day,nar_months):
            imports.append(sync.sync_month(year,month,force=True))
        paths = sorted(app.ARCHIVE_DIR.glob('*_race.zip'))
        report['NAR'] = audit(paths,target_date=target_date)
        report['NAR']['imports'] = imports
        sync.store.conn.close()
    except Exception as exc:
        report['errors'].append({'circuit':'NAR','type':type(exc).__name__,'error':str(exc)})
    jra, nar = report.get('JRA',{}), report.get('NAR',{})
    report['entryDeliveryGatePassed'] = bool(
        jra.get('races',0)>=min_races and jra.get('sourceRosterVerified') is True and not jra.get('invalidRaceIds') and not jra.get('fieldMismatches')
        and nar.get('targetRaces',0)>=min_races and not nar.get('targetFieldSizeMismatches'))
    report['finishedAt'] = datetime.now(timezone.utc).isoformat()
    report['limitations'] = ['Entry delivery does not prove lifetime history completeness.',
                             'Snapshots acquired after post time are retrospective inputs.',
                             'No prediction accuracy, model calibration, or production deployment is certified.']
    (output/'official-input-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--min-races',type=int,default=30)
    parser.add_argument('--nar-months',type=int,default=3)
    args=parser.parse_args()
    if args.min_races<1 or args.nar_months<1:
        parser.error('positive minimum races and history months required')
    root=args.output.resolve()
    if not os.environ.get('KEIBA_DATA_DIR'):
        os.environ['KEIBA_DATA_DIR']=str(root/'local-data')
    report=acquire(root,args.date,args.min_races,args.nar_months)
    print(json.dumps({k:v for k,v in report.items() if k not in ('JRA','NAR')},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['entryDeliveryGatePassed'] else 1)


if __name__=='__main__':
    main()
