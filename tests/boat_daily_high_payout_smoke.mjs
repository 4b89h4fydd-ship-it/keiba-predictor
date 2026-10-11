import assert from "node:assert/strict";
import {outcomeProbabilities} from "../arvexq/ui/static/sports/boat-app/core/prediction-model.js";
import {dailyRecommendations,eligibleHighPayout} from "../arvexq/ui/static/sports/boat-app/core/daily-selection.js";
import {selectedSection} from "../arvexq/ui/static/sports/boat-app/features/selected.js";
import {specialSection} from "../arvexq/ui/static/sports/boat-app/features/special.js";
const date="2026-10-12";
const entries=[1,2,3,4,5,6].map(boatNo=>({boatNo,name:"選手"+boatNo}));
const p=outcomeProbabilities(entries);
const code=p[0].combination;
const race={
  id:"boat-"+date+"-桐生-01",venue:"桐生",raceNo:1,
  closeAt:date+"T12:00:00+09:00",entries,
  forecast:{status:"verified",snapshotAt:date+"T11:00:00+09:00",calibration:{validated:true},
    probabilities:p.map(t=>({combination:t.combination,probability:t.p})),
    tickets:[{combination:code,stakeYen:100}],marks:{1:{symbol:"◎",role:"both",grade:"A"}}},
  odds3t:{verified:true,source:"BOATRACE公式",updatedAt:date+"T10:55:00+09:00",values:{[code]:500}},
  selection:{approved:true,lockedAt:date+"T10:00:00+09:00",snapshotAt:date+"T11:00:00+09:00"},
  special:{approved:true,lockedAt:date+"T10:00:00+09:00",snapshotAt:date+"T11:00:00+09:00"}
};
assert.equal(eligibleHighPayout(race),true);
let day=dailyRecommendations([race],date);
assert.equal(day.selected.length,1);
assert.equal(day.special.length,1);
assert.equal(day.metTarget,true);
assert.ok(selectedSection({date,races:[race]}).includes("桐生"));
assert.ok(specialSection({date,races:[race]}).includes("桐生"));
const bad={...race,forecast:{...race.forecast,calibration:{validated:false}}};
assert.equal(eligibleHighPayout(bad),false);
assert.equal(dailyRecommendations([bad],date).metTarget,false);
assert.equal(selectedSection({date,races:[]}).includes("1日1件以上"),true);
assert.equal(dailyRecommendations([{...race,odds3t:null}],date).metTarget,false);
assert.equal(dailyRecommendations([{...race,forecast:{...race.forecast,snapshotAt:date+"T12:01:00+09:00"}}],date).metTarget,false);
assert.equal(dailyRecommendations([race],"2026-10-13").metTarget,false);
console.log("BOAT_DAILY_HIGH_PAYOUT_POLICY_OK");
