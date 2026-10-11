// Smoke validated data contracts and pre-off performance accounting.
import assert from "node:assert/strict";
import {VENUES,validTicket,usableForecast,selectedRace,parseDay,displayMark} from "../arvexq/ui/static/sports/boat-app/core/contract.js";
import {summarize} from "../arvexq/ui/static/sports/boat-app/core/stats.js";
assert.equal(VENUES.length,24);
assert.equal(validTicket("1-2-3"),true);
assert.equal(validTicket("1-1-2"),false);
assert.equal(displayMark({symbol:"◎",role:"both",grade:"A"}),"◎【単】 ◎【軸】");
const day="2026-10-11",entries=[1,2,3,4,5,6].map(n=>({boatNo:n,name:"選手"+n}));
const race={id:"boat-"+day+"-桐生-01",venue:"桐生",raceNo:1,closeAt:"2026-10-11T12:00:00+09:00",entries,
  forecast:{status:"verified",snapshotAt:"2026-10-11T11:40:00+09:00",
    tickets:[{combination:"1-2-3",stakeYen:100},{combination:"1-3-2",stakeYen:100}],
    marks:{1:{symbol:"◎",role:"both",grade:"A"}}},
  result:{status:"confirmed",trifecta:"1-2-3",trifectaPayoutYen:850,confirmedAt:"2026-10-11T12:06:00+09:00"},
  selection:{approved:true,lockedAt:"2026-10-11T10:00:00+09:00",snapshotAt:"2026-10-11T11:40:00+09:00"}};
assert.equal(usableForecast(race),true);
assert.equal(selectedRace(race),true);
const one=summarize([race]);assert.equal(one.settled,1);assert.equal(one.hits,1);assert.equal(one.staked,200);assert.equal(one.returned,850);assert.equal(one.roi,425);
assert.equal(one.hitRate,1);
assert.equal(usableForecast({...race,forecast:{...race.forecast,tickets:[...race.forecast.tickets,...race.forecast.tickets,...race.forecast.tickets,...race.forecast.tickets]}}),false);
assert.equal(usableForecast({...race,forecast:{...race.forecast,snapshotAt:"2026-10-11T12:02:00+09:00"}}),false);
assert.equal(selectedRace({...race,selection:{...race.selection,lockedAt:"2026-10-11T12:05:00+09:00"}}),false);
const parsed=parseDay({version:"arvexq-boat-day-v1",date:day,verified:true,races:[race]},day);
assert.equal(parsed.races.length,1);
assert.throws(()=>parseDay({version:"arvexq-boat-day-v1",date:day,verified:false,races:[race]},day));
assert.equal(summarize([race,{...race,result:{status:"pending"}}]).settled,1);
console.log("BOAT_APP_SMOKE_OK");
