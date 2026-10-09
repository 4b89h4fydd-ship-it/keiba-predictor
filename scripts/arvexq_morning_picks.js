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
const structurallyReady=rows.length>0&&details.size>=rows.length&&rows.every(r=>{
 const d=details.get(String(r.id));return !!(d&&Array.isArray(d.horses)&&d.horses.filter(h=>h&&h.name&&Number(h.horseNumber)>0).length>=3);
});
const assessed=rows.filter(r=>{const d=details.get(String(r.id));return d&&d.preparedMeta&&d.preparedMeta.diagnosisReady===true;});
// One thin AI card no longer stalls all complete morning selections. Explicit
// 'assessed:false' is archived for those races, never silently called rejected.
const complete=structurallyReady&&assessed.length>=Math.max(1,Math.ceil(rows.length*.80));
function save(reason){
  fs.writeFileSync(output,JSON.stringify(payload));
  console.log('MORNING_PICKS_'+reason,'day='+day,'races='+rows.length,'complete='+complete);
}
const existingArchive='arvexq/ui/static/morning-picks/'+day+'.json';
if(/^20\d{2}-\d{2}-\d{2}$/.test(day)&&fs.existsSync(existingArchive)){
  const archive=JSON.parse(fs.readFileSync(existingArchive,'utf8'));
  if(archive.version!=='v1'||archive.date!==day||!archive.fixedAt||
     !Array.isArray(archive.races)||archive.races.length!==Number(archive.scope))
    throw Error('invalid immutable morning archive: '+existingArchive);
  const saved=new Map(archive.races.map(r=>[String(r.id),r]));
  function restore(r){
    const m=saved.get(String(r.id));if(!m)return;
    const frozen={version:'v1',fixedAt:archive.fixedAt,scope:archive.scope,
      selected:m.selected===true,selectedScore:Number(m.selectedScore)||0,special:m.special===true,
      assessed:m.assessed!==false,primaryType:String(m.primaryType||''),
      types:Array.isArray(m.types)?m.types.slice():[],selectionReason:String(m.selectionReason||''),
      selectionModelVersion:String(m.selectionModelVersion||'')};
    Object.assign(r,{morningPickVersion:'v1',morningPickFixedAt:archive.fixedAt,
      morningPickScope:archive.scope,morningSelected:frozen.selected,
      morningSelectedScore:frozen.selectedScore,morningSpecial:frozen.special,morningAssessed:frozen.assessed,
      morningPrimaryType:frozen.primaryType,morningSelectedTypes:frozen.types.slice(),
      morningSelectionReason:frozen.selectionReason});
    r.volatility={...(r.volatility||{}),morningPicks:frozen};
    r.environmentMeta={...(r.environmentMeta||{}),morningPicks:frozen};
  }
  rows.forEach(restore);
  (payload.details||[]).forEach(restore);
  fs.writeFileSync(output,JSON.stringify(payload));
  console.log('MORNING_PICKS_REUSED_ALREADY_FIXED',day,'races',saved.size);
  process.exit(0);
}
if(!complete){save('AWAITING_SUFFICIENT_MORNING_DATA');process.exit(0)}
// First scheduled prefetch at 05:30 is for early cards, not premature freezing.
const jstToday=new Date(now.getTime()+9*3600000).toISOString().slice(0,10);
const earliestMorning=Date.parse(day+'T06:15:00+09:00');
if(day===jstToday&&now.getTime()<earliestMorning){save('BEFORE_MORNING_FREEZE_WINDOW');process.exit(0)}
if(!Number.isFinite(earliest)||now.getTime()>=earliest){save('NOT_RECONSTRUCTED_AFTER_FIRST_OFF');process.exit(0)}
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const selectionModule=fs.readFileSync('arvexq/ui/static/morning/selection_cut.js','utf8');
const laneModule=fs.readFileSync('arvexq/ui/static/morning/ticket_lane_classifier.js','utf8');
const betModules=['legacy_v213_order_model.js','main_strategy.js','trifecta_strategy.js',
  'insurance_strategy.js','three_way_engine.js'];
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
if(!root.includes(boot))throw Error('morning picker boot entry missing');
const source=root.replace(boot,'window.__morningPicks={state,predict,selectedRaceCandidates:computeMorningRaceCandidates,specialForecastRaceCandidates:computeMorningSpecialRaceCandidates,add:function(k,v){instantTrackDetails[k]=v;}};');
const items=new Map(),store={getItem:k=>items.get(k)||null,setItem:(k,v)=>items.set(k,String(v)),removeItem:k=>items.delete(k)};
const document={getElementById:()=>({innerHTML:''}),addEventListener:()=>{},querySelector:()=>null,querySelectorAll:()=>[],visibilityState:'hidden'};
const window={addEventListener:()=>{},innerWidth:390,location:{href:'https://morning.invalid/'},navigator:{standalone:false},localStorage:store,document};
const ctx={window,document,localStorage:store,sessionStorage:store,console,
 URL,URLSearchParams,Date,Math,JSON,Intl,Number,String,Array,Object,Set,Map,
 Promise,RegExp,parseInt,parseFloat,isFinite,encodeURIComponent,decodeURIComponent,
 navigator:window.navigator,location:window.location,setTimeout:()=>0,
 clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{}};
