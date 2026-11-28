#!/usr/bin/env node
// Exact ARVEXQ browser marks for one licensed, pre-off official condition change.
// Retired 2026-11-28: the in-app predictor this capture ran was removed
// with the rich UI (the app is now the entry-table-only shell), so no
// revised marks can be captured from the terminal any more. The script
// fails loudly with that reason instead of producing marks; its only
// caller (user_approved_model_revision.py, itself gated to 2026-10-09)
// treats a failed capture as "compute-failed" and keeps the original.
'use strict';
const fs=require('node:fs'),vm=require('node:vm');
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot="installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);";
if(!root.includes(boot))throw Error('course mark capture unavailable: in-app predictor retired 2026-11-28 (entry-table-only app)');
const source=root.replace(boot,'window.__captureMarks={predict,state};');
const memory=new Map(),store={getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,String(v)),removeItem:k=>memory.delete(k)};
const document={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},querySelector:()=>null,querySelectorAll:()=>[],visibilityState:'hidden'};
const window={addEventListener:()=>{},innerWidth:390,location:{href:'https://marks.invalid/'},navigator:{standalone:false},localStorage:store,document};
const ctx={window,document,localStorage:store,sessionStorage:store,console,
URL,URLSearchParams,Date,Math,JSON,Intl,Number,String,Array,Object,Set,Map,
Promise,RegExp,parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,
navigator:window.navigator,location:window.location,setTimeout:()=>0,clearTimeout:()=>{},
setInterval:()=>0,clearInterval:()=>{}};
vm.createContext(ctx);
vm.runInContext(source,ctx,{timeout:12000,filename:'app.js'});
const detail=JSON.parse(fs.readFileSync(0,'utf8'));
const earliest=Date.parse(String(detail.date||'')+'T'+String(detail.startTime||'').slice(0,5)+':00+09:00');
if(!Number.isFinite(earliest)||Date.now()>=earliest)throw Error('cannot generate post-off revised marks');
const original=detail.morningMarkSnapshot;
if(!original||original.version!=='arvexq-morning-marks-v1'||String(original.raceId)!==String(detail.id))
  throw Error('morning mark original unavailable');
const working={...detail};
delete working.morningMarkSnapshot;delete working.officialMarkRevisions;delete working.preRacePrediction;
const official=detail.officialCourseCondition||{};
if(official.going)working.condition=String(official.going);
const engine=window.__captureMarks;
engine.state.date=String(detail.date||'');
engine.state.races=[{id:detail.id,circuit:detail.circuit,track:detail.track,
date:detail.date,startTime:detail.startTime,raceNumber:detail.raceNumber}];
engine.state.race=working;
const p=engine.predict(working);
const rows=(p.rows||[]).filter(x=>x&&x.horse&&Number(x.horse.horseNumber)>0);
const marks=rows.map(x=>({horseNumber:Number(x.horse.horseNumber),mark:String(x.predMark||''),
singleWinSuitable:!!x.singleWinSuitable}));
if(marks.length<3||marks.filter(x=>!!x.mark).length<3)throw Error('insufficient revised forecast');
process.stdout.write(JSON.stringify({horses:marks}));
