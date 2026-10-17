/* Real production rosters, independent odds, saved diagnoses and outage recovery. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const {chromium,webkit,devices}=require('playwright');
const verifyHonmeiRoles=require('./arvexq_honmei_dom_contract');
const directory='arvexq/ui/static/saved-snapshots';
const day=process.env.ARVEXQ_AUDIT_DATE||fs.readdirSync(directory).filter(f=>/^\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort().at(-1).slice(0,10);
const manifest=JSON.parse(fs.readFileSync(path.join(directory,day+'.json')));
const cards=JSON.parse(fs.readFileSync('arvexq/ui/static/racecards/'+day+'.json')).races;
const base=process.env.ARVEXQ_BASE_URL||'https://kraizweb1.4b89h4fydd.workers.dev';
const type=process.env.ARVEXQ_BROWSER==='webkit'?webkit:chromium;
const records=Object.entries(manifest.races).map(([id,ref])=>{
  const e=JSON.parse(fs.readFileSync(path.join(directory,ref.file)));
  return JSON.parse(zlib.gunzipSync(Buffer.from(e.gzipBase64,'base64')));
});
// WebKit checks real venues for this date, not a hardcoded historical card list.
const chosen=process.env.ARVEXQ_BROWSER==='webkit'?
  [...new Set(records.map(r=>r.track))].map(track=>records.find(r=>r.track===track)).filter(Boolean):records;
assert.ok(chosen.length>0,'No verified current-day race data available');
(async()=>{
  const browser=await type.launch({headless:true,...(process.env.CHROMIUM_PATH&&type===chromium?{executablePath:process.env.CHROMIUM_PATH}:{})});
  const context=await browser.newContext({...devices['iPhone 15 Pro'],locale:'ja-JP'});
  let cursor=0;
  async function oddsPublished(id){
    try{const res=await fetch(base+'/api/live-odds/'+encodeURIComponent(id),{signal:AbortSignal.timeout(20000)});
      if(!res.ok)return null;
      const body=await res.json();
      if(!body||body.ok!==true)return null;
      return ((body.odds)||[]).some(o=>Number(o&&o.win_odds)>0)}
    catch(e){return null}
  }
  async function check(page,r){
    const errors=[];const onerror=e=>errors.push(e.stack||String(e));page.on('pageerror',onerror);
    await page.goto(base+'/race?date='+day+'&race_id='+encodeURIComponent(r.id)+'&recovery='+Date.now(),{waitUntil:'domcontentloaded',timeout:45000});
    const expectedFrozenMarks=!!(manifest.races[r.id]&&manifest.races[r.id].morningMarks);
    // A race without a recorded pre-off mark must still show its roster.
    // Original acquisition failures remain visible in the independent seal audit.
    try{await page.waitForFunction(({expected})=>{const note=document.querySelector('.rc-mark-freeze-note');return !!(note&&note.textContent.trim()&&(expected?/発走後の再計算印|発走前保存印|保存予想原本|固定済み/.test(note.textContent):true))},{expected:expectedFrozenMarks},{timeout:30000})}catch(e){console.error('RECOVERY_FAILURE '+r.id+' '+errors.join(';')+' '+(await page.locator('body').innerText()).slice(0,2500));throw e}
    if(!expectedFrozenMarks)console.warn('PREOFF_MARKS_NOT_SEALED '+r.id);
    const roster=cards.find(c=>c.id===r.id)||r;
    await page.waitForFunction(count=>document.querySelectorAll('.racecard-row').length===count,roster.horses.length,{timeout:20000});
    assert.equal(await page.locator('.racecard-row').count(),roster.horses.length,'complete official roster '+r.id);
    // .rc-horse-name includes the optional new ◎【単】/◎【軸】 role suffix.
    // Compare the horse-name element alone, not its explanatory mark label.
    const names=await page.locator('.rc-horse-title').allTextContents();
    roster.horses.forEach(h=>assert.ok(names.includes(h.name),'runner identity missing '+r.id+' '+h.name));
    await page.waitForFunction(()=>document.querySelectorAll('.diagnosis-merged-row').length===document.querySelectorAll('.racecard-row').length,null,{timeout:20000});
    const diagnosis=page.locator('details.card').filter({has:page.locator('.diagnosis-merged-list')});
    // The live result refresh can replace this details node while Playwright
    // waits for a stable click; open via DOM on the currently matched node.
    await page.evaluate(()=>{const d=[...document.querySelectorAll('details.card')]
      .find(x=>x.querySelector('.diagnosis-merged-list'));if(d)d.open=true});
    assert.equal(await diagnosis.locator('.diagnosis-merged-row').count(),roster.horses.length);
    // Only factual acquired odds or an explicit missing status can appear.
    let odds=await page.locator('.rc-odds .odd').allTextContents();
    odds.forEach(x=>assert.ok(/^(?:\d+\.\d|未取得|取消)$/.test(x),'invalid odds text '+x));
    // Before the official source publishes (e.g. NAR overnight) no acquired odds can exist;
    // the roster must then show only the explicit missing status. Once the source has
    // odds the screen must show some acquired value.
    const published=await oddsPublished(r.id);
    if(published===true){
      // Published odds update independently of the base racecard request.
      // Wait for actual DOM values; timeout remains a hard failure, never a fake odd.
      const numericOddsVisible=()=>Array.from(document.querySelectorAll('.rc-odds .odd'))
        .some(el=>/^\d/.test(el.textContent.trim()));
      try {
        await page.waitForFunction(numericOddsVisible,null,{timeout:15000});
      } catch (error) {
        // Published odds may arrive after the page's initial request.
        // Re-query through the existing user-visible refresh control.
        console.warn('ODDS_INITIAL_DISPLAY_DELAY '+r.id+' initial='+JSON.stringify(odds));
        const update=page.locator('[data-action="odds-update"]');
        assert.ok(await update.count(),'odds refresh control missing '+r.id);
        const refreshResponse=page.waitForResponse(res=>
          res.url().includes('/api/live-odds/') && res.url().includes('force=1'),
          {timeout:20000});
        await update.click();
        assert.equal((await refreshResponse).status(),200,'odds source refresh failed '+r.id);
        await page.waitForFunction(numericOddsVisible,null,{timeout:15000});
        console.log('ODDS_MANUAL_RECOVERY_PASS '+r.id);
      }
      odds=await page.locator('.rc-odds .odd').allTextContents();
      assert.ok(odds.some(x=>/^\d/.test(x)),'no acquired odds for '+r.id);
    }
    else if(published===false)console.log('ODDS_NOT_YET_PUBLISHED '+r.id+' shown='+JSON.stringify(Array.from(new Set(odds))));
    else console.log('ODDS_SOURCE_UNAVAILABLE '+r.id+' shown='+JSON.stringify(Array.from(new Set(odds))));
    const red=await page.evaluate(()=>Array.from(document.querySelectorAll('.rc-odds .odd.single')).map(x=>({value:Number(x.textContent),color:getComputedStyle(x).color})));
    red.forEach(x=>{assert.ok(x.value>0&&x.value<10);const c=x.color.match(/\d+/g).map(Number);assert.ok(c[0]>c[1]*1.25&&c[0]>c[2]*1.15,'single digit odds must be red')});
    const roles=await page.locator('.racecard-row').evaluateAll(rows=>rows.map(row=>({
      mark:row.querySelector('.rc-ai-mark')?.getAttribute('data-ai-mark')||'',
      horseNumber:Number(row.querySelector('[data-horse-open]')?.getAttribute('data-horse-open')||0),
      win:!!row.querySelector('.arv-role-win'),axis:!!row.querySelector('.arv-role-axis')
    })));
    const deployedPolicy=await page.evaluate(()=>window.ARVEXQ_HONMEI_POLICY||'legacy');
    const originalHonmei=(r.preRacePrediction?.horses||[]).filter(h=>h.mark==='◎').map(h=>Number(h.horseNumber));
    verifyHonmeiRoles(roles,r.id,{legacyPolicy:deployedPolicy!=='unified-win-axis-v1',
      originalHonmeiHorseNumbers:originalHonmei});
    if(deployedPolicy!=='unified-win-axis-v1')console.log('PRODUCTION_LEGACY_HONMEI_POLICY '+r.id);
    // An intentionally aborted API prefetch may throw a WebKit access-control
    // pageerror. Ignore only that known effect inside the explicit outage
    // scenario; never ignore any other runtime error.
    const unexpected=errors.filter(message=>!(
      page._arvexqIntentionalApiOutage &&
      /Fetch API cannot load/.test(message) &&
      /kraiz-api\.4b89h4fydd\.workers\.dev\/api\//.test(message) &&
      /due to access control checks/.test(message)
    ));
    assert.equal(unexpected.length,0,'runtime errors '+unexpected.join(';'));

    page.off('pageerror',onerror);
    console.log('PRODUCTION_RECOVERY_PASS '+r.id+' horses='+r.horses.length+' diagnosis='+r.horses.length);
  }
  async function worker(){while(cursor<chosen.length){const r=chosen[cursor++],page=await context.newPage();try{await check(page,r)}finally{await page.close()}}}
  try{
    const r=chosen.find(r=>r.circuit==='地方')||chosen[0],page=await context.newPage();
    page._arvexqIntentionalApiOutage=true;
    await page.route('https://kraiz-api.4b89h4fydd.workers.dev/**',route=>route.abort());
    // Consume rejection even if another assertion closes the browser first;
    // a missing actual response is still an explicit failure when awaited.
    const initialResponse=page.waitForResponse(res=>res.url().includes('/api/live-odds/'),{timeout:20000}).catch(()=>null);
    await check(page,r);
    const firstSource=await initialResponse;
    if(firstSource?.status()===429){
      // The full-card sweep can exhaust the public odds quota. Retry with a
      // bounded cooldown; HTTP 429 remains a failure if the quota does not
      // recover. Do not fabricate odds or silently skip the outage test.
      const serverWait=Number(firstSource.headers()['retry-after']);
      const advertised=Number.isFinite(serverWait)&&serverWait>0?serverWait*1000:10000;
      let recovered=429;
      for(const delay of [Math.min(60000,Math.max(10000,advertised)),30000,60000]){
        console.warn('RATE_LIMITED_INITIAL_SOURCE status='+recovered+' retryMs='+delay);
        await page.waitForTimeout(delay);
        recovered=await page.evaluate(async id=>{
          try {
            const response=await fetch('/api/live-odds/'+encodeURIComponent(id));
            return response.status;
          } catch (_) { return 0; }
        },r.id);
        if(recovered===200)break;
        if(recovered!==429)break;
      }
      assert.equal(recovered,200,'independent source must recover from HTTP 429');
    }else{
      assert.equal(firstSource?.status(),200,'independent initial source request');
    }
    await page.waitForTimeout(250);
    const before=await page.locator('.rc-ai-mark').evaluateAll(xs=>xs.map(x=>x.getAttribute('data-ai-mark')));
    const response=page.waitForResponse(res=>res.url().includes('/api/live-odds/')&&res.url().includes('force=1'),{timeout:20000}).catch(()=>null);
    await page.locator('[data-action="odds-update"]').click();
    assert.equal((await response)?.status(),200,'manual source update with D1 API aborted');
    await page.waitForTimeout(300);
    assert.deepEqual(await page.locator('.rc-ai-mark').evaluateAll(xs=>xs.map(x=>x.getAttribute('data-ai-mark'))),before,'odds refresh must not rewrite saved marks');
    await page.close();
    await Promise.all([worker(),worker(),worker()]);
    // Exact recovered pre-off tickets must render even with the mutable API down.
    for(const [id,kind,patterns] of [
      ['nar-2026-10-10-高知-01','馬単',[/5\s*→\s*8/]],
      ['nar-2026-10-10-高知-05','馬連',[/1\s*-\s*5/,/3\s*-\s*5/]]
    ].filter(([id])=>records.some(r=>r.id===id))){
      const ticketPage=await context.newPage();
      ticketPage._arvexqIntentionalApiOutage=true;
      await ticketPage.route('https://kraiz-api.4b89h4fydd.workers.dev/**',route=>route.abort());
      await check(ticketPage,records.find(r=>r.id===id));
      assert.equal(await ticketPage.locator('.rc-ai-mark[data-ai-mark="◎"]').count(),1,'stored axis appears in roster before changing panel');
      await ticketPage.locator('[data-panel="bets"]').click();
      const box=ticketPage.locator('.ai-bet-box');
      await box.waitFor({state:'visible',timeout:20000});
      const text=await box.innerText();assert.ok(text.includes(kind));
      patterns.forEach(pattern=>assert.match(text,pattern,'actual saved numbered ticket '+id));
      assert.match(text,/保存/);
      await ticketPage.close();
      console.log('PRODUCTION_SAVED_NUMBERED_TICKET_API_OUTAGE_PASS '+id+' '+kind);
    }
    const fresh=await browser.newContext({...devices['iPhone 15 Pro'],locale:'ja-JP'});
    await fresh.route('https://kraiz-api.4b89h4fydd.workers.dev/**',route=>route.abort());
    const home=await fresh.newPage();
    await home.goto(base+'/?date='+day+'&offline-home='+Date.now(),{waitUntil:'domcontentloaded'});
    // Only demand venues that genuinely have races on this exact audited day.
    // An inactive venue (e.g. 高知 on 2026-10-12) must never be fabricated
    // to satisfy a stale UI test.
    for(const circuit of ['中央','地方']){
      const tracks=[...new Set(records.filter(r=>r.circuit===circuit).map(r=>r.track))];
      // Some calendar days have NAR only (or JRA only). Verify exactly the
      // venues present rather than inventing events to satisfy the fixture.
      if(!tracks.length){console.log('PRODUCTION_NO_SCHEDULED_CIRCUIT',circuit,day);continue;}
      await home.goto(base+'/?date='+day+'&offline-home='+Date.now(),{waitUntil:'domcontentloaded'});
      for(const track of tracks){
        await home.locator('.arv-all-panel [data-track="'+track+'"][data-circuit="'+circuit+'"]').first()
          .waitFor({state:'visible',timeout:30000});
      }
      console.log('PRODUCTION_VERIFIED_VENUE_HOME',circuit,JSON.stringify(tracks));
    }
    if(day==='2026-10-10'){
      // Selected races live under Home -> 厳選レース -> 地方, not the venue list.
      await home.goto(base+'/?date='+day+'&offline-selected='+Date.now(),{waitUntil:'domcontentloaded'});
      await home.locator('button[data-home-page="selected"]').click();
      await home.locator('button[data-pick-circuit="地方"]').click();
      const selected=home.locator('.arv-direct-picks').filter({hasText:'地方 厳選レース'});
      for(const id of ['nar-2026-10-10-高知-01','nar-2026-10-10-高知-05'])
        await selected.locator('[data-race="'+id+'"]').waitFor({state:'visible',timeout:30000});
      assert.equal(await selected.locator('[data-race]').count(),2,'only original numbered tickets qualify');
      console.log('PRODUCTION_SELECTED_EXACT_SAVED_TICKETS_FRESH_HOME_API_OUTAGE_PASS');
    }
    await fresh.close();
    console.log('PRODUCTION_FRESH_HOME_API_OUTAGE_ALL_VENUES_PASS');
    console.log('PRODUCTION_API_OUTAGE_MANUAL_ODDS_SAVED_MARKS_PASS '+process.env.ARVEXQ_BROWSER+' date='+day+' checked='+chosen.length);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
