#!/usr/bin/env node
'use strict';
/** Read-only date-scoped production audit of available real forecast marks. */
const vm=require('node:vm'),fs=require('node:fs');
const BASE='https://kraiz-api.4b89h4fydd.workers.dev';
const DATE='2026-10-25';
const ctx={ARVEXQProductionTickets:{build:()=>null,validatedReceipt:()=>null}};
vm.runInNewContext(fs.readFileSync('arvexq/ui/static/forecast/prediction.js','utf8'),ctx);
vm.runInNewContext(fs.readFileSync('arvexq/ui/static/forecast/marks.js','utf8'),ctx);
async function get(url){
  const res=await fetch(url,{signal:AbortSignal.timeout(15000),headers:{'cache-control':'no-cache'}});
  if(!res.ok)throw Error('HTTP '+res.status);
  return res.json();
}
async function main(){
  const day=await get(BASE+'/api/day?date='+DATE+'&details=0&t='+Date.now());
  let rows=(day.races||[]).filter(r=>r&&r.id&&!String(r.id).includes('帯広')
    &&r.track!=='帯広'&&r.track!=='帯広ば');
  const now=15*60+10;
  rows=rows.filter(r=>{const t=String(r.startTime||'');const m=/^(\d\d):(\d\d)/.exec(t);
    return m&&Number(m[1])*60+Number(m[2])>=now;});
  const central=rows.filter(r=>r.circuit==='中央').slice(0,7);
  const local=rows.filter(r=>r.circuit==='地方').slice(0,8);
  const selected=[...central,...local];
  console.log('TODAY_LIVE_MARKS_SAMPLE',JSON.stringify({
    dayRaces:(day.races||[]).length,remainingNonBanei:rows.length,
    sampledCentral:central.length,sampledLocal:local.length,
  }));
  let issues=[],ready=0,visible=0;
  for(const r of selected){
    try {
      const body=await get(BASE+'/api/race/'+encodeURIComponent(r.id)+'?view=display&t='+Date.now());
      const detail=body.detail;
      if(!detail||detail.id!==r.id)throw Error('no full original detail');
      const result=ctx.ARVEXQProductionPrediction.build(detail);
      const count=result.rows.filter(x=>ctx.ARVEXQProductionMarks.visible(x)).length;
      const current=ctx.ARVEXQProductionPrediction.current();
      if(detail.predictionStatus==='ready')ready++;
      if(count)visible++;
      console.log('RACE_LIVE_MARKS',JSON.stringify({
        raceId:r.id,forecastStatus:detail.predictionStatus||'missing',
        forecastModelVersion:detail.predictionModelVersion||null,
        source:current.source||null,storedMarks:(detail.predictionMarks||[]).length,
        storedMarkKeys:Object.keys((detail.predictionMarks||[])[0]||{}),
        shownMarks:count,fieldSize:detail.horses?.length||0
      }));
      if(!count)issues.push(r.id);
    } catch(e) {
      issues.push(r.id);console.log('RACE_LIVE_MARKS_ERROR',JSON.stringify({raceId:r.id,error:String(e.message).slice(0,140)}));
    }
  }
  console.log('TODAY_LIVE_MARKS_AUDIT',JSON.stringify({
    sampled:selected.length,readyStored:ready,visibleWithMarks:visible,
    noVisibleMarks:issues.length,strictPreoffValidation:false
  }));
}
main().catch(e=>{console.error('TODAY_LIVE_MARKS_AUDIT_FAILED',String(e.message));process.exitCode=1});
