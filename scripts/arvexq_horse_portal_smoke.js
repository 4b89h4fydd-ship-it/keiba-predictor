const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const root={};
vm.runInNewContext(fs.readFileSync('arvexq/ui/static/sports/horse-portal.js','utf8'),{window:root});
const ui=root.ARVEXQHorsePortal;
const date='2026-10-11';
const rows=[
{id:'jra-'+date+'-東京-01',circuit:'中央',track:'東京',raceNumber:1,startTime:'09:50',title:'第1レース',date},
{id:'nar-'+date+'-大井-03',circuit:'地方',track:'大井',raceNumber:3,startTime:'10:10',title:'第3レース',date},
{id:'jra-'+date+'-京都-02',circuit:'中央',track:'京都',raceNumber:2,startTime:'10:05',title:'第2レース',date},
{id:'jra-'+date+'-中山-12',circuit:'中央',track:'中山',raceNumber:12,startTime:'16:30',title:'第12レース',date}
];
const h=ui.home(rows,{date,today:date,nowMinutes:600,selected:{central:2,local:1},special:{central:1,local:0}});
for(const page of ['central','local','realtime','selected','special','ai-stats'])assert.ok(h.includes('data-home-page="'+page+'"'),page);
assert.ok(h.includes('data-race="nar-'+date+'-大井-03"'));
assert.ok(h.includes('data-circuit="中央"'));
assert.ok(h.includes('data-circuit="地方"'));
assert.ok(h.includes('data-track="京都"'));
const timeline=ui.timeline(rows,date,date,600);
assert.equal(timeline[0].startTime,'10:05');
assert.equal(timeline[1].startTime,'10:10');
assert.equal(ui.status(rows[0],date,date,600).label,'結果待ち');
assert.equal(ui.status(rows[1],date,date,600).label,'まもなく');
assert.ok(ui.realtime([], {date,today:date,nowMinutes:600}).includes('架空のレースは表示しません'));
assert.ok(ui.venues([], '地方').includes('開催場情報がまだありません'));
const dangerous='<img src=x onerror=alert(1)>';
assert.equal(ui.home([{...rows[0],title:dangerous}],{date,today:date,nowMinutes:600}).includes(dangerous),false);
console.log('HORSE_TELEBOAT_PORTAL_OK');
