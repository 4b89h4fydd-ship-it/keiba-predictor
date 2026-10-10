"""Read existing bound D1 metrics through a private temporary Worker; no SQL writes."""
import json
import os
from pathlib import Path
import secrets
import time
import urllib.request
import urllib.error

SOURCE = '''export default {async fetch(request,env){
if(request.headers.get('authorization')!=='Bearer '+env.AUDIT_TOKEN)return new Response(null,{status:401});
const statements={page_count:'PRAGMA page_count',page_size:'PRAGMA page_size',
details:'SELECT COUNT(*) AS rows, SUM(length(CAST(payload AS BLOB))) AS payload_bytes, MIN(race_date) AS first_date, MAX(race_date) AS last_date FROM race_details',
summaries:'SELECT COUNT(*) AS rows FROM race_summaries',
odds_current:'SELECT COUNT(*) AS rows FROM odds_current',
odds_history:'SELECT COUNT(*) AS rows FROM odds_history'};
const queries={};for(const [name,sql] of Object.entries(statements)){
try{const result=await env.DB.prepare(sql).all();queries[name]={results:result.results,meta:result.meta}}
catch(e){queries[name]={error:String(e.message||e)}}}
return Response.json({version:'arvexq-bound-d1-readonly-v1',sql_writes:0,queries});
}};'''

def run():
    token=os.environ['CLOUDFLARE_API_TOKEN']
    base='https://api.cloudflare.com/client/v4/accounts/'+os.environ['CLOUDFLARE_ACCOUNT_ID']
    name='kraiz-storage-readonly-audit'
    report={'sql_writes':0,'existing_workers_modified':0,'temporary_worker':name}
    def call(path,method='GET',data=None,content_type='application/json'):
        req=urllib.request.Request(base+path,data=data,method=method,headers={
            'Authorization':'Bearer '+token,'Content-Type':content_type})
        with urllib.request.urlopen(req,timeout=45) as response:
            return json.loads(response.read())
    created=False
    try:
        try:
            call('/workers/scripts/'+name)
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
        else:
            raise RuntimeError('temporary-worker-already-exists-refusing-to-overwrite')
        location=json.loads(Path('api-worker-location-audit.json').read_text())
        bindings=location['settings']['bindings']
        db=next(b['database_id'] for b in bindings if b['name']=='DB' and b['type']=='d1')
        access=secrets.token_urlsafe(32)
        metadata={'main_module':'audit.mjs','compatibility_date':'2026-09-29','bindings':[
            {'type':'d1','name':'DB','id':db},
            {'type':'plain_text','name':'AUDIT_TOKEN','text':access}]}
        boundary='arvexq'+secrets.token_hex(16)
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n'
              'Content-Type: application/json\r\n\r\n'+json.dumps(metadata)+'\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="audit.mjs"; filename="audit.mjs"\r\n'
              'Content-Type: application/javascript+module\r\n\r\n'+SOURCE+'\r\n'
              f'--{boundary}--\r\n').encode()
        result=call('/workers/scripts/'+name,'PUT',body,'multipart/form-data; boundary='+boundary)
        if not result.get('success'):raise RuntimeError('temporary-worker-create-denied')
        created=True
        call('/workers/scripts/'+name+'/subdomain','POST',b'{"enabled":true}')
        sub=call('/workers/subdomain')['result']['subdomain']
        req=urllib.request.Request('https://'+name+'.'+sub+'.workers.dev/',headers={'Authorization':'Bearer '+access})
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req,timeout=45) as response:
                    report['metrics']=json.loads(response.read())
                break
            except urllib.error.HTTPError as e:
                if e.code not in (404,503) or attempt==5:raise
                time.sleep(2)
    except urllib.error.HTTPError as e:
        report['http_error']=e.code
    except Exception as e:
        report['error']=str(e)
    finally:
        if created:
            try:
                result=call('/workers/scripts/'+name,'DELETE')
                report['temporary_worker_removed']=bool(result.get('success'))
            except Exception:
                report['temporary_worker_removed']=False
        Path('bound-d1-storage-audit.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))

if __name__=='__main__':run()
