"""Offload old race_details payloads from Cloudflare D1 to a file archive.

Design (user-approved 2026-11-21): past race details live outside D1; D1
keeps only the most recent days. This script is the client for that flow:

  export   Read every race_details row older than the retention cutoff
           through the authenticated fixed-query export endpoint (byte
           exact, chunked hex when needed) and write a per-date archive:
             <archive-dir>/details/<date>.jsonl.gz   (one JSON line/race)
             <archive-dir>/manifests/<date>.json     (sha256 per race)
             <archive-dir>/index.json                (date -> manifest)
           Every archive is re-read and fully verified (file hash, line
           count, per-race payload sha256/bytes) before export returns.
           Existing archives are skipped only when the live index shows
           the same race set and the same updated_at for every race;
           any divergence re-exports that date (self-healing).

  verify   Re-check archive files against their manifests. No API writes.

  prune    For each archived date older than the cutoff, ask the server
           (POST /api/admin/snapshot-prune) to delete rows. The server
           deletes a row only when the SHA-256 of the payload bytes it
           currently stores equals the archived hash AND the row's
           race_date is older than the cutoff (compare-and-delete).
           Default is dry-run; pass --execute to actually delete.

  restore  Disaster-recovery helper: re-insert one archived date through
           the normal /api/sync upsert (payload string stored verbatim,
           archived analysis_ready/updated_at preserved) and verify the
           read-back SHA-256 of every race against the manifest.

Banei (Obihiro) rows are never exported, pruned, or restored here.
All API calls retry 429/5xx with exponential backoff (30s -> 240s cap),
honour Retry-After, and keep a 0.5s minimum spacing between request
starts: rate limiting means "slow down", not "stop".
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import date as date_type, datetime, timedelta
from zoneinfo import ZoneInfo

BASE = os.environ.get('ARVEXQ_API_BASE', 'https://kraiz-api.4b89h4fydd.workers.dev')
ARCHIVE_VERSION = 'arvexq-d1-details-archive-v1'
BANEI = re.compile(r'^nar-\d{4}-\d{2}-\d{2}-(?:帯広|帯広ば)-\d{2}$')

MAX_ATTEMPTS = 6  # 1 initial try + up to 5 retries
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
BACKOFF_BASE_SECONDS = 30
BACKOFF_CAP_SECONDS = 240
THROTTLE_SECONDS = 0.5
_last_request_at = 0.0


def _throttle():
    global _last_request_at
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


def call(path, body=None, attempts=MAX_ATTEMPTS, quiet=False):
    data = None if body is None else json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
    request = urllib.request.Request(BASE + path, data=data, headers={
        'Authorization': 'Bearer ' + os.environ['SYNC_TOKEN'],
        'User-Agent': 'Mozilla/5.0 ARVEXQ-D1Offload/1.0',
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
                if not quiet:
                    print('OFFLOAD_HTTP_FAILURE', path, type(error).__name__,
                          getattr(error, 'code', ''), flush=True)
                    if isinstance(error, urllib.error.HTTPError):
                        print(error.read(600).decode('utf-8', 'replace'), flush=True)
                raise
            delay = _retry_delay(attempt, error)
            print('OFFLOAD_HTTP_RETRY', path,
                  getattr(error, 'code', type(error).__name__),
                  'attempt', attempt + 1, 'sleep', delay, flush=True)
            time.sleep(delay)


def storage_audit():
    result = call('/api/admin/storage-audit')
    assert result.get('ok'), 'storage-audit failed'
    return result


def audit_totals(audit):
    queries = audit.get('queries') or {}
    page_count = (queries.get('page_count') or {}).get('results', [{}])[0].get('page_count')
    page_size = (queries.get('page_size') or {}).get('results', [{}])[0].get('page_size')
    details = (queries.get('details') or {}).get('results', [{}])[0]
    return {
        'page_count': page_count,
        'page_size': page_size,
        'db_bytes': page_count * page_size if page_count is not None and page_size is not None else None,
        'race_details_rows': details.get('rows'),
        'race_details_payload_bytes': details.get('payload_bytes'),
        'race_details_first_date': details.get('first_date'),
        'race_details_last_date': details.get('last_date'),
    }


def export_index():
    result = call('/api/admin/snapshot-export')
    assert result.get('ok') and result.get('sql_writes') == 0, 'snapshot-export manifest failed'
    return result


def read_row(race_id):
    """Full row read as exact bytes; chunked hex fallback for big payloads."""
    try:
        # Short probe only; fall back to chunked reads quickly instead of
        # burning the full backoff schedule on a non-viable single read.
        result = call('/api/admin/snapshot-export?' + urllib.parse.urlencode(
            {'table': 'race_details', 'race_id': race_id}), attempts=2, quiet=True)
        assert result['ok'] and len(result['rows']) == 1
        row = result['rows'][0]
        return {
            'race_id': row['race_id'], 'race_date': row['race_date'],
            'analysis_ready': row['analysis_ready'], 'updated_at': row['updated_at'],
            'payload': row['payload'].encode('utf-8'),
        }
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
    payload = b''.join(chunks)
    assert len(payload) == first['payload_bytes'], 'chunked read byte count mismatch'
    return {
        'race_id': first['race_id'], 'race_date': first['race_date'],
        'analysis_ready': first['analysis_ready'], 'updated_at': first['updated_at'],
        'payload': payload,
    }


def is_banei(race_id):
    return bool(BANEI.match(race_id or ''))


def cutoff_for(today, keep_days):
    return (today - timedelta(days=keep_days)).isoformat()


def archive_paths(archive_dir, race_date):
    root = Path(archive_dir)
    return (root / 'details' / f'{race_date}.jsonl.gz',
            root / 'manifests' / f'{race_date}.json')


def load_manifest(archive_dir, race_date):
    _, manifest_path = archive_paths(archive_dir, race_date)
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding='utf-8'))


def verify_archive(archive_dir, race_date):
    """Full check: file hash, line count, per-race payload hash/bytes.

    Returns the manifest on success; raises AssertionError otherwise.
    """
    data_path, manifest_path = archive_paths(archive_dir, race_date)
    assert manifest_path.exists(), f'manifest missing for {race_date}'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest.get('version') == ARCHIVE_VERSION, f'manifest version mismatch {race_date}'
    assert manifest.get('date') == race_date, f'manifest date mismatch {race_date}'
    assert data_path.exists(), f'archive file missing for {race_date}'
    raw = data_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest['archive_sha256'], \
        f'archive file hash mismatch {race_date}'
    entries = {entry['race_id']: entry for entry in manifest['races']}
    assert len(entries) == manifest['race_count'], f'manifest race_count mismatch {race_date}'
    seen = set()
    with gzip.open(data_path, 'rt', encoding='utf-8') as source:
        for line in source:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            race_id = record['race_id']
            assert race_id in entries, f'{race_date}: unlisted race {race_id} in archive'
            assert race_id not in seen, f'{race_date}: duplicate race {race_id} in archive'
            seen.add(race_id)
            payload = record['payload'].encode('utf-8')
            entry = entries[race_id]
            assert len(payload) == entry['bytes'] == record['payload_bytes'], \
                f'{race_date}: byte count mismatch {race_id}'
            assert hashlib.sha256(payload).hexdigest() == entry['sha256'] == record['payload_sha256'], \
                f'{race_date}: payload hash mismatch {race_id}'
            assert record['race_date'] == race_date, f'{race_date}: line date mismatch {race_id}'
    assert seen == set(entries), f'{race_date}: archive/manifest race set mismatch'
    return manifest


def export_one_date(archive_dir, race_date, races):
    """Export one date's rows (races = live index entries) and verify."""
    data_path, manifest_path = archive_paths(archive_dir, race_date)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    entries = []
    for race in sorted(races, key=lambda r: r['race_id']):
        row = read_row(race['race_id'])
        assert row['race_date'] == race_date, f"race_date changed for {race['race_id']}"
        payload = row['payload']
        digest = hashlib.sha256(payload).hexdigest()
        entries.append({
            'race_id': race['race_id'], 'sha256': digest, 'bytes': len(payload),
            'analysis_ready': row['analysis_ready'], 'updated_at': row['updated_at'],
        })
        lines.append(json.dumps({
            'race_id': race['race_id'], 'race_date': race_date,
            'analysis_ready': row['analysis_ready'], 'updated_at': row['updated_at'],
            'payload_bytes': len(payload), 'payload_sha256': digest,
            'payload': payload.decode('utf-8'),
        }, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    blob = ('\n'.join(lines) + '\n').encode('utf-8')
    with open(data_path, 'wb') as target:
        target.write(gzip.compress(blob, compresslevel=9, mtime=0))
    manifest = {
        'version': ARCHIVE_VERSION,
        'date': race_date,
        'exported_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'race_count': len(entries),
        'payload_bytes_total': sum(entry['bytes'] for entry in entries),
        'archive_file': f'details/{race_date}.jsonl.gz',
        'archive_bytes': data_path.stat().st_size,
        'archive_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(),
        'races': entries,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    verify_archive(archive_dir, race_date)
    return manifest


def update_index(archive_dir, manifests):
    root = Path(archive_dir)
    index_path = root / 'index.json'
    index = {'version': ARCHIVE_VERSION, 'dates': {}}
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding='utf-8'))
        assert index.get('version') == ARCHIVE_VERSION, 'index version mismatch'
    for manifest in manifests:
        index['dates'][manifest['date']] = {
            'races': manifest['race_count'],
            'payload_bytes': manifest['payload_bytes_total'],
            'archive_bytes': manifest['archive_bytes'],
            'archive_sha256': manifest['archive_sha256'],
            'manifest': f"manifests/{manifest['date']}.json",
            'file': manifest['archive_file'],
        }
    index['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    return index


def mode_export(args):
    today = date_type.fromisoformat(args.today) if args.today \
        else datetime.now(ZoneInfo('Asia/Tokyo')).date()
    before_date = cutoff_for(today, args.keep_days)
    audit_before = audit_totals(storage_audit())
    index = export_index()
    by_date = {}
    for race in index.get('races') or []:
        if race['race_date'] < before_date and not is_banei(race['race_id']):
            by_date.setdefault(race['race_date'], []).append(race)
    exported, skipped, refreshed = [], [], []
    manifests = []
    for race_date in sorted(by_date):
        if args.max_dates and len(exported) + len(refreshed) >= args.max_dates:
            print('OFFLOAD_EXPORT_MAX_DATES_REACHED', args.max_dates, flush=True)
            break
        races = by_date[race_date]
        existing = load_manifest(args.archive_dir, race_date)
        if existing is not None:
            live = {r['race_id']: r['updated_at'] for r in races}
            archived = {e['race_id']: e['updated_at'] for e in existing['races']}
            if live == archived:
                verify_archive(args.archive_dir, race_date)
                skipped.append(race_date)
                manifests.append(existing)
                print('OFFLOAD_EXPORT_SKIP_VERIFIED', race_date, existing['race_count'], flush=True)
                continue
            print('OFFLOAD_EXPORT_REFRESH', race_date, 'live index diverged from archive', flush=True)
            refreshed.append(race_date)
        else:
            exported.append(race_date)
        manifest = export_one_date(args.archive_dir, race_date, races)
        manifests.append(manifest)
        print('OFFLOAD_EXPORT_DONE', race_date, manifest['race_count'],
              manifest['payload_bytes_total'], '->', manifest['archive_bytes'], flush=True)
    if manifests:
        update_index(args.archive_dir, manifests)
    summary = {
        'mode': 'export', 'today': today.isoformat(), 'keep_days': args.keep_days,
        'before_date': before_date, 'audit_before': audit_before,
        'dates_exported': exported, 'dates_refreshed': refreshed, 'dates_skipped_verified': skipped,
        'races': sum(m['race_count'] for m in manifests),
        'payload_bytes': sum(m['payload_bytes_total'] for m in manifests),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def mode_verify(args):
    root = Path(args.archive_dir)
    dates = [args.date] if args.date else \
        sorted(json.loads((root / 'index.json').read_text(encoding='utf-8'))['dates'])
    total_races = 0
    for race_date in dates:
        manifest = verify_archive(args.archive_dir, race_date)
        total_races += manifest['race_count']
        print('OFFLOAD_VERIFY_OK', race_date, manifest['race_count'],
              manifest['payload_bytes_total'], flush=True)
    print(json.dumps({'mode': 'verify', 'dates': dates, 'races': total_races}, ensure_ascii=False))
    return 0


def mode_prune(args):
    today = date_type.fromisoformat(args.today) if args.today \
        else datetime.now(ZoneInfo('Asia/Tokyo')).date()
    before_date = cutoff_for(today, args.keep_days)
    probe = call('/api/admin/snapshot-prune', {'before_date': before_date, 'items': []})
    assert probe.get('ok'), 'snapshot-prune readiness probe failed'
    audit_before = audit_totals(storage_audit())
    root = Path(args.archive_dir)
    index = json.loads((root / 'index.json').read_text(encoding='utf-8'))
    dates = sorted(d for d in index['dates'] if d < before_date)
    results = {}
    errors = {}
    totals = {'deleted': 0, 'would_delete': 0, 'not_found': 0, 'payload_bytes': 0}
    for race_date in dates:
        manifest = verify_archive(args.archive_dir, race_date)
        items = [{'race_id': e['race_id'], 'sha256': e['sha256']} for e in manifest['races']]
        per_date = {}
        for start in range(0, len(items), 50):
            batch = items[start:start + 50]
            response = call('/api/admin/snapshot-prune', {
                'before_date': before_date, 'dry_run': not args.execute, 'items': batch})
            assert response.get('ok'), f'snapshot-prune failed for {race_date}'
            for result in response['results']:
                per_date[result['race_id']] = result['status']
                if result['status'] in totals:
                    totals[result['status']] += 1
                if result['status'] in ('deleted', 'would_delete'):
                    totals['payload_bytes'] += result.get('payload_bytes') or 0
                if result['status'] not in ('deleted', 'would_delete', 'not_found'):
                    errors.setdefault(race_date, {})[result['race_id']] = result['status']
        results[race_date] = per_date
        print('OFFLOAD_PRUNE_DATE', race_date,
              'execute' if args.execute else 'dry-run',
              json.dumps({s: list(per_date.values()).count(s) for s in set(per_date.values())}),
              flush=True)
    audit_after = audit_totals(storage_audit())
    report = {
        'mode': 'prune', 'execute': bool(args.execute), 'today': today.isoformat(),
        'keep_days': args.keep_days, 'before_date': before_date,
        'run_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'audit_before': audit_before, 'audit_after': audit_after,
        'totals': totals, 'errors': errors, 'results': results,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in
                      ('mode', 'execute', 'before_date', 'audit_before', 'audit_after', 'totals', 'errors')},
                     ensure_ascii=False, indent=2))
    return 3 if errors else 0


def mode_restore(args):
    manifest = verify_archive(args.archive_dir, args.date)
    data_path, _ = archive_paths(args.archive_dir, args.date)
    records = {}
    with gzip.open(data_path, 'rt', encoding='utf-8') as source:
        for line in source:
            if line.strip():
                record = json.loads(line)
                records[record['race_id']] = record
    restored, mismatched = [], []
    for entry in manifest['races']:
        race_id = entry['race_id']
        record = records[race_id]
        if not args.execute:
            print('OFFLOAD_RESTORE_DRY_RUN', race_id, entry['bytes'], flush=True)
            continue
        call('/api/sync', {'details': [{
            'race_id': race_id, 'race_date': args.date,
            'payload': record['payload'],
            'analysis_ready': record['analysis_ready'],
            'updated_at': record['updated_at'],
        }]})
        row = read_row(race_id)
        digest = hashlib.sha256(row['payload']).hexdigest()
        if digest == entry['sha256'] and row['analysis_ready'] == record['analysis_ready']:
            restored.append(race_id)
            print('OFFLOAD_RESTORE_OK', race_id, flush=True)
        else:
            mismatched.append(race_id)
            print('OFFLOAD_RESTORE_MISMATCH', race_id, digest, entry['sha256'], flush=True)
    print(json.dumps({'mode': 'restore', 'date': args.date, 'execute': bool(args.execute),
                      'races': manifest['race_count'], 'restored': restored,
                      'mismatched': mismatched}, ensure_ascii=False, indent=2))
    return 3 if mismatched else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    for name in ('export', 'prune'):
        p = sub.add_parser(name)
        p.add_argument('--archive-dir', required=True)
        p.add_argument('--keep-days', type=int, default=30)
        p.add_argument('--today', default=None, help='YYYY-MM-DD (default: today in Asia/Tokyo)')
        if name == 'export':
            p.add_argument('--max-dates', type=int, default=None)
        else:
            p.add_argument('--execute', action='store_true', help='actually delete (default: dry-run)')
            p.add_argument('--report', default=None)
    p = sub.add_parser('verify')
    p.add_argument('--archive-dir', required=True)
    p.add_argument('--date', default=None)
    p = sub.add_parser('restore')
    p.add_argument('--archive-dir', required=True)
    p.add_argument('--date', required=True)
    p.add_argument('--execute', action='store_true', help='actually re-insert (default: dry-run)')
    args = parser.parse_args()
    if args.mode == 'export':
        return mode_export(args)
    if args.mode == 'verify':
        return mode_verify(args)
    if args.mode == 'prune':
        return mode_prune(args)
    if args.mode == 'restore':
        return mode_restore(args)
    return 2


if __name__ == '__main__':
    sys.exit(main())
