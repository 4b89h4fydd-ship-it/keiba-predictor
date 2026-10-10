const assert=require('node:assert/strict'),fs=require('node:fs');
const root={};new Function('window',fs.readFileSync('arvexq/ui/static/research/live_odds.js','utf8'))(root);
const mod=root.ARVEXQLiveOdds,id='nar-2026-10-10-高知-11';
const fixture={ok:true,race_id:id,odds:[
  {horse_no:1,win_odds:4.2,popularity:2,updated_at:1791598944},
  {horse_no:2,win_odds:null,popularity:null,horse_status:'出走取消',updated_at:1791598944}
]};
(async()=>{
  let calls=0;
  const fetcher=async url=>{calls++;assert.ok(url.includes('/api/odds/'));
    assert.ok(!url.includes('/api/race/'));return fixture};
  const [a,b]=await Promise.all([mod.fetch(id,fetcher),mod.fetch(id,fetcher)]);
  assert.equal(calls,1);assert.deepEqual(a,b);
  assert.equal(a.horses[0].winOdds,4.2);assert.equal(a.horses[0].popularity,2);
  assert.equal(a.horses[0].oddsForecast,false);
  assert.equal(a.horses[1].winOdds,null);
  assert.equal(a.oddsUpdatedAt,new Date(1791598944*1000).toISOString());
  assert.ok(mod.status(a).includes('2026/10/10'));
  assert.match(mod.status({}),/未取得/);
  assert.throws(()=>mod.normalize({...fixture,race_id:'other'},id),/identity/);
  assert.throws(()=>mod.normalize({...fixture,odds:[fixture.odds[0],fixture.odds[0]]},id),/runner/);
  assert.deepEqual(mod.normalize({...fixture,odds:[]},id).horses,[]);
  await mod.fetch(id,fetcher);assert.equal(calls,2,'manual refresh fetches again');
  console.log('INDEPENDENT_ODDS_SOURCE_TIME_IDENTITY_REFRESH_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