vm.createContext(ctx);
for(const name of betModules)vm.runInContext(fs.readFileSync('arvexq/ui/static/betting/'+name,'utf8'),
  ctx,{timeout:12000,filename:name});
vm.runInContext(laneModule,ctx,{timeout:12000,filename:'ticket_lane_classifier.js'});
vm.runInContext(selectionModule,ctx,{timeout:12000,filename:'selection_cut.js'});
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
const selectionById=new Map(selected.map(x=>[String(x.race.id),x.selection]));
const specials=new Set(special.map(x=>String(x.id)));
const fixedAt=now.toISOString();
const status={morningPickVersion:'v1',morningPickFixedAt:fixedAt,morningPickScope:rows.length};
for(const r of rows){
  const decision={
    version:'v1',fixedAt,scope:rows.length,
    selected:selectionById.has(String(r.id)),
    selectedScore:Number(selectionById.get(String(r.id))?.score)||0,
    special:specials.has(String(r.id)),assessed:assessed.some(z=>String(z.id)===String(r.id)),
    primaryType:String(selectionById.get(String(r.id))?.primaryType||''),
    types:Array.isArray(selectionById.get(String(r.id))?.types)?selectionById.get(String(r.id)).types.slice():[],
    selectionReason:String(selectionById.get(String(r.id))?.reason||''),
    selectionModelVersion:String(selectionById.get(String(r.id))?.modelVersion||''),
  };
  Object.assign(r,status,{
    morningSelected:decision.selected,
    morningSelectedScore:decision.selectedScore,
    morningSpecial:decision.special,morningAssessed:decision.assessed,
    morningPrimaryType:decision.primaryType,morningSelectedTypes:decision.types,
    morningSelectionReason:decision.selectionReason,
  });
  // A public D1 summary upsert currently whitelists unknown top-level keys.
  // Put the manifest inside the existing structured summary metadata as well.
  r.volatility={...(r.volatility||{}),morningPicks:decision};
  r.environmentMeta={...(r.environmentMeta||{}),morningPicks:decision};
}
for(const d of payload.details||[]){
  const r=rows.find(x=>String(x.id)===String(d.id));
  if(r){
    for(const key of ['morningPickVersion','morningPickFixedAt','morningPickScope','morningSelected','morningSelectedScore','morningSpecial','morningAssessed','morningPrimaryType','morningSelectedTypes','morningSelectionReason'])d[key]=r[key];
    d.volatility={...(d.volatility||{}),morningPicks:r.volatility.morningPicks};
    d.environmentMeta={...(d.environmentMeta||{}),morningPicks:r.volatility.morningPicks};
  }
}
let markCount=0,markErrors=0;
for(const detail of payload.details||[]){
  if(!detail||!detail.id||detail.morningMarkSnapshot)continue;
  try{
    const p=model.predict(detail);
    const active=(detail.horses||[]).filter(h=>h&&Number(h.horseNumber)>0&&!h.scratched&&!h.withdrawn&&!/取消|除外|欠場/.test(String(h.status||'')));
    const marks=(p.rows||[]).filter(z=>z&&z.horse&&Number(z.horse.horseNumber)>0)
      .map(z=>({horseNumber:Number(z.horse.horseNumber),mark:String(z.predMark||''),singleWinSuitable:!!z.singleWinSuitable}));
    if(active.length<3||marks.length<active.length||marks.filter(x=>!!x.mark).length<3)continue;
    detail.morningMarkSnapshot={version:'arvexq-morning-marks-v1',raceId:String(detail.id),
      raceDate:String(detail.date||day),fixedAt,source:'morning-full-prefetch-original',
      horses:marks,originalCondition:String(detail.condition||''),
      initialOfficialCourseCondition:detail.officialCourseCondition||null};
    markCount++;
  }catch(e){markErrors++;console.error('MORNING_MARKS_NOT_READY',String(detail.id),String(e&&e.message||e))}
}
fs.writeFileSync(output,JSON.stringify(payload));
console.log('MORNING_PICKS_FROZEN','date='+day,'races='+rows.length,
  'selected='+selectionById.size,'assessed='+assessed.length,'special='+specials.size,'marks='+markCount,'markErrors='+markErrors,'fixedAt='+fixedAt);
