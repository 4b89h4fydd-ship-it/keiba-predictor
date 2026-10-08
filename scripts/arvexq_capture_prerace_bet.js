#!/usr/bin/env node
// Run the SAME versioned browser betting core without displaying a race.
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
if(!root.includes(boot))throw Error('UI boot anchor changed');
const source=root.replace(boot,'window.__arvexqServer={predict,buildAiBetPlan,state};');
const saved=new Map();
const store={getItem:k=>saved.get(k)||null,
 setItem:(k,v)=>saved.set(k,String(v)),removeItem:k=>saved.delete(k)};
const doc={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},querySelector:()=>null,
 querySelectorAll:()=>[],visibilityState:'hidden'};
const window={addEventListener:()=>{},innerWidth:390,location:{href:'https://archive.invalid/'},
 navigator:{standalone:false},localStorage:store};
window.document=doc;
const ctx={window,document:doc,localStorage:store,sessionStorage:store,console,
 URL,URLSearchParams,Date,Math,JSON,Intl,Number,String,Array,Object,Set,Map,
 Promise,RegExp,parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,
 navigator:window.navigator,location:window.location,setTimeout:()=>0,
 clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{}};
vm.createContext(ctx);
vm.runInContext(source,ctx,{timeout:12000,filename:'app.js'});
const race=JSON.parse(fs.readFileSync(0,'utf8'));
const exported=window.__arvexqServer;
exported.state.date=String(race.date||'');
exported.state.circuit=String(race.circuit||'地方');
exported.state.track=String(race.track||'');
exported.state.races=[{id:race.id,date:race.date,circuit:race.circuit,track:race.track,
 raceNumber:race.raceNumber,startTime:race.startTime,title:race.title||''}];
exported.state.race=race;
const status={version:'arvexq-server-exact-js-bet-v1',
 jsHash:crypto.createHash('sha256').update(root).digest('hex')};
try{
 const prediction=exported.predict(race);
 const result=exported.buildAiBetPlan(race,prediction);
 if(!result){console.log(JSON.stringify({...status,decision:'見送り',
   reason:'現行買い目エンジンの購入条件未達。発走後に再計算しません。',
   items:[],singleWinHorseNumber:(prediction.rows||[]).find(x=>x&&x.singleWinSuitable)?.horse?.horseNumber||0,
   betQuality:0,trifectaReviewed:true,trifectaDecision:'見送り',trifectaReason:'入力または条件不足'}));
 }else{
   const out=JSON.parse(JSON.stringify(result));
   out.version=status.version;out.jsHash=status.jsHash;
   out.singleWinHorseNumber=(prediction.rows||[]).find(x=>x&&x.singleWinSuitable)?.horse?.horseNumber||0;
   console.log(JSON.stringify(out));
 }
}catch(error){console.error('SERVER_JS_BET_FAILED',String(error&&error.stack||error));process.exit(2)}
