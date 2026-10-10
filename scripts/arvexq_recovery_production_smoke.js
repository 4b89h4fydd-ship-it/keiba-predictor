/* Real production rosters, independent odds, saved diagnoses and outage recovery. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const {chromium,webkit,devices}=require('playwright');
const directory='arvexq/ui/static/saved-snapshots';
const day=process.env.ARVEXQ_AUDIT_DATE||fs.readdirSync(directory).filter(f=>/^\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort().at(-1).slice(0,10);
const manifest=JSON.parse(fs.readFileSync(path.join(directory,day+'.json')));
const cards=JSON.parse(fs.readFileSync('arvexq/ui/static/racecards/'+day+'.json')).races;
const base=process.env.ARVEXQ_BASE_URL||'https://kraizweb1.4b89h4fydd.workers.dev';
const type=process.env.ARVEXQ_BROWSER==='webkit'?webkit:chromium;
const marker=fs.readFileSync('arvexq/ui/static/index.html','utf8').match(/var tag="([^"]+)"/)[1];
const records=Object.entries(manifest.races).map(([id,ref])=>{
  const e=JSON.parse(fs.readFileSync(path.join(directory,ref.file)));
  return JSON.parse(zlib.gunzipSync(Buffer.from(e.gzipBase64,'base64')));
});
const chosen=process.env.ARVEXQ_BROWSER==='webkit'?
  ['京都','東京','佐賀','帯広ば','高知'].map(track=>records.find(r=>r.track===track&&r.raceNumber===(track==='高知'?3:9))).filter(Boolean):records;
(async()=>{
  const browser=await type.launch({headless:true,...(process.env.CHROMIUM_PATH&&type===chromium?{executablePath:process.env.CHROMIUM_PATH}:{})});
  const context=await browser.newContext({...devices['iPhone 15 Pro'],locale:'ja-JP'});
  await context.addInitScript(key=>localStorage.setItem(key,'1'),marker);
  let cursor=0;
  async function check(page,r){
    const errors=[];const onerror=e=>errors.push(String(e));page.on('pageerror',onerror);
    await page.goto(base+'/race?date='+day+'&race_id='+encodeURIComponent(r.id)+'&recovery='+Date.now(),{waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForFunction(()=>{const note=document.querySelector('.rc-mark-freeze-note');return note&&/保存予想原本|固定済み/.test(note.textContent)},null,{timeout:30000});
    const roster=cards.find(c=>c.id===r.id)||r;
    await page.waitForFunction(count=>document.querySelectorAll('.racecard-row').length===count,roster.horses.length,{timeout:20000});
    assert.equal(await page.locator('.racecard-row').count(),roster.horses.length,'complete official roster '+r.id);
    const names=await page.locator('.rc-horse-name').allTextContents();
    roster.horses.forEach(h=>assert.ok(names.includes(h.name),'runner identity missing '+r.id+' '+h.name));
    await page.waitForFunction(()=>document.querySelectorAll('.diagnosis-merged-row').length===document.querySelectorAll('.racecard-row').length,null,{timeout:20000});
    const diagnosis=page.locator('details.card').filter({has:page.locator('.diagnosis-merged-list')});
    await diagnosis.locator('summary').click();
    assert.equal(await diagnosis.locator('.diagnosis-merged-row').count(),roster.horses.length);
    // Only factual acquired odds or an explicit missing status can appear.
    const odds=await page.locator('.rc-odds .odd').allTextContents();
    odds.forEach(x=>assert.ok(/^(?:\d+\.\d|未取得|取消)$/.test(x),'invalid odds text '+x));
    assert.ok(odds.some(x=>/^\d/.test(x)),'no acquired odds for '+r.id);
    const red=await page.evaluate(()=>Array.from(document.querySelectorAll('.rc-odds .odd.single')).map(x=>({value:Number(x.textContent),color:getComputedStyle(x).color})));
    red.forEach(x=>{assert.ok(x.value>0&&x.value<10);const c=x.color.match(/\d+/g).map(Number);assert.ok(c[0]>c[1]*1.25&&c[0]>c[2]*1.15,'single digit odds must be red')});
    assert.ok((await page.locator('.rc-ai-mark[data-ai-mark="◎"]').count())<=1);
    assert.equal(errors.length,0,'runtime errors '+errors.join(';'));
    page.off('pageerror',onerror);
    console.log('PRODUCTION_RECOVERY_PASS '+r.id+' horses='+r.horses.length+' diagnosis='+r.horses.length);
  }
  async function worker(){const page=await context.newPage();try{while(cursor<chosen.length)await check(page,chosen[cursor++])}finally{await page.close()}}
  try{
    await Promise.all([worker(),worker(),worker()]);
    const r=chosen.find(r=>r.circuit==='地方')||chosen[0],page=await context.newPage();
    await page.route('https://kraiz-api.4b89h4fydd.workers.dev/**',route=>route.abort());
    const initialResponse=page.waitForResponse(res=>res.url().includes('/api/live-odds/'));
    await check(page,r);
    assert.equal((await initialResponse).status(),200,'independent initial source request');
    await page.waitForTimeout(250);
    const before=await page.locator('.rc-ai-mark').evaluateAll(xs=>xs.map(x=>x.getAttribute('data-ai-mark')));
    const response=page.waitForResponse(res=>res.url().includes('/api/live-odds/')&&res.url().includes('force=1'));
    await page.locator('[data-action="odds-update"]').click();
    assert.equal((await response).status(),200,'manual source update with D1 API aborted');
    await page.waitForTimeout(300);
    assert.deepEqual(await page.locator('.rc-ai-mark').evaluateAll(xs=>xs.map(x=>x.getAttribute('data-ai-mark'))),before,'odds refresh must not rewrite saved marks');
    await page.close();
    const fresh=await browser.newContext({...devices['iPhone 15 Pro'],locale:'ja-JP'});
    await fresh.addInitScript(key=>localStorage.setItem(key,'1'),marker);
    await fresh.route('https://kraiz-api.4b89h4fydd.workers.dev/**',route=>route.abort());
    const home=await fresh.newPage();
    await home.goto(base+'/?date='+day+'&offline-home='+Date.now(),{waitUntil:'domcontentloaded'});
    for(const [section,tracks] of [['central',['京都','東京']],['local',['佐賀','帯広ば','高知']]]){
      await home.goto(base+'/?date='+day+'&offline-home='+Date.now(),{waitUntil:'domcontentloaded'});
      await home.locator('[data-home-page="'+section+'"]').click();
      for(const track of tracks)
        await home.locator('[data-track="'+track+'"]').first().waitFor({state:'visible',timeout:30000});
    }
    await fresh.close();
    console.log('PRODUCTION_FRESH_HOME_API_OUTAGE_ALL_VENUES_PASS');
    console.log('PRODUCTION_API_OUTAGE_MANUAL_ODDS_SAVED_MARKS_PASS '+process.env.ARVEXQ_BROWSER+' date='+day+' checked='+chosen.length);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
