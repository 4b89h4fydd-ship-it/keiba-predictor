/* Read-only real production D1 -> iPhone Safari Stage64 display verification.
 * Uses the original /api/race endpoint and approved /race page only.
 */
'use strict';
const assert=require('node:assert/strict');
const {webkit,devices}=require('playwright');
const web=process.env.ARVEXQ_BASE_URL||'https://kraizweb1.4b89h4fydd.workers.dev';
const api='https://kraiz-api.4b89h4fydd.workers.dev';
const ids=(process.env.ARVEXQ_STAGE64_AUDIT_RACES||
  'nar-2026-10-24-佐賀-12,nar-2026-10-24-高知-12').split(',').filter(Boolean);

async function read(id){
 const response=await fetch(api+'/api/race/'+encodeURIComponent(id)+'?view=display&verify='+Date.now(),{
   headers:{accept:'application/json','cache-control':'no-cache'},
   signal:AbortSignal.timeout(25000)});
 assert.equal(response.status,200,'D1 detail HTTP '+response.status+' for '+id);
 const body=await response.json();
 assert.equal(body.ok,true,'D1 detail ok '+id);
 assert.equal(String(body.race_id),id,'D1 response identity');
 const d=body.detail;
 assert(d&&d.id===id,'D1 detail identity');
 return d;
}
function ready(d){
 const p=d&&d.prediction;
 return d&&d.predictionStatus==='ready'&&
   d.predictionModelVersion==='arvexq-stage64-product-v1'&&
   p&&p.modelVersion==='arvexq-stage64-product-v1'&&
   p.predictionStatus==='ready'&&p.raceId===d.id&&p.date===d.date&&
   Array.isArray(d.predictionMarks)&&d.predictionMarks.length===5&&
   Array.isArray(d.recommendedBets)&&d.recommendedBets.length>0;
}
(async()=>{
 const responses=[];
 for(const id of ids){
   try{
     const d=await read(id);
     responses.push({id,detail:d,status:d.predictionStatus,marks:(d.predictionMarks||[]).length});
   }catch(e){responses.push({id,error:String(e)});}
 }
 const eligible=responses.filter(x=>ready(x.detail));
 console.log('STAGE64_D1_REAL_READBACK',JSON.stringify(responses.map(x=>({
   raceId:x.id,status:x.status||null,marks:x.marks||0,error:x.error||null
 }))));
 assert(eligible.length>0,'no verified pre-off Stage64 D1 detail available: '+JSON.stringify(responses.map(x=>({
   id:x.id,status:x.status,error:x.error,marks:x.marks
 }))));
 const browser=await webkit.launch({headless:true});
 try{
  for(const item of eligible){
    const d=item.detail, page=await browser.newPage({...devices['iPhone 15 Pro'],locale:'ja-JP'});
    try{
      await page.goto(web+'/race?date='+encodeURIComponent(d.date)+'&race_id='+
        encodeURIComponent(d.id)+'&stage64-check='+Date.now(),{
         waitUntil:'domcontentloaded',timeout:40000});
      await page.locator('.racecard-row').first().waitFor({state:'visible',timeout:30000});
      await page.waitForFunction(()=>{
        return [...document.querySelectorAll('.rc-ai-mark')].some(x=>x.getAttribute('data-ai-mark')==='◎');
      },null,{timeout:25000});
      const rendered=await page.locator('.racecard-row').evaluateAll(rows=>rows.map(r=>({
        no:Number(r.querySelector('[data-horse-open]')?.getAttribute('data-horse-open')||0),
        mark:r.querySelector('.rc-ai-mark')?.getAttribute('data-ai-mark')||''
      })));
      for(const saved of d.predictionMarks){
        assert(rendered.some(x=>x.no===Number(saved.horseNumber)&&x.mark===saved.mark),
          'iPhone saved mark missing '+d.id+' '+saved.horseNumber+' '+saved.mark);
      }
      await page.locator('[data-panel="pace"]').first().click();
      await page.locator('#section-pace').waitFor({state:'visible',timeout:15000});
      assert.match(await page.locator('#section-pace').innerText(),/AI展開予想/);
      await page.locator('[data-panel="bets"]').first().click();
      await page.locator('.bet-detail-page-shell').waitFor({state:'visible',timeout:15000});
      const tickets=await page.locator('.bet-detail-page-shell .arv-three-ticket').count();
      assert(tickets>=1,'iPhone stored recommended bets missing '+d.id);
      console.log('STAGE64_PRODUCTION_IPHONE_PASS',JSON.stringify({
        id:d.id,stage64Model:d.prediction.stage64ModelVersion||d.prediction.modelVersion,
        expectedMarks:d.predictionMarks.length,visibleMarks:rendered.filter(x=>x.mark).length,
        betGroups:tickets,forecastVisible:true}));
    }finally{await page.close()}
  }
 }finally{await browser.close()}
})().catch(error=>{console.error(error.stack||String(error));process.exit(1)});
