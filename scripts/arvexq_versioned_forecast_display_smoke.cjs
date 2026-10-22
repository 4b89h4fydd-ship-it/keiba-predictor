const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const root={ARVEXQProductionTickets:{validatedReceipt(){return null},build(){return {decision:'未設定',items:[]}}}};
const ctx={window:root,globalThis:root};
vm.createContext(ctx);
for(const p of ['prediction.js','marks.js','prediction_frame.js','mark_frame.js']){
  vm.runInContext(fs.readFileSync('arvexq/ui/static/forecast/'+p,'utf8'),ctx,{filename:p});
}
const horses=Array.from({length:6},(_,i)=>({horseNumber:i+1,name:'馬'+(i+1)}));
const revision={version:'arvexq-forecast-revision-v1',raceId:'nar-2026-10-22-園田-01',
  raceDate:'2026-10-22',predictionStatus:'candidate-analysis',analysisType:'preoff-candidate',
  modelVersion:'existing-learned-model',probabilityModelStatus:'uncalibrated',
  scenarioSummaries:[{id:'usual',label:'通常'}],
  horses:horses.map((h,i)=>({horseNumber:h.horseNumber,mark:i===0?'◎':i===1?'○':i===2?'▲':''}))};
const race={id:revision.raceId,date:revision.raceDate,horses,_forecastRevisionView:revision};
let predicted=root.ARVEXQProductionPrediction.build(race);
assert.equal(predicted.rows[0].predMark,'◎');
assert.equal(root.ARVEXQProductionMarks.visible(predicted.rows[0]),'◎');
assert.equal(root.ARVEXQProductionPrediction.current().source,'learned-revision-preoff-candidate');
assert.match(root.ARVEXQMarkFrame.render(),/◎ 1 馬1/);
assert.match(root.ARVEXQPredictionFrame.render(),/仮予想/);
assert.ok(!root.ARVEXQProductionPrediction.current().active===false);
const historical={...race,_forecastRevisionView:{...revision,analysisType:'retrospective'}};
predicted=root.ARVEXQProductionPrediction.build(historical);
assert.equal(root.ARVEXQProductionPrediction.current().source,'learned-revision-retrospective');
assert.match(root.ARVEXQMarkFrame.render(),/事後再分析/);
assert.match(root.ARVEXQPredictionFrame.render(),/事後再分析/);
const invalid={...race,_forecastRevisionView:{...revision,horses:revision.horses.slice(1)}};
predicted=root.ARVEXQProductionPrediction.build(invalid);
assert.equal(root.ARVEXQProductionPrediction.current().active,false);
assert.equal(root.ARVEXQProductionMarks.visible(predicted.rows[0]),'');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert.match(app,/function fetchExistingForecastRevision\(/);
assert.match(app,/fetchExistingForecastRevision\(String\(id\),seq\)/);
assert.match(app,/x\.revisionId===body\.currentForecastRevisionId/);
console.log('VERIFIED_EXISTING_FORECAST_DISPLAY_OK');
