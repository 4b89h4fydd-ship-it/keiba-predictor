import assert from 'node:assert/strict';
import {realtimeRows,realtimeSection} from '../arvexq/ui/static/sports/boat-app/features/realtime.js';
const date='2026-10-11',now=new Date('2026-10-11T10:00:00+09:00');
const entries=[
{id:'boat-'+date+'-桐生-01',venue:'桐生',raceNo:1,closeAt:'2026-10-11T09:50:00+09:00',closeTime:'09:50',title:'第1レース'},
{id:'boat-'+date+'-津-02',venue:'津',raceNo:2,closeAt:'2026-10-11T10:12:00+09:00',closeTime:'10:12',title:'第2レース'},
{id:'boat-'+date+'-大村-03',venue:'大村',raceNo:3,closeAt:'2026-10-11T10:05:00+09:00',closeTime:'10:05',title:'第3レース'}
];
const day={date,races:entries,verifiedAt:'2026-10-11T09:30:00+09:00'};
const sorted=realtimeRows(day,now).map(x=>x.race.venue);
assert.deepEqual(sorted,['大村','津','桐生']);
assert.ok(realtimeSection(day,{full:true,now}).includes('data-race="boat-'+date+'-大村-03"'));
assert.ok(realtimeSection(day,{full:true,now}).includes('まもなく'));
assert.ok(realtimeSection(day,{full:true,now}).includes('結果待ち'));
assert.ok(realtimeSection(day,{now}).includes('data-view="realtime"'));
assert.equal(realtimeRows({date,races:[{id:'bad',venue:'大村',raceNo:1}]},now).length,0);
assert.ok(realtimeSection({date,races:[]},{now}).includes('未取得'));
console.log('BOAT_TELEBOAT_REALTIME_OK');
