// Offline browser regression: no public APIs or production caches are used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const date = '2026-10-07', id = 'nar-'+date+'-大井-11';
const base = {id,date,circuit:'地方',track:'大井',raceNumber:11,startTime:'20:05',
  title:'第２８回 ジャパンダートクラシックJpnＩ３歳選定馬重賞',distance:2000,weather:'曇',condition:'良'};
const detail = process.env.ARVEXQ_TEST_DETAIL_PATH ? JSON.parse(fs.readFileSync(process.env.ARVEXQ_TEST_DETAIL_PATH)).detail :
  {...base,fieldSize:2,horses:[1,2].map(no=>({horseNumber:no,frameNumber:no,name:'テスト馬'+no,jockey:'騎手',sex:'牡',age:3,carriedWeight:57,bodyWeight:480,winOdds:no*2,popularity:no,recentRaces:Array.from({length:5},(_,i)=>({date:'2026-09-0'+(i+1),track:'大井',distance:1800,fieldSize:12,finish:no,timeSeconds:112,cornerPositions:[no,no,no,no],condition:'良'}))}))};
const source = fs.readFileSync(path.join(root,'arvexq/ui/static/app.js'),'utf8');
const boot = 'installNavigation();installEdgeBack();installPwaCache();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);';
assert.ok(source.includes(boot));
const instrumented = source.replace(boot, `
  ensureAutoOdds=function(){};scheduleResultRefresh=function(){};scheduleRaceBiasRefresh=function(){};
  scheduleVenueTrendRefresh=function(){};
  window.testDetail={state,openRace,render,detailState,trace:raceDetailTrace,instantTrackDetails,
    saveDetailCache,loadDetailCache,detailCacheKey,raceHeadCountText,
    failPrediction:function(){predict=function(){throw Error('diagnosis test failure')}},
    failDiagnosisPanel:function(){diagnosisPanel=function(){throw Error('diagnosis panel failure')}},
    prediction:function(){return state.pred}};
`);
(async()=>{
 const launch={args:['--no-sandbox'],headless:true};
 if(process.env.CHROMIUM_PATH)launch.executablePath=process.env.CHROMIUM_PATH;
 else if(fs.existsSync('/usr/bin/chromium'))launch.executablePath='/usr/bin/chromium';
 const browser=await chromium.launch(launch);
 async function setup(response,extras={}){
  const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const requests=[];
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.pathname.startsWith('/api/racecard/')&&extras.card){await extras.card(route);return}
   if(url.pathname.startsWith('/api/odds/')&&extras.odds){await extras.odds(route);return}
   if(url.pathname.startsWith('/api/race/')){requests.push({url:url.href,at:Date.now()});await response(route,requests.length);return}
   await route.fulfill({status:200,contentType:'text/html',body:'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div></body></html>'});
  });
  await page.goto('https://arvexq.test/');
  await page.addStyleTag({content:fs.readFileSync(path.join(root,'arvexq/ui/static/styles.css'),'utf8')});
  await page.addScriptTag({content:instrumented});
  await page.evaluate(row=>{testDetail.state.races=[row];testDetail.state.date=row.date;testDetail.state.track=row.track},base);
  return {page,requests}
 }
 let recovered=false;
 let t=await setup(async route=>recovered?route.fulfill({json:{ok:true,race_id:id,detail,summary:base,odds:[]}}):route.fulfill({status:503,json:{error:'test outage'}}));
 await t.page.evaluate(id=>{localStorage.setItem('unrelated-cache','keep');testDetail.openRace(id)},id);
 await t.page.waitForSelector('.smart-race-title-stack h1');
 assert.equal(await t.page.locator('.smart-race-title-stack h1').textContent(),base.title);
 assert.ok((await t.page.locator('.smart-race-meta').textContent()).includes('2000m'));
 assert.ok((await t.page.locator('.smart-race-meta').textContent()).includes('頭数取得中'));
 assert.equal(await t.page.locator('.race-nav-v230-btn').count(),4);
 await t.page.waitForFunction(id=>testDetail.detailState(id).entry==='error'&&!testDetail.detailState(id).busy,id);
 assert.equal(t.requests.length,3);assert.ok(t.requests[1].at-t.requests[0].at>=900);assert.ok(t.requests[2].at-t.requests[1].at>=1900);
 assert.equal(await t.page.locator('.notice,.smart-loading').count(),0);
 recovered=true;await t.page.locator('[data-detail-retry]').first().click();await t.page.waitForSelector('.racecard-row');
 assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);
 assert.equal(await t.page.evaluate(()=>localStorage.getItem('unrelated-cache')),'keep');
 assert.ok(t.requests.every(x=>decodeURIComponent(new URL(x.url).pathname)==='/api/race/'+id));
 await t.page.waitForFunction(()=>testDetail.prediction()!=null);
 await t.page.locator('[data-panel="diagnosis"]').click();await t.page.waitForSelector('.diagnosis-merged-row');
 assert.equal(await t.page.locator('.diagnosis-merged-row').count(),detail.horses.length);
 await t.page.locator('.diagnosis-horse-main[data-horse-open="2"]').click();await t.page.waitForSelector('.horse-modal-body .recent');
 assert.equal(await t.page.locator('.horse-modal-body .recent').count(),Math.min(5,(detail.horses.find(h=>h.horseNumber===2).recentRaces||[]).length));
 await t.page.locator('.horse-modal-close').click();
 await t.page.locator('[data-panel="entry"]').click();
 const rects=await t.page.locator('.race-nav-v230-top .race-nav-v230-btn').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return [r.width,r.height,s.padding,s.fontSize,s.lineHeight,s.boxSizing]}));assert.deepEqual(rects[0],rects[1]);
 const layout=await t.page.evaluate(()=>{const h=document.querySelector('.smart-race-title-stack h1'),time=document.querySelector('.smart-race-result-side');return {title:h.getBoundingClientRect().toJSON(),time:time.getBoundingClientRect().toJSON(),lineHeight:parseFloat(getComputedStyle(h).lineHeight),clamp:getComputedStyle(h).webkitLineClamp}});
 assert.equal(layout.clamp,'2');assert.ok(layout.title.height<=layout.lineHeight*2+1);assert.ok(layout.title.bottom<=layout.time.top+1||layout.title.right<=layout.time.left+1);
 console.log('503 x3 -> summary stays visible -> fresh retry recovers roster, diagnosis; equal tabs and 2-line title PASS');
 await t.page.close();
 const card={...base,fieldSize:detail.horses.length,horses:detail.horses.map(h=>({horseNumber:h.horseNumber,name:h.name,frameNumber:h.frameNumber,jockey:h.jockey,sex:h.sex,age:h.age,carriedWeight:h.carriedWeight}))};
 t=await setup(route=>route.fulfill({status:503,body:'full detail outage'}),{
  card:route=>route.fulfill({json:{ok:true,race_id:id,detail:card,entry_state:'loaded'}}),
  odds:route=>route.fulfill({json:{ok:true,race_id:id,odds:detail.horses.map(h=>({horse_no:h.horseNumber,win_odds:h.winOdds,popularity:h.popularity}))}})
 });
 await t.page.evaluate(id=>testDetail.openRace(id),id);await t.page.waitForSelector('.racecard-row');
 assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);
 await t.page.waitForFunction(id=>testDetail.detailState(id).odds==='loaded',id);
 await t.page.waitForFunction(id=>!!testDetail.detailState(id).error&&!testDetail.detailState(id).busy,id);
 assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);
 assert.equal(await t.page.locator('.notice,.smart-loading').count(),0);
 await t.page.locator('[data-panel="diagnosis"]').click();assert.equal(await t.page.locator('[data-section-state="error"]').count(),1);
 await t.page.locator('[data-panel="entry"]').click();assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);
 console.log('Independent compact roster + odds survive full detail outage PASS');await t.page.close();
 t=await setup(route=>route.fulfill({status:503,body:'outage'}));
 await t.page.evaluate(({id,detail})=>{localStorage.setItem(testDetail.detailCacheKey(id),JSON.stringify({ts:Date.now()-3600000,row:detail}));testDetail.openRace(id)}, {id,detail});
 await t.page.waitForSelector('.racecard-row');assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);
 await t.page.waitForFunction(id=>!!testDetail.detailState(id).error&&!testDetail.detailState(id).busy,id);
 assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);console.log('Stale roster survives refresh outage PASS');await t.page.close();
 const thin={...detail,horses:detail.horses.map(h=>({...h,winOdds:null,popularity:null,recentRaces:[],allPastRuns:[]})),preparedMeta:{}};
 t=await setup(route=>route.fulfill({json:{ok:true,detail:thin,summary:base,odds:[]}}));
 await t.page.evaluate(id=>{testDetail.failPrediction();testDetail.openRace(id)},id);await t.page.waitForSelector('.racecard-row');
 await t.page.waitForFunction(id=>testDetail.detailState(id).diagnosis==='error',id);
 await t.page.locator('[data-panel="diagnosis"]').click();assert.equal(await t.page.locator('[data-section-state="error"]').count(),1);
 await t.page.locator('[data-panel="entry"]').click();assert.equal(await t.page.locator('.racecard-row').count(),thin.horses.length);
 assert.equal(await t.page.locator('.notice').count(),0);console.log('Missing odds/history and diagnosis exception cannot hide roster PASS');await t.page.close();
 t=await setup(route=>route.fulfill({json:{ok:true,detail,summary:base,odds:'invalid',analysis_ready:true}}));
 await t.page.evaluate(id=>testDetail.openRace(id),id);await t.page.waitForSelector('.racecard-row');await t.page.waitForFunction(()=>testDetail.prediction()!=null);
 await t.page.evaluate(()=>testDetail.failDiagnosisPanel());await t.page.locator('[data-panel="diagnosis"]').click();
 assert.equal(await t.page.locator('[data-section-state="error"]').count(),1);await t.page.locator('[data-panel="entry"]').click();
 assert.equal(await t.page.locator('.racecard-row').count(),detail.horses.length);console.log('Malformed odds array and failed diagnosis presenter isolated PASS');await t.page.close();
 t=await setup(route=>route.fulfill({json:{ok:true,detail:{...base,fieldSize:0,horses:[]},summary:base}}));
 await t.page.evaluate(id=>testDetail.openRace(id),id);await t.page.waitForFunction(id=>testDetail.detailState(id).entry==='empty',id);
 assert.ok((await t.page.locator('.smart-race-meta').textContent()).includes('0頭'));console.log('Explicit confirmed zero entries only -> empty PASS');await t.page.close();
 t=await setup(route=>route.fulfill({json:{ok:true,detail:{...detail,id:'wrong-id'}}}));await t.page.evaluate(id=>testDetail.openRace(id),id);
 await t.page.waitForFunction(id=>!!testDetail.detailState(id).error&&!testDetail.detailState(id).busy,id);
 assert.ok(await t.page.evaluate(()=>testDetail.trace.some(x=>(x.message||'').includes('id mismatch'))));assert.equal(await t.page.locator('.racecard-row').count(),0);console.log('Mismatched race IDs rejected with trace PASS');await t.page.close();
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
