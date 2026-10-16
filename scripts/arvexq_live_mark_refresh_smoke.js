#!/usr/bin/env node
'use strict';
// Run the live app.js prediction path. New measured 60/40 observed evidence must
// update marks without a page reload, while preoff archives remain immutable.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
assert(root.includes(boot),'main boot anchor changed');
const source=root.replace(boot,'window.__arvexqMarkTest={predict,state};');
const store=new Map(),localStorage={
 getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,String(v)),
 removeItem:k=>store.delete(k)
};
const document={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},
 querySelector:()=>null,querySelectorAll:()=>[],visibilityState:'hidden'};
const window={addEventListener:()=>{},innerWidth:390,
 location:{href:'https://archive.invalid/'},navigator:{standalone:false},
 document,localStorage};
const ctx={window,document,localStorage,sessionStorage:localStorage,console,
 URL,URLSearchParams,Date,Math,JSON,Intl,Number,String,Array,Object,Set,Map,
 Promise,RegExp,parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,
 navigator:window.navigator,location:window.location,setTimeout:()=>0,
 clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{}};
vm.createContext(ctx);
for(const file of ['arvexq/ui/static/morning/ticket_lane_classifier.js','arvexq/ui/static/betting/bet_view.js'])
  vm.runInContext(fs.readFileSync(file,'utf8'),ctx,{filename:file,timeout:20000});
vm.runInContext(source,ctx,{filename:'app.js',timeout:20000});
const {predict}=window.__arvexqMarkTest;
const horses=Array.from({length:7},(_,i)=>({
 horseNumber:i+1,name:'Horse-'+(i+1),jockey:'Jockey',winOdds:2.8+i*1.5,
 recentRaces:Array.from({length:5},(_,j)=>({
  date:'2098-12-'+String(20-3*j).padStart(2,'0'),
  track:'東京',distance:1400,surface:'ダート',fieldSize:12,
  finish:i===0?1:i===1?7:10,last3fRank:i===0?1:i===1?7:10,
  cornerPositions:[2,2,2,2],timeSeconds:85.7+i*.4,
  timeBehindWinner:i===0?0:i===1?1.5:2+i*.3,
  marginEvidenceSource:'JRA official',
  marginEvidence:{winnerTimeSeconds:85.7,horseTimeSeconds:85.7+(i===0?0:i===1?1.5:2+i*.3)}
 }))
}));
const race={id:'jra-2099-01-10-東京-08',date:'2099-01-10',startTime:'23:00',
 circuit:'中央',track:'東京',raceNumber:8,fieldSize:7,surface:'ダート',
 distance:1400,condition:'良',weather:'晴',horses};
function marks(p){return Array.from(p.rows).filter(z=>z.predMark==='◎').map(z=>Number(z.horse.horseNumber))}
function score(p,no){return Number(p.rows.find(z=>Number(z.horse.horseNumber)===no).threeFactorScore)}
const first=predict(race);
assert.deepEqual(marks(first),[1],'initial single ◎');
assert.equal(first.engineVersion,'arvexq-jra-mineta-margin-60-40-v1');
const noDataChange=predict(race);
assert.equal(noDataChange,first,'no input change should reuse the cached live prediction');
race.horses[0].winOdds=91;
assert.equal(predict(race),first,'odds alone cannot rewrite ability-based ◎');
race.horses[0].recentRaces.forEach(x=>{x.timeBehindWinner=4;x.marginEvidence.horseTimeSeconds=89.7});
race.horses[1].recentRaces.forEach(x=>{x.timeBehindWinner=0;x.marginEvidence.horseTimeSeconds=85.7});
const changed=predict(race);
assert.notEqual(changed,first,'fresh pre-off observed runs must invalidate old prediction');
assert.deepEqual(marks(changed),[2],'◎ follows new 60/40 observed score');
assert(score(changed,2)>score(changed,1),'actual model score must update');
assert.notEqual(changed.markInputSignature,first.markInputSignature,'cache signature must change');
race.horses[1].recentRaces.push({date:'2099-01-11',fieldSize:12,finish:12,last3fRank:12});
assert.equal(predict(race),changed,'future starts cannot affect the pre-off score');
// Completed races can be rerun as labeled revisions while their original
// pre-start receipts remain separate and immutable.
race.raceStatus='発走済';
const revised=predict(race);
assert.equal(revised.engineVersion,'arvexq-jra-mineta-margin-60-40-v1');
assert.equal(revised.postRaceRevision,true);
assert.deepEqual(marks(revised),[2]);
assert.equal(predict(race),revised,'post-race revision stays stable');
assert(store.has('arvexq:revised-marks:v1:'+race.id));
console.log('OBSERVED_6040_MARK_REFRESH_OK (preoff refresh, odds isolation, postoff archive)');
