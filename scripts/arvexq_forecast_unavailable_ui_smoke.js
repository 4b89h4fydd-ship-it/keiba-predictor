#!/usr/bin/env node
'use strict';
// Tests the real production JS adapters; neither invents marks nor restarts
// withdrawn forecast engines. Live user receipts are not generated here.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={window:{},console,Date,Set,Map,Number,String,Array,Object,JSON,Math};
vm.createContext(context);
for(const file of [
  'arvexq/ui/static/morning/frozen_ticket_evidence.js',
  'arvexq/ui/static/forecast/tickets.js',
  'arvexq/ui/static/forecast/prediction.js',
  'arvexq/ui/static/forecast/mark_frame.js',
  'arvexq/ui/static/forecast/ticket_frame.js',
  'arvexq/ui/static/forecast/prediction_frame.js'
]){
  vm.runInContext(fs.readFileSync(file,'utf8'),context,{filename:file,timeout:5000});
}
const root=context.window;
const source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function extract(start,end){
  const a=source.indexOf('function '+start+'(');
  const b=source.indexOf('function '+end+'(',a+1);
  assert(a>=0&&b>a,start+' extraction boundary missing');
  return source.slice(a,b);
}
const pace=new Function('r','p',extract('_arvexq_original_paceBoard','paceBoard')+
  ';return _arvexq_original_paceBoard(r,p)');
const outcome=new Function('r','p',extract('paceOutcomeModel','paceOutcomeSection')+
  ';return paceOutcomeModel(r,p)');
const menu=new Function('r','p',extract('paceStageMenu','openPaceStagePage')+
  ';return paceStageMenu(r,p)');
const horses=Array.from({length:5},(_,i)=>({horseNumber:i+1,name:'Horse-'+(i+1)}));
const race={id:'nar-2099-01-10-園田-03',date:'2099-01-10',
  scheduledStartTime:'15:00',circuit:'地方',predictionStatus:'disabled',
  track:'園田',horses};
const original=JSON.stringify(race);
const predicted=root.ARVEXQProductionPrediction.build(race);
assert.equal(predicted.rows.length,5);
assert.equal(predicted.rows.some(row=>row.predMark),false,'must not fabricate marks');
assert.equal(predicted.rows[0].winProbability,null);
assert.equal(root.ARVEXQProductionPrediction.current().status,'model-disabled');
assert.match(root.ARVEXQPredictionFrame.render(),/予想未生成/);
assert.match(root.ARVEXQMarkFrame.render(),/予想印は未生成/);
assert.match(root.ARVEXQTicketFrame.render(race,predicted),/買い目は未生成/);
assert.equal(root.ARVEXQProductionTickets.current(),null);
const fake={rows:predicted.rows,scenarios:[],plan:null,plans:{}};
assert.match(pace(race,fake),/展開予想は未生成/);
assert.doesNotMatch(pace(race,fake),/data-pace-open=/);
assert.equal(outcome(race,fake),null,'racecard order cannot stand in for a pace prediction');
assert.equal(menu(race,fake),'','no nonfunctional 4-stage menu');
assert.equal(JSON.stringify(race),original,'rendering must not change the record');
// A valid stored pre-off receipt remains displayable *without* generating new tips.
const receipt={version:'arvexq-morning-ticket-evidence-v1',raceId:race.id,
  raceDate:race.date,fixedAt:'2099-01-10T10:00:00+09:00',
  axisStatus:'honmei',axisHorseNumber:1,
  marks:horses.map((horse,i)=>({horseNumber:horse.horseNumber,mark:['◎','○','▲','',''][i]})),
  items:[{kind:'馬連',level:'本線',combos:[[1,2]],reason:'archived independent preoff'}],
  ticketKinds:['馬連'],modelVersion:'saved-user-preoff-original'};
const saved={...race,morningTicketEvidence:receipt};
assert.equal(root.ARVEXQMorningEvidence.verify(saved,receipt),true);
const restored=root.ARVEXQProductionPrediction.build(saved);
assert.equal(restored.rows[0].predMark,'◎');
assert.equal(root.ARVEXQProductionPrediction.current().source,'saved-preoff');
assert.match(root.ARVEXQMarkFrame.render(),/◎/);
assert.match(root.ARVEXQTicketFrame.render(saved,restored),/1 - 2/);
assert.match(root.ARVEXQPredictionFrame.render(),/保存の原本/);
assert.match(pace(saved,restored),/展開予想は未生成/,'saved tickets are not pace scenarios');
// Post-time or a mismatched roster must never be promoted into new marks or bets.
const late={...receipt,fixedAt:'2099-01-10T17:00:00+09:00'};
const invalid={...race,morningTicketEvidence:late};
const rejected=root.ARVEXQProductionPrediction.build(invalid);
assert.equal(rejected.rows.some(x=>x.predMark),false);
assert.match(root.ARVEXQTicketFrame.render(invalid,rejected),/買い目は未生成/);
const wrongField={...saved,horses:horses.slice(1)};
const wrong=root.ARVEXQProductionPrediction.build(wrongField);
assert.equal(wrong.rows.some(x=>x.predMark),false);
console.log('FORECAST_UNAVAILABLE_PACE_MARKS_TICKETS_PASS');
