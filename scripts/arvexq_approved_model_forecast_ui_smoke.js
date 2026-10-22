#!/usr/bin/env node
'use strict';
// Synthetic fixture ONLY: proves the adapter can SHOW approved JRA/NAR
// model results when deployed, not that a trained artifact exists today.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={window:{},console,Date,Set,Map,Number,String,Array,Object,JSON,Math};
vm.createContext(ctx);
for(const path of [
  'arvexq/ui/static/morning/frozen_ticket_evidence.js',
  'arvexq/ui/static/forecast/tickets.js',
  'arvexq/ui/static/forecast/prediction.js',
  'arvexq/ui/static/forecast/prediction_frame.js',
  'arvexq/ui/static/forecast/mark_frame.js',
  'arvexq/ui/static/forecast/ticket_frame.js'
])vm.runInContext(fs.readFileSync(path,'utf8'),ctx,{filename:path,timeout:20000});
const root=ctx.window,source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=source.indexOf('function paceOutcomeModel('),
 end=source.indexOf('function paceOutcomeNums(',start);
assert(start>=0&&end>start);
const modalPace=new Function('n',source.slice(start,end)+'\nreturn paceOutcomeModel')(
 (x,d=0)=>Number(x)||d);
const orders=[
 [[1,2,3],.45],[[2,3,1],.25],[[3,1,4],.15],
 [[4,5,2],.10],[[5,4,3],.05]
];
const horses=Array.from({length:5},(_,i)=>({horseNumber:i+1,name:'Horse-'+(i+1)}));
const probs=horses.map(h=>{
 const no=h.horseNumber;return {horseNumber:no,
   mark:['◎','○','▲','△','△'][no-1],
   win:orders.reduce((a,z)=>a+(z[0][0]===no?z[1]:0),0),
   top2:orders.reduce((a,z)=>a+(z[0].slice(0,2).includes(no)?z[1]:0),0),
   top3:orders.reduce((a,z)=>a+(z[0].includes(no)?z[1]:0),0)};
});
const stageOrders=[
 ['start',[2,1,3,4,5]],['turn3',[2,1,3,5,4]],
 ['turn4',[1,2,3,5,4]],['straight',[1,2,3,4,5]]
];
function makeRace(circuit){
 const raceId=(circuit==='地方'?'nar':'jra')+'-2099-01-10-'+
    (circuit==='地方'?'園田':'東京')+'-03';
 const cap=Date.parse('2099-01-10T09:00:00+09:00')/1000,
       post=Date.parse('2099-01-10T15:00:00+09:00')/1000;
 return {id:raceId,date:'2099-01-10',circuit,
    scheduledStartTime:'15:00',startTime:'15:00',horses,
    approvedForecast:{
      version:'arvexq-approved-forecast-v1',
      publicationStatus:'approved-calibrated-preoff',
      modelId:'CI-only-calibrated-model',modelFamily:circuit==='地方'?'nar-flat':'jra-flat',
      raceId,raceDate:'2099-01-10',circuit,
      capturedAtEpoch:cap,postAtEpoch:post,fixedAt:new Date(cap*1000).toISOString(),
      snapshotHash:'c'.repeat(64),horseNumbers:[1,2,3,4,5],
      modelEvidence:{holdoutArtifactSha256:'a'.repeat(64),
                     calibrationArtifactSha256:'b'.repeat(64)},
      probabilities:probs,
      scenarios:orders.map(z=>({horses:z[0],probability:z[1]})),
      pace:{stages:stageOrders.map(z=>({key:z[0],
        pack:z[1].map(n=>({no:n,lane:0}))}))},
      tickets:[{kind:'3連単',level:'本線',combos:[[1,2,3]],
        quotedOdds:5,hitProbability:.45,expectedReturn:2.25,
        reason:'synthetic fixture for UI test'}]
    }};
}
for(const circuit of ['中央','地方']){
 const race=makeRace(circuit),before=JSON.stringify(race);
 const result=root.ARVEXQProductionPrediction.build(race);
 assert.equal(result.rows.length,5);
 assert.equal(result.rows[0].predMark,'◎');
 assert.equal(result.rows[0].winProbability,.45);
 assert.equal(result.scenarios.length,5);
 assert.equal(result.plan.stages.length,4);
 assert.equal(result.approvedForecast.modelFamily,circuit==='中央'?'jra-flat':'nar-flat');
 assert.equal(root.ARVEXQProductionPrediction.current().source,'approved-model');
 assert.match(root.ARVEXQPredictionFrame.render(),/学習・校正モデル/);
 assert.match(root.ARVEXQMarkFrame.render(),/◎/);
 assert.match(root.ARVEXQTicketFrame.render(race,result),/1 - 2 - 3/);
 const pace=modalPace(race,result);
 assert.match(pace.verdict,/学習モデル/);
 assert.equal(pace.winner.horse.horseNumber,1);
 assert.equal(JSON.stringify(race),before,'no mutation allowed');
 for(const change of [
   r=>{r.approvedForecast.modelEvidence.holdoutArtifactSha256='bad'},
   r=>{r.approvedForecast.probabilities[0].top3=.01},
   r=>{r.approvedForecast.fixedAt='2099-01-10T18:00:00+09:00'},
   r=>{r.approvedForecast.pace.stages[0].pack.pop()},
   r=>{r.approvedForecast.scenarios[0].probability=2},
   r=>{r.horses[0].horseNumber=99},
   r=>{r.approvedForecast.modelFamily=circuit==='中央'?'nar-flat':'jra-flat'}
 ]){
   const fake=makeRace(circuit);change(fake);
   assert.equal(root.ARVEXQProductionTickets.approvedForecast(fake),null,
     'tampered approval must fail closed');
   const gated=root.ARVEXQProductionPrediction.build(fake);
   assert.equal(gated.rows.some(x=>!!x.predMark),false);
   assert.match(root.ARVEXQTicketFrame.render(fake,gated),/買い目は未生成/);
 }
}
console.log('APPROVED_MODEL_FORECAST_PACE_MARKS_TICKETS_PASS (synthetic fixture only)');
