"""Build and reopen a complete logical backup of all five application tables.

Reads only the authenticated, fixed-query export endpoint. No original DB writes.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import urllib.parse
import urllib.request

def canonical(value):
    if value is None:return ['null']
    if isinstance(value,(int,float)):return ['number',format(value,'.17g')]
    return ['text',value]

def row_hash(row):
    data={key:canonical(value) for key,value in sorted(row.items())}
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def aggregate(hashes):
    return hashlib.sha256('\n'.join(sorted(hashes)).encode()).hexdigest()

def backup(fetch,destination):
    manifest=fetch({})
    assert manifest['ok'] and manifest['sql_writes']==0
    assert set(manifest['tables'])=={'race_details','race_summaries','odds_current','odds_history','meta'}
    destination=Path(destination)
    if destination.exists():raise RuntimeError('backup destination already exists')
    conn=sqlite3.connect(destination)
    conn.row_factory=sqlite3.Row
    expected={table:[] for table in manifest['tables']}
    payloads={}
    def insert(table,row):
        names=list(row)
        assert all(re.fullmatch('[a-zA-Z_][a-zA-Z_0-9]*',name) for name in names)
        sql='INSERT INTO "'+table+'" ('+','.join('"'+name+'"' for name in names)+') VALUES ('+','.join('?' for _ in names)+')'
        conn.execute(sql,[row[name] for name in names])
        expected[table].append(row_hash(row))
        if table=='race_details':
            raw=row['payload'].encode('utf-8')
            payloads[row['race_id']]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'race_date':row['race_date']}
    try:
        for schema in manifest['schema']:
            if schema['type']=='table':
                assert re.match(r'^CREATE\s+TABLE\b',schema['sql'],re.I)
                conn.execute(schema['sql'])
        for table in manifest['tables']:
            if table=='race_details':
                def read(race):
                    result=fetch({'table':table,'race_id':race['race_id']})
                    assert result['ok'] and len(result['rows'])==1
                    row=result['rows'][0];assert row['race_id']==race['race_id']
                    return row
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                    futures=[pool.submit(read,race) for race in manifest['races']]
                    for index,future in enumerate(concurrent.futures.as_completed(futures),1):
                        insert(table,future.result())
                        if index%100==0:print('D1_BACKUP_READ',index,flush=True)
            else:
                offset=0
                while True:
                    result=fetch({'table':table,'offset':offset,'limit':500})
                    assert result['ok'] and result['table']==table
                    rows=result['rows']
                    for row in rows:insert(table,row)
                    offset+=len(rows)
                    if len(rows)<500:break
        for schema in manifest['schema']:
            if schema['type']=='index':
                assert re.match(r'^CREATE\s+(?:UNIQUE\s+)?INDEX\b',schema['sql'],re.I)
                conn.execute(schema['sql'])
        conn.commit()
    finally:conn.close()
    with sqlite3.connect(destination) as restored:
        restored.row_factory=sqlite3.Row
        assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        tables={}
        for table in manifest['tables']:
            actual=[row_hash(dict(row)) for row in restored.execute('SELECT * FROM "'+table+'"')]
            assert len(actual)==len(expected[table]) and aggregate(actual)==aggregate(expected[table]),'restored table mismatch '+table
            tables[table]={'rows':len(actual),'sha256':aggregate(actual)}
        for row in restored.execute('SELECT race_id,payload FROM race_details'):
            raw=row['payload'].encode('utf-8');ref=payloads[row['race_id']]
            assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    summary={'version':'arvexq-full-logical-backup-v1','restore_verified':True,'original_sql_writes':0,
             'tables':tables,'races':payloads,'schema':manifest['schema']}
    return summary

def main():
    base='https://kraiz-api.4b89h4fydd.workers.dev/api/admin/snapshot-export'
    headers={'Authorization':'Bearer '+os.environ['SYNC_TOKEN'],'User-Agent':'Mozilla/5.0 ARVEXQ-ReadOnlyAudit/1.0','Accept':'application/json'}
    def fetch(params):
        req=urllib.request.Request(base+'?'+urllib.parse.urlencode(params),headers=headers)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)
            except Exception:
                if attempt==4:raise
                time.sleep(attempt+1)
    summary=backup(fetch,'/tmp/arvexq-complete-d1.sqlite3')
    digest=hashlib.sha256()
    with open('/tmp/arvexq-complete-d1.sqlite3','rb') as source:
        for chunk in iter(lambda:source.read(1048576),b''):digest.update(chunk)
    summary['sqlite_sha256']=digest.hexdigest()
    Path('/tmp/arvexq-complete-d1-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print('D1_FULL_LOGICAL_RESTORE_VERIFIED',json.dumps(summary['tables']))

if __name__=='__main__':main()
