'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const first=src.indexOf('// A rank saved at a different market timestamp');
const last=src.indexOf('function smartVal(',first);
assert(first>=0&&last>first,'market rank must have one live UI authority');
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const scratch=h=>!!h&&(h.scratched===true||/取消|除外|欠場/.test(h.status||''));
const state={race:null};
const market=new Function('state','n','isScratchHorse',src.slice(first,last)+'return {marketPopularity,popularityText}')(state,n,scratch);
function fixture(){
 const horses=[
  {horseNumber:1,winOdds:4.5,popularity:1,oddsSource:'NAR公式'},
  {horseNumber:2,winOdds:2.4,popularity:3,oddsSource:'NAR公式'},
  {horseNumber:3,winOdds:6.3,popularity:2,oddsSource:'NAR公式'}
 ];
 return {horses};
}
let race=fixture();state.race=race;
assert.deepEqual(race.horses.map(h=>market.marketPopularity(h,race)),[2,1,3],'stale saved ranks may not contradict visible prices');
race.horses[0].winOdds=1.9;
assert.deepEqual(race.horses.map(h=>market.marketPopularity(h,race)),[1,2,3],'live repricing must reorder popularity');
race.horses[0].winOdds=2.4;
assert.deepEqual(race.horses.map(h=>market.marketPopularity(h,race)),[1,1,3],'identical displayed odds must share a rank');
race.horses[2].winOdds=null;
assert.deepEqual(race.horses.map(h=>market.marketPopularity(h,race)),[0,0,0],'partial odds must never masquerade as full-field popularity');
race.horses[2].winOdds=6.3;race.horses[2].scratched=true;
assert.deepEqual(race.horses.map(h=>market.marketPopularity(h,race)),[1,1,0],'withdrawn runners excluded from popularity');
race.horses[2].scratched=false;race.horses[2].oddsForecast=true;
assert.deepEqual(race.horses.map(h=>market.marketPopularity(h,race)),[0,0,0],'predicted and confirmed odds cannot share one popularity chart');
const start=src.indexOf('function racecardOddsHtml(h,r){');
const end=src.indexOf('function racecardMarkDisplay(',start);
assert(start>=0&&end>start,'racecard must render current popularity');
const esc=v=>String(v==null?'':v);
const render=new Function('n','isScratchHorse','marketPopularity','esc',src.slice(start,end)+'return racecardOddsHtml')(n,scratch,market.marketPopularity,esc);
race=fixture();
const displayed=race.horses.map(h=>render(h,race));
assert.match(displayed[0],/2人気/);assert.match(displayed[1],/1人気/);assert.match(displayed[2],/3人気/);
race.horses[2].winOdds=null;
assert.match(render(race.horses[0],race),/未取得<\/span>/);
race.horses[2].winOdds=6.3;race.horses[2].oddsForecast=true;
assert.match(render(race.horses[0],race),/未取得/);
console.log('LIVE_ODDS_POPULARITY_SNAPSHOT_CONSISTENCY_PASS');
