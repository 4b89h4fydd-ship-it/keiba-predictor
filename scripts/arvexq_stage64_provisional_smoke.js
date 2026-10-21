#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

let time=Date.parse('2026-10-20T09:00:00+09:00');
class TestDate extends Date {static now(){return time;}}
const root={ARVEXQProductionTickets:{validatedReceipt(){return null;},build(){return {decision:'未設定',items:[]};}}};
const ctx=vm.createContext({window:root,Date:TestDate,Number,String,Array,Set,Object,Math});
for(const file of ['prediction.js','marks.js','mark_frame.js','ticket_frame.js']){
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../arvexq/ui/static/forecast',file),'utf8'),ctx,{filename:file});
}
function race(circuit='地方'){
  const owner=circuit==='地方'?'nar':'jra',venue=owner==='nar'?'高知':'京都';
  return {id:owner+'-2099-01-01-'+venue+'-01',date:'2099-01-01',startTime:'12:00',
    circuit: circuit,horses:[1,2,3,4].map(n=>({horseNumber:n,name:'馬'+n})),
    researchShadow:{stage64:{raceId:owner+'-2099-01-01-'+venue+'-01',date:'2099-01-01',
      circuit:owner,stages:{
        marks:{value:{winRole:{horseNumber:1},axisRole:{horseNumber:2}}},
        pace:{value:[{1:0,2:0,3:0,4:0}]},
        runningStyle:{value:{1:[1,0,0,0]}},
        tickets:{value:{hypotheticalTrifectaTop10:[[1,2,3],[2,1,3]]}}
      }}}};
}
const nar=race();
let result=root.ARVEXQProductionPrediction.build(nar);
assert.equal(result.rows.find(x=>x.horse.horseNumber===1).honmeiRole,'win');
assert.equal(result.rows.find(x=>x.horse.horseNumber===2).honmeiRole,'axis');
assert.equal(root.ARVEXQProductionMarks.visible(result.rows[0]),'◎');
assert.equal(root.ARVEXQProductionMarks.visible(result.rows[1]),'◎');
assert.equal(root.ARVEXQProductionMarks.visible(result.rows[2]),'');
let content=root.ARVEXQTicketFrame.contents(nar,result);
assert.ok(content.includes('おすすめ候補')&&content.includes('1 - 2 - 3'));
assert.ok(!content.includes('発走前固定'));
assert.ok(root.ARVEXQTicketFrame.render(nar,result).includes('1 - 2 - 3'));
assert.equal(root.ARVEXQProductionPrediction.current().marks.length,2);
const displayedMarks=root.ARVEXQMarkFrame.render();
assert.ok(displayedMarks.includes('◎【単】')&&displayedMarks.includes('◎【軸】'));
const appSource=fs.readFileSync(path.join(__dirname,'../arvexq/ui/static/app.js'),'utf8');
assert.ok(appSource.includes(
  'content+window.ARVEXQPredictionFrame.render()+window.ARVEXQMarkFrame.render()+window.ARVEXQTicketFrame.render()'),
  'the approved race layout must remain unchanged');
assert.ok(root.ARVEXQTicketFrame.render().includes('1 - 2 - 3'),
  'argument-free race layout must show the current validated 3連単');


const central=race('中央');
result=root.ARVEXQProductionPrediction.build(central);
assert.equal(result.rows.filter(x=>x.stage64Provisional).length,2);
const tampered=race();
tampered.researchShadow.stage64.circuit='jra';
assert.equal(root.ARVEXQProductionPrediction.trial(tampered),null);
const incomplete=race();
incomplete.researchShadow.stage64.stages.tickets.value.hypotheticalTrifectaTop10=[[9,2,3]];
assert.equal(root.ARVEXQProductionPrediction.trial(incomplete),null);

time=Date.parse('2100-01-01T00:00:00+09:00');
assert.equal(root.ARVEXQProductionPrediction.trial(nar),null);
assert.equal(root.ARVEXQProductionPrediction.build(nar).rows.filter(x=>x.predMark).length,0);
assert.equal(root.ARVEXQProductionPrediction.current().marks.length,0);
assert.ok(!root.ARVEXQMarkFrame.render().includes('◎【単】'));
assert.ok(!root.ARVEXQTicketFrame.contents(nar,result).includes('1 - 2 - 3'));
assert.ok(!root.ARVEXQTicketFrame.render().includes('1 - 2 - 3'),
  'a prior trial must not leak into a postoff or empty race');

console.log('Stage64 preoff JRA/NAR UI role/ticket trial: PASS');
