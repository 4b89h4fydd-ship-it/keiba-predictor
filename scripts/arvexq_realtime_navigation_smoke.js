/* Horse-only iPhone Chromium/WebKit race-grid and darkening regression.
   Uses isolated fixed-time fixtures in the browser; no fabricated races are deployed. */
const {chromium,webkit,devices}=require('playwright');
const assert=require('node:assert/strict');
const base=(process.env.ARVEXQ_BASE_URL||'http://127.0.0.1:8790').replace(/\/$/,'');
// WebKit may replace the page context while the PWA initial route is settling.
async function evaluateAfterStableNavigation(page,fn){
 for(let attempt=0;attempt<4;attempt++){
  try{return await page.evaluate(fn)}
  catch(error){
   if(!/Execution context was destroyed|most likely because of a navigation/i.test(String(error))||attempt===3)throw error;
   await page.waitForLoadState('domcontentloaded',{timeout:30000});
   await page.waitForFunction(()=>Boolean(window.ARVEXQUnifiedHome&&window.ARVEXQHorsePortal),{timeout:30000});
  }
 }
 throw Error('browser navigation did not stabilize');
}
async function verify(kind,name){
 const browser=await kind.launch({headless:true});
 try{
  const page=await browser.newPage({...devices['iPhone 15 Pro'],locale:'ja-JP'});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(base+'/?horse-grid-smoke='+Date.now(),{waitUntil:'domcontentloaded',timeout:50000});
  await page.waitForFunction(()=>Boolean(window.ARVEXQUnifiedHome&&window.ARVEXQHorsePortal),{timeout:45000});
  const result=await evaluateAfterStableNavigation(page,()=>{
    const day='2026-10-12',rows=[
      {id:'jra-'+day+'-東京-01',circuit:'中央',track:'東京',raceNumber:1,startTime:'10:30'},
      {id:'jra-'+day+'-東京-02',circuit:'中央',track:'東京',raceNumber:2,startTime:'11:30'},
      {id:'nar-'+day+'-大井-01',circuit:'地方',track:'大井',raceNumber:1,startTime:'10:50'}
    ];
    const home=window.ARVEXQUnifiedHome,portal=window.ARVEXQHorsePortal;
    const scope=document.createElement('div');scope.className='smart-shell smart-home';scope.innerHTML=home.dateBar(day)+home.buttons('horse')+
      portal.home(rows,{date:day,today:day,nowMinutes:610});
    document.body.appendChild(scope);
    const initial=home.liveModel('horse',rows,day,new Date(day+'T10:20:00+09:00'));
    const after=home.liveModel('horse',rows,day,new Date(day+'T10:40:00+09:00'));
    home.syncLiveUI('horse',rows,day,scope,new Date(day+'T10:40:00+09:00'));
    const first=scope.querySelector('[data-race="'+rows[0].id+'"]');
    const grid=scope.querySelector('.arv-all-races-grid');
    const raceTiles=[...grid.querySelectorAll('.arv-all-race')];
    const venue=grid.closest('.arv-all-venue');
    const top=i=>raceTiles[i].getBoundingClientRect().top;
    const result={
      actions:[...scope.querySelectorAll('.arv-unified-action-label')].map(e=>e.textContent),
      fullGrid:scope.querySelectorAll('.arv-all-panel button.arv-all-race').length,
      booked:scope.querySelectorAll('.arv-all-panel button[data-race]').length,
      firstNext:initial.find(r=>r.next&&r.venue==='東京')?.number,
      nextAfter:after.find(r=>r.next&&r.venue==='東京')?.number,
      firstState:first?.getAttribute('data-race-state'),
      firstText:first?.querySelector('.arv-race-state')?.textContent,
      opacity:first?Number(getComputedStyle(first).opacity):1,
      firstClickable:!first?.disabled,
      columns:getComputedStyle(grid).gridTemplateColumns.trim().split(/\s+/).length,
      topRowSix:Math.abs(top(0)-top(5))<1,
      secondRowStartsAtSeven:top(6)>top(0)+30,
      tileHeight:raceTiles[0].getBoundingClientRect().height,
      venueBorder:getComputedStyle(venue).borderTopWidth,
      arrowContent:getComputedStyle(raceTiles[0],'::after').content,
      shortcutsAboveGrid:scope.querySelector('.arv-unified-actions')?.compareDocumentPosition(scope.querySelector('.arv-all-panel'))&Node.DOCUMENT_POSITION_FOLLOWING,
      navOnHome:document.querySelectorAll('.arvexq-sport-nav').length,
      realtime:document.querySelectorAll('.arv-realtime-section').length,
      alerts:scope.querySelectorAll('.arv-unified-alert').length
    };scope.remove();return result;
  });
  const simpleHome=await evaluateAfterStableNavigation(page,()=>{
    const home=document.querySelector('.smart-shell.smart-home');
    const date=home?.querySelector('.arv-unified-date');
    return {hero:!!home?.querySelector('.arv-unified-hero'),
      background:home?getComputedStyle(home).backgroundColor:null,
      datePosition:date?getComputedStyle(date).position:null};
  });
  assert.equal(simpleHome.hero,true,'Home hero should be rendered');
  assert.equal(simpleHome.background,'rgb(246, 242, 232)','Home must match the approved brush-logo paper background');
  assert.equal(simpleHome.datePosition,'relative','Date should scroll naturally');
  // Fixture DOM uses actual classes from app.js. Assert *computed*, not just source CSS.
  const paper=await evaluateAfterStableNavigation(page,()=>{
    const fx=document.createElement('div');
    fx.innerHTML=[
      '<div class="smart-shell paper-race-fixture"><header class="smart-topbar smart-topbar-clean smart-race-topbar"><div class="smart-head-copy"><strong>園田 1R</strong></div></header><main class="smart-main smart-race-page"><div class="race-nav-v230"><div class="race-nav-v230-row race-nav-v230-top"><button class="race-nav-v230-btn active"><span class="race-nav-v230-label">出走表</span></button></div></div></main></div>',
      '<div class="smart-shell paper-special-fixture"><header class="smart-topbar smart-section-topbar arv-dated-subbar"><div class="smart-head-copy"><strong>地方 特別予想</strong></div></header><main class="smart-main smart-home-subpage"><section class="smart-fixed-picks arv-direct-picks"><div class="smart-fixed-picks-head"><span><b>地方 特別予想</b><small>メイン・重賞</small></span></div><div class="fixed-pick-box-body"><button class="fixed-pick-row arv-direct-pick-row"><span><b>園田11R</b><small>開催レース</small></span><time>16:05</time></button></div></section></main></div>',
      '<div class="smart-shell pace-stage-shell paper-pace-fixture"><header class="smart-topbar smart-race-topbar pace-stage-topbar"><div class="pace-stage-top-title"><strong>スタート</strong></div></header><main class="smart-main smart-race-page pace-stage-page"><section class="pace-stage-explain"><h2>スタート直後</h2><p class="pace-stage-narrative">隊列予想</p></section><section class="pace-formation-card"><div class="pace-formation-track">隊列図</div></section></main></div>',
      '<div class="smart-shell horse-detail-page-shell paper-horse-fixture"><header class="smart-topbar smart-race-topbar horse-detail-topbar"><div class="horse-detail-top-title"><strong>馬詳細</strong></div></header><main class="smart-main smart-race-page horse-detail-page"><section class="card"><div class="horse-detail"><div class="runner-overall-box"><div class="runner-overall-head"><span class="label">AI総合評価</span></div></div><div class="horse-info-grid"><div class="horse-info-cell"><small>騎手</small><b>未取得</b></div></div></div></section></main></div>',
      '<div class="smart-shell bet-detail-page-shell paper-bet-fixture"><main class="smart-main smart-race-page"><section class="card bet-card-clean"><div class="arv-three-bet"><div class="arv-three-section"><h3>本線</h3></div></div></section></main></div>'
    ].join('');
    fx.style.cssText='position:absolute;left:-10000px;top:0;width:393px;pointer-events:none';
    document.body.appendChild(fx);
    const selectors={
      raceHeader:'.paper-race-fixture>header',
      raceHeaderTitle:'.paper-race-fixture .smart-head-copy strong',
      raceTabFrame:'.paper-race-fixture .race-nav-v230-top',
      raceTab:'.paper-race-fixture .race-nav-v230-btn',
      specialHeader:'.paper-special-fixture>header',
      specialText:'.paper-special-fixture .smart-fixed-picks-head b',
      specialSubtitle:'.paper-special-fixture .smart-fixed-picks-head small',
      specialRowText:'.paper-special-fixture .fixed-pick-row small',
      paceHeader:'.paper-pace-fixture>header',
      paceExplanation:'.paper-pace-fixture .pace-stage-explain',
      paceDiagram:'.paper-pace-fixture .pace-formation-card',
      paceTrack:'.paper-pace-fixture .pace-formation-track',
      horseHeader:'.paper-horse-fixture>header',
      horseOverall:'.paper-horse-fixture .runner-overall-head',
      horseInfo:'.paper-horse-fixture .horse-info-cell',
      betSection:'.paper-bet-fixture .arv-three-bet'
    };
    const result={};
    for(const [label,selector] of Object.entries(selectors)){
      const el=fx.querySelector(selector),css=el&&getComputedStyle(el);
      result[label]=css?{bg:css.backgroundColor,foreground:css.color,opacity:css.opacity}:null;
    }
    fx.remove();return result;
  });
  const dark=color=>{const a=(color||'').match(/\d+(?:\.\d+)?/g);if(!a||a.length<3)return false;const nums=a.slice(0,3).map(Number);return nums.reduce((sum,v)=>sum+v,0)<350};
  for(const k of ['raceHeader','raceTabFrame','raceTab','specialHeader','paceHeader','paceExplanation','paceDiagram','paceTrack','horseHeader','horseOverall','horseInfo','betSection']){
    assert.ok(paper[k]&&!dark(paper[k].bg),'Dark surface still visible: '+k+' '+JSON.stringify(paper[k]));
  }
  for(const k of ['raceHeaderTitle','specialText','specialSubtitle','specialRowText']){
    assert.ok(paper[k]&&dark(paper[k].foreground),'Unreadable pale text on paper: '+k+' '+JSON.stringify(paper[k]));
    assert.equal(paper[k].opacity,'1','Transparent/washed-out text: '+k);
  }
  assert.deepEqual(result.actions,['厳選','特別','AI成績','お気に入り']);
  assert.equal(result.fullGrid,24);assert.equal(result.booked,3);
  assert.equal(result.firstNext,1);assert.equal(result.nextAfter,2);
  assert.equal(result.firstState,'elapsed');assert.equal(result.firstText,'結果待ち');
  assert.ok(result.opacity<0.8,'elapsed race must be darkened');
  assert.equal(result.firstClickable,true);assert.ok(result.shortcutsAboveGrid);
  assert.equal(result.columns,6,'Reference image requires exactly six races per row');
  assert.equal(result.topRowSix,true,'1R through 6R must remain in the first row');
  assert.equal(result.secondRowStartsAtSeven,true,'7R must start the second row');
  assert.ok(result.tileHeight>=47&&result.tileHeight<=50,'Reference tiles must be compact');
  assert.equal(result.venueBorder,'0px','Venue inner frame must be removed');
  assert.notEqual(result.arrowContent,'none','Each clickable race tile needs a small arrow');
  assert.equal(result.navOnHome,0);assert.equal(result.realtime,0);
  assert.equal(result.alerts,2,'selected and special warning icons are visible');
  assert.equal(errors.filter(e=>/ReferenceError|SyntaxError/.test(e)).length,0,errors.join('; '));
  console.log('HORSE_12R_IPHONE_GRID_OK',name);
 }finally{await browser.close()}
}
(async()=>{await verify(chromium,'chromium');await verify(webkit,'webkit')})()
.catch(e=>{console.error(e);process.exit(1)});
