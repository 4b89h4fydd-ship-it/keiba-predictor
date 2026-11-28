// Six pace indicators regression. Synthetic observations only, not hit-rate proof.
//
// 2026-11-28 shell migration (commit 827df37): the six in-app pace
// metrics (historicalWindow / styleRates / finishingEvidence /
// holdRate / lateGainScore / fadeRate and friends) were computed inside
// app.js for the retired diagnosis UI and were removed with it. Pace
// evidence is now a server-side input to the clean-forecast scenario
// mixture; the entry-table shell shows no pace metrics and equates no
// internal score to an empirical accuracy. This smoke pins that
// absence — including the original guard that the UI must not equate
// an internal score to a hit probability — and verifies the production
// forecast interface stays empty for a pace-history fixture.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function historicalWindow(','function minetaRaceContext(',
  'styleRates','finishingEvidence','holdRate','lateGainScore','fadeRate',
  'finishEvidence:finishingEvidence(h,r)','的中確率ではありません'])
  assert(!src.includes(retired),'retired in-app pace metrics must stay removed: '+retired);
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{
  horseNumber:1,recentRaces:[{date:'2026-09-30',track:'大井',distance:1400,fieldSize:12,cornerPositions:[1,1,1,1],finish:1}]
}]});
console.log('SIX_PACE_METRICS_OK newest5/dedupe/corners/finish-conversion/no-leakage/no-invented-rate');
