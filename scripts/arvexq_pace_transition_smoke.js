// Synthetic consistency regressions, NOT historical hit-rate validation.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function extract(from,to){
  const a=src.indexOf(from),b=src.indexOf(to,a+from.length);
  assert.ok(a>=0&&b>a,'missing pace function '+from);
  return src.slice(a,b);
}
const n=(v,f=0)=>{
  if(v===null||v===undefined||v==='')return f;
  const x=Number(v);return Number.isFinite(x)?x:f;
};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const past=new Function('n','clamp','recencyWeights','raceField',
  extract('function historicalWindow(','function minetaRaceContext(')+'\nreturn minetaPastProfile;')(
    n,clamp,count=>Array.from({length:count},(_,i)=>Math.pow(.85,i)),r=>n(r.fieldSize,12));
const takeover=past({recentRaces:[{date:'2026-09-30',track:'大井',distance:1400,fieldSize:12,cornerPositions:[6,1,1,1]}]},{date:'2026-10-08',track:'大井',distance:1400});
assert.equal(takeover.prevLeader,false,'midrace takeover cannot be a start lead');
assert.equal(takeover.prevEarly,false,'midrace pass cannot be first-corner occupancy');
assert.ok(takeover.midRaceLead>.5,'midrace takeover evidence must survive');
const leader=past({recentRaces:[{date:'2026-09-30',track:'大井',distance:1400,fieldSize:12,cornerPositions:[1,3,3,3]}]},{date:'2026-10-08',track:'大井',distance:1400});
assert.equal(leader.prevLeader,true);
assert.equal(leader.prevEarly,true);
assert.equal(past({recentRaces:[{date:'2026-09-30',track:'大井',distance:1400,fieldSize:12,cornerPositions:[]}]},{date:'2026-10-08'}).firstPos,0);
const repeatedLead=past({recentRaces:[
 {date:'2026-09-30',track:'大井',distance:1400,fieldSize:12,cornerPositions:[2,2,2,3]},
 {date:'2026-09-20',track:'大井',distance:1400,fieldSize:12,cornerPositions:[1,1,2,3]},
 {date:'2026-09-10',track:'大井',distance:1400,fieldSize:12,cornerPositions:[1,1,1,2]},
 {date:'2026-09-01',track:'大井',distance:1400,fieldSize:12,cornerPositions:[1,1,1,1]},
 {date:'2026-08-20',track:'大井',distance:1400,fieldSize:12,cornerPositions:[2,2,2,2]},
 {date:'2026-08-01',track:'大井',distance:1400,fieldSize:12,cornerPositions:[12,12,12,12]}
]},{date:'2026-10-08',track:'大井',distance:1400});
assert.equal(repeatedLead.samples,5,'must only include the latest five prior runs');
assert.ok(repeatedLead.leadRate>.45,'multi-race first-corner lead rate should survive');
const leakage=past({recentRaces:[
 {date:'2026-10-09',track:'大井',distance:1400,fieldSize:12,cornerPositions:[1,1,1,1]},
 {date:'2026-09-20',track:'大井',distance:1400,fieldSize:12,cornerPositions:[8,6,5,4]}
]},{date:'2026-10-08',track:'大井',distance:1400});
assert.equal(leakage.samples,1,'future observations must not be model inputs');
assert.equal(leakage.leadRate,0,'future lead cannot inflate early-speed evidence');
assert.ok(src.includes("if(!p.firstPos){x.expected='不明'"),
  'missing corner data cannot create an invented running style');

assert(!src.includes('function scenarioPlan('),'retired future simulation is deleted');
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{horseNumber:1,recentRaces:[{finish:1,cornerPositions:[1,1]}]}]});
console.log('OBSERVED_PACE_LEAKAGE_SAFE_NO_UNAPPROVED_SIMULATION_OK');
