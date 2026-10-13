#!/usr/bin/env node
'use strict';
// Execute the real server-side capture command against a future synthetic race.
// A successful result proves the deleted old JS modules cannot be loaded.
const fs=require('node:fs'),assert=require('node:assert/strict');
const child=require('node:child_process');
const capture=fs.readFileSync('scripts/arvexq_capture_prerace_bet.js','utf8');
for(const old of ['podium_axis_guard.js','legacy_v213_order_model.js','three_way_engine.js','bet_readiness.js','main_strategy.js']){
  assert(!capture.includes(old),'server capture still loads retired module '+old);
}
const horses=Array.from({length:7},(_,i)=>({
  horseNumber:i+1,name:'Racehorse '+(i+1),jockey:'Jockey '+(i+1),
  sex:'牡',age:4,weight:57,bodyWeight:460+i*5,winOdds:2.5+i*2,
  recentRaces:Array.from({length:5},(_,j)=>({
    date:'2098-12-'+String(20-j*3).padStart(2,'0'),track:'園田',distance:1400,
    surface:'ダート',condition:'良',fieldSize:12,
    finish:i===0?1:Math.min(11,i+2+j%2),last3fRank:i===0?1:Math.min(11,i+2+j%2),
    cornerPositions:[2,2,2,2],timeSeconds:85+i*.8
  }))
}));
const race={id:'nar-2099-01-10-園田-01',date:'2099-01-10',startTime:'23:00',
  circuit:'地方',track:'園田',raceNumber:1,title:'Three factor capture regression',
  fieldSize:7,surface:'ダート',distance:1400,condition:'良',weather:'晴',
  horses};
const run=child.spawnSync(process.execPath,['scripts/arvexq_capture_prerace_bet.js'],
  {input:JSON.stringify(race),encoding:'utf8',timeout:30000});
assert.equal(run.status,0,'preoff capture failed: '+String(run.stderr||run.stdout).slice(0,5000));
const out=JSON.parse(run.stdout);
assert.equal(out.engineVersion,'arvexq-true-run-pure-sectional-v2');
assert.equal(out.honmei.horseNumber,1);
assert.equal(out.decision,'購入候補');
assert(out.items.length>=1,'new unified method must produce purchasable tickets');
assert(out.items.every(x=>x.level==='本線'||x.level==='保険'||x.level==='3連単チャレンジ'));
assert(!out.items.some(x=>x.kind==='旧方式'));
assert.equal(out.singleWinHorseNumber,1);
assert.match(out.version,/three-factor/);
console.log('SERVER_PREOFF_CAPTURE_THREE_FACTOR_OK',out.items.map(i=>i.kind).join(','));
