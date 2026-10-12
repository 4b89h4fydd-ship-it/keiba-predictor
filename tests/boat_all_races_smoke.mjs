import assert from "node:assert/strict";
import {allBoatRaces} from "../arvexq/ui/static/sports/boat-app/features/all-races.js";
import {raceList} from "../arvexq/ui/static/sports/boat-app/features/races.js";
const date="2026-10-12",now=new Date("2026-10-12T09:45:00+09:00");
const day={date,verifiedAt:"2026-10-12T09:00:00+09:00",races:[
 {id:"boat-"+date+"-桐生-01",venue:"桐生",raceNo:1,closeAt:"2026-10-12T09:50:00+09:00",closeTime:"09:50"},
 {id:"boat-"+date+"-桐生-02",venue:"桐生",raceNo:2,closeAt:"2026-10-12T10:20:00+09:00",closeTime:"10:20"},
 {id:"boat-"+date+"-大村-03",venue:"大村",raceNo:3,closeAt:"2026-10-12T10:50:00+09:00",closeTime:"10:50"},
 {id:"boat-"+date+"-大村-04",venue:"大村",raceNo:4,closeTime:"11:05",result:{status:"中止"}}
]};
const html=allBoatRaces(day,{now});
assert.ok(!html.includes('arv-all-venue-thumb'));
assert.ok(!html.includes('aria-hidden="true">≋'));

assert.ok(html.includes("各会場の全レース"));
assert.ok(!html.includes("arv-all-venue-thumb"),"no unused boat thumbnail column");
assert.ok(!html.includes("開催場一覧"));
assert.ok(!html.includes("リアルタイム"));
assert.ok(html.includes('data-venue="桐生"'));
assert.ok(html.includes('data-venue="大村"'));
assert.ok(html.includes('data-race="boat-'+date+'-桐生-01"'));
assert.ok(!html.includes('data-race="boat-'+date+'-大村-04"'));
assert.equal((html.match(/class="arv-all-race /g)||[]).length,24);
assert.equal((html.match(/aria-disabled="true"/g)||[]).length,21);
const empty=allBoatRaces({date,races:[]},{now});
assert.ok(empty.includes("未取得"));
assert.ok(!empty.includes('data-race="'));
assert.ok(!empty.includes('data-venue="'));
// The BOAT venue page now uses the exact 1R-12R horse-style grid,
// not the retired three-column row layout.
const venueRaceHtml=raceList({races:[{
  id:"boat-"+date+"-桐生-01",venue:"桐生",raceNo:1,
  title:"予選",closeTime:"10:30"
}]}, "桐生");
assert.ok(venueRaceHtml.includes('class="arv-all-races-grid boat-venue-race-grid"'));
assert.ok(venueRaceHtml.includes('data-race="boat-'+date+'-桐生-01"'));
assert.equal((venueRaceHtml.match(/<button/g)||[]).length,12);
assert.equal((venueRaceHtml.match(/disabled/g)||[]).length,11);
assert.ok(venueRaceHtml.includes('<strong>1R</strong><small>10:30</small>'));
assert.ok(!venueRaceHtml.includes('</small><em'));
console.log("BOAT_ALL_RACES_OK");
