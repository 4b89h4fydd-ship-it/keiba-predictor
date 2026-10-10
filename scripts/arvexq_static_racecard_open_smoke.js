const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function extract(name){
  const start=src.indexOf('function '+name+'(');
  const end=src.indexOf('\n}',start)+2;
  assert.ok(start>=0&&end>start,'missing '+name);
  return src.slice(start,end);
}
const history=[];
const race='jra-2026-10-10-東京-03';
const state={date:'2026-10-10',races:[{id:race,date:'2026-10-10',track:'東京',raceNumber:3}]};
const summary={id:race,date:'2026-10-10',horses:[
  {horseNumber:1,name:'甲'},{horseNumber:2,name:'乙'}],fieldSize:2};
let upstreamFail=true,usedArchive=false;
const loader={available:async(day,id,fetcher)=>{
  assert.equal(day,'2026-10-10');assert.equal(id,race);
  assert.equal(typeof fetcher,'function');
  usedArchive=true;return Object.assign({},summary,{_entryOnly:true,_staticRacecardFallback:true});
}};
const make=new Function('edgeFetchJson','traceRaceDetail','entryDataAvailable','state','window',
  extract('fetchRacecardOnly')+';return fetchRacecardOnly;');
const f=make(async url=>{
  if(upstreamFail)throw Error('http 404');
  return {ok:true,detail:summary};
},(...args)=>history.push(args),d=>!!(d&&d.horses&&d.horses.length),state,
 {ARVEXQStaticRacecard:loader});
(async()=>{
  const fallback=await f(race);
  assert.equal(fallback.horses.length,2);
  assert.equal(fallback._entryOnly,true);
  assert.equal(fallback._staticRacecardFallback,true);
  assert.equal(usedArchive,true);
  assert.ok(history.some(x=>x[1]==='racecard-static-backup'));
  upstreamFail=false;usedArchive=false;
  const normal=await f(race);
  assert.equal(normal._entryOnly,true);
  assert.equal(normal._staticRacecardFallback,undefined);
  assert.equal(usedArchive,false);
  console.log('RACECARD_D1_404_STATIC_FALLBACK_PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
