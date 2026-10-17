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
console.log('production prediction, mark, ticket and three frame contracts OK');
