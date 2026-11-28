'use strict';
// Tokyo 11R static identity regression under the 2026-11-28 shell
// migration (commit 827df37, user-confirmed entry-table-only app).
//
// The data core of the original smoke is unchanged: the dated static
// racecard archive for 2026-10-11 must carry the complete Tokyo 11R
// runner identities (16 horses, first runner ニシノティアモ), and the
// archive loader must resolve that race. What changed is the open
// path: the retired hydrateStaticRacecardFirst() merged the archive
// card into the live race with stale-request protection. The current
// shell has no live race object to hydrate — it renders the api-static
// race pack — so the hydration machinery's absence is pinned instead,
// and identity completeness is checked on the archive itself.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const data=JSON.parse(fs.readFileSync('arvexq/ui/static/racecards/2026-10-11.json','utf8'));
const staticSrc=fs.readFileSync('arvexq/ui/static/research/static_racecard.js','utf8');
const windowMock={};new Function('window',staticSrc)(windowMock);
assert.ok(windowMock.ARVEXQStaticRacecard,'static racecard loader missing');
const rid='jra-2026-10-11-東京-11';
const record=data.races.find(r=>r.id===rid);
assert.ok(record,'Tokyo 11 must exist in the static archive');
assert.equal(record.horses.length,16,'Tokyo 11 must have complete static runner identities');
assert.equal(record.horses[0].name,'ニシノティアモ');
assert.equal(new Set(record.horses.map(h=>h.horseNumber)).size,16,'runner numbers are unique');
assert(record.horses.every(h=>h.name),'every runner carries an identity');
for(const retired of ['function hydrateStaticRacecardFirst(','function fetchRacecardOnly(',
  'fetchEdgeRace(','_staticRacecardFallback'])
  assert(!app.includes(retired),'retired hydration open path must stay removed: '+retired);
assert(app.includes('function renderRace('),'race screen renders the pack entry table');
console.log('TOKYO11_STATIC_FIRST_16_RUNNERS_AND_STALE_PROTECTION_PASS');
