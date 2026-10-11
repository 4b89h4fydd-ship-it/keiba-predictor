import assert from "node:assert/strict";
import {detail} from "../arvexq/ui/static/sports/boat-app/features/races.js";
const date="2026-10-12";
const race={
  id:"boat-"+date+"-桐生-01",date,venue:"桐生",raceNo:1,title:"予選",
  closeAt:date+"T12:00:00+09:00",entries:[1,2,3,4,5,6].map(boatNo=>
  ({boatNo,name:"選手"+boatNo,class:"A1",motorNo:boatNo,
    player:{winRate:6.5,top3Rate:65,avgST:.14},motor:{top2Rate:45},exhibition:{time:6.8}})),
  forecast:{status:"verified",snapshotAt:date+"T11:40:00+09:00",
    tickets:[{combination:"1-2-3",stakeYen:100},{combination:"2-1-3",stakeYen:100}],
    marks:{1:{symbol:"◎",role:"both",grade:"A"},2:{symbol:"○",role:"none",grade:"B"}}},
  odds3t:{verified:true,source:"BOATRACE公式",updatedAt:date+"T11:40:00+09:00",
    values:{"1-2-3":4.5,"2-1-3":10.5}},
  result:{status:"confirmed",trifecta:"1-2-3",trifectaPayoutYen:450}
};
const html=detail(race);
assert.equal((html.match(/class="boat-entry"/g)||[]).length,6,"all six racers must be in the card");
for(let n=1;n<=6;n++)assert.ok(html.includes("選手"+n),"missing race entry "+n);
assert.ok(html.includes("全艇診断"));
assert.ok(html.includes("スタート展示"));
assert.ok(html.includes("4.5倍"));
assert.ok(html.includes("10.5倍"));
assert.ok(html.includes("◎【単】 ◎【軸】"));
assert.ok(html.includes("class=\"boat-mark-cell\""));
assert.ok(html.includes("3連単払戻 450円"));
const unknown=detail({...race,entries:[],forecast:null,result:null});
assert.ok(unknown.includes("6艇分の出走表は未取得"));
assert.ok(unknown.includes("検証済み予想はまだありません"));
assert.ok(unknown.includes("結果未確定・未取得"));
console.log("BOAT_SIX_RACER_ODDS_RESULT_DETAIL_OK");
