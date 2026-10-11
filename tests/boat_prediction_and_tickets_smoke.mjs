import assert from "node:assert/strict";
import {orderedTrifectas,outcomeProbabilities,marginalProbabilities,predictionMarks,MODEL_VERSION} from "../arvexq/ui/static/sports/boat-app/core/prediction-model.js";
import {expandFormation,oddsQuote,chooseTickets,summarizeFormation,experimentalForecast,inputQuality} from "../arvexq/ui/static/sports/boat-app/core/ticket-engine.js";
import {ticketPanel} from "../arvexq/ui/static/sports/boat-app/features/tickets.js";
import {statsSection} from "../arvexq/ui/static/sports/boat-app/features/ai-stats.js";
const entries=[1,2,3,4,5,6].map(boatNo=>({
  boatNo,name:"選手"+boatNo,player:{winRate:6.5,top3Rate:65,avgST:.14},
  motor:{top2Rate:43},exhibition:{time:6.8},expectedCourse:boatNo
}));
const p=outcomeProbabilities(entries);
assert.equal(p.length,120);assert.equal(new Set(p.map(x=>x.combination)).size,120);
assert.ok(Math.abs(p.reduce((s,x)=>s+x.p,0)-1)<1e-10);
const m=marginalProbabilities(p);
assert.ok(Math.abs(m.reduce((s,x)=>s+x.win,0)-1)<1e-10);
assert.ok(Math.abs(m.reduce((s,x)=>s+x.top3,0)-3)<1e-10);
assert.deepEqual(expandFormation("1-23-234"),["1-2-3","1-2-4","1-3-2","1-3-4"]);
assert.equal(summarizeFormation(expandFormation("1-23-234")),"1-23-234");
assert.equal(summarizeFormation(["1-2-3","2-1-3"]),null);
assert.throws(()=>expandFormation("1-1-1"));
const date="2026-10-12";
const race={
  id:"boat-"+date+"-桐生-01",date,venue:"桐生",raceNo:1,
  closeAt:date+"T12:00:00+09:00",entries,
  odds3t:{verified:true,source:"BOATRACE公式",updatedAt:date+"T11:40:00+09:00",
    values:{"1-2-3":4.5,"1-2-4":15.0,"1-3-2":10.5,"1-3-4":32.0}},
  forecast:{status:"verified",snapshotAt:date+"T11:42:00+09:00",marks:predictionMarks(p),
    tickets:expandFormation("1-23-234").map(combination=>({combination,stakeYen:100}))},
  result:{status:"pending"}
};
const text=ticketPanel(race);
assert.ok(text.includes("1-23-234"));
assert.ok(text.includes("4.5倍"));
assert.ok(text.includes("10.5倍"));
assert.ok(text.includes("想定払戻"));
assert.equal(oddsQuote(race,"1-2-3"),4.5);
assert.equal(oddsQuote({...race,odds3t:{...race.odds3t,verified:false}},"1-2-3"),null);
assert.ok(ticketPanel({...race,odds3t:null}).includes("オッズは未取得"));
assert.equal(chooseTickets(p,race,{limit:6}).length,6);
assert.ok(chooseTickets(p,race,{limit:6,mode:"high-payout"}).length<=4);
assert.throws(()=>chooseTickets(p,race,{limit:7}));
assert.equal(experimentalForecast(entries,race,p).status,"experimental");
assert.ok(!Object.values(predictionMarks(p,{calibrated:false})).some(v=>v.grade==="A"));
assert.equal(inputQuality(race).ready,true);
assert.equal(inputQuality({...race,entries:[]}).ready,false);
assert.ok(statsSection([race]).includes("AI成績")===false);
assert.ok(statsSection({races:[race]}).includes("3連単的中"));
console.log("BOAT_PREDICTION_AND_TICKETS_OK",MODEL_VERSION);
