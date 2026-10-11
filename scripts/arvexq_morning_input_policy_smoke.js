#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const {status}=require('../arvexq/pipeline/morning_input_policy.js');
const day='2026-10-12';
const rows=[1,2,3,4,5].map(i=>({id:'race-'+i,date:day,track:'大井',raceNumber:i,startTime:'12:00'}));
const horses=(complete)=>Array.from({length:8},(_,i)=>({
 horseNumber:i+1,name:'Horse '+(i+1),
 recentRaces:complete?[{date:'2026-09-01',finish:2}]:[]
}));
const details=new Map(rows.map((r,i)=>[r.id,{
 id:r.id,horses:horses(i!==4),preparedMeta:{diagnosisReady:i!==4,careerReady:false},
 careerReadiness:{ready:false}
}]));
let result=status(rows,details,day);
assert.equal(result.scheduleReady,true);
assert.deepEqual([...result.assessedIds],['race-1','race-2','race-3','race-4']);
assert.deepEqual(result.missingCards,['race-5']);
assert.equal(result.assessedIds.size/rows.length,.8);
details.get('race-5').horses=horses(true);
result=status(rows,details,day);
assert.equal(result.assessedIds.size,5,'history evidence, not full-career-complete flag, drives assessment');
result=status(rows,new Map(),day);
assert.equal(result.scheduleReady,true,'special membership must not depend on horse history');
assert.equal(result.assessedIds.size,0,'empty horse details do not fabricate a selected race');
result=status([{...rows[0],startTime:'bad'}],details,day);
assert.equal(result.scheduleReady,false,'invalid schedule cannot be morning frozen');
console.log('MORNING_INPUT_BRANCH_ISOLATION_OK');