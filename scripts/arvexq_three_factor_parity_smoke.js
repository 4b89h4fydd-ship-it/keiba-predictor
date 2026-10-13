#!/usr/bin/env node
'use strict';
// Executable contract for the one active 45/35/20 scoring method.
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function arvexqFactorValues(');
const end=src.indexOf('function arvexqRacePolicy(',start);
assert(start>=0&&end>start,'new factors must be part of the real predictor');
const model=new Function(src.slice(start,end)+'; return arvexqFactorValues;')();
const hist=[1,2,1,2,1].map((finish,i)=>({
  date:'2026-10-'+String(11-i*2).padStart(2,'0'),
  fieldSize:12,finish,last3fRank:finish,track:'園田',distance:1400
}));
const horse={horseNumber:1,recentRaces:hist,allPastRuns:hist,
  integratedEvaluation:{v218Audit:{trueRun:0,pure:0,sectional:0}}};
const x=model({horse},{date:'2026-10-13'});
const q=hist.map(h=>(12-h.finish)/11);
const tr=q.reduce((sum,v,i)=>sum+v*(5-i),0)/15;
const sorted=q.slice().sort((a,b)=>a-b);
const pure=(sorted[4]+sorted[2])/2, sec=q.reduce((a,b)=>a+b,0)/5;
const expected=.45*tr+.35*pure+.20*sec;
assert.equal(x.coverage,3);
assert(Math.abs(x.score-expected)<1e-12,'three direct pre-off factors and weights');
assert(!src.slice(start,end).includes('v218Audit'),'old v218 model score cannot rank horses');
horse.recentRaces.push({date:'2026-10-14',fieldSize:12,finish:1,last3fRank:1});
assert(Math.abs(model({horse},{date:'2026-10-13'}).score-expected)<1e-12,'future excluded');
const absent=model({horse:{recentRaces:[]}},{date:'2026-10-13'});
assert.equal(absent.coverage,0);
assert.equal(absent.score,.5,'missing cannot create a fabricated 80+ elite rating');
console.log('THREE_FACTOR_PARITY_OK TRUE_RUN_45 PURE_35 SECTIONAL_20');


// Cross-language parity: production JS and authoritative Python must select
// identical date-bounded five runs, including mixed provider date formats.
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
  {label:'missing recent lane but historical alias supplied',race:{date:'2026-10-14'},
   horse:{history:[{raceDate:'2026.10.12',runners:12,finishPosition:1,last3fRank:1},
                   {date:'2026-10-13',fieldSize:11,finish:2,last3fRank:3}]}},
  {label:'future only is not evidence',race:{date:'2026-10-14'},
   horse:{recentRaces:[{date:'2026-10-14',fieldSize:12,finish:1,last3fRank:1}]}},
];
const py=String.raw`import json,sys
from arvexq.prediction.factor_model import collect_horse_raw_metrics
cases=json.load(sys.stdin)
out=[]
for c in cases:
  v=collect_horse_raw_metrics(c["horse"],c["race"])
  out.append({"trueRun":v["trueRun"],"pure":v["pure"],"sectional":v["sectional"],
              "coverage":sum(v[k] is not None for k in ("trueRun","pure","sectional")),
              "score":sum(w*(v[k] if v[k] is not None else .5) for k,w in
                          (("trueRun",.45),("pure",.35),("sectional",.20)))})
print(json.dumps(out))
`;
const proc=spawnSync('python',['-c',py],{input:JSON.stringify(cases),encoding:'utf8'});
assert.equal(proc.status,0,proc.stderr||'Python parity unavailable');
const pythonRows=JSON.parse(proc.stdout);
cases.forEach((c,i)=>{
  const got=model({horse:c.horse},c.race), expected=pythonRows[i];
  assert.equal(got.coverage,expected.coverage,c.label+' coverage');
  for(const key of ['trueRun','pure','sectional','score']){
    if(expected[key]==null)assert.equal(got[key],null,c.label+' '+key);
    else assert(Math.abs(got[key]-expected[key])<1e-12,
      c.label+' '+key+': JS='+got[key]+' Python='+expected[key]);
  }
});
console.log('THREE_FACTOR_CROSS_LANGUAGE_PARITY_OK',cases.length,'cases');
