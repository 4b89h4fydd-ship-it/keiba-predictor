'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const root='arvexq/ui/static/forecast/',context={};vm.createContext(context);
for(const file of fs.readdirSync(root).filter(x=>x.endsWith('.js')))
  vm.runInContext(fs.readFileSync(root+file,'utf8'),context,{filename:file});
const race={
  id:'nar-2026-10-18-test',date:'2026-10-18',startTime:'12:00',
  horses:[{horseNumber:1,name:'<img onerror=alert(1)>',mark:'◎'},
          {horseNumber:2,name:'B',mark:'○'},{horseNumber:3,name:'C',mark:'▲'}],
  predictionStatus:'provisional',predictionModelVersion:'arvexq-observed-history-baseline-v1',
  predictionRunnerCount:3,
  predictionMarks:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'},{horseNumber:3,mark:'▲'}],
  postRaceReference:{raceId:'nar-2026-10-18-test',status:'reference',
    marks:[{horseNumber:1,mark:'◎'}]},
  preRaceBet:{items:[{amount:1000}]},forecastRevisions:[{mark:'◎'}]
};
const before=JSON.stringify(race);
for(const circuit of ['中央','地方']){
  const input=Object.assign({},race,{circuit});
  const prediction=context.ARVEXQProductionPrediction.build(input);
  assert.equal(prediction.rows.length,3);
  assert(prediction.rows.every(row=>row.predMark===''&&!row.originalPreoffMark));
  assert(prediction.rows.every(row=>row.winProbability===null));
  assert.equal(context.ARVEXQProductionTickets.build(input,prediction).items.length,0);
  assert.equal(context.ARVEXQProductionMarks.visible(prediction.rows[0]),'');
  const current=context.ARVEXQProductionPrediction.current();
  assert.equal(current.source,'');
  assert.equal(current.active,false);
  assert.equal(current.unavailable,true);
  assert(!context.ARVEXQMarkFrame.render().includes('◎'));
  assert(!context.ARVEXQPredictionFrame.render().includes('事後参考再計算'));
  assert(context.ARVEXQTicketFrame.render().includes('おすすめ買い目'));
}
assert.equal(JSON.stringify(race),before);
require('./arvexq_original_ticket_live_view_smoke.cjs');
console.log('REJECTED_ASSISTANT_PREDICTIONS_REMOVED_REAL_PREOFF_ORIGINALS_RETAINED');
