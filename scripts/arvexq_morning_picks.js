#!/usr/bin/env node
// Freeze ALL of today's selected/special race IDs once, from the morning's
// complete pre-off cards. No selected race can be added on a later refresh.
'use strict';
const fs=require('node:fs'),vm=require('node:vm');
const [input,output]=process.argv.slice(2);
if(!input||!output)throw Error('usage: arvexq_morning_picks.js prepared.json output.json');
const payload=JSON.parse(fs.readFileSync(input,'utf8'));
const rows=(payload.summaries||[]).filter(r=>r&&r.id);
const details=new Map((payload.details||[]).filter(d=>d&&d.id).map(d=>[String(d.id),d]));
const day=String((payload.meta||{}).sync_date||rows[0]?.date||'');
const now=new Date();
const earliest=Math.min(...rows.map(r=>Date.parse(String(r.date||day)+'T'+String(r.startTime||'').slice(0,5)+':00+09:00')));
const complete=rows.length>0&&details.size>=rows.length&&rows.every(r=>{
  const d=details.get(String(r.id));
  return d&&Array.isArray(d.horses)&&d.horses.filter(h=>h&&h.name&&Number(h.horseNumber)>0).length>=3
    &&d.preparedMeta&&d.preparedMeta.diagnosisReady===true;
});
function save(reason){
  fs.writeFileSync(output,JSON.stringify(payload));
  console.log('MORNING_PICKS_'+reason,'day='+day,'races='+rows.length,'complete='+complete);
}
if(!complete){save('AWAITING_COMPLETE_PREOFF_DATA');process.exit(0)}
if(!Number.isFinite(earliest)||now.getTime()>=earliest){save('NOT_RECONSTRUCTED_AFTER_FIRST_OFF');process.exit(0)}
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
if(!root.includes(boot))throw Error('morning picker boot entry missing');
const source=root.replace(boot,'window.__morningPicks={state,selectedRaceCandidates:computeMorningRaceCandidates,specialForecastRaceCandidates:computeMorningSpecialRaceCandidates,add:function(k,v){instantTrackDetails[k]=v;}};');
const items=new Map(),store={getItem:k=>items.get(k)||null,setItem:(k,v)=>items.set(k,String(v)),removeItem:k=>items.delete(k)};
const document={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},querySelector:()=>null,querySelectorAll:()=>[],visibilityState:'hidden'};
const window={addEventListener:()=>{},innerWidth:390,location:{href:'https://morning.invalid/'},navigator:{standalone:false},localStorage:store,document};
const ctx={window,document,localStorage:store,sessionStorage:store,console,
 URL,URLSearchParams,Date,Math,JSON,Intl,Number,String,Array,Object,Set,Map,
 Promise,RegExp,parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,
 navigator:window.navigator,location:window.location,setTimeout:()=>0,
 clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{}};
vm.createContext(ctx);
vm.runInContext(source,ctx,{timeout:12000,filename:'app.js'});
const model=window.__morningPicks;
model.state.date=day;model.state.races=rows;model.state.circuit='地方';
for(const [id,d] of details)model.add(id,d);
let selected=[],special=[];
try{
  selected=[...model.selectedRaceCandidates('中央'),...model.selectedRaceCandidates('地方')];
  special=model.specialForecastRaceCandidates();
}catch(e){
  console.error('MORNING_SELECTION_ERROR',String(e&&e.stack||e));
  save('MODEL_FAILED_NO_FREEZE');process.exit(0)
}
const selectionById=new Map(selected.map(x=>[String(x.race.id),Number(x.selection?.score||0)]));
const specials=new Set(special.map(x=>String(x.id)));
const fixedAt=now.toISOString();
const status={morningPickVersion:'v1',morningPickFixedAt:fixedAt,morningPickScope:rows.length};
for(const r of rows){
  const decision={
    version:'v1',fixedAt,scope:rows.length,
    selected:selectionById.has(String(r.id)),
    selectedScore:selectionById.get(String(r.id))||0,
    special:specials.has(String(r.id)),
  };
  Object.assign(r,status,{
    morningSelected:decision.selected,
    morningSelectedScore:decision.selectedScore,
    morningSpecial:decision.special,
  });
  // A public D1 summary upsert currently whitelists unknown top-level keys.
  // Put the manifest inside the existing structured summary metadata as well.
  r.volatility={...(r.volatility||{}),morningPicks:decision};
  r.environmentMeta={...(r.environmentMeta||{}),morningPicks:decision};
}
for(const d of payload.details||[]){
  const r=rows.find(x=>String(x.id)===String(d.id));
  if(r){
    for(const key of ['morningPickVersion','morningPickFixedAt','morningPickScope','morningSelected','morningSelectedScore','morningSpecial'])d[key]=r[key];
    d.volatility={...(d.volatility||{}),morningPicks:r.volatility.morningPicks};
    d.environmentMeta={...(d.environmentMeta||{}),morningPicks:r.volatility.morningPicks};
  }
}
fs.writeFileSync(output,JSON.stringify(payload));
console.log('MORNING_PICKS_FROZEN','date='+day,'races='+rows.length,
  'selected='+selectionById.size,'special='+specials.size,'fixedAt='+fixedAt);
