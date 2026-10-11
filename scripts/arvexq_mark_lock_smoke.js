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
  'return {raceMarkClock,markFreezeKey,loadFrozenMarks,applyFrozenMarks};')(
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
const old=make(['◎','▲','注','○']);
assert.equal(fn.applyFrozenMarks(race,old).markFreeze.source,'live-before-post');
assert.equal(fn.loadFrozenMarks(race),null,'no local receipt 12 min before post');
minute=20*60+1;
assert.equal(fn.applyFrozenMarks(race,old).markFreeze.source,'live-before-post');
const frozen=fn.loadFrozenMarks(race);
assert.equal(frozen.marks[0].mark,'◎','historical pre-off receipt created once');
assert.equal(frozen.marks[2].single,true);
const next=make(['△','◎','○','▲']);
fn.applyFrozenMarks(race,next);
assert.deepEqual(next.rows.map(z=>z.predMark),['△','◎','○','▲'],'fresh data controls preoff displayed marks');
assert.equal(next.markFreeze.originalPreserved,true);
assert.equal(fn.loadFrozenMarks(race).marks[0].mark,'◎','old saved original never rewritten');
minute=20*60+15;
const after=make(['△','◎','○','▲']);
fn.applyFrozenMarks(race,after);
assert.deepEqual(after.rows.map(z=>z.predMark),['◎','▲','注','○'],'postoff restores prior original');
const cancelled=make(['△','◎','▲','○']);cancelled.rows[0].horse.scratched=true;
fn.applyFrozenMarks(race,cancelled);
assert.equal(cancelled.rows[0].predMark,'','scratched cannot retain public mark');
const resultWithoutClock={...race,startTime:'',result:{status:'確定',
  finishers:[{horseNumber:3,finish:1}]}};
assert.equal(fn.raceMarkClock(resultWithoutClock).started,true);
const onOtherDevice={...race,id:'nar-2026-10-08-大井-12',startTime:'20:10'};
const noHistory=fn.applyFrozenMarks(onOtherDevice,make(['◎','○','▲','☆']));
assert.equal(noHistory.markFreeze.source,'missing-prerace');
assert.ok(noHistory.rows.every(z=>z.predMark===''),'no post-hoc inferred opinion');
assert.ok(!src.includes('function applyServerAuthoritativeMarks('),'obsolete server mark overwriter deleted');
assert.match(src,/if\(raceMarkClock\(r\)\.started\)/,'post-start archive path');
assert.match(src,/resultPublished=isFinal\(r\)\|\|isFlash\(r\)\|\|hasAnyResultData\(r\)/);
console.log('ARVEXQ_MARK_PREOFF_LATEST_OK preoff=updated original=preserved postoff=immutable scratch=safe');
