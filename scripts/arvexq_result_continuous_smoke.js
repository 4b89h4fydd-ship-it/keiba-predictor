#!/usr/bin/env node
'use strict';
// Synthetic runner: verify that result/payout polling is independent of AI
// diagnosis, and that sparse responses cannot erase already published results.
const assert=require('node:assert/strict'),fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert.ok(app.includes('if(state.race) scheduleResultRefresh();'),
  'polling must start even when diagnosis is missing');
assert.ok(app.includes("if(key==='result')return resultPanel(r);"),
  'the result panel must not be replaced by a perpetual skeleton');
const useful=v=>v!==null&&v!==undefined&&v!==''&&
 (!Array.isArray(v)||v.length>0)&&
 (typeof v!=='object'||Array.isArray(v)||Object.keys(v).length>0);
const n=(v,d=0)=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):d;
const a=app.indexOf('function mergePublishedResult('),b=app.indexOf('function mergeRaceReflection(',a);
assert.ok(a>0&&b>a,'result merge is an independent function');
const merge=new Function('reflectUseful','n',app.slice(a,b)+';return mergePublishedResult;')(useful,n);
const final={status:'確定',finishers:[{horseNumber:1,finish:1,name:'Winner'},
 {horseNumber:2,finish:2},{horseNumber:3,finish:3}],
 payouts:[{type:'単勝',amount:120},{type:'馬連',amount:300}]};
const partial=merge(final,{status:'速報',finishers:[{horseNumber:1,finish:1}],payouts:[]});
assert.equal(partial.status,'確定','a stale速報 cannot downgrade final');
assert.deepEqual(partial.finishers,final.finishers);
assert.deepEqual(partial.payouts,final.payouts);
const payoutOnly=merge({status:'確定',finishers:final.finishers},
 {payouts:final.payouts});
assert.deepEqual(payoutOnly.payouts,final.payouts,
 'payout-only updates must work even without a new finisher list');
const improved=merge({status:'速報',finishers:final.finishers,payouts:[final.payouts[0]]},
 {status:'確定',finishers:final.finishers,payouts:final.payouts});
assert.equal(improved.status,'確定');assert.equal(improved.payouts.length,2);
assert.equal(improved.finishers[0].name,'Winner');

const i=app.indexOf('var resultPollBusy=false'),j=app.indexOf('function refreshPayoutsOnly(',i);
assert.ok(i>0&&j>i);
const timers=new Map();let nextId=0,requests=0,renders=0;
const state={race:{id:'nar-2026-10-11-大井-04',date:'2026-10-11',
 startTime:'09:00',horses:[],result:{status:'速報',finishers:[]}},
 detailSeq:1,resultTimer:null};
const env={state, today:()=> '2026-10-11', n, mins:s=>Number(s.slice(0,2))*60+Number(s.slice(3,5)),
 nowMins:()=>600, isFinal:r=>r.result?.status==='確定',
 hasResultData:r=>(r.result?.finishers||[]).length>=3,
 setTimeout:(fn,delay)=>{assert.ok(delay>=20000);const id=++nextId;timers.set(id,fn);return id},
 clearTimeout:id=>timers.delete(id),
 fetchEdgeRace:async id=>{requests++;return {...state.race,result:final}},
 applySummaryEnvironment:x=>x,
 mergeRaceReflection:(old,current)=>({...old,...current,result:merge(old.result,current.result)}),
 instantTrackDetails:{},saveDetailCache:()=>{},updateDetailSections:()=>{},
 traceRaceDetail:()=>{},detailState:()=>({}),
 render:()=>{renders++}
};
const scheduler=new Function(...Object.keys(env),app.slice(i,j)+
 ';return {scheduleResultRefresh,active:function(){return resultPollActiveId}};')
 (...Object.values(env));
(async()=>{
 scheduler.scheduleResultRefresh();
 assert.equal(timers.size,1,'results should schedule without a prediction');
 const existing=state.resultTimer;
 scheduler.scheduleResultRefresh();
 assert.equal(state.resultTimer,existing,'a re-render must not reset the pending poll');
 const action=timers.get(existing);timers.delete(existing);action();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests,1);
 assert.equal(renders,1);
 assert.equal(state.race.result.status,'確定');
 assert.equal(state.race.result.payouts.length,2);
 assert.equal(timers.size,0,'full final result+payout stops polling');
 state.race.result={status:'確定',finishers:final.finishers,payouts:[]};
 scheduler.scheduleResultRefresh();
 assert.equal(timers.size,1,'confirmed result without payout continues polling');
 console.log('RESULT_CONTINUOUS_SMOKE_OK missing-diagnosis=polled payout-wait=retried stale=protected');
})().catch(e=>{console.error(e);process.exitCode=1;});
