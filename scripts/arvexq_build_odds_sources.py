"""Build bounded, observed race identities for independent real-odds transport."""
import base64
import gzip
import hashlib
import json
from pathlib import Path


def build_sources(static: Path, dist: Path):
    directory = static / 'saved-snapshots'
    if not directory.is_dir():
        return
    target = dist / 'odds-sources'
    target.mkdir(exist_ok=True)
    for path in directory.glob('????-??-??.json'):
        manifest = json.loads(path.read_text())
        if manifest.get('version') != 'arvexq-saved-snapshots-v1':
            raise ValueError('invalid original manifest')
        races = {}
        for rid, ref in manifest['races'].items():
            if ref['file'] != ref['sha256']+'.json':
                raise ValueError('invalid original path')
            envelope = json.loads((directory / ref['file']).read_text())
            raw = gzip.decompress(base64.b64decode(envelope['gzipBase64']))
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('original restore hash mismatch')
            d = json.loads(raw)
            if d.get('id') != rid or d.get('date') != manifest['date']:
                raise ValueError('original source identity mismatch')
            races[rid] = {k: d[k] for k in ('id','date','circuit','track','raceNumber','netkeibaRaceId') if k in d}
            races[rid]['horses'] = [{'horseNumber': h['horseNumber'], 'name': h['name']} for h in d['horses']]
        (target / path.name).write_text(json.dumps({'version':'arvexq-odds-sources-v1',
            'date':manifest['date'],'races':races}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
