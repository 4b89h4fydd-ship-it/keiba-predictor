'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const helpers=src.slice(src.indexOf('function n(v,d)'),src.indexOf('function predict('));
const predict=src.slice(src.indexOf('function predict('),src.indexOf('function nextRace('));
const build=src.slice(src.indexOf('function buildAiBetPlan('),src.indexOf('function betItemHit('));
const factory=new Function('window','n','isScratchHorse','esc',helpers+predict+build+';return {predict,buildAiBetPlan,latestSavedForecastRevision};');
const ui=require('./test_support/production_ui.cjs');
// predict() reaches window.ARVEXQPastRunView via historicalWindow /
// finishingEvidence; load the real history modules onto the shared
// test window, as the page bundle does.
const vm=require('node:vm');
const historyContext={window:ui.window};vm.createContext(historyContext);
for(const f of ['deduplicate','temporal','view'])
  vm.runInContext(fs.readFileSync('arvexq/ui/static/history/'+f+'.js','utf8'),historyContext,{filename:f});
const api=factory(ui.window,(v,d=0)=>Number(v)||d,h=>!!h.scratched,String);
const r=JSON.parse(fs.readFileSync('tests/fixtures/forecast_revision_transport.json')).detail;
const before=JSON.stringify(r),revision=api.latestSavedForecastRevision(r);
const p=api.predict(r),bet=api.buildAiBetPlan(r,p);
assert(!p.savedForecastRevision);
assert(p.rows.every(x=>x.predMark===''));
assert.equal(bet.items.length,0);
assert.equal(JSON.stringify(r),before,'old archives cannot become active and cannot be mutated');
const bad=JSON.parse(before);bad.forecastRevisions[0].horses.pop();
assert.equal(api.latestSavedForecastRevision(bad),null);
assert(src.includes('!plan||plan.postRaceRevision'),'retrospective plans must be excluded from hit-rate scoring');
console.log('LATEST_FORECAST_REVISION_MARKS_BETS_AND_ORIGINAL_PRESERVATION_PASS');
