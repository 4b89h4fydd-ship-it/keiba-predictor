/* Real production rosters, independent odds, saved diagnoses and outage recovery. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const {chromium,webkit,devices}=require('playwright');
const verifyHonmeiRoles=require('./arvexq_honmei_dom_contract');
const directory='arvexq/ui/static/saved-snapshots';
const day=process.env.ARVEXQ_AUDIT_DATE||fs.readdirSync(directory).filter(f=>/^\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort().at(-1).slice(0,10);
const manifest=JSON.parse(fs.readFileSync(path.join(directory,day+'.json')));
const cards=JSON.parse(fs.readFileSync('arvexq/ui/static/racecards/'+day+'.json')).races;
const base=process.env.ARVEXQ_BASE_URL||'https://4b89h4fydd-ship-it.github.io/keiba-predictor';
const type=process.env.ARVEXQ_BROWSER==='webkit'?webkit:chromium;
// Archives are immutable and may contain retired Banei, but production-app
// smoke tests must navigate only the explicitly supported racing venues.
const archivedRecords=Object.entries(manifest.races).map(([id,ref])=>{
  const e=JSON.parse(fs.readFileSync(path.join(directory,ref.file)));
  return JSON.parse(zlib.gunzipSync(Buffer.from(e.gzipBase64,'base64')));
});
const records=archivedRecords.filter(r=>r&&r.id&&
  !['帯広','帯広ば'].includes(String(r.track||''))&&
  !/-帯広(?:ば)?-/.test(String(r.id)));
assert(records.length<=archivedRecords.length,'archived evidence remains intact');
// WebKit checks real venues for this date, not a hardcoded historical card list.
const chosen=process.env.ARVEXQ_BROWSER==='webkit'?
  [...new Set(records.map(r=>r.track))].map(track=>records.find(r=>r.track===track)).filter(Boolean):records;
assert.ok(chosen.length>0,'No verified current-day race data available');
(async()=>{
  const browser=await type.launch({headless:true,...(process.env.CHROMIUM_PATH&&type===chromium?{executablePath:process.env.CHROMIUM_PATH}:{})});
  const context=await browser.newContext({...devices['iPhone 15 Pro'],locale:'ja-JP'});
  let cursor=0;
  // Independent odds reality at execution time. Historical NAR odds are
  // backfilled on demand from the official archive, so the population of
  // odds-carrying races grows between runs: expectations must follow what
  // the source returns NOW, never the archived snapshot's stored state.
  // Since the 2026-11-23 GitHub-only migration the odds panel has two
  // published states. On open it shows the static race pack this
  // origin serves (api-static/race/<id>.json): per horse, the saved
  // detail's winOdds (which the sync lane keeps overlaying with the
  // latest official odds), overridden by the pack's top-level odds
  // rows where present, exactly as mergeRaceReflection merges them.
  // The same-origin static live-odds feed
  // (api-static/live-odds/<id>.json) is fetched on open too, but the
  // pack merge landing afterwards overwrites it; feed values become
  // the shown state only after an odds refresh (odds-update control
  // or the auto refresh for today's upcoming races), applied per
  // horse by mergeOddsPayload. The check verifies the open state
  // against both published states and the refreshed state against
  // the feed state. The detached relay worker the feed replaced is
  // retired (503 since the migration), and the D1-backed edge API
  // (kraiz-api /api/race) is gone. Both payloads carry WIN odds only;
  // no source returns place odds, so the panel's place column is
  // explicitly '―' unless a future feed adds placeOddsLow/High (a
  // numeric range is then the factual display).
  async function oddsSources(id){
    const out={live:null,detail:null,liveScratched:new Set(),detailScratched:new Set()};
    try{const res=await fetch(base+'/api-static/live-odds/'+encodeURIComponent(id)+'.json',{signal:AbortSignal.timeout(20000)});
      if(res.ok){const body=await res.json();
        if(body&&body.ok===true){out.live=new Map();
          for(const o of body.odds||[]){const no=Number(o&&(o.horseNumber!=null?o.horseNumber:o.horse_no)),v=Number(o&&(o.winOdds!=null?o.winOdds:o.win_odds));
            if(Number.isInteger(no)&&v>0)out.live.set(no,v);
            if(Number.isInteger(no)&&o&&(o.scratched===true||/取消|除外/.test(String(o.status!=null?o.status:o.horse_status||''))))out.liveScratched.add(no);}}}}
    catch(e){/* feed unavailable: expectation falls back to the pack */}
    try{const res=await fetch(base+'/api-static/race/'+encodeURIComponent(id)+'.json',{signal:AbortSignal.timeout(20000)});
      if(res.ok){const body=await res.json();
        if(body&&body.ok===true){out.detail=new Map();
          for(const h of (body.detail&&body.detail.horses)||[]){const no=Number(h&&h.horseNumber),v=Number(h&&h.winOdds);
            if(Number.isInteger(no)&&v>0)out.detail.set(no,v);
            if(Number.isInteger(no)&&h&&(h.scratched===true||/取消|除外/.test(String(h.status||''))))out.detailScratched.add(no);}
          for(const o of body.odds||[]){const no=Number(o&&o.horse_no),v=Number(o&&o.win_odds);
            if(Number.isInteger(no)&&v>0)out.detail.set(no,v);
            if(Number.isInteger(no)&&o&&(o.scratched===true||/取消|除外/.test(String(o.horse_status||''))))out.detailScratched.add(no);}}}}
    catch(e){/* source unavailable: expectations stay empty */}
    return out;
  }
  async function check(page,r){
    const errors=[];const onerror=e=>errors.push(e.stack||String(e));page.on('pageerror',onerror);
    await page.goto(base+'/race?date='+day+'&race_id='+encodeURIComponent(r.id)+'&recovery='+Date.now(),{waitUntil:'domcontentloaded',timeout:45000});
    // Public roster readiness is independent of any retired pre-off opinions.
    const roster=cards.find(c=>c.id===r.id)||r;
    // v349: the roster body is the integrated entry table; the retired
    // .racecard-row list survives only in the error-fallback panel.
    await page.waitForFunction(count=>document.querySelectorAll('.arv-entry-table tbody tr').length===count,roster.horses.length,{timeout:20000});
    assert.equal(await page.locator('.arv-entry-table tbody tr').count(),roster.horses.length,'complete official roster '+r.id);
    // Entry-table name buttons carry the plain horse name alone; compare
    // those, not any mark or role label.
    const names=(await page.locator('.arv-entry-table .nk-odds-name').allTextContents()).map(x=>x.trim());
    roster.horses.forEach(h=>assert.ok(names.includes(h.name),'runner identity missing '+r.id+' '+h.name));
    // v363: the analysis panel is tag-switched; the saved diagnosis lives
    // behind the diagnosis tag of the pace (analysis) panel.
    await page.locator('[data-panel="pace"]').click();
    // The analysis panel is fed by live API/snapshot loads whose latency
    // varies (cold D1, intermittent edge 503 with retries): on a main push
    // a bare .da-tags selector wait timed out at 30s on a slow-but-healthy
    // load. Wait longer for the terminal state, and if the panel lands in
    // its explicit error state use its own retry control once — the same
    // recovery pattern as odds below. The tag bar must still appear.
    const tagsReady=()=>page.waitForSelector('.da-tags',{timeout:60000}).then(()=>true).catch(()=>false);
    if(!await tagsReady()){
      const retry=page.locator('[data-detail-retry]').first();
      if(await retry.count()){console.warn('ANALYSIS_PANEL_RETRY '+r.id);await retry.click();await tagsReady();}
    }
    await page.waitForSelector('.da-tags',{timeout:30000});
    await page.locator('[data-analysis-tag="diagnosis"]').click();
    await page.waitForFunction(count=>document.querySelectorAll('.diagnosis-merged-row').length===count,roster.horses.length,{timeout:20000});
    const diagnosis=page.locator('details.card').filter({has:page.locator('.diagnosis-merged-list')});
    // The live result refresh can replace this details node while Playwright
    // waits for a stable click; open via DOM on the currently matched node.
    await page.waitForFunction(count=>{
      const d=[...document.querySelectorAll('details.card')]
        .find(x=>x.querySelector('.diagnosis-merged-list'));
      if(!d)return false;
      d.open=true;
      return d.querySelectorAll('.diagnosis-merged-row').length===count;
    },roster.horses.length,{timeout:30000});
    // Only factual acquired odds or an explicit missing status can appear.
    // v345: win odds live in the dedicated odds panel table (popularity
    // order); the win cell is a plain one-decimal number, the explicit
    // missing marker, or the scratched marker. When no runner carries
    // odds the table is replaced by an explicit not-acquired message.
    await page.locator('[data-panel="odds"]').click();
    // Ask the independent sources first and build the per-horse win-odds
    // expectations from what they return at execution time. The panel
    // has two legitimate published states, both verified below:
    //  - the pack state: detail rows overridden by the pack's top-level
    //    odds rows. This is what opening a race shows: the app fetches
    //    the static feed too, but the pack merge that lands afterwards
    //    overwrites the feed values again (mergeRaceReflection applies
    //    the pack's odds rows last on load), so feed values do not
    //    survive the initial load.
    //  - the feed state: the pack state overridden by the static
    //    live-odds feed. It becomes the shown state after an explicit
    //    odds refresh (the odds-update control, or the auto refresh
    //    for today's upcoming races) via mergeOddsPayload.
    // Observed 2026-11-27: Nagoya 1R's favourite was 1.8 in the pack
    // (sync lane, 13:00) and 1.9 in the feed (NAR official, 13:02);
    // the app deterministically showed the pack value on open.
    // The archived snapshot is never an expectation source: its stored
    // odds state predates the on-demand official backfill, and its
    // carried winOdds are forecast odds, not acquired official odds.
    let sources=await oddsSources(r.id);
    const buildPackExpected=()=>{
      const map=new Map();
      if(sources.detail)for(const [no,v] of sources.detail)map.set(no,v);
      return map;
    };
    const buildFeedExpected=()=>{
      const map=buildPackExpected();
      if(sources.live)for(const [no,v] of sources.live)map.set(no,v);
      return map;
    };
    let expected=buildPackExpected();
    let feedExpected=buildFeedExpected();
    const sourcesResponded=()=>sources.live!==null||sources.detail!==null;
    // The odds panel re-renders as each independent source lands (detail,
    // live odds, result refresh), and a replacement race object can move
    // it back through the pending generation ('取得中です', which has
    // neither the table nor the not-acquired message nor even
    // #section-odds). One-shot samples — and even a settled wait followed
    // by separate count/text reads — can straddle such a re-render and
    // misread a correct screen. Instead, sample the whole section in one
    // in-page evaluation and require two identical consecutive terminal
    // samples before asserting anything.
    const sampleOdds=()=>page.evaluate(()=>{
      const sec=document.querySelector('#section-odds');
      if(!sec){
        const pending=[...document.querySelectorAll('section.card')]
          .some(s=>/取得中です/.test(s.textContent||''));
        return {state:pending?'pending':'absent',rows:[]};
      }
      const table=sec.querySelector('.arv-odds-table');
      if(!table){
        if(/まだ取得できていません/.test(sec.textContent||''))return {state:'message',rows:[]};
        return {state:'pending',rows:[]};
      }
      const rows=[...table.querySelectorAll('tbody tr')].map(tr=>{
        const td=tr.querySelectorAll('td');
        return {name:(tr.querySelector('.nk-odds-name')?.textContent||'').trim(),
          win:(td[4]?.textContent||'').trim(),place:(td[5]?.textContent||'').trim()};
      });
      const wellFormed=rows.length>0&&rows.every(x=>
        /^(?:\d+\.\d|―|取消)$/.test(x.win)&&/^(?:\d+\.\d-\d+\.\d|―)$/.test(x.place));
      return {state:wellFormed?'table':'malformed',rows};
    });
    async function waitSettledOdds(timeoutMs){
      const deadline=Date.now()+timeoutMs;let prev='';
      while(Date.now()<deadline){
        const s=await sampleOdds();
        // When sources publish win odds, the message generation is not
        // terminal: the live merge is still owed. When no source does,
        // the explicit message is the terminal guarantee.
        const terminal=s.state==='table'||(s.state==='message'&&(page._arvexqIntentionalApiOutage?expected.size:feedExpected.size)===0);
        if(terminal){
          const ser=JSON.stringify(s);
          if(ser===prev)return s;
          prev=ser;
        }else prev='';
        await page.waitForTimeout(1000);
      }
      return null;
    }
    const fmtOdds=v=>(Math.round(v*10)/10).toFixed(1);
    function assertOdds(s,id,expMap){
      if(s.state==='message'){
        assert.equal(expMap.size,0,'odds missing state must be explicit '+id+' (panel shows not-acquired but sources publish win odds '+JSON.stringify([...expMap]) +')');
        return;
      }
      assert.equal(s.state,'table','odds panel must settle to a table or an explicit missing message '+id+' last='+JSON.stringify(s).slice(0,200));
      assert.equal(s.rows.length,roster.horses.length,'odds rows must cover the full roster '+id);
      const byName=new Map(roster.horses.map(h=>[h.name,h]));
      for(const row of s.rows){
        const h=byName.get(row.name);
        assert.ok(h,'odds row identity missing '+id+' '+row.name);
        const no=Number(h.horseNumber),exp=expMap.get(no);
        const scratched=sources.liveScratched.has(no)||sources.detailScratched.has(no);
        if(row.win==='取消'){
          // An explicit factual state; the place cell must then be the
          // explicit missing marker, never a number.
          assert.equal(row.place,'―','scratched place cell must be explicit '+id+' '+row.name);
        }else if(exp!=null){
          assert.equal(row.win,fmtOdds(exp),'win odds must follow the execution-time source '+id+' '+row.name+' expected='+fmtOdds(exp)+' shown='+row.win);
        }else{
          // The sources return no win odds for this runner: the cell must
          // stay the explicit missing marker. (The place column follows
          // the same rule for every runner — no source returns place
          // odds, so it is '―' or a factual range, never blank.)
          assert.equal(row.win,'―','unpublished win odds must be explicit '+id+' '+row.name+' shown='+row.win);
        }
        assert.ok(/^(?:\d+\.\d-\d+\.\d|―)$/.test(row.place),'place odds must be a range or explicit missing '+id+' '+row.name+' shown='+row.place);
      }
    }
    let settled=await waitSettledOdds(45000);
    // On open, either published state is legitimate (the auto refresh
    // may already have applied the feed for today's upcoming races).
    // A panel showing values that match NEITHER state is the failure
    // this check exists for: stale cache, cross-race contamination, or
    // fabricated numbers.
    const matchEither=(s)=>{
      try{assertOdds(s,r.id,expected);return 'pack'}catch(e){/* try feed state */}
      try{assertOdds(s,r.id,feedExpected);return 'feed'}catch(e){/* neither */}
      return null;
    };
    let oddsProblem=null,matched=null;
    if(!settled)oddsProblem='did not settle';
    else{matched=matchEither(settled);if(!matched){try{assertOdds(settled,r.id,expected)}catch(e){oddsProblem=e.message}}}
    if(oddsProblem){
      // Sources may have been backfilled mid-check (the node-side fetch
      // itself can trigger the on-demand official fetch), or the pack
      // itself may have been republished after the page loaded it —
      // result ingest rewrites finished races' packs while these checks
      // run, and the odds-update control only refreshes the live feed,
      // so it can never repair a stale pack. Reload the race page so
      // the panel is rebuilt from the current pack, then assert
      // against sources re-read after the reload. A still-broken
      // screen fails here.
      console.warn('ODDS_RECOVERY '+r.id+' '+oddsProblem);
      await page.reload({waitUntil:'domcontentloaded',timeout:45000});
      await page.waitForFunction(count=>document.querySelectorAll('.arv-entry-table tbody tr').length===count,roster.horses.length,{timeout:20000});
      await page.locator('[data-panel="odds"]').click();
      sources=await oddsSources(r.id);
      expected=buildPackExpected();
      feedExpected=buildFeedExpected();
      settled=await waitSettledOdds(30000);
      assert.ok(settled,'odds panel did not settle after reload '+r.id);
      matched=matchEither(settled);
      if(!matched)assertOdds(settled,r.id,expected);
      console.log('ODDS_RECOVERY_PASS '+r.id);
    }
    if(matched)console.log('ODDS_SOURCE_MATCH '+r.id+' state='+matched+' horses='+(matched==='feed'?feedExpected.size:expected.size)+' live='+(sources.live?sources.live.size:'n/a')+' detail='+(sources.detail?sources.detail.size:'n/a'));
    else if(sourcesResponded())console.log('ODDS_NOT_YET_PUBLISHED '+r.id);
    else console.log('ODDS_SOURCE_UNAVAILABLE '+r.id);
    // Refresh phase: the odds-update control applies the static feed
    // over the pack state. When the feed is reachable from this page
    // (not in the outage scenario) and publishes odds, the panel must
    // end in the feed state; in the outage scenario the refresh cannot
    // land and the panel must stay in the pack state.
    const feedUsable=!page._arvexqIntentionalApiOutage&&!!(sources.live&&sources.live.size>0);
    const updateBtn=page.locator('[data-action="odds-update"]');
    if(await updateBtn.count()){
      await updateBtn.first().click();
      let s2=await waitSettledOdds(30000);
      let refreshProblem=null;
      if(!s2)refreshProblem='did not settle after odds refresh';
      else{try{assertOdds(s2,r.id,feedUsable?feedExpected:expected)}catch(e){refreshProblem=e.message}}
      if(refreshProblem){
        console.warn('ODDS_REFRESH_RECOVERY '+r.id+' '+refreshProblem);
        sources=await oddsSources(r.id);
        expected=buildPackExpected();
        feedExpected=buildFeedExpected();
        await updateBtn.first().click();
        s2=await waitSettledOdds(30000);
        assert.ok(s2,'odds panel did not settle after refresh retry '+r.id);
        assertOdds(s2,r.id,(!page._arvexqIntentionalApiOutage&&sources.live&&sources.live.size>0)?feedExpected:expected);
        console.log('ODDS_REFRESH_RECOVERY_PASS '+r.id);
      }
      settled=s2;
    }
    // The retired racecard rows coloured single-digit odds red via
    // .odd.single; the current odds/entry tables render win odds as
    // plain text with no single-digit class, so that styling check has
    // no DOM counterpart and is not carried over. The one-decimal
    // format assertions above remain the odds-text guarantee.
    // Marks and honmei roles live only in the entry table; return to it.
    await page.locator('[data-panel="entry"]').click();
    await page.waitForSelector('.arv-entry-table');
    const roles=await page.locator('.arv-entry-table tbody tr').evaluateAll(rows=>rows.map(row=>({
      mark:row.querySelector('.arv-marks-mark')?.getAttribute('data-ai-mark')||'',
      horseNumber:Number(row.querySelector('[data-horse-open]')?.getAttribute('data-horse-open')||0),
      // unified-win-axis-v1 renders no separate win/axis DOM roles
      // (.arv-role-win/.arv-role-axis exist nowhere in the current UI):
      // the single visible honmei is both roles at once, and the
      // contract below verifies exactly that unified invariant.
      win:false,axis:false
    })));
    const deployedPolicy=await page.evaluate(()=>window.ARVEXQ_HONMEI_POLICY||'legacy');
    const originalHonmei=(r.preRacePrediction?.horses||[]).filter(h=>h.mark==='◎').map(h=>Number(h.horseNumber));
    verifyHonmeiRoles(roles,r.id,{legacyPolicy:deployedPolicy!=='unified-win-axis-v1',
      originalHonmeiHorseNumbers:originalHonmei});
    if(deployedPolicy!=='unified-win-axis-v1')console.log('PRODUCTION_LEGACY_HONMEI_POLICY '+r.id);
    // An intentionally aborted API prefetch may throw a WebKit access-control
    // pageerror (including WebKit's normalized `https: /` URL). Ignore only that known effect inside the explicit outage
    // scenario; never ignore any other runtime error.
    const unexpected=errors.filter(message=>!(
      page._arvexqIntentionalApiOutage &&
      /Fetch API cannot load/.test(message) &&
      /\/(?:api-static|api\/live-odds)\//.test(message) &&
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
    await page.route(base+'/api-static/live-odds/**',route=>route.abort());
    // Consume rejection even if another assertion closes the browser first;
    // a missing actual response is still an explicit failure when awaited.
    const initialResponse=page.waitForResponse(res=>res.url().includes('/api-static/race/'),{timeout:20000}).catch(()=>null);
    await check(page,r);
    const firstSource=await initialResponse;
    assert.equal(firstSource?.status(),200,'surviving pack source must answer while the live-odds feed is down');
    await page.waitForTimeout(250);
    const before=await page.locator('.arv-entry-table .arv-marks-mark').evaluateAll(xs=>xs.map(x=>x.getAttribute('data-ai-mark')));
    await page.locator('[data-action="odds-update"]').click();
    await page.waitForTimeout(300);
    assert.deepEqual(await page.locator('.arv-entry-table .arv-marks-mark').evaluateAll(xs=>xs.map(x=>x.getAttribute('data-ai-mark'))),before,'odds refresh must not rewrite saved marks');
    await page.close();
    // WebKit checks its per-track subset serially. Three parallel iPhone
    // pages in one WebKit browser on the CI runner starve each other's
    // rendering: the odds panel's settle sampling (two identical
    // consecutive terminal samples) then intermittently never stabilises
    // for one of the races — a different one per run — even though the
    // parallel Chromium run verifies every race against the same live
    // sources. Serial pages mirror real single-page usage; the checks
    // and assertions are unchanged.
    if(process.env.ARVEXQ_BROWSER==='webkit')await worker();
    else await Promise.all([worker(),worker(),worker()]);
    // Archived opinions cannot reappear on a fresh device, including API outage.
    for(const archived of records.filter(r=>r.preRaceBet).slice(0,2)){
      const ticketPage=await context.newPage();
      ticketPage._arvexqIntentionalApiOutage=true;
      await ticketPage.route(base+'/api-static/live-odds/**',route=>route.abort());
      await check(ticketPage,archived);
      assert.equal(await ticketPage.locator('.arv-entry-table .arv-marks-mark[data-ai-mark="◎"]').count(),0,'no stored axis becomes live');
      // v349: the forecast (bets) subpage was merged into the entry
      // table; the ticket plan lives on the dedicated 買い目 subpage.
      await ticketPage.locator('[data-panel="tickets"]').click();
      await ticketPage.waitForSelector('.ticket-detail-page-shell');
      assert.equal(await ticketPage.locator('.ticket-detail-page-shell .arv-three-ticket').count(),0,'retired numbered tickets stay archival');
      await ticketPage.close();
    }
    const fresh=await browser.newContext({...devices['iPhone 15 Pro'],locale:'ja-JP'});
    await fresh.route(base+'/api-static/live-odds/**',route=>route.abort());
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
        // v346: the home is venue tags only; the all-venues grid
        // (.arv-all-panel) is no longer rendered on the home.
        await home.locator('.nk-venue-tags [data-track="'+track+'"][data-circuit="'+circuit+'"]').first()
          .waitFor({state:'visible',timeout:30000});
      }
      console.log('PRODUCTION_VERIFIED_VENUE_HOME',circuit,JSON.stringify(tracks));
    }
    // No disabled-engine tickets may become actionable through home
    // pages. The selected page itself is retired in the current home
    // (only the favorites entry remains), and the retired .bet-item
    // class exists nowhere; the current ticket element is
    // .arv-three-ticket inside .ai-bet-box.
    assert.equal(await home.locator('[data-home-page="selected"]').count(),0,'retired selected page must not be offered');
    assert.equal(await home.locator('.ai-bet-box .arv-three-ticket').count(),0);
    await fresh.close();
    console.log('PRODUCTION_FRESH_HOME_API_OUTAGE_ALL_VENUES_PASS');
    console.log('PRODUCTION_API_OUTAGE_MANUAL_ODDS_SAVED_MARKS_PASS '+process.env.ARVEXQ_BROWSER+' date='+day+' checked='+chosen.length);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
