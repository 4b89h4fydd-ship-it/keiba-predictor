"""Rebuild every saved race into a separate, verifiable revision ledger.

Reads a verified SQLite backup. Never modifies the input or original race tables.
Training is bounded strictly before each target date and separated by circuit/family.
Uncalibrated output remains explicitly labelled and cannot claim betting accuracy.
"""
from __future__ import annotations
import argparse
import concurrent.futures
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import urllib.request
import urllib.parse

from arvexq.ingest.full_snapshot_codec import unpack_detail
from arvexq.ingest.full_career import merge_career
from arvexq.databanks.nar_official_csv import NarOfficialArchive,normalize,item,date,number,carried_weight
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.forecast_revisions import append_revision, latest_revision, originals_hash
from arvexq.prediction.learned_scenarios import fit_model, race_family


def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)



def enrich_official_history(detail, archive):
    if archive is None or detail.get('circuit')!='地方':return detail
    out=deepcopy(detail)
    key=(normalize(detail.get('track')),detail.get('date'),int(detail.get('raceNumber') or 0))
    for horse in out.get('horses',[]):
        row=archive.entry_rows.get((key,int(horse.get('horseNumber') or 0)))
        if row and normalize(item(row,6))==normalize(horse.get('name')):
            birth=date(item(row,10))
            if birth and horse.get('birthDate') and date(horse['birthDate'])!=birth:continue
            if birth:horse['birthDate']=birth
        found=archive.horse_history(horse,detail).get('allPastRuns',[])
        if not found:continue
        existing=observed_runs(horse,detail,limit=None)
        full=merge_career(found,existing,detail['date'])
        horse['allPastRuns']=full;horse['recentRaces']=full[:5]
    return out



def official_training_races(archive, cutoff, family, limit):
    """Earlier completed official races; every feature history has its own cutoff."""
    if not hasattr(archive,'revision_entries_by_race'):
        archive.revision_entries_by_race={}
        for (key,_),row in archive.entry_rows.items():archive.revision_entries_by_race.setdefault(key,[]).append(row)
    # Race archive rows and prior-run enrichment do not change between target
    # dates. Keep their identity and cutoff, but do not rebuild the same 60
    # labelled historical races for every successive prediction date.
    if not hasattr(archive,'revision_ordered_races'):
        archive.revision_ordered_races=sorted(
            archive.race_rows.items(),
            key=lambda pair:(pair[0][1],pair[0][0],pair[0][2]),reverse=True)
    if not hasattr(archive,'revision_training_cache'):
        archive.revision_training_cache={}
    training=[]
    for key,row in archive.revision_ordered_races:
        if not key[1] or key[1]>=cutoff:continue
        cached=archive.revision_training_cache.get(key)
        if cached is None:
            detail={'id':f'nar-{key[1]}-{item(row,0)}-{key[2]:02d}','date':key[1],'track':item(row,0),
                    'raceNumber':key[2],'circuit':'地方','surface':item(row,21),'direction':item(row,22),
                    'distance':number(item(row,23)),'condition':item(row,25),'class':item(row,27),'title':item(row,5)}
            entries=archive.revision_entries_by_race.get(key,[])
            valid=(len(entries)>=3 and len(entries)==number(item(row,26))
                   and not any(number(item(h,31))<1 for h in entries))
            if valid:
                detail['horses']=[{'horseNumber':number(item(h,5)),'frameNumber':number(item(h,3)),
                                  'name':item(h,6),'birthDate':date(item(h,10)),'jockey':item(h,14),
                                  'carriedWeight':carried_weight(item(h,16)),'trainer':item(h,18)} for h in entries]
                detail['result']={'status':'確定','finishers':[{'horseNumber':number(item(h,5)),'finish':number(item(h,31))} for h in entries]}
                cached=enrich_official_history(detail,archive)
            else:
                cached=False
            archive.revision_training_cache[key]=cached
        if not cached or race_family(cached)!=family:continue
        training.append(cached)
        if len(training)>=limit:break
    return training


