#!/usr/bin/env node
// Morning freeze runner contract after the 2026-11-28 engine retirement.
// The in-app predictor that computed the freeze was removed with the
// rich UI (the app is now the entry-table-only shell), so
// arvexq_morning_picks.js must now:
//   - never fabricate a freeze: a complete future card, a past card and
//     an incomplete card all come back unchanged, with no morning
//     fields stamped and no mark snapshots invented;
//   - never overwrite morning fields already present on the payload;
//   - still honour a genuine pre-existing archive (first-write-wins
//     restore; fixedAt comes from the archive, never from "now");
//   - still refuse a corrupt archive (the identity guard stays fatal).
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),
 path=require('node:path'),cp=require('node:child_process');
const repo=process.cwd();
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'arvexq-morning-'));
const work=path.join(temp,'work');
// The producer resolves app.js and the morning modules relative to its
// working directory, so stage the real current files in a scratch tree.
fs.mkdirSync(path.join(work,'arvexq/ui/static'),{recursive:true});
fs.copyFileSync(path.join(repo,'arvexq/ui/static/app.js'),
  path.join(work,'arvexq/ui/static/app.js'));
fs.cpSync(path.join(repo,'arvexq/ui/static/morning'),
  path.join(work,'arvexq/ui/static/morning'),{recursive:true});
function fixture(date,start){
  const races=[
    {id:'nar-'+date+'-大井-01',date,circuit:'地方',track:'大井',raceNumber:1,startTime:start,title:'朝の能力判定'},
    {id:'nar-'+date+'-大井-02',date,circuit:'地方',track:'大井',raceNumber:2,startTime:start,title:'大井記念 重賞'},
  ];
  const details=races.map(r=>({...r,careerReadiness:{ready:true},preparedMeta:{diagnosisReady:true,careerReady:true},
    horses:[1,2,3,4,5].map(n=>({horseNumber:n,name:'テスト馬'+n,frameNumber:n,sex:'牡',age:4,
      recentRaces:[{date:'2026-08-01',cornerPositions:[n,n],finish:n,fieldSize:8,distance:1200,track:'大井'}]}))}));
  return {summaries:races,details,meta:{sync_date:date,race_count:races.length}};
}
function run(testcase){
  const src=path.join(temp,'in.json'),out=path.join(temp,'out.json');
  fs.writeFileSync(src,JSON.stringify(testcase));
  const stdout=cp.execFileSync(process.execPath,
    [path.join(repo,'scripts/arvexq_morning_picks.js'),src,out],
    {cwd:work,stdio:'pipe',timeout:30000}).toString();
  return {payload:JSON.parse(fs.readFileSync(out,'utf8')),stdout};
}
function assertNoMorningFields(payload){
  for(const r of payload.summaries)
    for(const k of Object.keys(r))assert(!k.startsWith('morning'),'summary gained '+k);
  for(const d of payload.details){
    assert(!('morningMarkSnapshot' in d),'detail gained a mark snapshot');
    for(const k of Object.keys(d))assert(!k.startsWith('morning'),'detail gained '+k);
  }
}
try{
  const tomorrow=new Date(Date.now()+9*3600000+86400000).toISOString().slice(0,10);
  // A complete morning card can no longer be frozen: the payload comes
  // back identical and the producer says so honestly.
  const prepared=fixture(tomorrow,'21:00');
  const r1=run(prepared);
  assert(r1.stdout.includes('MORNING_PICKS_ENGINE_UNAVAILABLE_NO_FREEZE'),r1.stdout);
  assert.deepEqual(r1.payload,prepared);
  assertNoMorningFields(r1.payload);
  // A past card is never reconstructed after the first off.
  const past=fixture('2025-10-01','09:00');
  const r2=run(past);
  assert(r2.stdout.includes('MORNING_PICKS_NOT_RECONSTRUCTED_AFTER_FIRST_OFF'),r2.stdout);
  assert.deepEqual(r2.payload,past);
  // An incomplete card freezes nothing either.
  const partial=fixture(tomorrow,'21:00');partial.details.pop();
  const r3=run(partial);
  assert(r3.stdout.includes('MORNING_PICKS_AWAITING_SUFFICIENT_MORNING_DATA'),r3.stdout);
  assert.deepEqual(r3.payload,partial);
  assertNoMorningFields(r3.payload);
  // Morning fields already on the payload are preserved untouched:
  // no re-freeze, no new fixedAt, no reshuffle.
  const stamped=fixture(tomorrow,'21:00');
  for(const r of stamped.summaries){
    r.morningPickVersion='v1';r.morningPickFixedAt='2026-01-01T06:30:00.000Z';
    r.morningSelected=false;r.morningSpecial=false;
  }
  const r4=run(stamped);
  assert.deepEqual(r4.payload,stamped);
  // A genuine archive is still restored first-write-wins.
  const archive={version:'v1',date:tomorrow,fixedAt:'2026-01-02T06:30:00.000Z',scope:2,races:[
    {id:'nar-'+tomorrow+'-大井-01',selected:false,selectedScore:0,special:false,
     assessed:true,primaryType:'',types:[],selectionReason:'',selectionModelVersion:'',
     selectionSystems:[],selectionProdPick:null,selectionV26Pick:null,
     selectionFavourite:null,ticketKinds:[],ticketEvidence:null},
    {id:'nar-'+tomorrow+'-大井-02',selected:false,selectedScore:0,special:true,
     assessed:true,primaryType:'',types:[],selectionReason:'',selectionModelVersion:'',
     selectionSystems:[],selectionProdPick:null,selectionV26Pick:null,
     selectionFavourite:null,ticketKinds:[],ticketEvidence:null}]};
  const dir=path.join(work,'arvexq/ui/static/morning-picks');
  fs.mkdirSync(dir,{recursive:true});
  fs.writeFileSync(path.join(dir,tomorrow+'.json'),JSON.stringify(archive));
  const r5=run(fixture(tomorrow,'21:00'));
  assert(r5.stdout.includes('MORNING_PICKS_REUSED_ALREADY_FIXED'),r5.stdout);
  assert(r5.payload.summaries.every(r=>r.morningPickVersion==='v1'&&
    r.morningPickFixedAt===archive.fixedAt));
  assert.equal(r5.payload.summaries[0].morningSpecial,false);
  assert.equal(r5.payload.summaries[1].morningSpecial,true);
  assert(r5.payload.details.every(d=>d.morningPickFixedAt===archive.fixedAt));
  // Corrupt archives stay fatal (scope mismatch, wrong version).
  fs.writeFileSync(path.join(dir,tomorrow+'.json'),JSON.stringify({...archive,scope:3}));
  assert.throws(()=>run(fixture(tomorrow,'21:00')));
  fs.writeFileSync(path.join(dir,tomorrow+'.json'),JSON.stringify({...archive,version:'v2'}));
  assert.throws(()=>run(fixture(tomorrow,'21:00')));
  console.log('MORNING_PICKS_RUNNER_FREEZE_NO_POST_HOC_PASS');
}finally{fs.rmSync(temp,{recursive:true,force:true})}
