#!/usr/bin/env node
'use strict';
// Executable parity contract for staged no-sectional pre-off scoring.
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function arvexqFactorValues(');
const end=src.indexOf('function arvexqRacePolicy(',start);
assert(start>=0&&end>start,'active pre-off factor function missing');
const model=new Function(src.slice(start,end)+'; return arvexqFactorValues;')();
const hist=[1,2,1,2,1].map((finish,i)=>({
  date:'2026-10-'+String(11-i*2).padStart(2,'0'),
  fieldSize:12,finish,last3fRank:finish,track:'園田',distance:1400,surface:'ダート'
}));
const horse={horseNumber:1,recentRaces:hist,allPastRuns:hist,
  integratedEvaluation:{v218Audit:{trueRun:0,pure:0,sectional:0}}};
const race={date:'2026-10-13',distance:1400,surface:'ダート'};
const x=model({horse},race);
const q=hist.map(h=>(12-h.finish)/11);
const recent=q.reduce((sum,v,i)=>sum+v*(5-i),0)/15;
const condition=q.reduce((sum,v)=>sum+v,0)/5;
const expected=.75*recent+.25*condition;
assert.equal(x.coverage,2);
assert(Math.abs(x.score-expected)<1e-12,'observed form and condition blend');
assert(!src.slice(start,end).includes('v218Audit'),'legacy score may not affect live model');
assert(!src.slice(start,end).includes('.35*pure'),'retired peak score must not return');
horse.recentRaces.push({date:'2026-10-14',fieldSize:12,finish:1,last3fRank:1,surface:'ダート'});
assert(Math.abs(model({horse},race).score-expected)<1e-12,'future excluded');
const rankless=JSON.parse(JSON.stringify(horse));
for(const run of rankless.recentRaces)delete run.last3fRank;
for(const run of rankless.allPastRuns)delete run.last3fRank;
assert(Math.abs(model({horse:rankless},race).score-expected)<1e-12,'missing sectionals cannot alter score');
const absent=model({horse:{recentRaces:[]}},race);
assert.equal(absent.coverage,0);
assert.equal(absent.score,.5,'missing records do not create elite scores');
console.log('FORM_CONDITION_PARITY_OK');

// Cross-language test covers mixed date formats, complementary duplicates,
// future observations, missing prior runs, and matching/nonmatching conditions.
const {spawnSync}=require('node:child_process');
const cases=[
  {label:'compact and slash dates',race:{date:'2026-10-14'},
   horse:{recentRaces:[
     {date:'20261012',fieldSize:8,finish:2,last3fRank:1},
     {date:'2026/10/11',fieldSize:11,finish:3,last3fRank:2},
     {date:'2026-10-15',fieldSize:9,finish:1,last3fRank:1}] }},
  {label:'provider duplicate merged by day',race:{date:'2026-10-14'},
   horse:{recentRaces:[{date:'2026-10-12',fieldSize:12,finish:4}],
          allPastRuns:[{date:'20261012',fieldSize:12,finish:4,last3fRank:2},
                       {date:'2026-10-10',fieldSize:11,finish:3,last600Rank:1}]}},
  {label:'history alias',race:{date:'2026-10-14'},
   horse:{history:[{raceDate:'2026.10.12',runners:12,finishPosition:1,last3fRank:1},
                   {date:'2026-10-13',fieldSize:11,finish:2,last3fRank:3}]}},
  {label:'future only',race:{date:'2026-10-14'},
   horse:{recentRaces:[{date:'2026-10-14',fieldSize:12,finish:1,last3fRank:1}]}},
  {label:'pastRaces alias',race:{date:'2026-10-14'},
   horse:{pastRaces:[{raceDate:'2026/10/13',fieldSize:9,finishPosition:2,last3fRank:1}]}},
  {label:'runs alias invalid dates',race:{date:'2026-10-14'},
   horse:{runs:[{date:'2026.10.11',runners:10,finish:4,last3fRank:3},
                {date:'2026-10-14',runners:12,finish:1,last3fRank:1},
                {date:'2026-02-30',runners:11,finish:1,last3fRank:1}]}},
  {label:'matched course with form sample',race:{date:'2026-10-14',distance:1400,surface:'ダート'},
   horse:{recentRaces:[
     {date:'2026-10-12',fieldSize:10,finish:1,distance:1400,surface:'ダート'},
     {date:'2026-10-10',fieldSize:10,finish:6,distance:2000,surface:'芝'},
     {date:'2026-10-08',fieldSize:10,finish:3,distance:1400,surface:'ダート'}]}},
];
const py=String.raw`import json,sys
from arvexq.prediction.factor_model import rank_factor_model
cases=json.load(sys.stdin)
rows=[]
for c in cases:
  horse={"horseNumber":1,**c["horse"]}
  ranked=rank_factor_model([horse],c["race"])
  if not ranked:
    rows.append({"recentForm":None,"conditionForm":None,"coverage":0,"score":.5})
  else:
    item=ranked[0]
    rows.append({**item["factors"],"coverage":item["primaryPillarCoverage"],"score":item["score"]})
print(json.dumps(rows))
`;
const proc=spawnSync('python',['-c',py],{input:JSON.stringify(cases),encoding:'utf8'});
assert.equal(proc.status,0,proc.stderr||'Python parity unavailable');
const pythonRows=JSON.parse(proc.stdout);
cases.forEach((c,i)=>{
  const got=model({horse:c.horse},c.race), expected=pythonRows[i];
  assert.equal(got.coverage,expected.coverage,c.label+' coverage');
  for(const key of ['recentForm','conditionForm','score']){
    if(expected[key]==null)assert.equal(got[key],null,c.label+' '+key);
    else assert(Math.abs(got[key]-expected[key])<1e-12,
      c.label+' '+key+': JS='+got[key]+' Python='+expected[key]);
  }
});
console.log('FORM_CONDITION_CROSS_LANGUAGE_PARITY_OK',cases.length,'cases');
