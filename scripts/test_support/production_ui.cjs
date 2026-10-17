'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const window={};
const context={window};vm.createContext(context);
for(const name of fs.readdirSync('arvexq/ui/static/forecast').filter(n=>n.endsWith('.js')))
 vm.runInContext(fs.readFileSync('arvexq/ui/static/forecast/'+name,'utf8'),context);
function assertNoForecast(race){
 const before=JSON.stringify(race),prediction=window.ARVEXQProductionPrediction.build(race);
 assert.equal(prediction.rows.length,(race.horses||[]).filter(h=>h&&Number(h.horseNumber)>0).length);
 for(const row of prediction.rows){
  assert.equal(row.predMark,'');assert.equal(row.winProbability,null);
  assert.equal(window.ARVEXQProductionMarks.visible(row),'');
 }
 assert.equal(prediction.scenarios.length,0);
 assert.equal(window.ARVEXQProductionTickets.build(race,prediction).items.length,0);
 assert.equal(JSON.stringify(race),before,'stored race facts and audit originals remain immutable');
 return prediction;
}
module.exports={window,assertNoForecast};
