// Static racecard open path under the 2026-11-28 shell migration
// (commit 827df37, user-confirmed entry-table-only app).
//
// The retired fetchRacecardOnly was static-only by contract: the dated
// static racecard archive, loaded through ARVEXQStaticRacecard, was its
// one and only source, and any miss resolved to null instead of
// throwing. The current shell does not open races that way at all — a
// race renders from the api-static race pack, or shows the empty
// message. The archive loader module itself is unchanged and is still
// exercised by arvexq_static_racecard_smoke.js; this smoke pins the
// shell side: no racecard-only fetch, no edge fetch, and the loader
// module still loads standalone.
const assert=require('node:assert/strict'),fs=require('node:fs');
const appSrc=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function fetchRacecardOnly(','function hydrateStaticRacecardFirst(',
  'fetchEdgeRace(','_staticRacecardFallback','_entryOnly'])
  assert(!appSrc.includes(retired),'retired racecard open path must stay removed: '+retired);
assert(appSrc.includes('function staticRaceUrl('),'race display comes from the api-static race pack');
assert(appSrc.includes('function renderRace('),'race screen is the entry table only');
const loaderSrc=fs.readFileSync('arvexq/ui/static/research/static_racecard.js','utf8');
const win={};new Function('window',loaderSrc)(win);
assert.ok(win.ARVEXQStaticRacecard,'static racecard loader missing');
console.log('RACECARD_STATIC_ONLY_OPEN_PASS');
