// Current preview marks may update before off, while saved originals are immutable.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function extract(a,b){
 const start=src.indexOf('function '+a+'('),stop=src.indexOf('function '+b+'(',start+1);
 assert.ok(start>=0&&stop>start,'missing '+a);return src.slice(start,stop);
}
const storage=new Map(),localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
let minute=19*60+58;
const n=(v,d=0)=>v==null||!Number.isFinite(Number(v))?d:Number(v);
const fn=new Function('localStorage','mins','today','nowMins','n','isScratchHorse','esc','isFinal','isFlash','hasAnyResultData',
  extract('raceMarkClock','predict')+
  extract('validatedHonmeiMetadata','racecardMarkLegend')+
  'return {raceMarkClock,applyFrozenMarks};')(
    localStorage,t=>Number(t.slice(0,2))*60+Number(t.slice(3)),
    ()=>'2026-10-08',()=>minute,n,h=>!!h.scratched,v=>String(v),
    r=>r?.result?.status==='確定',r=>r?.result?.status==='速報',
    r=>Array.isArray(r?.result?.finishers)&&r.result.finishers.some(x=>x.finish>0));
const race={id:'nar-2026-10-08-大井-11',date:'2026-10-08',startTime:'20:10',
  horses:Array.from({length:4},(_,i)=>({horseNumber:i+1}))};
function make(marks){
 return {coverage:.65,rows:marks.map((mark,i)=>({horse:{horseNumber:i+1},predMark:mark,
  singleWinSuitable:i===2,overallRaw:.65}))};
}
const old=make(['◎','○','▲','△']);
assert.equal(fn.applyFrozenMarks(race,old).markFreeze.source,'live-before-post');
assert.ok(!src.includes('loadFrozenMarks'),'old v345 local receipt is retired');
minute=20*60+1;
assert.equal(fn.applyFrozenMarks(race,old).markFreeze.source,'live-before-post');
assert.ok(!src.includes('loadFrozenMarks'),'no v345 receipt loader exists');
assert.equal(storage.size,0,'no obsolete mark receipt write');
const next=make(['△','◎','○','▲']);
fn.applyFrozenMarks(race,next);
assert.deepEqual(next.rows.map(z=>z.predMark),['△','◎','○','▲'],
  'fresh data controls preoff displayed marks');
minute=20*60+15;
const after=make(['△','◎','○','▲']);
fn.applyFrozenMarks(race,after);
assert.ok(after.rows.every(z=>z.predMark===''),
  'no old local guess is presented as pre-off archive');
const resultWithoutClock={...race,startTime:'',result:{status:'確定',
  finishers:[{horseNumber:3,finish:1}]}};
assert.equal(fn.raceMarkClock(resultWithoutClock).started,true);
const onOtherDevice={...race,id:'nar-2026-10-08-大井-12',startTime:'20:10'};
const noHistory=fn.applyFrozenMarks(onOtherDevice,make(['◎','○','▲','☆']));
assert.equal(noHistory.markFreeze.source,'missing-prerace');
assert.ok(noHistory.rows.every(z=>z.predMark===''),'no post-hoc inferred opinion');
assert.ok(!src.includes('function applyServerAuthoritativeMarks('),'obsolete server mark overwriter deleted');
assert.doesNotMatch(extract('predict','nextRace'),/postRaceRevision=true/,'retired postoff recomputation must be absent');
assert.match(extract('predict','nextRace'),/learnedD1Prediction\(r\)/,'D1 learned marks are authoritative');
assert.match(src,/resultPublished=isFinal\(r\)\|\|isFlash\(r\)\|\|hasAnyResultData\(r\)/);
console.log('ARVEXQ_MARK_PREOFF_LATEST_OK preoff=updated old_local=retired postoff=no_guess scratch=safe');
