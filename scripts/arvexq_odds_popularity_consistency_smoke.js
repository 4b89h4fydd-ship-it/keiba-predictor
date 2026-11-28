'use strict';
// Live odds/popularity consistency under the 2026-11-28 shell
// migration (commit 827df37, user-confirmed entry-table-only app).
//
// The retired shell recomputed popularity from live odds inside app.js
// (marketPopularity / racecardOddsHtml). Its contract was: one live UI
// authority for market rank, so stale saved ranks could never
// contradict visible prices. The current shell renders no odds and no
// popularity at all — the confirmed columns are horse number, mark,
// name, win probability and top-3 probability — so no client-side rank
// can contradict anything. Consistency of the odds/popularity data
// itself is enforced at the source and covered by
// arvexq_official_odds_smoke.mjs, arvexq_live_odds_smoke.js and the
// Python test_odds_popularity_consistency suite. This smoke pins the
// shell side of the contract.
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function marketPopularity(','popularityText','function racecardOddsHtml(',
  'function smartVal(','人気','オッズ'])
  assert(!src.includes(retired),'retired odds/popularity rendering must stay removed: '+retired);
assert(src.includes("el('th', 'winprob', '勝率')"),'win probability column is shown');
assert(src.includes("el('th', 'top3prob', '3着内率')"),'top-3 probability column is shown');
console.log('LIVE_ODDS_POPULARITY_SNAPSHOT_CONSISTENCY_PASS');
