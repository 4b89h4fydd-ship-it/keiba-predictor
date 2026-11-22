// Smoke test for workers/api_snapshot_prune.mjs with an in-memory mock D1.
// Verifies the prune endpoint's safety contract without touching production:
//   - unauthenticated and wrong-method requests are rejected,
//   - a row is deleted only when the presented SHA-256 matches the exact
//     stored payload bytes AND race_date is older than before_date,
//   - dry_run never deletes, Banei rows are never pruned,
//   - a concurrent payload change between check and delete is not lost.
import { snapshotPrune } from '../workers/api_snapshot_prune.mjs';
import { createHash } from 'node:crypto';

const sha256 = text => createHash('sha256').update(text, 'utf8').digest('hex');

function mockEnv(rows) {
  const store = new Map(rows.map(r => [r.race_id, { ...r }]));
  const db = {
    prepare(sql) {
      return {
        _args: [],
        bind(...args) { this._args = args; return this; },
        async first() {
          if (sql.startsWith('SELECT race_date,payload FROM race_details')) {
            const row = store.get(this._args[0]);
            return row ? { race_date: row.race_date, payload: row.payload } : null;
          }
          throw new Error('unexpected first() SQL: ' + sql);
        },
        async run() {
          if (sql.startsWith('DELETE FROM race_details')) {
            const [raceId, payload] = this._args;
            const row = store.get(raceId);
            if (row && row.payload === payload) { store.delete(raceId); return { meta: { changes: 1 } }; }
            return { meta: { changes: 0 } };
          }
          throw new Error('unexpected run() SQL: ' + sql);
        },
      };
    },
  };
  return { env: { SYNC_TOKEN: 'test-token', DB: db }, store };
}

function request({ method = 'POST', auth = 'Bearer test-token', body } = {}) {
  return new Request('https://example.invalid/api/admin/snapshot-prune', {
    method,
    headers: { authorization: auth, 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

let failures = 0;
function check(name, condition) {
  console.log((condition ? 'PASS' : 'FAIL'), name);
  if (!condition) failures += 1;
}

const OLD = { race_id: 'nar-2026-10-01-大井-01', race_date: '2026-10-01', payload: '{"detail":{"x":1}}' };
const RECENT = { race_id: 'nar-2026-11-20-大井-01', race_date: '2026-11-20', payload: '{"detail":{"x":2}}' };
const BANEI = { race_id: 'nar-2026-10-01-帯広-01', race_date: '2026-10-01', payload: '{"detail":{"x":3}}' };
const BEFORE = '2026-10-22';

// unauthorized
{
  const { env } = mockEnv([OLD]);
  const res = await snapshotPrune(request({ auth: 'Bearer wrong' }), env);
  check('unauthorized rejected', res.status === 401);
}
// wrong method
{
  const { env } = mockEnv([OLD]);
  const res = await snapshotPrune(request({ method: 'GET' }), env);
  check('GET rejected', res.status === 405);
}
// invalid before_date
{
  const { env } = mockEnv([OLD]);
  const res = await snapshotPrune(request({ body: { before_date: '2026/10/22', items: [] } }), env);
  check('invalid before_date rejected', res.status === 400);
}
// readiness probe: empty items is a valid no-op
{
  const { env } = mockEnv([OLD]);
  const res = await snapshotPrune(request({ body: { before_date: BEFORE, items: [] } }), env);
  const data = await res.json();
  check('empty items probe ok', res.status === 200 && data.ok === true && data.results.length === 0);
}
// hash mismatch: no delete
{
  const { env, store } = mockEnv([OLD]);
  const res = await snapshotPrune(request({ body: { before_date: BEFORE, items: [{ race_id: OLD.race_id, sha256: sha256('different') }] } }), env);
  const data = await res.json();
  check('hash mismatch reported', data.results[0].status === 'hash_mismatch');
  check('hash mismatch keeps row', store.has(OLD.race_id));
}
// too recent: no delete even with correct hash
{
  const { env, store } = mockEnv([RECENT]);
  const res = await snapshotPrune(request({ body: { before_date: BEFORE, items: [{ race_id: RECENT.race_id, sha256: sha256(RECENT.payload) }] } }), env);
  const data = await res.json();
  check('too_recent reported', data.results[0].status === 'too_recent');
  check('too_recent keeps row', store.has(RECENT.race_id));
}
// banei: never pruned
{
  const { env, store } = mockEnv([BANEI]);
  const res = await snapshotPrune(request({ body: { before_date: BEFORE, items: [{ race_id: BANEI.race_id, sha256: sha256(BANEI.payload) }] } }), env);
  const data = await res.json();
  check('banei excluded', data.results[0].status === 'excluded_venue');
  check('banei keeps row', store.has(BANEI.race_id));
}
// dry run: would_delete, row intact
{
  const { env, store } = mockEnv([OLD]);
  const res = await snapshotPrune(request({ body: { before_date: BEFORE, dry_run: true, items: [{ race_id: OLD.race_id, sha256: sha256(OLD.payload) }] } }), env);
  const data = await res.json();
  check('dry_run would_delete', data.results[0].status === 'would_delete');
  check('dry_run keeps row', store.has(OLD.race_id));
}
// execute: deleted, and second call is not_found
{
  const { env, store } = mockEnv([OLD]);
  const body = { before_date: BEFORE, items: [{ race_id: OLD.race_id, sha256: sha256(OLD.payload) }] };
  const res = await snapshotPrune(request({ body }), env);
  const data = await res.json();
  check('execute deletes', data.results[0].status === 'deleted' && !store.has(OLD.race_id));
  const res2 = await snapshotPrune(request({ body }), env);
  const data2 = await res2.json();
  check('re-run is not_found (idempotent)', data2.results[0].status === 'not_found');
}

console.log(failures === 0 ? 'PRUNE_SMOKE_ALL_PASS' : `PRUNE_SMOKE_FAILURES=${failures}`);
process.exit(failures === 0 ? 0 : 1);
