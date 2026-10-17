"""Rebuild every saved race into a separate, verifiable revision ledger.

Reads a verified SQLite backup. Never modifies the input or original race tables.
Training is bounded strictly before each target date and separated by circuit/family.
Uncalibrated output remains explicitly labelled and cannot claim betting accuracy.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import urllib.request
import urllib.parse

from arvexq.ingest.full_snapshot_codec import unpack_detail
from arvexq.prediction.forecast_revisions import append_revision, latest_revision, originals_hash
from arvexq.prediction.learned_scenarios import fit_model, race_family


def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def rebuild(source, output, *, training_limit=60):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    ledger=sqlite3.connect(output/'revisions.sqlite3')
    ledger.execute('CREATE TABLE IF NOT EXISTS revisions(race_id TEXT PRIMARY KEY,race_date TEXT,revision_id TEXT,payload_json TEXT,payload_sha256 TEXT,original_records_sha256 TEXT,status TEXT)')
    source=sqlite3.connect('file:'+str(Path(source).resolve())+'?mode=ro',uri=True)
    models={};counts=Counter();errors=[]
    dates=[r[0] for r in source.execute('SELECT DISTINCT race_date FROM race_details ORDER BY race_date')]
    for day in dates:
        targets=source.execute('SELECT race_id,payload FROM race_details WHERE race_date=? ORDER BY race_id',(day,)).fetchall()
        for race_id,raw in targets:
            try:
                detail=unpack_detail(json.loads(raw))
                if detail.get('id')!=race_id or detail.get('date')!=day:raise ValueError('source identity mismatch')
                key=(day,detail.get('circuit'),race_family(detail))
                if key not in models:
                    # Database dates select the split before model fitting. No target outcomes enter fit.
                    training=[]
                    for oldraw, in source.execute('SELECT payload FROM race_details WHERE race_date<? ORDER BY race_date DESC,race_id DESC',(day,)):
                        old=unpack_detail(json.loads(oldraw))
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
    report={'targetRaces':total,'revisions':actual,'statuses':dict(counts),'errors':errors,
            'allSavedRebuilt':actual==total and not errors,'originalSqlWrites':0,
            'trainingLimit':training_limit,'trainingSplit':'strictly-earlier-race-date-per-circuit-and-family',
            'productionEligible':False,'recommendedAccuracyTargetAchieved':False,
            'limitations':['Models remain uncalibrated; no 80% claim','Some earliest dates have no earlier labelled training races','Post-off revisions are retrospective and never original predictions']}
    (output/'rebuild-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    ledger.close();source.close()
    return report


def publish(ledger_path,base,token):
    db=sqlite3.connect(ledger_path);failures=[];verified=0
    headers={'Content-Type':'application/json','Authorization':'Bearer '+token}
    def request(path,value=None):
        data=encoded(value).encode() if value is not None else None
        req=urllib.request.Request(base.rstrip('/')+path,data=data,headers=headers)
        with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
    for race_id,revision_id,raw,digest in db.execute('SELECT race_id,revision_id,payload_json,payload_sha256 FROM revisions ORDER BY race_id'):
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
            verified+=1
            if verified%50==0:print('PUBLISHED_AND_RELOADED',verified,flush=True)
        except Exception as exc:failures.append({'raceId':race_id,'error':str(exc)})
    report={'verifiedRevisions':verified,'failures':failures,'allPublished':not failures,'originalSqlWrites':0}
    Path(str(ledger_path)+'.publish.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--publish-base');args=p.parse_args()
    report=rebuild(args.source,args.output)
    print(encoded(report))
    if args.publish_base:
        import os
        assert report['allSavedRebuilt']
        result=publish(Path(args.output)/'revisions.sqlite3',args.publish_base,os.environ['SYNC_TOKEN'])
        if result['failures']:raise SystemExit('publish/readback failures: '+str(len(result['failures'])))
    if report['errors']:raise SystemExit(1)
