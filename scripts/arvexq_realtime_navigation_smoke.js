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
  // Verify the actual home hero no longer scrolls away on iPhone.
  const sticky=await evaluateAfterStableNavigation(page,()=>{
    const hero=document.querySelector('.smart-home>.arv-unified-hero');
    const date=document.querySelector('.smart-home .arv-unified-date');
    if(!hero||!date)return {exists:false};
    const a=getComputedStyle(hero),b=getComputedStyle(date);
    return {exists:true,heroPosition:a.position,datePosition:b.position,
      heroBlur:a.backdropFilter??a.webkitBackdropFilter??'none',dateBlur:b.backdropFilter??b.webkitBackdropFilter??'none',heroOpacity:a.opacity};
  });
  assert.equal(sticky.exists,true,'Real home must render hero and date');
  assert.ok(['fixed','sticky'].includes(sticky.heroPosition),'Hero must stay pinned on iPhone');
  assert.equal(sticky.datePosition,'sticky','Date bar must remain sticky on iPhone');
  assert.equal(sticky.heroBlur,'none','Hero blur overlay must be removed');
  assert.equal(sticky.dateBlur,'none','Date blur overlay must be removed');
  const scrollCheck=await evaluateAfterStableNavigation(page,async()=>{
    const hero=document.querySelector('.smart-home>.arv-unified-hero');
    if(!hero)return {found:false};
    const before=hero.getBoundingClientRect().top;
    const probe=document.createElement('div');
    probe.style.cssText='height:1300px;pointer-events:none';
    document.querySelector('.smart-home .smart-main')?.appendChild(probe);
    window.scrollTo(0,180);
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    const after=hero.getBoundingClientRect().top,scroll=window.scrollY;
    probe.remove();window.scrollTo(0,0);
    return {found:true,before,after,scroll};
  });
  assert.equal(scrollCheck.found,true);
  assert.ok(scrollCheck.scroll>70,'Actual page scroll did not happen');
  assert.ok(Math.abs(scrollCheck.after-scrollCheck.before)<3,
    'Hero moved while scrolling: '+JSON.stringify(scrollCheck));
  assert.deepEqual(result.actions,['厳選','特別','AI成績']);
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
