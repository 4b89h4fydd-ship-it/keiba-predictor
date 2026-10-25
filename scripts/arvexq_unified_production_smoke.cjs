#!/usr/bin/env node
'use strict';
/** Production post-write test: exact real D1 receipt to real PWA mark adapter.
 *  Never substitutes fixture runners or guesses a market selection.
 */
const fs=require('node:fs'),vm=require('node:vm');
const report=JSON.parse(fs.readFileSync(process.argv[2]||'unified-preoff-report.json','utf8'));
const pub=report.publishedIds||[];
if(!pub.length){
  if(report.scored>0){
    console.error('UNIFIED_PROD_INCOMPLETE',JSON.stringify({scored:report.scored,published:0,
      failures:(report.missingOrSkipped||[]).slice(0,3)}));process.exit(1);
  }
  console.log('UNIFIED_PROD_NO_NEW_CARDS',{
    foundCards:report.foundCards,eligibleUpcoming:report.eligibleUpcoming});
  process.exit(0);
}
const ctx={};
for(const path of ['arvexq/ui/static/forecast/prediction.js',
                   'arvexq/ui/static/forecast/marks.js',
                   'arvexq/ui/static/forecast/tickets.js']){
  vm.runInNewContext(fs.readFileSync(path,'utf8'),ctx,{filename:path});
}
async function getJson(url){
  const res=await fetch(url,{signal:AbortSignal.timeout(25000),
                            headers:{'cache-control':'no-cache'}});
  if(!res.ok)throw Error('HTTP '+res.status);
  return res.json();
}
(async()=>{
 let checked=0,marks=0;
 for(const id of pub){
   const body=await getJson('https://kraiz-api.4b89h4fydd.workers.dev/api/race/'+
     encodeURIComponent(id)+'?view=display&verify='+Date.now());
   const race=body.detail;
   if(!race||race.id!==id)throw Error('D1 missing '+id);
   const product=race.unifiedForecast;
   if(!product||product.raceId!==id)throw Error('D1 receipt missing '+id);
   const forecast=ctx.ARVEXQProductionPrediction.build(race);
   const rows=forecast.rows.filter(x=>ctx.ARVEXQProductionMarks.visible(x));
   if(rows.length<3||rows.filter(x=>x.predMark==='◎').length!==1||
       ctx.ARVEXQProductionPrediction.current().source!=='arvexq-unified-preoff'){
     throw Error('D1 saved marks but PWA cannot display '+id);
   }
   const ticket=ctx.ARVEXQProductionTickets.build(race,forecast);
   if(!ticket||ticket.researchOnly!==true||!Array.isArray(ticket.items)){
     throw Error('D1 saved marks but PWA ticket origin mismatched '+id);
   }
   checked++;marks+=rows.length;
 }
 const res=await fetch('https://kraizweb1.4b89h4fydd.workers.dev/app-v330.js?verify='+Date.now(),
                       {signal:AbortSignal.timeout(25000),headers:{'cache-control':'no-cache'}});
 const bundle=res.ok?await res.text():'';
 // This script is published separately from the app and verifies new branch.
 const deployed=bundle.includes('arvexq-unified-preoff');
 console.log('UNIFIED_REAL_LIVE_VISIBLE',JSON.stringify({checked,visibleMarkRows:marks,
   oneHonmeiPerRace:true,ticketsSameOrigin:true,deployedBundleContainsUnifiedCode:deployed}));
 if(!deployed)throw Error('production PWA bundle has not yet deployed unified marks');
})().catch(e=>{console.error('UNIFIED_PROD_SMOKE_FAILED',e.message);process.exitCode=1});
