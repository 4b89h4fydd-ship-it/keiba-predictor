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
  extract('function paceHistoryRuns(','function minetaRaceContext(')+'\nreturn minetaPastProfile;')(
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

const pack=(rows,order,laneMap,stage)=>
  order.map((x,i)=>({no:x.horse.horseNumber,lane:0,gap:i*.02,score:1-i/Math.max(1,order.length-1)}));
const plan=new Function('n','clamp','courseTraits','firstTurnDistance','eventOrderPack',
  extract('function scenarioPlan(','function gradeClass(')+'\nreturn scenarioPlan;')(
    n,clamp,()=>({straight:.75,moveRoom:.65}),()=>350,pack);
function horse(no,fields){
  return Object.assign({horse:{horseNumber:no},goProb:.2,needLead:.2,breakSkill:.4,
    ten:.4,holdFront:.5,stamina:.6,ability:.5,latePower:.4,comeFromBehind:.3,
    fade:.3,frontStay:.4,frontCost:.03,trafficTol:.5,move:.25,turnSkill:.5,
    close:.1,stalk:.25,mid:.25,outerStress:0,flexibility:.5,posCons:.5,
    lateGain:.5,draw:no/5,minetaPast:{},expected:'中団',hold:.5},fields);
}
function simulate(closerAbility,mode){
  const rows=[
    horse(1,{goProb:.9,needLead:.9,breakSkill:.9,ten:.9,holdFront:.95,
      stamina:.95,ability:.9,latePower:.55,frontStay:.96,fade:.08,
      minetaPast:{prevLeader:true},minetaLeadRank:1,expected:'逃げ候補'}),
    horse(2,{goProb:.7,needLead:.7,breakSkill:.7,ten:.7,holdFront:.7,
      frontStay:.7,ability:.75,stamina:.75,expected:'先行'}),
    horse(3,{goProb:.4,ability:.65,expected:'好位',stalk:.42}),
    horse(4,{goProb:.15,ability:closerAbility,latePower:.66,
      comeFromBehind:.65,stamina:closerAbility,move:.83,turnSkill:.8,
      close:.7,expected:'後方'}),
  ];
  const arrangement={leadCandidates:rows.slice(0,2),front:rows.slice(0,3),
    hardLeadCount:1,middleFront:[],secondCandidates:rows.slice(1,3)};
  const p=plan({distance:1200},rows,[{code:mode,prob:1}],{},{},arrangement);
  const orders=Object.fromEntries(p.stages.map(st=>[st.key,st.pack.map(row=>row.no)]));
  return {p,orders};
}
const weakA=simulate(.2,'A'),strongC=simulate(.99,'C');
assert.equal(weakA.orders.start[0],1,'first-corner evidence controls leader');
assert.ok(weakA.orders.first.indexOf(2)<=2,'genuine lead battler stays in front cluster');
assert.equal(weakA.orders.straight[0],1,'weak late horse cannot leap over strong leader');
assert.equal(strongC.orders.straight[0],4,'strong late horse can make a supported pass');
for(const orders of [weakA.orders,strongC.orders]){
  for(const key of ['start','first','back','turn3','turn4','straight']){
    assert.equal(new Set(orders[key]).size,4,'unique runner identities at '+key);
  }
  for(const [before,after] of [['first','back'],['back','turn3'],['turn3','turn4']]){
    for(const no of [1,2,3,4]){
      const gain=orders[before].indexOf(no)-orders[after].indexOf(no);
      assert.ok(gain<=2,'unexpected '+gain+'-place leap '+no+' at '+after);
    }
  }
}
assert.ok(src.includes("model:'event-transition-v2'"),'pace model version');
assert.ok(src.includes('finishStrength(z)<finishStrength(rival)+required'),
  'late pass requires superiority over the actual horse immediately ahead');
assert.ok(src.includes('leaderHold&&!leaderCollapse&&!challenger'),
  'front runner yields to a strong challenger');
console.log('PACE_TRANSITION_OK genuine lead, no teleport, bounded 3C/4C, conditional late pass');
