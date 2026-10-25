#!/usr/bin/env node
'use strict';
/** Ensure iPhone's ability/pace/marks/bets originate from one validated source. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const root={};
for(const path of ['arvexq/ui/static/forecast/prediction.js',
                   'arvexq/ui/static/forecast/marks.js',
                   'arvexq/ui/static/forecast/tickets.js']){
  vm.runInNewContext(fs.readFileSync(path,'utf8'),root,{filename:path});
}
const now='2026-10-26T08:00:00+09:00';
function fixture(){
  const horses=Array.from({length:6},(_,i)=>({horseNumber:i+1,name:'テスト馬'+(i+1)}));
  return {id:'nar-2026-10-26-園田-05',date:'2026-10-26',
    circuit:'地方',track:'園田',raceNumber:5,startTime:'12:00',
    horses,predictionStatus:'ready',
    unifiedForecast:{
      version:'arvexq-unified-live-v1',raceId:'nar-2026-10-26-園田-05',
      raceDate:'2026-10-26',circuit:'地方',modelFamily:'flat',
      capturedAt:now,trainedThrough:'2026-10-25',
      modelVersion:'arvexq-learned-whole-career-scenarios-v2',
      modelHash:'a'.repeat(64),receiptSha256:'b'.repeat(64),
      researchOnly:true,probabilitiesCalibrated:false,
      roster:horses.map(h=>({horseNumber:h.horseNumber,name:h.name})),
      marks:[{horseNumber:1,markSymbol:'◎',winProbabilityRange:[0.2,0.4]},
        {horseNumber:2,markSymbol:'○'},{horseNumber:3,markSymbol:'▲'},
        {horseNumber:4,markSymbol:'△'},{horseNumber:5,markSymbol:'☆'}],
      pace:{text:'過去走の初角位置から先行候補を評価',likelyForwardNumbers:[1,2],
        testedScenarios:['usual','forward','held-up']},
      ticketPlan:{sameModelAndMarks:true,status:'見送り',
        reason:'発売時点の実オッズが未取得',items:[]}
    }
  };
}
{
 const r=fixture(),p=root.ARVEXQProductionPrediction.build(r);
 const marks=p.rows.filter(row=>root.ARVEXQProductionMarks.visible(row));
 assert.equal(marks.length,5);
 assert.equal(marks.filter(x=>x.predMark==='◎').length,1);
 assert.equal(root.ARVEXQProductionPrediction.current().source,'arvexq-unified-preoff');
 assert.equal(root.ARVEXQProductionPrediction.current().forecastText,r.unifiedForecast.pace.text);
 const tickets=root.ARVEXQProductionTickets.build(r,p);
 assert.equal(tickets.decision,'見送り');assert.equal(tickets.items.length,0);
 assert.equal(tickets.researchOnly,true);
 r.unifiedForecast.ticketPlan.items=[{kind:'3連複',combo:[1,2,3]}];
 const same=root.ARVEXQProductionTickets.build(r,p);
 assert.equal(same.items.length,1);
 assert.equal(same.items[0].kind,'3連複');
 assert.equal(same.referenceBudget.points,1);
}
for(const mutate of [
 r=>r.unifiedForecast.raceId='different-race',
 r=>r.unifiedForecast.circuit='中央',
 r=>r.unifiedForecast.capturedAt='2026-10-26T12:01:00+09:00',
 r=>r.unifiedForecast.trainedThrough='2026-10-26',
 r=>r.unifiedForecast.marks[0].markSymbol='!',
 r=>r.unifiedForecast.marks[1].markSymbol='◎',
 r=>r.unifiedForecast.roster[0].name='別の馬',
 r=>r.unifiedForecast.roster.push({horseNumber:7,name:'extra'})
]){
 const r=fixture();mutate(r);
 const p=root.ARVEXQProductionPrediction.build(r);
 assert.equal(p.rows.filter(row=>root.ARVEXQProductionMarks.visible(row)).length,0);
 const plan=root.ARVEXQProductionTickets.build(r,p);
 assert.equal(!!plan&&Array.isArray(plan.items)&&plan.items.length>0,false);
}
console.log('UNIFIED_JRA_NAR_SAME_SOURCE_UI_OK marks, pace, ticket reference and eight reject cases');
