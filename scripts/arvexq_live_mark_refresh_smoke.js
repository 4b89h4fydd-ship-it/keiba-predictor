#!/usr/bin/env node
'use strict';
// The retired 60/40 engine must never regenerate marks from raw past runs.\n// Only learned D1 predictions or verified historical originals can appear.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function loadActualProductionApp(){
  const versionPath='dist/version.json';
  if(fs.existsSync(versionPath)){
    const version=JSON.parse(fs.readFileSync(versionPath,'utf8')).build;
    return fs.readFileSync('dist/app-'+version+'.js','utf8');
  }
  // Standalone smoke tests must still execute the actual box-composed source.
  const {execFileSync}=require('node:child_process');
  return execFileSync('python',['-c',
    "from pathlib import Path; from arvexq.ui.bundle import compose_app_script; print(compose_app_script(Path('arvexq/ui/static/app.js').read_text(encoding='utf-8')))"
  ],{encoding:'utf8'});
}
const root=loadActualProductionApp();
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
for(const file of fs.readdirSync('arvexq/ui/static/forecast').filter(x=>x.endsWith('.js')).map(x=>'arvexq/ui/static/forecast/'+x).concat(['arvexq/ui/static/morning/ticket_lane_classifier.js','arvexq/ui/static/betting/bet_view.js']))
  vm.runInContext(fs.readFileSync(file,'utf8'),ctx,{filename:file,timeout:20000});
vm.runInContext(source,ctx,{filename:'app.js',timeout:20000});
const {predict}=window.__arvexqMarkTest;
const horses=Array.from({length:7},(_,i)=>({
 horseNumber:i+1,name:'Horse-'+(i+1),recentRaces:[{date:'2098-12-01',finish:1,fieldSize:12}]
}));
const race={id:'jra-2099-01-10-東京-08',date:'2099-01-10',startTime:'23:00',
 circuit:'中央',track:'東京',raceNumber:8,fieldSize:7,surface:'ダート',distance:1400,horses};
function marks(p){return Array.from(p.rows).filter(z=>z.predMark==='◎').map(z=>Number(z.horse.horseNumber))}
const missing=predict(race);
assert.deepEqual(marks(missing),[],'no old engine may calculate a replacement mark');
assert.equal(missing.rows[0].winProbability,null);
race.horses[0].recentRaces[0].finish=12;
assert.deepEqual(marks(predict(race)),[],'raw result mutations cannot resurrect legacy marks');
race.predictionModelVersion='arvexq-learned-whole-career-scenarios-v2';
race.horses.forEach((h,i)=>{h.integratedEvaluation={
 mark:i===0?'◎':'',
 modelProbabilities:{win:[.1,.2],top2:[.2,.3],top3:[.3,.4]}
}});
const learned=predict(race);
assert.deepEqual(marks(learned),[]);
assert.equal(learned.rows[0].winProbability,null);
race.raceStatus='確定';
assert.deepEqual(marks(predict(race)),[],'unapproved saved candidate remains disabled after result');
assert.equal(store.size,0,'no post-race marks should be minted into localStorage');
console.log('LEARNED_D1_ONLY_MARKS_NO_RETIRED_SCORE_PASS');
