// Contract tests for independent history modules and actual frontend integration.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
global.window=global;
for(const name of ['deduplicate','temporal','view']){
  vm.runInThisContext(fs.readFileSync(path.join(root,'arvexq/ui/static/history',name+'.js'),'utf8'));
}
const old={date:'2026-10-01',track:'大井',distance:1800,raceNumber:5,
  finish:0,cornerPositions:[2,0],marginSeconds:null};
const updated={date:'20261001',track:'大井',distance:1800,raceNo:5,
  finish:3,cornerPositions:[0,4],marginSeconds:0.6};
const next={date:'2026-09-01',track:'園田',distance:1400,finish:2};
const horse={recentRaces:[old],allPastRuns:[updated,next,
  {date:'2026-10-07',track:'大井',distance:2000,finish:1},
  {date:'2026-10-08',track:'大井',distance:2000,finish:1}]};
const original=JSON.stringify(horse);
const combined=ARVEXQPastRunDeduplicate.merge(horse);
assert.equal(combined.length,4);
assert.equal(combined[0].finish,3);
assert.deepEqual(Array.from(combined[0].cornerPositions),[2,4]);
assert.equal(combined[0].marginSeconds,0.6);
const runs=ARVEXQPastRunTemporal.beforeRace(combined,{date:'2026-10-07'},5);
assert.equal(runs.length,2);
assert.equal(runs[0].date,'2026-10-01');
assert.equal(runs[1].date,'2026-09-01');
assert.equal(JSON.stringify(horse),original,'source evidence must remain immutable');
assert.deepEqual(ARVEXQPastRunTemporal.beforeRace(combined,{date:'2026-02-30'},5),[]);
const allOnly={recentRaces:[],allPastRuns:[next]};
const html=ARVEXQPastRunView.recentRows(allOnly,{date:'2026-10-07'},String);
assert.match(html,/class="recent"/);
assert.match(html,/園田/);
assert.equal(ARVEXQPastRunView.visible(allOnly,{date:'2026-08-01'},5).length,0);
const app=fs.readFileSync(path.join(root,'arvexq/ui/static/app.js'),'utf8');
assert.match(app,/ARVEXQPastRunView\.recentRows\(/,'horse detail must use standalone history presenter');
assert.match(app,/ARVEXQPastRunView\.visible\(/,'historical window must delegate to standalone history');
const bundle=fs.readFileSync(path.join(root,'arvexq/ui/bundle.py'),'utf8');
assert.match(bundle,/HISTORY_SCRIPTS/,'Web and static build must share history modules');
console.log('INDEPENDENT_HISTORICAL_FACTS_PASS');
