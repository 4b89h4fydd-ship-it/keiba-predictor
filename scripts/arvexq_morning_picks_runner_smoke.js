#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),
 path=require('node:path'),cp=require('node:child_process');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'arvexq-morning-'));
function fixture(date,start){
  const races=[
    {id:'nar-'+date+'-大井-01',date,circuit:'地方',track:'大井',raceNumber:1,startTime:start,title:'朝の能力判定'},
    {id:'nar-'+date+'-大井-02',date,circuit:'地方',track:'大井',raceNumber:2,startTime:start,title:'大井記念 重賞'},
  ];
  const details=races.map(r=>({...r,preparedMeta:{diagnosisReady:true},
    horses:[1,2,3,4,5].map(n=>({horseNumber:n,name:'テスト馬'+n,frameNumber:n,sex:'牡',age:4,
      recentRaces:[{date:'2026-08-01',cornerPositions:[n,n],finish:n,fieldSize:8,distance:1200,track:'大井'}]}))}));
  return {summaries:races,details,meta:{sync_date:date,race_count:races.length}};
}
function run(testcase){
  const src=path.join(temp,'in.json'),out=path.join(temp,'out.json');
  fs.writeFileSync(src,JSON.stringify(testcase));
  cp.execFileSync(process.execPath,['scripts/arvexq_morning_picks.js',src,out],{cwd:process.cwd(),stdio:'pipe',timeout:30000});
  return JSON.parse(fs.readFileSync(out,'utf8'));
}
try{
  const today=new Date(Date.now()+9*3600000).toISOString().slice(0,10);
  const tomorrow=new Date(Date.now()+9*3600000+86400000).toISOString().slice(0,10);
  const prepared=fixture(tomorrow,'21:00');
  const frozen=run(prepared);
  assert.equal(frozen.summaries.length,2);
  assert(frozen.summaries.every(r=>r.morningPickVersion==='v1'&&typeof r.morningSelected==='boolean'));
  assert.equal(frozen.summaries[1].morningSpecial,true,'grade race selected before post');
  assert(frozen.summaries.every(r=>Array.isArray(r.morningSelectedTypes)),'public labels must be archived');
  assert(frozen.summaries.every(r=>typeof r.morningPrimaryType==='string'));
  assert(frozen.summaries.every(r=>typeof r.morningSelectionReason==='string'));
  assert(frozen.details.every(d=>d.morningPickFixedAt));
  // Once a complete morning card is known, a single missing AI diagnosis may
  // be archived as unassessed rather than freezing zero races for everyone.
  const mixed=fixture(tomorrow,'21:00');
  for(let k=3;k<=5;k++){
    const r={id:'nar-'+tomorrow+'-大井-'+String(k).padStart(2,'0'),date:tomorrow,
      circuit:'地方',track:'大井',raceNumber:k,startTime:'21:00',title:'未判定も記録する朝の出走表'};
    mixed.summaries.push(r);
    mixed.details.push({...mixed.details[0],...r});
  }
  mixed.details[4].preparedMeta={diagnosisReady:false};
  const partialDiagnosis=run(mixed);
  assert.equal(partialDiagnosis.summaries.length,5);
  assert(partialDiagnosis.summaries.every(r=>r.morningPickVersion==='v1'));
  assert.equal(partialDiagnosis.summaries[4].morningAssessed,false);
  assert.deepEqual(partialDiagnosis.summaries[4].morningSelectedTypes,[]);
  assert.equal(partialDiagnosis.summaries[4].morningSelected,false,'never promote unassessed cards');
  assert(partialDiagnosis.summaries.slice(0,4).every(r=>r.morningAssessed===true));
  const past=fixture('2025-10-01','09:00');
  assert(run(past).summaries.every(r=>!r.morningPickFixedAt),'do not fabricate after first post');
  const partial=fixture(tomorrow,'21:00');partial.details.pop();
  assert(run(partial).summaries.every(r=>!r.morningPickFixedAt),'do not publish incomplete morning card');
  console.log('MORNING_PICKS_RUNNER_FREEZE_NO_POST_HOC_PASS');
}finally{fs.rmSync(temp,{recursive:true,force:true})}
