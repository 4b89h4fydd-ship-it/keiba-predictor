"""Local validation API and read-only UI. No imports of app.py or legacy engine."""
import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from .store import Store

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]


def handler(database):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, payload, content_type='application/json; charset=utf-8'):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            parsed = urlparse(self.path)
            path, query = unquote(parsed.path), parse_qs(parsed.query)
            assets = {'/':(ROOT/'index.html','text/html; charset=utf-8'),
                      '/slice.js':(ROOT/'slice.js','text/javascript; charset=utf-8'),
                      '/styles.css':(REPOSITORY/'arvexq/ui/static/styles.css','text/css; charset=utf-8')}
            if path in assets:
                asset, mime = assets[path]
                return self.send(200,asset.read_bytes(),mime)
            store = None
            try:
                store = Store(database, read_only=True)
                if path == '/api/v1/health':
                    records = store.list()
                    return self.send(200,{'ok':True,'engine':'independent-slice-v1',
                                         'verified_saved_races':len(records),'production_eligible':False})
                if path == '/api/v1/races':
                    races = [r['race'] for r in store.list()]
                    for field in ('date','circuit','track'):
                        if field in query:
                            races = [r for r in races if r[field]==query[field][0]]
                    return self.send(200,{'ok':True,'races':[{k:r[k] for k in ('id','date','circuit','track','title','race_number','declared_count','starts_at')} for r in races]})
                parts = path.strip('/').split('/')
                if len(parts) in (4,6) and parts[:3]==['api','v1','races']:
                    record=store.read(parts[3])
                    if len(parts)==4:
                        return self.send(200,record)
                    if parts[4]=='horses' and parts[5].isdigit():
                        number=int(parts[5])
                        horse=next((h for h in record['race']['horses'] if h['number']==number),None)
                        row=next((r for r in record['analysis']['rows'] if r['number']==number),None)
                        if horse and row:
                            return self.send(200,{'ok':True,'race_id':parts[3],'horse':horse,'analysis':row,
                                                 'quality':next(h for h in record['analysis']['quality']['horses'] if h['number']==number)})
                self.send(404,{'ok':False,'error':'not_found'})
            except KeyError:
                self.send(404,{'ok':False,'error':'race_not_found'})
            except (ValueError, sqlite3.DatabaseError):
                self.send(500,{'ok':False,'error':'stored_artifact_integrity_failed'})
            finally:
                if store is not None:
                    store.close()
    return Handler


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',required=True)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    print(f'ARVEXQ independent validation http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),handler(args.database)).serve_forever()
