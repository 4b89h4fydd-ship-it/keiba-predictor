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
  for(const name of ['deduplicate','temporal','view']) await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/history/'+name+'.js','utf8')});

  for(const name of fs.readdirSync('arvexq/ui/static/forecast').filter(n=>n.endsWith('.js')))await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/forecast/'+name,'utf8')});
  await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/research/diagnosis_view.js','utf8')});await page.addScriptTag({content:fs.readFileSync('arvexq/ui/static/research/live_odds.js','utf8')});await page.addScriptTag({content:code});
  await page.evaluate(d=>{revisionTest.state.date=d.date;revisionTest.state.circuit=d.circuit;revisionTest.state.races=[d]},originalDetail);
  await page.evaluate(id=>revisionTest.openRace(id),detail.id);
  // v349: the entry panel is the integrated entry table; the retired
  // .racecard-row list survives only in the error-fallback panel.
  await page.waitForFunction(()=>document.querySelectorAll('.arv-entry-table tbody tr').length===6);
  // This fixture is retrospective, uncalibrated and explicitly production-ineligible.
  // Existing retrospective reference marks must be labelled and never become actionable tickets.
  assert.equal(detail.forecastRevisions[0].analysisType,'retrospective');
  assert.equal(detail.forecastRevisions[0].productionEligible,false);
  assert.equal(await page.locator('.arv-marks-mark[data-ai-mark="◎"]').count(),1);
  assert.equal(await page.evaluate(()=>window.ARVEXQProductionPrediction.current().source),'learned-revision-retrospective');
  // v349: the compact marks frame (with the retrospective label) is
  // appended under the non-entry panels. v363: the analysis panel is
  // tag-switched; the diagnosis list and the pace section live behind
  // their own tags.
  await page.locator('[data-panel="pace"]').click();
  await page.waitForSelector('.da-tags');
  assert.match(await page.locator('#section-aimarks').innerText(),/事後再分析の参考印/);
  assert.equal(await page.locator('#section-aimarks').count(),1);
  await page.locator('[data-analysis-tag="diagnosis"]').click();
  await page.waitForFunction(()=>document.querySelectorAll('.diagnosis-merged-row').length===6);
  await page.locator('[data-analysis-tag="paceview"]').click();
  await page.waitForSelector('#section-pace');
  await page.locator('[data-panel="entry"]').click();
  await page.waitForSelector('.arv-entry-table');
  assert.equal(await page.locator('.arv-entry-table .bet-item').count(),0);
  assert.equal(await page.evaluate(()=>JSON.stringify(revisionTest.state.race.preRaceBet)),JSON.stringify(detail.preRaceBet));
  await page.locator('[data-panel="pace"]').click();
  await page.waitForSelector('.da-tags');
  await page.locator('[data-panel="entry"]').click();
  await page.waitForSelector('.arv-entry-table');
  assert.equal(await page.evaluate(()=>JSON.stringify(revisionTest.state.race.preRacePrediction)),before);
  assert.equal(errors.length,0,errors.join(';'));
  console.log('SAVED_FORECAST_REVISION_MOBILE_BROWSER_PASS');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
