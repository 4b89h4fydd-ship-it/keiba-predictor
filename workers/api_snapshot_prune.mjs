// Authenticated, hash-verified prune of already-archived race_details rows.
//
// A row is deleted only when ALL of these hold, checked on the server from
// the live row at request time:
//   1. the caller presents the SHA-256 of the exact payload bytes currently
//      stored for that race_id (i.e. the caller provably archived those
//      exact bytes first),
//   2. the row's race_date is strictly older than the body's before_date
//      retention cutoff,
//   3. the race is not a retired Banei record (never pruned via this route).
// The DELETE itself re-binds the payload it just verified (compare-and-
// delete), so a row updated concurrently after the check is not lost.
// dry_run reports what would be deleted without writing anything.
// Fixed SQL only; no arbitrary queries, no unauthenticated access.
const VERSION = 'arvexq-snapshot-prune-v1';
const BANEI = /^nar-\d{4}-\d{2}-\d{2}-(?:帯広|帯広ば)-\d{2}$/;
const MAX_ITEMS = 100;

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, '0')).join('');
}

export async function snapshotPrune(request, env) {
  if (!env.SYNC_TOKEN || request.headers.get('authorization') !== 'Bearer ' + env.SYNC_TOKEN)
    return Response.json({ ok: false, error: 'unauthorized' }, { status: 401 });
  if (request.method !== 'POST')
    return Response.json({ ok: false, error: 'method not allowed' }, { status: 405 });
  let body;
  try { body = await request.json(); } catch { return Response.json({ ok: false, error: 'invalid JSON' }, { status: 400 }); }
  const beforeDate = String(body.before_date || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(beforeDate))
    return Response.json({ ok: false, error: 'invalid before_date' }, { status: 400 });
  if (!Array.isArray(body.items) || body.items.length > MAX_ITEMS)
    return Response.json({ ok: false, error: 'invalid items' }, { status: 400 });
  const dryRun = body.dry_run === true;
  const results = [];
  for (const item of body.items) {
    const raceId = String((item && item.race_id) || '');
    const expected = String((item && item.sha256) || '');
    if (!raceId || raceId.length > 200 || !/^[a-f0-9]{64}$/.test(expected)) {
      results.push({ race_id: raceId, status: 'invalid_item' });
      continue;
    }
    if (BANEI.test(raceId)) {
      results.push({ race_id: raceId, status: 'excluded_venue' });
      continue;
    }
    const row = await env.DB.prepare('SELECT race_date,payload FROM race_details WHERE race_id=?').bind(raceId).first();
    if (!row) {
      results.push({ race_id: raceId, status: 'not_found' });
      continue;
    }
    if (typeof row.race_date !== 'string' || !(row.race_date < beforeDate)) {
      results.push({ race_id: raceId, status: 'too_recent' });
      continue;
    }
    const actual = await sha256Hex(row.payload);
    if (actual !== expected) {
      results.push({ race_id: raceId, status: 'hash_mismatch' });
      continue;
    }
    if (dryRun) {
      results.push({ race_id: raceId, status: 'would_delete', payload_bytes: new TextEncoder().encode(row.payload).byteLength });
      continue;
    }
    const deleted = await env.DB.prepare('DELETE FROM race_details WHERE race_id=? AND payload=?').bind(raceId, row.payload).run();
    if (!deleted.meta || deleted.meta.changes !== 1) {
      results.push({ race_id: raceId, status: 'concurrent_update' });
      continue;
    }
    results.push({ race_id: raceId, status: 'deleted', payload_bytes: new TextEncoder().encode(row.payload).byteLength });
  }
  const counts = {};
  for (const result of results) counts[result.status] = (counts[result.status] || 0) + 1;
  return Response.json({ ok: true, version: VERSION, dry_run: dryRun, before_date: beforeDate, results, counts },
    { headers: { 'cache-control': 'no-store' } });
}
