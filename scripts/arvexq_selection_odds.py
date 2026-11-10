#!/usr/bin/env python3
"""Record all-circuit pre-off win/place and NAR official wide observations.

Run after sync; no D1 forecast writes. Each run has an immutable JSONL artifact.
An old API observation retains its old timestamp even when fetched now.
"""
from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rewrite.data.sources import API_BASE, BROWSER_UA
from rewrite.selection.market import (JST, append_observation, observation, off_time,
                                      open_store, parse_nar_wide, timestamp, digest)
from rewrite.selection.policy import evaluate, VERSION
from rewrite.selection.models import prepare, predict, partner_pool
from rewrite.safety.probability import distribution

NAR_CODES = {"門別":36,"盛岡":10,"水沢":11,"浦和":18,"船橋":19,"大井":20,
             "川崎":21,"金沢":22,"笠松":23,"名古屋":24,"園田":27,"姫路":28,
             "高知":31,"佐賀":32}


def get(url):
    with urlopen(Request(url, headers={"User-Agent": BROWSER_UA,
                                      "Cache-Control":"no-cache"}), timeout=20) as response:
        return response.read()


def collect_detail(detail, fetch=get, now=None):
    injected_clock = now is not None
    now = now or datetime.now(timezone.utc)
    off = off_time(detail)
    if not off or not 3 <= (off-now).total_seconds()/60 <= 45:
        return [], ["outside-T45-T3"]
    records, errors = [], []
    stamp = str(detail.get("oddsUpdatedAt") or "")
    if len(stamp) == 8 and stamp.count(":") == 2:
        stamp = f"{detail['date']}T{stamp}+09:00"
    source = str(detail.get("oddsSource") or "")
    actual = source in {"NAR公式","NAR公式出馬表","JRA公式","netkeiba実オッズ","netkeiba"}
    body = json.dumps(detail, ensure_ascii=False).encode()
    for kind, fields in (("win", ("winOdds", "winOdds")),
                         ("place", ("placeOddsLow", "placeOddsHigh"))):
        quotes = []
        for h in detail.get("horses", []):
            if (h.get("scratched") or h.get("withdrawn") or h.get("oddsForecast") is True
                    or h.get("oddsSource", source) not in {"NAR公式","NAR公式出馬表","JRA公式","netkeiba実オッズ","netkeiba"}):
                continue
            low, high = h.get(fields[0]), h.get(fields[1])
            if low is not None and high is not None:
                quotes.append({"combo":[h["horseNumber"]], "oddsLow":low, "oddsHigh":high})
        try:
            if not actual or detail.get("oddsForecast") is True:
                raise ValueError("actual-market-source-unavailable")
            records.append(observation(detail, quotes, observed_at=stamp,
                fetched_at=now.isoformat(), source=source,
                source_url=f"{API_BASE}/api/race/{quote(detail['id'],safe='')}",
                source_body_sha256=sha256(body).hexdigest(),kind=kind))
        except ValueError as exc: errors.append(f"{kind}:{exc}")
    if detail.get("track") in NAR_CODES:
        url = "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsWide?"+urlencode({
            "k_raceDate":detail["date"].replace("-","/"),
            "k_raceNo":detail["raceNumber"],"k_babaCode":NAR_CODES[detail["track"]]})
        try:
            raw = fetch(url)
            # This is a fresh direct observation, not an API retrieval of old odds.
            at = now if injected_clock else datetime.now(timezone.utc)
            records.append(observation(detail, parse_nar_wide(raw.decode("utf-8")),
                observed_at=at.isoformat(), fetched_at=at.isoformat(),source="NAR公式ワイド",
                source_url=url,source_body_sha256=sha256(raw).hexdigest(),kind="wide"))
        except Exception as exc: errors.append(f"wide:{type(exc).__name__}:{exc}")
    else: errors.append("wide:actual-source-unavailable")
    return records, errors


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", default=datetime.now(JST).date().isoformat())
    p.add_argument("--store",default="var/selection/market.sqlite3")
    p.add_argument("--output",default="var/selection/market.jsonl")
    p.add_argument("--report",default="var/selection/market-report.json")
    p.add_argument("--forward-output",default="var/selection/forward.jsonl")
    p.add_argument("--model-dir",default="rewrite/selection/candidates")
    p.add_argument("--validation",default="rewrite/selection/approved.json")
    p.add_argument("--publication-dir",default="arvexq/ui/static/selection-decisions")
    args=p.parse_args()
    if args.date != datetime.now(JST).date().isoformat():
        p.error("Live market collection only supports today's date; no historical backfill")
    day=json.loads(get(API_BASE+"/api/day?date="+args.date+"&details=0"))
    now=datetime.now(timezone.utc)
    races=[r for r in day.get("races",[]) if off_time(r) and
           3 <= (off_time(r)-now).total_seconds()/60 <= 45 and r.get("track") not in ("帯広","帯広ば")]
    def one(r):
        try:
            data=json.loads(get(API_BASE+"/api/race/"+quote(r["id"],safe="")))
            detail=data.get("detail") or data.get("race") or data
            if detail.get('id')!=r['id'] or detail.get('date')!=args.date:
                raise ValueError('cross-race-or-date-response')
            # API detail odds keep their own provider timestamp; a current fetch
            # never relabels stale observations as fresh.
            return r["id"],detail,collect_detail(detail)
        except Exception as exc:return r["id"],None,([], [f"fetch:{type(exc).__name__}:{exc}"])
    Path(args.store).parent.mkdir(parents=True,exist_ok=True)
    db=open_store(args.store); report={"date":args.date,"races":len(races),"records":0,"errors":{},"purchaseAssessments":{}}
    db.executescript('''CREATE TABLE IF NOT EXISTS purchase_decisions (race_id TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS decision_no_update BEFORE UPDATE ON purchase_decisions
        BEGIN SELECT RAISE(ABORT,'append-only purchase decision'); END;
        CREATE TRIGGER IF NOT EXISTS decision_no_delete BEFORE DELETE ON purchase_decisions
        BEGIN SELECT RAISE(ABORT,'append-only purchase decision'); END;''')
    validation=json.loads(Path(args.validation).read_text()) if Path(args.validation).exists() else {}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.forward_output).parent.mkdir(parents=True,exist_ok=True)
    with open(args.output,"w") as out, open(args.forward_output,"w") as forward, ThreadPoolExecutor(max_workers=4) as pool:
        for rid,detail,(records,errors) in pool.map(one,races):
            if errors:report["errors"][rid]=errors
            for record in records:
                append_observation(db,record);out.write(json.dumps(record,ensure_ascii=False)+"\n")
                report["records"]+=1
            if detail:
                at=datetime.now(timezone.utc)
                try:
                    raw=prepare(detail);base={r['number']:r['baseWin'] for r in raw['rows']}
                    record={'raceId':rid,'date':detail['date'],'capturedAt':at.isoformat(),
                            'sourceCapturedAt':raw['capturedAt'],'sourceReceipt':raw['sourceReceipt'],
                            'sourceVectorSha256':raw['sourceVectorSha256'],'status':'research-only',
                            'baselineWin':base,'candidates':{}}
                    for target in ('partner','winner'):
                        path=Path(args.model_dir,f"{raw['segment']}-{target}.json")
                        if not path.exists():continue
                        model=json.loads(path.read_text());values=predict(model,raw)
                        record['candidates'][target]={'modelSha256':model['artifactSha256'],
                            'values':values,'pool':partner_pool(raw,values) if target=='partner' else sorted(values,key=lambda n:(-values[n],n))[:5]}
                    if at>=off_time(detail):raise ValueError('forward-window-closed')
                    record['contentSha256']=digest(record)
                    forward.write(json.dumps(record,ensure_ascii=False)+'\n')
                    minutes=(off_time(detail)-at).total_seconds()/60
                    if 15<=minutes<=20:
                        wide=next((r for r in records if r['kind']=='wide'),None)
                        e=evaluate(detail,wide,outcomes=distribution(base),validation=validation,decided_at=at.isoformat())
                        report['purchaseAssessments'][rid]=e
                        # Explicitly unassessed decisions are recorded for diagnosis,
                        # never promoted or mislabeled as losing / not-selected races.
                        if e['status'] in ('selected','not-selected'):
                            entry=publication_entry(detail,e)
                            db.execute('INSERT OR IGNORE INTO purchase_decisions VALUES (?,?)',
                                       (rid,json.dumps(entry,ensure_ascii=False)));db.commit()
                except Exception as exc:report['errors'].setdefault(rid,[]).append(f'forward:{type(exc).__name__}:{exc}')
    public={'version':VERSION,'date':args.date,'races':{}}
    for rid,body in db.execute('SELECT race_id,body FROM purchase_decisions ORDER BY race_id'):
        entry=json.loads(body)
        if entry['evaluation']['raceDate']==args.date:public['races'][rid]=entry
    db.close()
    Path(args.publication_dir).mkdir(parents=True,exist_ok=True)
    Path(args.publication_dir,f'{args.date}.json').write_text(json.dumps(public,ensure_ascii=False,indent=2))
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
    return int(bool(races) and report["records"]==0)


