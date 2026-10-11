import assert from "node:assert/strict";
import {allBoatRaces} from "../arvexq/ui/static/sports/boat-app/features/all-races.js";
const date="2026-10-12",now=new Date("2026-10-12T09:45:00+09:00");
const day={date,verifiedAt:"2026-10-12T09:00:00+09:00",races:[
 {id:"boat-"+date+"-桐生-01",venue:"桐生",raceNo:1,closeAt:"2026-10-12T09:50:00+09:00",closeTime:"09:50"},
 {id:"boat-"+date+"-桐生-02",venue:"桐生",raceNo:2,closeAt:"2026-10-12T10:20:00+09:00",closeTime:"10:20"},
 {id:"boat-"+date+"-大村-03",venue:"大村",raceNo:3,closeAt:"2026-10-12T10:50:00+09:00",closeTime:"10:50"},
 {id:"boat-"+date+"-大村-04",venue:"大村",raceNo:4,closeTime:"11:05",result:{status:"中止"}}
]};
const html=allBoatRaces(day,{now});
assert.ok(html.includes("各会場の全レース"));
assert.ok(!html.includes("開催場一覧"));
assert.ok(!html.includes("リアルタイム"));
assert.ok(html.includes('data-venue="桐生"'));
assert.ok(html.includes('data-venue="大村"'));
assert.ok(html.includes('data-race="boat-'+date+'-桐生-01"'));
assert.ok(!html.includes('data-race="boat-'+date+'-大村-04"'));
assert.equal((html.match(/class="arv-all-race/g)||[]).length,24);
assert.equal((html.match(/aria-disabled="true"/g)||[]).length,21);
const empty=allBoatRaces({date,races:[]},{now});
assert.ok(empty.includes("未取得"));
assert.ok(!empty.includes('data-race="'));
assert.ok(!empty.includes('data-venue="'));
console.log("BOAT_ALL_RACES_OK");
