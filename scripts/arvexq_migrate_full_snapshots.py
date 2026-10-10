"""Compare-and-swap lossless migration, anchored to a verified full backup.

No deletes, no prediction computation, no changes to non-payload columns.
Every stored envelope is read back and restored to the exact backup hash.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arvexq.ingest.full_snapshot_codec import KEY, pack_raw, unpack_raw

BASE = 'https://kraiz-api.4b89h4fydd.workers.dev'

def call(path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
    request = urllib.request.Request(BASE + path, data=data, headers={
        'Authorization': 'Bearer ' + os.environ['SYNC_TOKEN'],
        'User-Agent': 'Mozilla/5.0 ARVEXQ-ProtectedMigration/1.0',
        'Content-Type': 'application/json', 'Accept': 'application/json'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1 + attempt)

def migrate(manifest_path):
    path = Path(manifest_path)
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == os.environ['VERIFIED_BACKUP_MANIFEST_SHA256']
    manifest = json.loads(data)
    assert manifest['restore_verified'] is True and manifest['original_sql_writes'] == 0
    assert manifest['tables']['race_details']['rows'] == len(manifest['races'])
    # The independently decrypted/reopened full SQLite has already been verified.
    # Check that its encrypted durable transport is still exactly available.
    digest = hashlib.sha256()
    for name in manifest['encrypted_parts']:
        digest.update((path.parent / name).read_bytes())
    assert digest.hexdigest() == manifest['encrypted_sha256']
    before = call('/api/admin/storage-audit')
    totals = {'verified': 0, 'original_bytes': 0, 'stored_bytes': 0}
    def read(race_id):
        result = call('/api/admin/snapshot-export?' + urllib.parse.urlencode({'table':'race_details','race_id':race_id}))
        assert result['ok'] and len(result['rows']) == 1
        return result['rows'][0]
    def one(item):
        race_id, proof = item
        row = read(race_id)
        raw = row['payload']
        parsed = json.loads(raw)
        if KEY in parsed:
            original = unpack_raw(parsed)
        else:
            original = raw
        assert hashlib.sha256(original.encode()).hexdigest() == proof['sha256'], 'changed original: '+race_id
        if KEY not in parsed:
            packed = pack_raw(original)
            response = call('/api/admin/snapshot-compress', {
                'race_id':race_id, 'expected_sha256':proof['sha256'], 'payload':packed})
            assert response['ok'], race_id
            restored_row = read(race_id)
            assert {k:v for k,v in row.items() if k!='payload'} == {k:v for k,v in restored_row.items() if k!='payload'}, 'metadata changed'
            raw = restored_row['payload']
            parsed = json.loads(raw)
        restored = unpack_raw(parsed) if KEY in parsed else raw
        assert restored == original, 'restore mismatch: '+race_id
        return len(original.encode()), len(raw.encode())
    # Old dates first; release occupied pages before today's original snapshots.
    items = sorted(manifest['races'].items(), key=lambda x:(x[1]['race_date'], x[0]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for original_bytes, stored_bytes in pool.map(one, items):
            totals['verified'] += 1
            totals['original_bytes'] += original_bytes
            totals['stored_bytes'] += stored_bytes
            if totals['verified'] % 50 == 0:
                print('D1_LOSSLESS_MIGRATION_PROGRESS', json.dumps(totals), flush=True)
    after = call('/api/admin/storage-audit')
    # All original rows retained. Other tables are not written by this migration.
    assert before['queries']['details']['results'][0]['rows'] == after['queries']['details']['results'][0]['rows']
    report = {'version':'arvexq-lossless-migration-v1', 'backup_manifest_sha256':hashlib.sha256(data).hexdigest(),
              'all_originals_restored':True, 'original_metadata_unchanged':True,
              'deletes':0, **totals, 'before':before, 'after':after}
    Path('d1-lossless-migration-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('D1_LOSSLESS_MIGRATION_PASS', json.dumps(report), flush=True)

if __name__ == '__main__':
    migrate(sys.argv[1])
