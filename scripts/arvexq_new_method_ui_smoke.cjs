#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const ctx=vm.createContext({});
function load(p){vm.runInContext(fs.readFileSync(p,"utf8"),ctx,{filename:p});}
load("arvexq/ui/static/forecast/prediction.js");
load("arvexq/ui/static/forecast/prediction_frame.js");
load("arvexq/ui/static/forecast/ticket_frame.js");
const horses=[1,2,3,4,5].map(n=>({horseNumber:n,name:"Runner-"+n}));
const marks=["◎","○","▲","△","☆"].map((mark,i)=>({horseNumber:i+1,mark}));
const race={
  id:"nar-2099-01-01-園田-01",date:"2099-01-01",track:"園田",horses,
  predictionStatus:"ready",
  predictionMarks:marks,
  prediction:{
    predictionStatus:"ready",modelVersion:"arvexq-three-analysis-vnext-1",
    probabilities:{win:{1:.44,2:.26,3:.15,4:.1,5:.05},top3:{1:.77,2:.68,3:.62,4:.52,5:.41}},
    forecastText:"能力・展開から計算した発走前確率"
  },
  recommendedBets:[{kind:"3連単",combos:[[1,2,3]],points:1,reason:"確率と実オッズ"}]
};
const result=ctx.ARVEXQProductionPrediction.build(race);
assert.equal(result.rows[0].winProbability,.44);
assert.equal(result.rows[0].p3Probability,.77);
assert.equal(ctx.ARVEXQProductionPrediction.current().source,"three-analysis-preoff");
assert.equal(ctx.ARVEXQProductionPrediction.current().uncalibrated,false);
const pred=ctx.ARVEXQPredictionFrame.render();
assert.match(pred,/新方式/);
assert.doesNotMatch(pred,/Stage64|stage64/);
const bet=ctx.ARVEXQTicketFrame.contents(race,{});
assert.match(bet,/3連単/);
assert.match(bet,/1 - 2 - 3/);
assert.doesNotMatch(bet,/Stage64|stage64/);
const without={...race,predictionStatus:"disabled",recommendedBets:[]};
const empty=ctx.ARVEXQTicketFrame.contents(without,{});
assert.doesNotMatch(empty,/1 - 2 - 3/);
console.log("ARVEXQ_NEW_METHOD_UI_SMOKE_OK");
