// fetchRacecardOnly open-path regression (GitHub-only migration block D).
//
// Contract under test: fetchRacecardOnly is static-only.  The dated
// static racecard archive (/racecards/<date>.json), loaded through the
// real ARVEXQStaticRacecard module, is its one and only source; the
// old D1 racecard endpoint is never consulted.  A card that comes from
// the archive must keep the loader's provenance flags (_entryOnly and
// _staticRacecardFallback) so the UI can label it as factual
// entry-only data, and any archive miss/unavailability resolves to
// null (the caller keeps its no-data state) instead of throwing.
const assert=require('node:assert/strict'),fs=require('node:fs');
const appSrc=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const loaderSrc=fs.readFileSync('arvexq/ui/static/research/static_racecard.js','utf8');
function extract(name){
  const start=appSrc.indexOf('function '+name+'(');
  const end=appSrc.indexOf('\n}',start)+2;
  assert.ok(start>=0&&end>start,'missing '+name);
  return appSrc.slice(start,end);
}
// Real dated-archive loader bound to a fake window (same harness as
// arvexq_static_racecard_smoke.js).
const win={};new Function('window',loaderSrc)(win);
assert.ok(win.ARVEXQStaticRacecard,'static racecard loader missing');
const history=[];
const race='jra-2026-10-10-東京-03';
const archive={version:'arvexq-static-entry-v1',date:'2026-10-10',
  races:[{id:race,date:'2026-10-10',track:'東京',raceNumber:3,fieldSize:2,
    horses:[{horseNumber:1,name:'甲'},{horseNumber:2,name:'乙'}]}]};
const fetched=[];
const edgeFetchJson=async url=>{
  fetched.push(url);
  if(url==='/racecards/2026-10-10.json')return archive;
  throw Error('http 404');
};
const entryDataAvailable=d=>!!(d&&d.horses&&d.horses.length);
const trace=(...args)=>history.push(args);
const state={date:'2026-10-10',race:null,
  races:[{id:race,date:'2026-10-10',track:'東京',raceNumber:3}]};
const make=new Function('edgeFetchJson','traceRaceDetail','entryDataAvailable','state','window',
  extract('fetchRacecardOnly')+';return fetchRacecardOnly;');
const f=make(edgeFetchJson,trace,entryDataAvailable,state,win);
(async()=>{
  // Archive hit: card returned with its provenance flags intact, and
  // the dated archive is the one and only network fetch (static-only).
  const card=await f(race);
  assert.ok(card,'archive card expected');
  assert.equal(card.horses.length,2);
  assert.equal(card._entryOnly,true);
  assert.equal(card._staticRacecardFallback,true);
  assert.deepEqual(fetched,['/racecards/2026-10-10.json']);
  assert.ok(history.some(x=>x[1]==='racecard-static-request'));
  assert.ok(history.some(x=>x[1]==='racecard-static-backup'));
  // Archive miss (race not in a served archive): null, and no backup
  // trace may be emitted for a card that does not exist.
  history.length=0;
  const miss=await f('jra-2026-10-10-東京-99');
  assert.equal(miss,null);
  assert.ok(history.some(x=>x[1]==='racecard-static-request'));
  assert.ok(!history.some(x=>x[1]==='racecard-static-backup'));
  // Archive unavailable (the dated file itself 404s): null, no throw.
  state.date='2026-10-11';state.races=[];
  const unavailable=await f(race);
  assert.equal(unavailable,null);
  // Loader absent (module failed to load): null, no throw.
  const bare=make(edgeFetchJson,trace,entryDataAvailable,state,{});
  assert.equal(await bare(race),null);
  console.log('RACECARD_STATIC_ONLY_OPEN_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
