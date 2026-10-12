/* One shared live selector for both sports. Enforced in CI.
 * Uses fixed JST timestamps; never depends on the machine's timezone.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const shared=fs.readFileSync('arvexq/ui/static/sports/unified-home.js','utf8');
const ctx={window:{},Date,Map,Set,String,Number,Math};
vm.runInNewContext(shared,ctx,{filename:'unified-home.js'});
const {liveModel,liveSignature,liveRaces}=ctx.window.ARVEXQUnifiedHome;
assert.equal(typeof liveModel,'function');
const today='2026-10-12', at=t=>new Date(today+'T'+t+':00+09:00');
const horse=[
 {id:'jra-'+today+'-東京-01',circuit:'中央',track:'東京',raceNumber:1,startTime:'10:00'},
 {id:'jra-'+today+'-東京-02',circuit:'中央',track:'東京',raceNumber:2,startTime:'10:40'},
 {id:'nar-'+today+'-浦和-01',circuit:'地方',track:'浦和',raceNumber:1,startTime:'10:10'},
 {id:'nar-'+today+'-浦和-02',circuit:'地方',track:'浦和',raceNumber:2,startTime:'10:50'}
];
const boat=[
 {id:'boat-'+today+'-桐生-01',venue:'桐生',raceNo:1,closeTime:'10:00',closeAt:at('10:00').toISOString()},
 {id:'boat-'+today+'-桐生-02',venue:'桐生',raceNo:2,closeTime:'10:35',closeAt:at('10:35').toISOString()},
 {id:'boat-'+today+'-津-01',venue:'津',raceNo:1,closeTime:'10:10',closeAt:at('10:10').toISOString()},
 {id:'boat-'+today+'-津-02',venue:'津',raceNo:2,closeTime:'10:55',closeAt:at('10:55').toISOString()},
 {id:'boat-'+today+'-戸田-01',venue:'戸田',raceNo:1,closeTime:'11:00',closeAt:at('11:00').toISOString(),
  result:{status:'cancelled'}}
];
const status=(mode,rows,t,id)=>Array.from(liveModel(mode,rows,today,at(t)))
  .find(r=>r.id.endsWith(id));
assert.equal(liveModel('horse',horse,today,at('09:59')).length,4);
assert.equal(liveModel('boat',boat,today,at('09:59')).length,5);
assert.equal(status('horse',horse,'09:59','東京-01').status,'soon');
assert.equal(status('horse',horse,'09:59','東京-01').next,true);
assert.equal(status('horse',horse,'10:01','東京-01').status,'elapsed');
assert.equal(status('horse',horse,'10:01','東京-02').next,true);
assert.equal(status('boat',boat,'10:01','桐生-01').status,'elapsed');
assert.equal(status('boat',boat,'10:01','桐生-02').next,true);
assert.equal(status('boat',boat,'10:11','津-01').status,'elapsed');
assert.equal(status('boat',boat,'10:11','津-02').next,true);
assert.equal(status('boat',boat,'09:59','戸田-01').status,'cancelled');
assert.equal(liveModel('boat',boat,'2026-10-11',at('09:59')).length,5);
assert.equal(liveModel('horse',horse,today,at('23:58')).length,4);
assert.ok(liveModel('horse',horse,today,at('23:58'))
  .every(r=>r.status==='elapsed'));
assert.notEqual(liveSignature('boat',boat,today,at('09:59')),
                liveSignature('boat',boat,today,at('10:01')));
assert.match(liveRaces('boat',boat,today,at('10:01')),/全会場・全レース自動更新/);
assert.match(liveRaces('horse',horse,today,at('10:01')),/全4R/);
assert.match(liveRaces('boat',boat,today,at('10:01')),/全5R/);
assert.match(liveRaces('boat',boat,today,at('10:01')),/暗色＝時刻経過・確定/);
assert.doesNotMatch(liveRaces('boat',[],today,at('10:01')),/データ確認 0場/);
for(const path of ['arvexq/ui/static/app.js','arvexq/ui/static/sports/boat-app/app.js']){
  const js=fs.readFileSync(path,'utf8');
  const mode=path.endsWith('boat-app/app.js')?'boat':'horse';
  if(mode==='horse')assert.match(js,/ARVEXQHorsePortal\.home/);
  else assert.match(js,/allBoatRaces\(day\)/);
  assert.doesNotMatch(js,new RegExp("liveRaces\\('"+mode+"'"));
  assert.match(js,new RegExp("syncLiveUI\\('"+mode+"'"));
  assert.match(js,/10000/);
}
const dark=fs.readFileSync('arvexq/ui/static/sports/all-races.css','utf8');
assert.match(dark,/\.arv-all-race\.elapsed,\.arv-all-race\.finished/);
assert.match(dark,/opacity:\.63/);
const raceSource=fs.readFileSync('arvexq/ui/static/sports/boat-app/features/races.js','utf8');
const section=raceSource.slice(raceSource.indexOf('export function raceList('),raceSource.indexOf('export function detail('))
  .replace('export function raceList','function raceList');
const raceList=new Function('esc','usableForecast',section+'\nreturn raceList;')(
  x=>String(x),()=>false);
const grid=raceList({races:boat},'桐生');
assert.match(grid,/class="arv-all-races-grid boat-venue-race-grid"/);
assert.equal((grid.match(/<button/g)||[]).length,12);
assert.equal((grid.match(/data-race=/g)||[]).length,2);
assert.equal((grid.match(/disabled/g)||[]).length,10);
assert.match(grid,/10:35/);
console.log('SHARED_REALTIME_JST_ADVANCE_HORSE_BOAT_12R_GRID_PASS');
