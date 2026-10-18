'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const root='arvexq/ui/static/forecast/';const context={};vm.createContext(context);
for(const file of fs.readdirSync(root).filter(x=>x.endsWith('.js')))vm.runInContext(fs.readFileSync(root+file,'utf8'),context);
const race={horses:[{horseNumber:1,name:'馬',mark:'◎',integratedEvaluation:{mark:'◎'}},{horseNumber:2,name:'馬二'}],preRaceBet:{items:[{amount:1000}]},currentForecastRevisionId:'old'};
const before=JSON.stringify(race),prediction=context.ARVEXQProductionPrediction.build(race);
assert.equal(prediction.rows.length,2);assert.equal(prediction.rows[0].predMark,'');assert.equal(prediction.rows[0].winProbability,null);
assert.equal(context.ARVEXQProductionMarks.visible(race.horses[0]),'');
assert.equal(context.ARVEXQProductionTickets.build(race,prediction).items.length,0);
for(const [key,id] of [['ARVEXQPredictionFrame','section-prediction'],['ARVEXQMarkFrame','section-aimarks'],['ARVEXQTicketFrame','section-bets']]){
 const html=context[key].render(race,prediction);assert(html.includes(id));assert(!html.includes('◎'));assert(!html.includes('1000'));
}
assert.equal(JSON.stringify(race),before);
for(const circuit of ['中央','地方'])assert.equal(context.ARVEXQProductionPrediction.build({...race,circuit}).rows.length,2);
// Only a server-published, race-matched, pre-off provisional set may be shown.
// No JS-generated rank, archived mark or unverified odds may become a ticket.
const approved={
  id:'jra-future-check',date:'2099-12-31',startTime:'23:50',
  predictionStatus:'provisional',predictionModelVersion:'arvexq-observed-history-baseline-v1',
  predictionRunnerCount:3,
  predictionMarks:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'},{horseNumber:3,mark:'▲'}],
  horses:[{horseNumber:1,name:'<img src=x onerror=alert(1)>',mark:'☆'},
          {horseNumber:2,name:'B'},{horseNumber:3,name:'C'}]
};
const original=JSON.stringify(approved);
const live=context.ARVEXQProductionPrediction.build(approved);
assert.deepEqual(Array.from(live.rows,x=>x.predMark),['◎','○','▲']);
assert.equal(context.ARVEXQProductionMarks.visible(live.rows[0]),'◎');
assert.equal(live.rows[0].winProbability,null,'client must not invent calibrated probabilities');
assert.deepEqual(Array.from(context.ARVEXQProductionTickets.build(approved,live).items),[]);
const visible=context.ARVEXQMarkFrame.render();
assert(visible.includes('◎')&&visible.includes('○')&&visible.includes('▲'));
assert(!visible.includes('<img'),'unsafe horse name must be escaped');
assert(context.ARVEXQPredictionFrame.render().includes('暫定予想'));
assert(context.ARVEXQTicketFrame.render().includes('おすすめ買い目'));
assert.equal(JSON.stringify(approved),original,'read-only browser adapter changed source facts');
for(const bad of [
  {...approved,predictionStatus:'disabled'},
  {...approved,predictionModelVersion:'unverified'},
  {...approved,predictionRunnerCount:4},
  {...approved,predictionMarks:[{horseNumber:2,mark:'◎'},{horseNumber:2,mark:'○'},{horseNumber:3,mark:'▲'}]},
  {...approved,date:'2020-10-18'},
]){
  const output=context.ARVEXQProductionPrediction.build(bad);
  assert(Array.from(output.rows).every(x=>!x.predMark));
  assert(!context.ARVEXQMarkFrame.render().includes('◎'));
}

// A retrospective display is not a pre-off prediction, a betting ticket, or a hit.
const late={
  id:'nar-2026-10-18-test-11',date:'2026-10-18',startTime:'19:50',
  horses:[{horseNumber:1,name:'A'},{horseNumber:2,name:'B'},{horseNumber:3,name:'C'}],
  result:{status:'確定',finishers:[{horseNumber:3,finish:1}]},
  postRaceReference:{
    raceId:'nar-2026-10-18-test-11',status:'reference',
    retrospective:true,modelVersion:'arvexq-observed-history-baseline-v1',
    runnerNumbers:[1,2,3],
    marks:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'},{horseNumber:3,mark:'▲'}]
  }
};
const untouched=JSON.stringify(late);
const retro=context.ARVEXQProductionPrediction.build(late);
assert.equal(context.ARVEXQProductionPrediction.current().source,'postrace-reference');
assert.deepEqual(Array.from(retro.rows,x=>x.predMark),['◎','○','▲']);
assert.equal(retro.rows[0].serverPreoffMark,false);
assert.equal(retro.rows[0].originalPreoffMark,false);
assert.equal(retro.rows[0].referencePostoffMark,true);
assert.equal(context.ARVEXQProductionMarks.visible(retro.rows[0]),'◎');
assert(context.ARVEXQMarkFrame.render().includes('事後参考再計算'));
assert(context.ARVEXQPredictionFrame.render().includes('発走前保存予想ではありません'));
assert.equal(context.ARVEXQProductionTickets.build(late,retro).items.length,0);
assert.equal(JSON.stringify(late),untouched);
for(const invalid of [
  {...late,id:'nar-2026-10-18-wrong'},
  {...late,date:'2026-10-17'},
  {...late,postRaceReference:{...late.postRaceReference,modelVersion:'wrong'}},
  {...late,postRaceReference:{...late.postRaceReference,runnerNumbers:[1,2,4]}},
  {...late,postRaceReference:{...late.postRaceReference,marks:[{horseNumber:3,mark:'◎'}]}}
]){
  const result=context.ARVEXQProductionPrediction.build(invalid);
  assert(result.rows.every(x=>!x.predMark));
}

// Replacement policy: 10/18 only ONE prediction display is allowed.
// Previously cached provisional marks must never override the new reference.
const superseded={...late,
  predictionStatus:'provisional',
  predictionModelVersion:'arvexq-observed-history-baseline-v1',
  predictionRunnerCount:3,
  predictionMarks:[{horseNumber:1,mark:'▲'},{horseNumber:2,mark:'○'},{horseNumber:3,mark:'◎'}]
};
const replacement=context.ARVEXQProductionPrediction.build(superseded);
assert.equal(context.ARVEXQProductionPrediction.current().source,'postrace-reference');
assert.deepEqual(Array.from(replacement.rows,x=>x.predMark),['◎','○','▲']);
const unavailable=context.ARVEXQProductionPrediction.build({
  ...superseded,postRaceReference:null
});
assert(unavailable.rows.every(x=>!x.predMark),'old marks leaked back into 10/18');
assert.equal(context.ARVEXQProductionPrediction.current().unavailable,true);
assert(context.ARVEXQMarkFrame.render().includes('データ不足'));
assert(context.ARVEXQPredictionFrame.render().includes('以前の予想を代わりに表示しません'));

require('./arvexq_original_ticket_live_view_smoke.cjs');
console.log('production prediction, mark, ticket and three frame contracts OK');
