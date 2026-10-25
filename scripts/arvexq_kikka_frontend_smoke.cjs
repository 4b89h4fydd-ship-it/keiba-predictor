#!/usr/bin/env node
'use strict';
// Validate the actual iPhone PWA prediction module without executing app.js.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('arvexq/ui/static/forecast/prediction.js','utf8');
const context={
  ARVEXQProductionTickets:{build(){throw Error('cannot calculate betting advice for Kikuka');
  },validatedReceipt(){throw Error('cannot use retired sealed forecast for Kikuka')}}
};
vm.runInNewContext(source,context,{filename:'arvexq/ui/static/forecast/prediction.js'});
vm.runInNewContext(fs.readFileSync('arvexq/ui/static/forecast/marks.js','utf8'),context);
const names=['エムズビギン','コンジェスタス','アウダーシア','ショウナンガルフ',
  'ジャスティンシカゴ','バステール','ラージアンサンブル','ロブチェン',
  'ゴーイントゥスカイ','ダノンヒストリー','アスクエジンバラ',
  'サノノグレーター','キンググローリー','マジョレルブルー',
  'シートゥサミット','ショウナンハヤナミ','チャリングクロス',
  'ナリタエスペランサ'];
const base=()=>({
  id:'jra-2026-10-25-京都-11',date:'2026-10-25',track:'京都',
  raceNumber:11,distance:3000,surface:'芝',startTime:'15:40',
  scheduledStartTime:'15:40',predictionStatus:'ready',
  // Must ignore any pre-existing retired production forecast.
  prediction:{modelVersion:'retired-prediction-model',predictionStatus:'ready'},
  horses:names.map((name,i)=>({horseNumber:i+1,name})),
});
const candidate=()=>({
  version:'arvexq-kikka-urgent-learned-candidate-v1',
  raceId:'jra-2026-10-25-京都-11',raceDate:'2026-10-25',
  modelVersion:'arvexq-learned-whole-career-scenarios-v2',
  trainedThrough:'2026-10-24',capturedAt:'2026-10-25T14:20:00+09:00',
  provisional:true,productionEligible:false,bettingRecommended:false,
  probabilityCalibration:'unverified',modelHash:'a'.repeat(64),sourceHash:'b'.repeat(64),
  marks:[
    {horseNumber:8,markSymbol:'◎'},{horseNumber:10,markSymbol:'○'},
    {horseNumber:9,markSymbol:'▲'},{horseNumber:6,markSymbol:'△'},
    {horseNumber:5,markSymbol:'☆'}
  ],
});
{
  const race=base(); race.kikkaCandidate=candidate();
  const p=context.ARVEXQProductionPrediction.build(race);
  assert.equal(p.rows.length,18);
  assert.equal(p.rows.find(x=>x.horse.horseNumber===8).predMark,'◎');
  assert.equal(p.rows.find(x=>x.horse.horseNumber===8).revisionCandidateMark,true);
  assert.equal(context.ARVEXQProductionMarks.visible(p.rows.find(x=>x.horse.horseNumber===8)),'◎');
  assert.equal(p.plan,null);assert.deepEqual(Object.keys(p.plans),[]);
  assert.equal(p.rows.every(x=>x.winProbability===null),true);
  assert.equal(context.ARVEXQProductionPrediction.current().uncalibrated,true);
  assert.equal(context.ARVEXQProductionPrediction.current().source,'kikka-2026-learned-preoff-candidate');
}
for(const update of [
  r=>delete r.kikkaCandidate,
  r=>r.kikkaCandidate.capturedAt='2026-10-25T15:41:00+09:00',
  r=>r.kikkaCandidate.trainedThrough='2026-10-25',
  r=>r.kikkaCandidate.bettingRecommended=true,
  r=>r.kikkaCandidate.marks.push({horseNumber:7,mark:'◎'}),
  r=>r.horses[8].name='違う馬',
  r=>r.kikkaCandidate.raceId='jra-2026-10-25-東京-11',
]) {
  const race=base();race.kikkaCandidate=candidate();update(race);
  const p=context.ARVEXQProductionPrediction.build(race);
  assert.equal(p.rows.some(x=>!!x.predMark),false,'tampered candidate must not show marks');
  assert.equal(context.ARVEXQProductionPrediction.current().active,false);
}
console.log('KIKKA_PWA_PROVISIONAL_MARKS_OK no retired forecast/no tickets, 8 negative cases');
