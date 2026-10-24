const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const root={};
vm.runInNewContext(fs.readFileSync("arvexq/ui/static/sports/horse-portal.js","utf8"),{window:root});
const ui=root.ARVEXQHorsePortal,date="2026-10-12";
const rows=[
 {id:"jra-"+date+"-東京-01",circuit:"中央",track:"東京",raceNumber:1,startTime:"09:50",title:"東京1R",date},
 {id:"jra-"+date+"-東京-02",circuit:"中央",track:"東京",raceNumber:2,startTime:"10:20",date},
 {id:"nar-"+date+"-大井-03",circuit:"地方",track:"大井",raceNumber:3,startTime:"10:10",date},
 {id:"nar-"+date+"-大井-04",circuit:"地方",track:"大井",raceNumber:4,startTime:"10:40",date,result:{status:"中止"}}
];
const opts={date,today:date,nowMinutes:600,selected:{central:2,local:1},special:{central:1,local:0}};
const rendered=ui.home(rows,opts);
assert.ok(!rendered.includes('arv-all-venue-thumb'));
assert.ok(!rendered.includes('♞'));

assert.equal(rendered.includes("各会場の全レース"),true);
assert.ok(!rendered.includes("arv-all-venue-thumb"),"no unused horse thumbnail column");
assert.equal(rendered.includes("開催場一覧"),false);
assert.equal(rendered.includes("リアルタイム"),false);
assert.equal(rendered.includes("data-home-page=\"central\""),false);
assert.equal(rendered.includes("data-home-page=\"realtime\""),false);
assert.equal(rendered.includes("data-track=\"東京\""),true);
assert.equal(rendered.includes("data-track=\"大井\""),true);
assert.equal(rendered.includes("data-race=\"jra-"+date+"-東京-02\""),true);
assert.equal(rendered.includes("data-race=\"nar-"+date+"-大井-03\""),true);
assert.equal(rendered.includes("data-race=\"nar-"+date+"-大井-04\""),false);
assert.equal((rendered.match(/class="arv-all-race /g)||[]).length,24);
assert.equal((rendered.match(/aria-disabled="true"/g)||[]).length,21);
for(const tag of ["selected","special","ai-stats"])assert.ok(!rendered.includes('data-home-page="'+tag+'"'));
assert.ok(ui.home([],opts).includes("未取得"));
assert.ok(!ui.home([],opts).includes("data-race="));
const injected=ui.home([{...rows[0],track:'<img src=x onerror=alert(1)>'}],opts);
assert.ok(!injected.includes('<img src=x onerror=alert(1)>'));
console.log("HORSE_ALL_RACES_OK");

// Excluded Banei must never reappear from old API lists, even if a later
// venue has a valid 1R-12R card. Preserve other NAR/JRA venues.
const archived=[...rows,
 {id:"nar-"+date+"-帯広ば-01",circuit:"地方",track:"帯広ば",raceNumber:1,date,startTime:"14:35"},
 {id:"nar-"+date+"-帯広-02",circuit:"地方",track:"帯広",raceNumber:2,date,startTime:"15:10"},
 {id:"nar-"+date+"-帯広ば-03",circuit:"地方",track:"大井",raceNumber:3,date,startTime:"15:50"}
];
const withoutBanei=ui.home(archived,opts);
assert(!withoutBanei.includes("帯広"),"retired Banei must not render");
assert(withoutBanei.includes('data-track="大井"'));
assert(withoutBanei.includes('data-track="東京"'));
console.log("HORSE_PORTAL_BANEI_EXCLUDED_PASS");
