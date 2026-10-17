'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require(process.env.ARVEXQ_PLAYWRIGHT_MODULE||'playwright');
const detail=JSON.parse(fs.readFileSync('tests/fixtures/forecast_revision_transport.json')).detail;
const before=JSON.stringify(detail.preRacePrediction);
const originalDetail=structuredClone(detail);delete originalDetail.forecastRevisions;delete originalDetail.currentForecastRevisionId;
const source=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const boot='installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
assert(source.includes(boot));
const code=source.replace(boot,`ensureAutoOdds=function(){};scheduleResultRefresh=function(){};scheduleRaceBiasRefresh=function(){};scheduleVenueTrendRefresh=function(){};window.revisionTest={state,openRace};`);
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.route('**/*',route=>{
   if(route.request().url().includes('/api/forecast-revisions/'))return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,raceId:detail.id,forecastRevisions:detail.forecastRevisions,currentForecastRevisionId:detail.currentForecastRevisionId})});
   if(route.request().url().includes('/api/live-odds/'))return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,raceId:detail.id,horses:[]})});
   if(route.request().url().includes('/api/race/'))return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,detail:originalDetail})});
   return route.fulfill({status:200,contentType:'text/html',body:'<html><body><div id="app"></div></body></html>'});
  });
  await page.goto('https://arvexq.test/');
  for(const name of fs.readdirSync('arvexq/ui/static/forecast').filter(n=>n.endsWith('.js')))await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/forecast/'+name,'utf8')});
  await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/research/diagnosis_view.js','utf8')});await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/research/live_odds.js','utf8')});await page.addScriptTag({content:code});
  await page.evaluate(d=>{revisionTest.state.date=d.date;revisionTest.state.circuit=d.circuit;revisionTest.state.races=[d]},originalDetail);
  await page.evaluate(id=>revisionTest.openRace(id),detail.id);
  await page.waitForFunction(()=>document.querySelectorAll('.racecard-row').length===6);
  assert.equal(await page.locator('.rc-ai-mark[data-ai-mark="◎"]').count(),0);
  for(const id of ['section-prediction','section-aimarks','section-bets'])assert.equal(await page.locator('#'+id).count(),1);
  assert.equal(await page.locator('#section-aimarks .ai-mark-list').innerText(),'');
  assert.equal(await page.locator('#section-bets .ai-bet-box').innerText(),'');
  assert.equal(await page.locator('.diagnosis-merged-row').count(),6);
  assert.equal(await page.evaluate(()=>JSON.stringify(revisionTest.state.race.preRacePrediction)),before);
  assert.equal(errors.length,0,errors.join(';'));
  console.log('SAVED_FORECAST_REVISION_MOBILE_BROWSER_PASS');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
