#!/usr/bin/env node
'use strict';
// Exercise the actual pre-off JS engine for local races only.
const assert=require('node:assert/strict'),cp=require('node:child_process');
const horses=Array.from({length:7},(_,i)=>({
 horseNumber:i+1,frameNumber:i+1,name:'地方馬'+(i+1),sex:'牡',age:4,
 recentRaces:Array.from({length:5},(_,j)=>({
  date:'2098-12-'+String(20-j*3).padStart(2,'0'),track:'園田',distance:1400,
  surface:'ダート',fieldSize:12,finish:Math.min(11,i+1+j%2),
  cornerPositions:[2,2,2,2],timeBehindWinner:i===0?0:1+i*.25
 }))
}));
const race={id:'nar-2099-01-10-園田-01',date:'2099-01-10',startTime:'23:00',
  circuit:'地方',track:'園田',raceNumber:1,title:'NAR dedicated live model',
  fieldSize:7,surface:'ダート',distance:1400,horses};
function capture(r){
 return cp.spawnSync(process.execPath,['scripts/arvexq_capture_prerace_bet.js'],
   {input:JSON.stringify(r),encoding:'utf8',timeout:30000});
}
const ok=capture(race);
assert.equal(ok.status,0,'NAR capture failed: '+String(ok.stderr).slice(0,2500));
const plan=JSON.parse(ok.stdout);
assert.equal(plan.engineVersion,'arvexq-nar-mineta-margin-60-40-v1');
assert.equal(plan.honmei.horseNumber,1);
assert.equal(plan.decision,'購入候補');
assert(plan.items.some(x=>x.level==='本線'&&x.kind==='馬連'));
assert(plan.items.every(x=>['本線','保険','3連単チャレンジ'].includes(x.level)));
// An older allPastRuns array must not hide new official proof in recentRaces.
const split={...race,horses:horses.map(h=>({
  ...h,allPastRuns:h.recentRaces.map(q=>({...q,timeBehindWinner:null}))
}))};
const splitResult=capture(split);
assert.equal(splitResult.status,0,'NAR recentRaces proof lost behind stale allPastRuns: '+String(splitResult.stderr).slice(0,1000));
const broken={...race,horses:horses.map((h,i)=>i===6?
 {...h,recentRaces:h.recentRaces.map(q=>({...q,timeBehindWinner:null}))}:h)};
const refused=capture(broken);
assert.notEqual(refused.status,0,'Missing historical margins must NOT seal local legacy-model tickets');
console.log('NAR_ONLY_6040_MARKS_AND_BETS_NO_LEGACY_FALLBACK_PASS');
