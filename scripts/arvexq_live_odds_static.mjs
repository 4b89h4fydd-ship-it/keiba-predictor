// ARVEXQ live-odds static generator (Cloudflare exit, 2026-11-23).
//
// Replaces the detached relay Worker (workers/live_relay.mjs) with a
// scheduled GitHub Actions job: the very same verified source fetcher
// the relay used (workers/live_odds.mjs `sourceOdds`, a pure function
// of the source descriptor + fetch) is run here in Node, and each
// race's response body — byte-for-byte the shape the relay returned —
// is committed as a static JSON file:
//
//   arvexq/ui/static/api-static/live-odds/<race_id>.json
//   arvexq/ui/static/api-static/live-odds/index.json
//
// build_static.py copies the api-static tree wholesale into dist, so
// the files are served by GitHub Pages (and, during the transition,
// by the Workers app) with no server-side code at all.
//
// Semantics mirror the relay exactly:
//   * success            -> the sourceOdds body verbatim (ok:true)
//   * failure + last good-> the last good body with oddsStatus:'saved'
//                           and refreshFailed:true (never invented
//                           prices, never a silent hole)
//   * failure, no good   -> {ok:false, race_id, odds:[],
//                           oddsStatus:'unavailable', refreshFailed:true,
//                           error:'official odds unavailable'}
// The client (research/live_odds.js) treats these bodies exactly as
// it treated the relay's responses.
//
// Cost of the move, stated plainly: freshness is bounded by the
// Actions schedule + commit + Pages deploy cycle (minutes), not the
// relay's 30-60 second cache.  This feed serves only the research
// screen; the main app never used the relay.
import {readFile, writeFile, mkdir, readdir, unlink} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {sourceOdds} from '../workers/live_odds.mjs';

export function shapeSaved(existing) {
  return {...existing, oddsStatus: 'saved', refreshFailed: true};
}

export function shapeUnavailable(raceId) {
  return {
    ok: false, race_id: raceId, odds: [], oddsStatus: 'unavailable',
    refreshFailed: true, error: 'official odds unavailable',
  };
}

async function readJsonOrNull(file) {
  try {
    const value = JSON.parse(await readFile(file, 'utf8'));
    return value && typeof value === 'object' ? value : null;
  } catch {
    return null;
  }
}

function canonical(value) {
  return JSON.stringify(value, Object.keys(value ?? {}).sort());
}

async function writeIfChanged(file, body) {
  const text = JSON.stringify(body, null, 1) + '\n';
  try {
    const old = await readFile(file, 'utf8');
    if (old === text) return false;
  } catch { /* absent: write */ }
  await writeFile(file, text);
  return true;
}

export async function generateRace(source, outDir, fetcher = fetch) {
  const file = path.join(outDir, `${source.id}.json`);
  const existing = await readJsonOrNull(file);
  try {
    const body = await sourceOdds(source, fetcher);
    const changed = await writeIfChanged(file, body);
    return {id: source.id, outcome: 'live', changed, body};
  } catch (error) {
    if (existing && existing.ok === true && Array.isArray(existing.odds)) {
      const body = shapeSaved(existing);
      const changed = await writeIfChanged(file, body);
      return {id: source.id, outcome: 'saved', changed, body};
    }
    const body = shapeUnavailable(source.id);
    const changed = await writeIfChanged(file, body);
    return {id: source.id, outcome: 'unavailable', changed, body};
  }
}

export async function runGeneration({manifestDir, outDir, date, fetcher = fetch,
                                     concurrency = 8, retainDays = 3}) {
  const manifestPath = path.join(manifestDir, 'odds-sources', `${date}.json`);
  const manifest = await readJsonOrNull(manifestPath);
  if (!manifest) {
    console.log(`LIVE_ODDS_STATIC_SKIP no odds-sources manifest for ${date}`);
    return {date, skipped: true, races: 0, live: 0, saved: 0, unavailable: 0, changed: 0};
  }
  if (manifest.version !== 'arvexq-odds-sources-v1' || manifest.date !== date
      || !manifest.races || typeof manifest.races !== 'object') {
    throw new Error(`odds-sources manifest for ${date} failed verification`);
  }
  await mkdir(outDir, {recursive: true});
  const sources = Object.values(manifest.races).filter(
    (s) => s && s.id && s.date === date);
  const results = [];
  let cursor = 0;
  async function worker() {
    while (cursor < sources.length) {
      const source = sources[cursor++];
      results.push(await generateRace(source, outDir, fetcher));
    }
  }
  await Promise.all(Array.from({length: Math.min(concurrency, sources.length)}, worker));

  // Prune files for race dates older than the retention window so the
  // committed tree cannot grow without bound.
  const cutoff = new Date(`${date}T00:00:00+09:00`);
  cutoff.setDate(cutoff.getDate() - retainDays);
  const cutoffIso = cutoff.toISOString().slice(0, 10);
  let pruned = 0;
  for (const name of await readdir(outDir)) {
    const m = /^(?:jra|nar)-(\d{4}-\d{2}-\d{2})-.+\.json$/.exec(name);
    if (m && m[1] < cutoffIso) {
      await unlink(path.join(outDir, name));
      pruned += 1;
    }
  }

  const index = {
    version: 'arvexq-live-odds-static-v1',
    date,
    generatedAt: new Date().toISOString(),
    races: {},
  };
  for (const r of results) {
    index.races[r.id] = {
      ok: r.body?.ok === true,
      oddsStatus: r.body?.oddsStatus ?? (r.body?.ok === true ? 'live' : 'unavailable'),
      oddsUpdatedAt: r.body?.oddsUpdatedAt ?? '',
      sourcePublishedAt: r.body?.sourcePublishedAt ?? '',
    };
  }
  await writeIfChanged(path.join(outDir, 'index.json'), index);

  const tally = {live: 0, saved: 0, unavailable: 0, changed: 0};
  for (const r of results) {
    tally[r.outcome] += 1;
    if (r.changed) tally.changed += 1;
  }
  console.log(
    `LIVE_ODDS_STATIC date=${date} races=${results.length} ` +
    `live=${tally.live} saved=${tally.saved} unavailable=${tally.unavailable} ` +
    `changed=${tally.changed} pruned=${pruned}`);
  return {date, skipped: false, races: results.length, ...tally, pruned};
}

function jstToday() {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
}

async function main(argv) {
  const args = {manifestDir: 'dist-live-relay', outDir: 'arvexq/ui/static/api-static/live-odds',
                date: jstToday(), retainDays: 3};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === '--manifest-dir') args.manifestDir = argv[++i];
    else if (key === '--out-dir') args.outDir = argv[++i];
    else if (key === '--date') args.date = argv[++i];
    else if (key === '--retain-days') args.retainDays = Number(argv[++i]);
    else throw new Error(`unknown argument: ${key}`);
  }
  if (!existsSync(path.join(args.manifestDir, 'odds-sources'))) {
    console.log('LIVE_ODDS_STATIC_SKIP manifest dir absent; run scripts/arvexq_build_live_relay_assets.py first');
    return 0;
  }
  await runGeneration(args);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv).then(
    (code) => { process.exitCode = code; },
    (error) => { console.error('LIVE_ODDS_STATIC_FAILED', error); process.exitCode = 1; },
  );
}
