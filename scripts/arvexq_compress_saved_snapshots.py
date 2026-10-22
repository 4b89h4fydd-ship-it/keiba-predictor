"""Compress eligible originals through the existing CAS-guarded snapshot API."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import urllib.parse
import urllib.request

from arvexq.ingest.full_snapshot_codec import KEY, pack_raw, unpack_raw


def compress(source, base, token):
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
               'User-Agent': 'Mozilla/5.0 ARVEXQ-LosslessStorage/1.0'}
    def request(path, value=None):
        data = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode() if value is not None else None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=headers), timeout=60) as response:
                    return json.load(response)
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    with sqlite3.connect('file:' + str(source) + '?mode=ro', uri=True) as db:
        candidates = list(db.execute("SELECT race_id,payload FROM race_details WHERE json_extract(payload,'$.arvexqFullPayload.version') IS NULL"))
    def one(row):
        rid, raw = row
        packed = pack_raw(raw)
        if len(json.dumps(packed, ensure_ascii=False, separators=(',', ':')).encode()) >= len(raw.encode()):
            return {'raceId': rid, 'status': 'no-saving'}
        digest = hashlib.sha256(raw.encode()).hexdigest()
        result = request('/api/admin/snapshot-compress', {'race_id': rid, 'expected_sha256': digest, 'payload': packed})
        assert result.get('ok'), result
        if result.get('skipped_no_saving'):
            return {'raceId': rid, 'status': 'no-saving'}
        exported = request('/api/admin/snapshot-export?' + urllib.parse.urlencode({'table': 'race_details', 'race_id': rid}))
        assert exported.get('ok') and len(exported['rows']) == 1
        stored = json.loads(exported['rows'][0]['payload'])
        assert KEY in stored and unpack_raw(stored) == raw, 'ORIGINAL_RAW_RESTORE_MISMATCH'
        return {'raceId': rid, 'status': 'compressed-and-restored', 'originalSha256': digest,
                'originalBytes': len(raw.encode()), 'storedBytes': len(exported['rows'][0]['payload'].encode())}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, candidates))
    report = {'candidateOriginals': len(candidates), 'results': results, 'allRestored': True}
    Path('/tmp/forecast-revisions/original-compression-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('ELIGIBLE_ORIGINAL_SNAPSHOTS_COMPRESSED_AND_RESTORED', len(results), flush=True)
    return report


if __name__ == '__main__':
    compress('/tmp/arvexq-complete-d1.sqlite3', 'https://kraiz-api.4b89h4fydd.workers.dev', os.environ['SYNC_TOKEN'])
