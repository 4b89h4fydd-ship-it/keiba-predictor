"""Lossless D1 capacity recovery anchored to a fresh verified backup.

For every race_details row: read the current original through the fixed
export endpoint, cross-check it against the verified backup manifest
(sha256/bytes per race), archive any post-backup divergence to a local
supplementary JSONL BEFORE touching that row, then replace the stored
payload with the thin index + gzip envelope via the server-verified
compare-and-swap endpoint. Every stored envelope is read back and restored
to the exact original bytes before the next row is processed.

No deletes, no prediction computation, no changes to non-payload columns.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arvexq.ingest.full_snapshot_codec import KEY, pack_raw, unpack_raw

BASE = 'https://kraiz-api.4b89h4fydd.workers.dev'
SUPPLEMENTARY = Path('supplementary-originals.jsonl')
_archive_lock = threading.Lock()

# The production API rate-limits aggressively (HTTP 429, sometimes 503).
# Rate limiting means "slow down", not "stop": retry with exponential
# backoff (30s -> 60s -> 120s -> 240s, capped), honour Retry-After when
# the server sends one, and keep a small minimum spacing between any two
# request starts so bursts do not re-trigger the limiter. A job taking
# tens of minutes is acceptable; aborting the recovery is not.
MAX_ATTEMPTS = 6  # 1 initial try + up to 5 retries
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
BACKOFF_BASE_SECONDS = 30
BACKOFF_CAP_SECONDS = 240
THROTTLE_SECONDS = 0.5
_throttle_lock = threading.Lock()
_last_request_at = 0.0


def _throttle():
    global _last_request_at
    with _throttle_lock:
        wait = _last_request_at + THROTTLE_SECONDS - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _retry_delay(attempt, error):
    """Seconds to wait before the next attempt (attempt is 0-based)."""
    if isinstance(error, urllib.error.HTTPError) and error.headers is not None:
        retry_after = error.headers.get('Retry-After')
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass  # HTTP-date form: fall through to exponential backoff
    return min(BACKOFF_BASE_SECONDS * (2 ** attempt), BACKOFF_CAP_SECONDS)


def call(path, body=None, attempts=MAX_ATTEMPTS):
    data = None if body is None else json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
    request = urllib.request.Request(BASE + path, data=data, headers={
        'Authorization': 'Bearer ' + os.environ['SYNC_TOKEN'],
        'User-Agent': 'Mozilla/5.0 ARVEXQ-CapacityRecovery/1.0',
        'Content-Type': 'application/json', 'Accept': 'application/json'})
    for attempt in range(attempts):
        _throttle()
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except Exception as error:
            retryable = not isinstance(error, urllib.error.HTTPError) \
                or error.code in RETRYABLE_STATUSES
            if attempt == attempts - 1 or not retryable:
                print('RECOVERY_HTTP_FAILURE', path, type(error).__name__, flush=True)
                if isinstance(error, urllib.error.HTTPError):
                    print(error.read(600).decode('utf-8', 'replace'), flush=True)
                raise
            delay = _retry_delay(attempt, error)
            print('RECOVERY_HTTP_RETRY', path,
                  getattr(error, 'code', type(error).__name__),
                  'attempt', attempt + 1, 'sleep', delay, flush=True)
            time.sleep(delay)


def read_row(race_id):
    """Full row read; fall back to exact byte chunks for multi-MB payloads."""
    try:
        # Short probe only: if the single-shot read is not viable for this
        # row, fall back to the chunked reader quickly instead of burning
        # the full backoff schedule here. Chunk reads use the full retry.
        result = call('/api/admin/snapshot-export?' + urllib.parse.urlencode(
            {'table': 'race_details', 'race_id': race_id}), attempts=2)
        assert result['ok'] and len(result['rows']) == 1
        return result['rows'][0]
    except Exception:
        pass
    chunks = []
    first = None
    index = 0
    while True:
        result = call('/api/admin/snapshot-export?' + urllib.parse.urlencode(
            {'table': 'race_details', 'race_id': race_id, 'chunk': index}))
        assert result['ok'] and len(result['rows']) == 1
        row = result['rows'][0]
        if first is None:
            first = row
        assert all(row[key] == first[key] for key in
                   ['race_id', 'race_date', 'analysis_ready', 'updated_at', 'payload_bytes']), \
            'concurrent metadata update'
        chunks.append(bytes.fromhex(row['payload_hex']))
        if sum(map(len, chunks)) >= first['payload_bytes']:
            break
        index += 1
    raw = b''.join(chunks)
    assert len(raw) == first['payload_bytes']
    return {key: value for key, value in first.items()
            if key not in ['payload_bytes', 'payload_hex']} | {'payload': raw.decode('utf-8')}


def original_of(payload_text):
    parsed = json.loads(payload_text)
    if isinstance(parsed, dict) and KEY in parsed:
        return unpack_raw(parsed), True
    return payload_text, False


def archive_supplementary(race_id, race_date, original):
    line = json.dumps({'race_id': race_id, 'race_date': race_date, 'payload': original},
                      ensure_ascii=False, separators=(',', ':'))
    with _archive_lock:
        with SUPPLEMENTARY.open('a', encoding='utf-8') as handle:
            handle.write(line + '\n')
            handle.flush()


def recover(manifest_path):
    path = Path(manifest_path)
    manifest = json.loads(path.read_bytes())
    assert manifest['restore_verified'] is True and manifest['original_sql_writes'] == 0
    # Confirm the encrypted durable transport of the verified backup is intact.
    digest = hashlib.sha256()
    for name in manifest['encrypted_parts']:
        digest.update((path.parent / name).read_bytes())
    assert digest.hexdigest() == manifest['encrypted_sha256']
    anchor = manifest['races']
    assert manifest['tables']['race_details']['rows'] == len(anchor)

    before = call('/api/admin/storage-audit')
    index = call('/api/admin/snapshot-export')
    assert index['ok']
    live = sorted(index['races'], key=lambda r: (r['race_date'], r['race_id']))
    totals = {'verified': 0, 'compressed': 0, 'already_compressed': 0,
              'skipped_no_saving': 0, 'diverged_archived': 0,
              'original_bytes': 0, 'stored_bytes': 0}
    diverged_ids = []

    def one(entry):
        race_id = entry['race_id']
        row = read_row(race_id)
        payload_text = row['payload']
        original, was_compressed = original_of(payload_text)
        raw = original.encode('utf-8')
        osha = hashlib.sha256(raw).hexdigest()
        expected = anchor.get(race_id)
        diverged = expected is None or expected['sha256'] != osha
        if diverged:
            # Archive the exact current original BEFORE any change to this row.
            archive_supplementary(race_id, row['race_date'], original)
        if was_compressed:
            return len(raw), len(payload_text.encode('utf-8')), 'already', diverged, race_id
        packed = pack_raw(original)
        response = call('/api/admin/snapshot-compress', {
            'race_id': race_id, 'expected_sha256': osha, 'payload': packed})
        assert response['ok'], race_id
        if response.get('skipped_no_saving'):
            return len(raw), len(raw), 'skipped', diverged, race_id
        if response.get('already_compressed'):
            return len(raw), len(raw), 'already', diverged, race_id
        restored_row = read_row(race_id)
        assert {k: v for k, v in row.items() if k != 'payload'} == \
               {k: v for k, v in restored_row.items() if k != 'payload'}, \
            'metadata changed: ' + race_id
        restored, now_compressed = original_of(restored_row['payload'])
        assert now_compressed and restored == original, 'restore mismatch: ' + race_id
        return len(raw), len(restored_row['payload'].encode('utf-8')), 'compressed', diverged, race_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for original_bytes, stored_bytes, kind, diverged, race_id in pool.map(one, live):
            totals['verified'] += 1
            totals['original_bytes'] += original_bytes
            totals['stored_bytes'] += stored_bytes
            if kind == 'compressed':
                totals['compressed'] += 1
            elif kind == 'already':
                totals['already_compressed'] += 1
            elif kind == 'skipped':
                totals['skipped_no_saving'] += 1
            if diverged:
                totals['diverged_archived'] += 1
                diverged_ids.append(race_id)
            if totals['verified'] % 50 == 0:
                print('D1_RECOVERY_PROGRESS', json.dumps(totals), flush=True)

    after = call('/api/admin/storage-audit')
    assert before['queries']['details']['results'][0]['rows'] == \
           after['queries']['details']['results'][0]['rows'], 'race_details row count changed'
    report = {'version': 'arvexq-d1-capacity-recovery-v1',
              'backup_manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'all_originals_retained_in_verified_backup_or_supplementary': True,
              'every_stored_envelope_restore_verified': True,
              'deletes': 0, **totals,
              'diverged_race_ids': sorted(diverged_ids),
              'before': before, 'after': after}
    Path('d1-compress-recovery-report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2))
    print('D1_COMPRESS_RECOVERY_PASS', json.dumps(report), flush=True)


if __name__ == '__main__':
    recover(sys.argv[1])
