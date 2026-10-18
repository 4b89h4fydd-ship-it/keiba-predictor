'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
assert(!src.includes('function latestSavedForecastRevision('),'retired model revision validator must be deleted');
assert(!src.includes('/api/forecast-revisions/'),'retired forecast revision API must not be queried');
assert(src.includes('function verifiedOriginalMarks('),'only verified pre-off originals can be displayed');
const context={};context.window=context;vm.createContext(context);
for(const file of ['prediction','marks','tickets']){
  const path='arvexq/ui/static/forecast/'+file+'.js';
  vm.runInContext(fs.readFileSync(path,'utf8'),context,{filename:path});
}
const race=JSON.parse(fs.readFileSync('tests/fixtures/forecast_revision_transport.json','utf8')).detail;
const before=JSON.stringify(race);
const p=context.ARVEXQProductionPrediction.build(race);
const bet=context.ARVEXQProductionTickets.build(race,p);
assert(!p.savedForecastRevision);
assert(p.rows.every(x=>x.predMark===''),'retired revisions must never produce marks');
assert.equal(bet.items.length,0,'retired revisions must never produce bet picks');
assert.equal(JSON.stringify(race),before,'historical audit payload must never be mutated');
console.log('RETIRED_FORECAST_REVISION_REMOVED_ORIGINAL_PRESERVED');