def rebuild(source, output, *, training_limit=60, nar_archives=(), only_missing=False):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    ledger=sqlite3.connect(output/'revisions.sqlite3')
    ledger.execute('CREATE TABLE IF NOT EXISTS revisions(race_id TEXT PRIMARY KEY,race_date TEXT,revision_id TEXT,payload_json TEXT,payload_sha256 TEXT,original_records_sha256 TEXT,status TEXT)')
    source=sqlite3.connect('file:'+str(Path(source).resolve())+'?mode=ro',uri=True)
    archive=NarOfficialArchive(nar_archives) if nar_archives else None
    models={};counts=Counter();errors=[]
    dates=[r[0] for r in source.execute('SELECT DISTINCT race_date FROM race_details ORDER BY race_date')]
    for day in dates:
        targets=source.execute('SELECT race_id,payload FROM race_details WHERE race_date=? ORDER BY race_id',(day,)).fetchall()
        for race_id,raw in targets:
            if only_missing and ledger.execute('SELECT 1 FROM revisions WHERE race_id=?',(race_id,)).fetchone():continue
            try:
                detail=enrich_official_history(unpack_detail(json.loads(raw)),archive)
                if detail.get('id')!=race_id or detail.get('date')!=day:raise ValueError('source identity mismatch')
                key=(day,detail.get('circuit'),race_family(detail))
                if key not in models:
                    # Database dates select the split before model fitting. No target outcomes enter fit.
                    training=official_training_races(archive,day,key[2],training_limit) if archive is not None and key[1]=='地方' else []
                    if not training:
                        training=[]
                        for oldraw, in source.execute('SELECT payload FROM race_details WHERE race_date<? ORDER BY race_date DESC,race_id DESC',(day,)):
                            old=enrich_official_history(unpack_detail(json.loads(oldraw)),archive)
                            if old.get('circuit')==key[1] and race_family(old)==key[2] and (old.get('result') or {}).get('status')=='確定':
                                training.append(old)
                                if len(training)>=training_limit:break
                    try:models[key]=fit_model(training,circuit=key[1],family=key[2])
                    except ValueError:models[key]=None
                model=models[key]
                if model:assert model['training']['lastDate']<day and race_id not in model['training']['raceIds']
                updated=append_revision(detail,model)
                revision=latest_revision(updated)
                assert revision and originals_hash(detail)==originals_hash(updated)
                prior=ledger.execute('SELECT payload_json FROM revisions WHERE race_id=? AND revision_id=?',(race_id,revision['revisionId'])).fetchone()
                # Preserve the first timestamp and exact raw bytes across resumptions.
                payload=prior[0] if prior else encoded(revision)
                digest=hashlib.sha256(payload.encode()).hexdigest()
                ledger.execute('INSERT OR REPLACE INTO revisions VALUES(?,?,?,?,?,?,?)',(race_id,day,revision['revisionId'],payload,digest,originals_hash(detail),revision['predictionStatus']))
                counts[revision['predictionStatus']]+=1
            except Exception as exc:
                errors.append({'raceId':race_id,'error':str(exc)})
        ledger.commit()
        # Only one target date's models need to remain resident.
        models.clear()
        print('REBUILT_DATE',day,len(targets),'errors',len(errors),flush=True)
    total=source.execute('SELECT COUNT(*) FROM race_details').fetchone()[0]
    actual=ledger.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]
    counts=dict(ledger.execute('SELECT status,COUNT(*) FROM revisions GROUP BY status').fetchall())
    report={'targetRaces':total,'revisions':actual,'statuses':dict(counts),'errors':errors,
            'allSavedRebuilt':actual==total and not errors,'originalSqlWrites':0,
            'officialNarArchiveSha256':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in nar_archives},
            'trainingLimit':training_limit,'trainingSplit':'strictly-earlier-race-date-per-circuit-and-family',
            'productionEligible':False,'recommendedAccuracyTargetAchieved':False,
            'limitations':['Models remain uncalibrated; no 80% claim','Some earliest dates have no earlier labelled training races','Post-off revisions are retrospective and never original predictions']}
    (output/'rebuild-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    ledger.close();source.close()
    return report



def capacity_preview(source_path, ledger_path, destination):
    """Apply the exact additive schema and real revisions to an expendable copy."""
    import shutil
    destination=Path(destination)
    if destination.exists():raise ValueError('capacity preview already exists')
    shutil.copyfile(source_path,destination)
    ledger=sqlite3.connect('file:'+str(Path(ledger_path).resolve())+'?mode=ro',uri=True)
    with sqlite3.connect(destination) as shadow:
        before=shadow.execute('PRAGMA page_count').fetchone()[0]*shadow.execute('PRAGMA page_size').fetchone()[0]
        def original_hash():
            h=hashlib.sha256()
            for rid,payload in shadow.execute('SELECT race_id,payload FROM race_details ORDER BY race_id'):
                h.update(encoded([rid,payload]).encode())
            return h.hexdigest()
        original=original_hash()
        shadow.execute('CREATE TABLE IF NOT EXISTS forecast_revisions (race_id TEXT NOT NULL,revision_id TEXT NOT NULL,race_date TEXT NOT NULL,model_version TEXT NOT NULL,created_at TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,PRIMARY KEY(race_id,revision_id))')
        shadow.execute('CREATE TABLE IF NOT EXISTS forecast_revision_current (race_id TEXT PRIMARY KEY,revision_id TEXT NOT NULL,updated_at TEXT NOT NULL)')
        count=0
        for rid,raw,digest in ledger.execute('SELECT race_id,payload_json,payload_sha256 FROM revisions'):
            r=json.loads(raw)
            shadow.execute('INSERT OR IGNORE INTO forecast_revisions VALUES(?,?,?,?,?,?,?)',(rid,r['revisionId'],r['raceDate'],r['modelVersion'],r['createdAt'],raw,digest))
            shadow.execute('INSERT INTO forecast_revision_current VALUES(?,?,?) ON CONFLICT(race_id) DO UPDATE SET revision_id=excluded.revision_id,updated_at=excluded.updated_at',(rid,r['revisionId'],r['createdAt']))
            count+=1
        shadow.commit()
        assert shadow.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert original_hash()==original
        after=shadow.execute('PRAGMA page_count').fetchone()[0]*shadow.execute('PRAGMA page_size').fetchone()[0]
    ledger.close()
    return {'revisionRows':count,'beforeBytes':before,'afterBytes':after,'additionalBytes':max(0,after-before),'originalsUnchanged':True,'integrityCheck':'ok','originalPayloadsSha256':original}


def publish(ledger_path,base,token, *, only_ids=None):
    db=sqlite3.connect(ledger_path);failures=[];verified=0
    headers={'Content-Type':'application/json','Authorization':'Bearer '+token}
    def request(path,value=None):
        data=encoded(value).encode() if value is not None else None
        req=urllib.request.Request(base.rstrip('/')+path,data=data,headers=headers)
        with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
    def publish_one(row):
        race_id,revision_id,raw,digest=row
        try:
            path='/api/forecast-revisions/'+urllib.parse.quote(race_id,safe='')
            before=request(path)
            existing=next((r for r in before.get('forecastRevisions',[]) if r['revisionId']==revision_id),None)
            if existing:
                # Raw payload formatting may differ after JSON decoding; never rewrite a known immutable ID.
                assert {k:v for k,v in existing.items() if k!='createdAt'}=={k:v for k,v in json.loads(raw).items() if k!='createdAt'}
                if before.get('currentForecastRevisionId')!=revision_id:raise ValueError('known revision is not current; refusing rollback of newer display')
            else:
                result=request('/api/admin/forecast-revisions',{'revisionRawJson':raw,'payloadSha256':digest})
                assert result.get('ok') and result.get('original_tables_modified') is False
            after=request(path)
            assert after.get('currentForecastRevisionId')==revision_id
            saved=next(r for r in after['forecastRevisions'] if r['revisionId']==revision_id)
            assert {k:v for k,v in saved.items() if k!='createdAt'}=={k:v for k,v in json.loads(raw).items() if k!='createdAt'}
            return None
        except Exception as exc:return {'raceId':race_id,'error':str(exc)}

    rows=db.execute('SELECT race_id,revision_id,payload_json,payload_sha256 FROM revisions ORDER BY race_id').fetchall()
    if only_ids is not None:rows=[row for row in rows if row[0] in set(only_ids)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(publish_one,rows):
            if result is not None:failures.append(result)
            else:
                verified+=1
                if verified%50==0:print('PUBLISHED_AND_RELOADED',verified,flush=True)
    expected=len(rows)
    report={'targetRevisions':expected,'verifiedRevisions':verified,'failures':failures,'allPublished':expected>0 and verified==expected and not failures,'originalSqlWrites':0}
    Path(str(ledger_path)+'.publish.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    history_path=Path(str(ledger_path)+'.publish-history.json')
    history=json.loads(history_path.read_text()) if history_path.exists() else []
    history.append(report);history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--publish-base');p.add_argument('--nar-archives',nargs='*',default=[]);args=p.parse_args()
    report=rebuild(args.source,args.output,nar_archives=args.nar_archives)
    print(encoded(report))
    if args.publish_base:
        import os
        assert report['allSavedRebuilt']
        result=publish(Path(args.output)/'revisions.sqlite3',args.publish_base,os.environ['SYNC_TOKEN'])
        if result['failures']:raise SystemExit('publish/readback failures: '+str(len(result['failures'])))
    if report['errors']:raise SystemExit(1)
