"""Copy existing SQLite snapshots losslessly; never run prediction or write D1.

Content-addressed originals are immutable and round-trip verified before publish.
The date manifest is first-write-wins per race. No old file is deleted.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
import json
import re
import sqlite3
from pathlib import Path


def envelope(raw: str) -> dict:
    data = raw.encode('utf-8')
    compressed = gzip.compress(data, mtime=0)
    if gzip.decompress(compressed) != data:
        raise ValueError('snapshot restore mismatch')
    return {'version': 'arvexq-saved-snapshot-v1', 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'gzipBase64': base64.b64encode(compressed).decode('ascii')}


def publish(root: Path, directory: Path, date: str, payload: dict | None = None) -> dict:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        raise ValueError('invalid date')
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / (date + '.json')
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        'version': 'arvexq-saved-snapshots-v1', 'date': date, 'races': {}}
    if manifest.get('version') != 'arvexq-saved-snapshots-v1' or manifest.get('date') != date:
        raise ValueError('snapshot manifest identity mismatch')
    candidates = {}
    databases = []
    def consider(rid, stamp, raw, table):
        d = json.loads(raw)
        if str(d.get('id')) != str(rid) or d.get('date') != date:
            return False
        hs = d.get('horses') or []
        numbers = [h.get('horseNumber') for h in hs if isinstance(h, dict)]
        if len(hs) < 2 or len(numbers) != len(hs) or len(set(numbers)) != len(hs) or not all(
                isinstance(n, int) and n > 0 for n in numbers) or not all(h.get('name') for h in hs):
            return False
        if int(d.get('fieldSize') or 0) > len(hs):
            return False
        quality = (sum(bool(d.get(k)) for k in ('morningMarkSnapshot', 'preRacePrediction', 'preRaceBet', 'morningTicketEvidence')),
                   int(table == 'payload'), int(table == 'prepared_races'), int(stamp or 0))
        if rid not in candidates or quality > candidates[rid][0]:
            candidates[rid] = (quality, raw, d)
        return True
    for path in sorted(root.rglob('*.sqlite3')):
        conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('prepared_races', 'race_snapshots'):
                if table not in tables:
                    continue
                count = 0
                for rid, stamp, raw in conn.execute(
                        f'SELECT race_id,updated_at,payload FROM {table} WHERE race_date=?', (date,)):
                    if consider(rid, stamp, raw, table):
                        count += 1
                databases.append({'file': str(path.relative_to(root)), 'table': table, 'races': count})
        finally:
            conn.close()
    if payload is not None:
        for d in payload.get('details') or []:
            if isinstance(d, dict) and d.get('id'):
                consider(str(d['id']), 0, json.dumps(d, ensure_ascii=False, separators=(',', ':')), 'payload')
    added = 0
    for rid, (_, raw, d) in sorted(candidates.items()):
        if rid in manifest['races']:
            continue
        e = envelope(raw)
        name = e['sha256'] + '.json'
        target = directory / name
        serialized = json.dumps(e, ensure_ascii=False, separators=(',', ':'))
        if len(serialized.encode()) >= 24_000_000:
            raise ValueError('snapshot exceeds static asset size limit')
        if target.exists() and target.read_text() != serialized:
            raise ValueError('immutable snapshot collision')
        if not target.exists():
            target.write_text(serialized, encoding='utf-8')
        # Verify the published file, not just the compression function.
        saved = json.loads(target.read_text())
        restored = gzip.decompress(base64.b64decode(saved['gzipBase64']))
        if restored.decode() != raw or hashlib.sha256(restored).hexdigest() != saved['sha256']:
            raise ValueError('published snapshot restore mismatch')
        manifest['races'][rid] = {'file': name, 'sha256': e['sha256'], 'bytes': e['bytes'],
            'horses': len(d['horses']), 'morningMarks': bool(d.get('morningMarkSnapshot')),
            'prediction': bool(d.get('preRacePrediction')), 'bet': bool(d.get('preRaceBet'))}
        added += 1
    if manifest['races']:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    report = {'date': date, 'added': added, 'races': len(manifest['races']),
              'databases': databases, 'restoreVerified': True, 'd1Writes': 0,
              'originalsModified': 0, 'predictionsRecalculated': 0}
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--directory', type=Path, default=Path('arvexq/ui/static/saved-snapshots'))
    p.add_argument('--date', required=True)
    p.add_argument('--input', type=Path)
    a = p.parse_args()
    publish(a.root, a.directory, a.date, json.loads(a.input.read_text()) if a.input else None)
