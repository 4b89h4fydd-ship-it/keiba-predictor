#!/usr/bin/env node
// Run the SAME versioned browser betting core without displaying a race.
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const strategies=['podium_axis_guard.js','bet_readiness.js','no_axis_strategy.js','main_strategy.js','trifecta_strategy.js',
 'insurance_strategy.js'].map(name=>({name,code:fs.readFileSync('arvexq/ui/static/betting/'+name,'utf8')}));
const lane=fs.readFileSync('arvexq/ui/static/morning/ticket_lane_classifier.js','utf8');
const legacy=fs.readFileSync('arvexq/ui/static/betting/legacy_v213_order_model.js','utf8');
const engine=fs.readFileSync('arvexq/ui/static/betting/three_way_engine.js','utf8');
const view=fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
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
strategies.forEach(({name,code})=>vm.runInContext(code,ctx,{timeout:12000,filename:name}));
vm.runInContext(legacy,ctx,{timeout:12000,filename:'legacy_v213_order_model.js'});
vm.runInContext(engine,ctx,{timeout:12000,filename:'three_way_engine.js'});
vm.runInContext(lane,ctx,{timeout:12000,filename:'ticket_lane_classifier.js'});
vm.runInContext(view,ctx,{timeout:12000,filename:'bet_view.js'});
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
 jsHash:crypto.createHash('sha256').update(root).update('\0').update(legacy).update('\0').update(strategies.map(x=>x.code).join('\0')).update('\0').update(engine).update('\0').update(lane).digest('hex')};
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
