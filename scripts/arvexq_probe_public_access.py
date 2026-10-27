"""Bounded public GET diagnosis; never reads credentials or changes Cloudflare."""
import argparse
import hashlib
import json
import urllib.request
import urllib.error
from datetime import datetime,timezone
from pathlib import Path


def probe():
    records=[]
    for url in ('https://kraizweb1.4b89h4fydd.workers.dev/',
                'https://kraiz-api.4b89h4fydd.workers.dev/api/health'):
        for agent in ('Python-urllib/3.12','ARVEXQ-Research/1.0 (read-only validation)'):
            try:
                response=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':agent}),timeout=25)
            except urllib.error.HTTPError as error:
                response=error
            raw=response.read()
            records.append({'url':url,'user_agent':agent,'checked_at':datetime.now(timezone.utc).isoformat(),
                            'status':response.status,'cf_ray':response.headers.get('cf-ray'),
                            'content_type':response.headers.get('content-type'),
                            'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                            'body_excerpt':raw[:180].decode('utf-8',errors='replace')})
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();records=probe()
    with args.output.open('x') as stream:json.dump(records,stream,ensure_ascii=False,indent=2)
    print(json.dumps(records,ensure_ascii=False,indent=2))
