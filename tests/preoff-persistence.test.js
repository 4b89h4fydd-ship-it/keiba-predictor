import test from 'node:test';
import assert from 'node:assert/strict';
import {stage64Archive, retainStage64Archive, applyStage64Archive} from '../preoff-persistence.js';
import {publicRace} from '../public-race.js';
import {readRaceDisplay} from '../racecard.js';

function race() {
 const d={id:'nar-2026-10-23-園田-11',date:'2026-10-23',
  horses:[1,2,3,4,5,6].map(horseNumber=>({horseNumber,name:String(horseNumber)})),
  predictionStatus:'ready', predictionModelVersion:'arvexq-stage64-product-v1'};
 d.prediction={raceId:d.id,date:d.date,modelVersion:'arvexq-stage64-product-v1',
   predictionStatus:'ready',productionEligible:true,stages:{probability:{value:{win:{1:0.3}}}}};
 d.predictionMarks=['◎','○','▲','△','☆'].map((mark,i)=>({horseNumber:i+1,mark}));
 d.recommendedBets=[{kind:'馬連',combos:[[1,2]]},{kind:'3連複',combos:[[1,2,3]]}];
 return d;
}
test('final result sync retains exact stored bets without any post-off computation',()=>{
 const preoff=race(), archived=stage64Archive(preoff);
 const final={id:preoff.id,date:preoff.date,horses:preoff.horses,
   result:{status:'確定',finishers:[{horseNumber:3,finish:1}]}};
 const stored={...preoff,preoffStage64Archive:archived};
 const next=retainStage64Archive(final,stored,null);
 assert.deepEqual(next.preoffStage64Archive,archived);
 const restored=applyStage64Archive(final,next);
 assert.deepEqual(restored.recommendedBets,preoff.recommendedBets);
 assert.deepEqual(restored.predictionMarks,preoff.predictionMarks);
 assert.deepEqual(restored.result,final.result);
 const published=publicRace({ok:true,detail:restored}).detail;
 assert.equal(published.predictionStatus,'ready');
 assert.deepEqual(published.recommendedBets,preoff.recommendedBets);
 assert.equal(published.preoffStage64Archive,undefined);
 assert.deepEqual(published.horses.slice(0,5).map(h=>h.predMark),['◎','○','▲','△','☆']);
});
test('wrong race, altered mark and missing archival originals cannot restore',()=>{
 const original=race(),archive=stage64Archive(original);
 const final={id:original.id,date:original.date,horses:original.horses,result:{status:'確定'}};
 for(const invalid of [
   {...archive,raceId:'different'},
   {...archive,predictionMarks:[...archive.predictionMarks.slice(0,4),{horseNumber:5,mark:'◎'}]},
   {...archive,prediction:{...archive.prediction,productionEligible:false}},
   null]){
   const stored=retainStage64Archive(final,{...original,preoffStage64Archive:invalid},null);
   const result=applyStage64Archive(final,{preoffStage64Archive:invalid});
   assert.equal(result.predictionStatus,undefined);
   assert.equal(stored.preoffStage64Archive,undefined);
 }
});
test('existing display route returns original bets from stored sidecar',async()=>{
 const original=race(),stored={id:original.id,date:original.date,horses:original.horses,
   result:{status:'確定'},preoffStage64Archive:stage64Archive(original)};
 const env={DB:{prepare(sql){return {bind(...args){return {async first(){
   if(sql.includes('FROM race_details')) return {payload:JSON.stringify(stored),analysis_ready:1,updated_at:1};
   return null;
 },async all(){return {results:[]}}}}}}}};
 const resp=await readRaceDisplay(env,original.id);
 assert.equal(resp.status,200);
 const body=await resp.json();
 assert.deepEqual(body.detail.recommendedBets,original.recommendedBets);
 assert.equal(body.detail.result.status,'確定');
});