def publication_entry(detail,evaluation):
    """Snapshot the exact selected ticket and source identity, outside D1 forecasts."""
    uf=detail['unifiedForecast'];marks={m['horseNumber']:m.get('mark','') for m in detail.get('predictionMarks',[])}
    no=next((n for n,m in marks.items() if m=='◎'),0)
    name=next((h.get('name','') for h in detail['horses'] if h['horseNumber']==no),'')
    minimal={k:copy.deepcopy(detail[k]) for k in ('id','date','startTime','scheduledStartTime') if k in detail}
    minimal['horses']=[{k:h[k] for k in ('horseNumber','name','scratched','withdrawn','status') if k in h} for h in detail['horses']]
    minimal['unifiedForecast']={k:copy.deepcopy(uf.get(k)) for k in ('modelVersion','modelHash','receiptSha256','capturedAt')}
    receipt={'version':'arvexq-morning-ticket-evidence-v1','origin':'morning-lane-v9b',
             'raceId':detail['id'],'raceDate':detail['date'],'fixedAt':evaluation['decidedAt'],
             'axisStatus':'honmei','axisHorseNumber':no,'modelVersion':uf['modelVersion'],
             'marks':[{'horseNumber':n,'mark':marks.get(n,''),'singleWinSuitable':False}
                      for n in sorted(d['horseNumber'] for d in uf.get('diagnosis',[]))],
             'items':[{'level':'本線','kind':'ワイド','combos':[i['combo'] for i in evaluation['items']],
                       'points':len(evaluation['items'])}], 'ticketKinds':['ワイド']}
    return {'detail':minimal,'evaluation':evaluation,'ticketEvidence':receipt,
            'prodPick':{'horseNumber':no,'horseName':name,'rank':None,'odds':None}}


if __name__=="__main__":raise SystemExit(main())
