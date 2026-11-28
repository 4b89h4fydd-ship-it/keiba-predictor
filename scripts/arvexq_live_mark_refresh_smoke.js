#!/usr/bin/env node
'use strict';
// The retired 60/40 engine must never regenerate marks from raw past runs.
// Only learned D1 predictions or verified historical originals can appear.
//
// 2026-11-28 shell migration (commit 827df37): app.js no longer contains
// predict() or the old boot sequence at all — the entry-table shell
// computes nothing and keeps no localStorage state. The guarantee this
// smoke protected is therefore pinned in its current form:
//   - the shell has no prediction entry point, no boot anchor and no
//     storage a regenerated mark could be minted into, and
//   - the production forecast interface (forecast modules, exercised
//     through production_ui.cjs) still yields no mark and no win
//     probability for raw past runs, for a learned-version stamp, or
//     after a result — the same three scenarios as the original smoke.
const fs=require('node:fs'),assert=require('node:assert/strict');
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
assert(!root.includes(boot),'retired boot anchor must stay removed');
assert(!root.includes('function predict('),'shell must not regenerate marks');
assert(!root.includes('localStorage'),'no post-race marks can be minted into localStorage');
assert(root.includes('function marksByNumber('),'shell displays pack marks only');
const {assertNoForecast}=require('./test_support/production_ui.cjs');
const horses=Array.from({length:7},(_,i)=>({
 horseNumber:i+1,name:'Horse-'+(i+1),recentRaces:[{date:'2098-12-01',finish:1,fieldSize:12}]
}));
const race={id:'jra-2099-01-10-東京-08',date:'2099-01-10',startTime:'23:00',
 circuit:'中央',track:'東京',raceNumber:8,fieldSize:7,surface:'ダート',distance:1400,horses};
// Raw past runs alone: no replacement mark, no win probability.
const missing=assertNoForecast(race);
assert.equal(missing.rows[0].winProbability,null);
// Mutating a raw result cannot resurrect legacy marks.
race.horses[0].recentRaces[0].finish=12;
assertNoForecast(race);
// A learned version stamp plus integrated evaluations stays disabled.
race.predictionModelVersion='arvexq-learned-whole-career-scenarios-v2';
race.horses.forEach((h,i)=>{h.integratedEvaluation={
 mark:i===0?'◎':'',
 modelProbabilities:{win:[.1,.2],top2:[.2,.3],top3:[.3,.4]}
}});
assertNoForecast(race);
// An unapproved saved candidate remains disabled after the result.
race.raceStatus='確定';
assertNoForecast(race);
console.log('LEARNED_D1_ONLY_MARKS_NO_RETIRED_SCORE_PASS');
