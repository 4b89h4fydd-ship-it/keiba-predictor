// Tests for scripts/arvexq_live_odds_static.mjs (Cloudflare exit).
// Run: node tests/test_live_odds_static.mjs   (exit 0 = PASS)
//
// Covers the three relay-equivalent outcomes of the static generator
// with a stubbed fetcher (no network): live success parsed from an
// official-style NAR odds table, failure falling back to the last
// good body as 'saved', and failure with no history as 'unavailable'.
// Prices are never invented: the saved body reuses the previously
// fetched odds verbatim, and the unavailable body carries odds: [].
import assert from 'node:assert/strict';
import {mkdtemp, readFile, writeFile, mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {generateRace, runGeneration, shapeSaved, shapeUnavailable}
  from '../scripts/arvexq_live_odds_static.mjs';

const SOURCE = {
  id: 'nar-2026-11-23-金沢-01', circuit: '地方', track: '金沢',
  date: '2026-11-23', raceNumber: 1,
  horses: [
    {horseNumber: 1, name: 'テストイチ'},
    {horseNumber: 2, name: 'テストニ'},
  ],
};

const HTML = `<html><body><p>オッズ 14:30 現在</p><table>
<tr><td>1</td><td>1</td><td>テストイチ</td><td>2.5</td><td>1</td></tr>
<tr><td>2</td><td>2</td><td>テストニ</td><td>5.0</td><td>2</td></tr>
</table></body></html>`;

const okFetcher = async () => ({ok: true, text: async () => HTML, json: async () => ({})});
const failFetcher = async () => { throw new Error('source down'); };

const tmp = await mkdtemp(path.join(tmpdir(), 'live-odds-static-'));
const outDir = path.join(tmp, 'live-odds');
await mkdir(outDir, {recursive: true});
const file = path.join(outDir, `${SOURCE.id}.json`);

// 1) live success: body is the sourceOdds result, relay-shaped.
{
  const r = await generateRace(SOURCE, outDir, okFetcher);
  assert.equal(r.outcome, 'live');
  const body = JSON.parse(await readFile(file, 'utf8'));
  assert.equal(body.ok, true);
  assert.equal(body.race_id, SOURCE.id);
  assert.equal(body.odds.length, 2);
  assert.equal(body.odds[0].win_odds, 2.5);
  assert.equal(body.odds[0].popularity, 1);
  assert.equal(body.sourcePublishedAt, '2026-11-23T14:30:00+09:00');
  console.log('PASS live success');
}

// 2) failure after success: saved fallback reuses the fetched odds.
{
  const r = await generateRace(SOURCE, outDir, failFetcher);
  assert.equal(r.outcome, 'saved');
  const body = JSON.parse(await readFile(file, 'utf8'));
  assert.equal(body.ok, true);
  assert.equal(body.oddsStatus, 'saved');
  assert.equal(body.refreshFailed, true);
  assert.equal(body.odds.length, 2);
  assert.equal(body.odds[0].win_odds, 2.5);
  console.log('PASS saved fallback');
}

// 3) failure with no history: unavailable, empty odds, nothing invented.
{
  const fresh = {...SOURCE, id: 'nar-2026-11-23-金沢-02'};
  const r = await generateRace(fresh, outDir, failFetcher);
  assert.equal(r.outcome, 'unavailable');
  const body = JSON.parse(
    await readFile(path.join(outDir, `${fresh.id}.json`), 'utf8'));
  assert.equal(body.ok, false);
  assert.deepEqual(body.odds, []);
  assert.equal(body.oddsStatus, 'unavailable');
  console.log('PASS unavailable shape');
}

// 4) shaping helpers keep the relay contract.
{
  assert.deepEqual(shapeUnavailable('x'),
    {ok: false, race_id: 'x', odds: [], oddsStatus: 'unavailable',
     refreshFailed: true, error: 'official odds unavailable'});
  const saved = shapeSaved({ok: true, race_id: 'x', odds: [{horse_no: 1}]});
  assert.equal(saved.ok, true);
  assert.equal(saved.oddsStatus, 'saved');
  assert.equal(saved.odds.length, 1);
  console.log('PASS shaping helpers');
}

// 5) runGeneration verifies the manifest before writing anything.
{
  const manifestDir = path.join(tmp, 'manifests');
  await mkdir(path.join(manifestDir, 'odds-sources'), {recursive: true});
  await writeFile(path.join(manifestDir, 'odds-sources', '2026-11-23.json'),
    JSON.stringify({version: 'bogus', date: '2026-11-23', races: {}}));
  await assert.rejects(
    runGeneration({manifestDir, outDir, date: '2026-11-23', fetcher: okFetcher}),
    /failed verification/);
  console.log('PASS manifest verification');
}

console.log('LIVE_ODDS_STATIC_TESTS_PASS');
