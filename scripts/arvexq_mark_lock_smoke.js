// v345 frozen-mark regression: reproduces an actual pre-race mark flip and
// confirms that late odds, updates and results never rewrite a saved opinion.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function extract(a,b){
 const start=src.indexOf('function '+a+'('),stop=src.indexOf('function '+b+'(',start+1);
 assert.ok(start>=0&&stop>start,'missing '+a);return src.slice(start,stop);
}
const storage=new Map(),localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
let minute=19*60+58;
const n=(v,d=0)=>v==null||!Number.isFinite(Number(v))?d:Number(v);
const fn=new Function('localStorage','mins','today','nowMins','n','isScratchHorse','esc','isFinal','isFlash','hasAnyResultData',
  extract('raceMarkClock','applyServerAuthoritativeMarks')+
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
const p=make(['◎','▲','注','○']);
assert.equal(fn.applyFrozenMarks(race,p).markFreeze.source,'provisional');
assert.equal(fn.loadFrozenMarks(race),null,'cannot freeze 12 min before post');
minute=20*60+1;
assert.equal(fn.applyFrozenMarks(race,p).markFreeze.source,'local-prepost');
const frozen=fn.loadFrozenMarks(race);
assert.equal(frozen.marks[0].mark,'◎');
assert.equal(frozen.marks[2].single,true);
const flipped=make(['△','◎','○','▲']);
fn.applyFrozenMarks(race,flipped);
assert.deepEqual(flipped.rows.map(z=>z.predMark),['◎','▲','注','○']);
assert.equal(flipped.rows[2].singleWinSuitable,true);
minute=20*60+15;
fn.applyFrozenMarks(race,flipped);
assert.deepEqual(flipped.rows.map(z=>z.predMark),['◎','▲','注','○'],'result cannot change pre-race opinion');
const cancelled=make(['△','◎','▲','○']);
cancelled.rows[0].horse.scratched=true;
fn.applyFrozenMarks(race,cancelled);
assert.equal(cancelled.rows[0].predMark,'','cancelled horse must not retain publishable mark');
const resultWithoutClock={...race,startTime:'',result:{status:'確定',
  finishers:[{horseNumber:3,finish:1}]}};
assert.equal(fn.raceMarkClock(resultWithoutClock).started,true,
 'published result must always suppress prediction regardless of missing clock');
const onOtherDevice={...race,id:'nar-2026-10-08-大井-12',startTime:'20:10'};
const postResult=fn.applyFrozenMarks(onOtherDevice,make(['◎','○','▲','☆']));
assert.equal(postResult.markFreeze.source,'missing-prerace');
assert.ok(postResult.rows.every(z=>z.predMark===''),'no post-hoc prediction without a recorded pre-off mark');
assert.match(src,/if\(started&&!Object\.keys\(byNo\)\.length\)return false/,'post-race cannot apply rerun mark');
assert.match(src,/if\(raceMarkClock\(r\)\.started\)/,'post-start must use archived read-only path');
assert.match(src,/if\(changed\)\{saveDetailCache\(id,state\.race\);render\(\)\}/,'odds-only refresh must not blindly reset');
assert.match(src,/resultPublished=isFinal\(r\)\|\|isFlash\(r\)\|\|hasAnyResultData\(r\)/,
  'official results must stop prediction even without a scheduled start time');
console.log('ARVEXQ_MARK_FREEZE_OK late_update=stable historical_no_posthoc scratch=safe');
