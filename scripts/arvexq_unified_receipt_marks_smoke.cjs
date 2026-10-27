'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={};
context.window=context;
vm.createContext(context);
vm.runInContext(fs.readFileSync('arvexq/ui/static/forecast/prediction.js','utf8'),context);
const race={
  id:'jra-2026-10-27-東京-01',date:'2026-10-27',circuit:'中央',startTime:'12:00',
  horses:[
    ...[1,2,3,4,5].map(i=>({horseNumber:i,name:'検証馬'+i})),
    {horseNumber:6,name:'取消馬',scratched:true}
  ],
};
race.unifiedForecast={
  version:'arvexq-unified-live-v1',raceId:race.id,raceDate:race.date,
  circuit:race.circuit,researchOnly:true,probabilitiesCalibrated:false,
  roster:race.horses.slice(0,5).map(h=>({horseNumber:h.horseNumber,name:h.name})),
  marks:['◎','○','▲','△','☆'].map((markSymbol,i)=>({horseNumber:i+1,markSymbol})),
  receiptSha256:'a'.repeat(64),modelHash:'b'.repeat(64),trainedThrough:'2026-10-26',
  capturedAt:'2026-10-26T09:00:00+09:00',modelVersion:'synthetic-valid-preoff-test',
  pace:{text:'検証用'}
};
const result=context.ARVEXQProductionPrediction.build(race);
assert.equal(context.ARVEXQProductionPrediction.current().active,true);
assert.equal(result.rows.find(x=>x.horse.horseNumber===1).predMark,'◎');
assert.equal(result.rows.find(x=>x.horse.horseNumber===6).predMark,'');
assert.deepEqual(context.ARVEXQProductionPrediction.current().marks.map(x=>x.mark),['◎','○','▲','△','☆']);
console.log('UNIFIED_MARKS_RETAINED_WITH_SCRATCHED_HORSE_OK');
