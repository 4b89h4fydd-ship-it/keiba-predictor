#!/usr/bin/env node
'use strict';
// Exercise the actual pre-off JS engine for central races only.
const assert=require('node:assert/strict'),cp=require('node:child_process');
const horses=Array.from({length:7},(_,i)=>({
 horseNumber:i+1,frameNumber:i+1,name:'地方馬'+(i+1),sex:'牡',age:4,
 recentRaces:Array.from({length:5},(_,j)=>({
  date:'2098-12-'+String(20-j*3).padStart(2,'0'),track:'東京',distance:1400,
  surface:'芝',fieldSize:12,finish:Math.min(11,i+1+j%2),
  cornerPositions:[2,2,2,2],timeBehindWinner:i===0?0:1+i*.25,
  marginEvidenceSource:'JRA official',
  marginEvidence:{winnerTimeSeconds:95.0,horseTimeSeconds:95.0+(i===0?0:1+i*.25)}
 }))
}));
const race={id:'jra-2099-01-10-東京-01',date:'2099-01-10',startTime:'23:00',
  circuit:'中央',track:'東京',raceNumber:1,title:'JRA dedicated live model',
  fieldSize:7,surface:'芝',distance:1400,horses};
function capture(r){
 return cp.spawnSync(process.execPath,['scripts/arvexq_capture_prerace_bet.js'],
   {input:JSON.stringify(r),encoding:'utf8',timeout:30000});
}
const ok=capture(race);
assert.equal(ok.status,0,'JRA capture failed: '+String(ok.stderr).slice(0,2500));
const plan=JSON.parse(ok.stdout);
assert.equal(plan.engineVersion,'arvexq-jra-observed-consensus-v1');
assert.equal(plan.honmei.horseNumber,1);
assert.equal(plan.decision,'購入候補');
assert(plan.items.some(x=>x.level==='本線'&&x.kind==='馬連'));
assert(plan.items.every(x=>['本線','保険','3連単チャレンジ'].includes(x.level)));
// An older allPastRuns array must not hide new official proof in recentRaces.
const split={...race,horses:horses.map(h=>({
  ...h,allPastRuns:h.recentRaces.map(q=>({...q,timeBehindWinner:null}))
}))};
const splitResult=capture(split);
assert.equal(splitResult.status,0,'JRA recentRaces proof lost behind stale allPastRuns: '+String(splitResult.stderr).slice(0,1000));
const broken={...race,horses:horses.map((h,i)=>i===6?
 {...h,recentRaces:h.recentRaces.map(q=>({...q,timeBehindWinner:null}))}:h)};
const refused=capture(broken);
assert.notEqual(refused.status,0,'Missing historical margins must NOT seal central legacy-model tickets');
console.log('JRA_ONLY_6040_MARKS_AND_BETS_NO_LEGACY_FALLBACK_PASS');
