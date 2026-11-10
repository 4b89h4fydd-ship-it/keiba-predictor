/* Verify retired pull gestures stay inactive and the current reload button fetches fresh data. */
const {chromium,webkit,devices}=require('playwright');
const assert=require('node:assert/strict');
const base=(process.env.ARVEXQ_BASE_URL||'http://127.0.0.1:8788').replace(/\/$/,'');
async function swipe(page){
  await page.evaluate(()=>{scrollTo(0,0)});
  // WebKit commits scrollTo asynchronously; don't simulate a gesture mid-scroll.
  await page.waitForFunction(()=>Math.max(0,window.scrollY||0,document.scrollingElement?.scrollTop||0)<=2,null,{timeout:10000});
  return page.evaluate(()=>{
    scrollTo(0,0);
    // A swipe on a link/button intentionally does not refresh. Dispatch on a
    // stable neutral surface, not a hero image that may become a linked control.
    const target=document.body;
    // Playwright WebKit exposes TouchEvent but Touch has an illegal public
    // constructor on Linux. Dispatch DOM touch-shaped events instead; the
    // application listens for these standard payload fields.
    const touch=(y)=>({identifier:31,target,clientX:120,clientY:y,pageX:120,pageY:y,screenX:120,screenY:y});
    function fire(type,now){
      const ev=new Event(type,{bubbles:true,cancelable:true});
      const active=type==='touchend'?[]:[touch(now)];
      Object.defineProperties(ev,{
        touches:{value:active},
        targetTouches:{value:active},
        changedTouches:{value:[touch(now)]}
      });
      target.dispatchEvent(ev);
    }
    const before=Number(document.documentElement.dataset.arvexqPullRefreshCount||0);
    fire('touchstart',160);
    fire('touchmove',198);
    fire('touchmove',265);
    fire('touchend',265);
    return {before,after:Number(document.documentElement.dataset.arvexqPullRefreshCount||0),
      label:document.querySelector('#arvexq-pull-refresh b')?.textContent};
  });
}
async function check(browserType,browserName){
  const browser=await browserType.launch({headless:true});
  try{
    const page=await browser.newPage({...devices['iPhone 15 Pro'],locale:'ja-JP'});
    for(const pagePath of ['', 'keiba']){
      const errors=[],morningRequests=[];
      const onError=e=>errors.push(String(e));
      const onRequest=request=>{
        const u=new URL(request.url());
        if(u.pathname.startsWith('/morning-picks/'))morningRequests.push(Number(u.searchParams.get('t'))||0);
      };
      page.on('pageerror',onError);page.on('request',onRequest);
      await page.goto(base+'/'+pagePath+'/?pull-smoke='+Date.now(),{waitUntil:'domcontentloaded',timeout:50000});
      await page.locator('.arv-unified-hero').waitFor({state:'visible',timeout:45000});
      await page.waitForFunction(()=>window.ARVEXQPullRefresh,null,{timeout:15000});
      assert.equal(await page.locator('#arvexq-pull-refresh').count(),0,'retired gesture indicator must not be mounted');
      for(let attempt=0;attempt<2;attempt++){
        const gesture=await swipe(page);
        assert.equal(gesture.after,gesture.before,browserName+' '+pagePath+' retired swipe must not trigger refresh');
        assert.equal(await page.locator('#arvexq-pull-refresh').count(),0);
      }
      const priorSequence=Math.max(0,...morningRequests);
      const freshRequest=page.waitForRequest(request=>{
        const u=new URL(request.url());
        return u.pathname.startsWith('/morning-picks/')&&Number(u.searchParams.get('t'))>priorSequence;
      },{timeout:15000});
      await page.locator('[data-action="reload-all"]').click();
      await freshRequest;
      await page.locator('.arv-unified-hero').waitFor({state:'visible',timeout:15000});
      assert.equal(await page.locator('#arvexq-pull-refresh').count(),0);
      assert.equal(errors.filter(e=>/ReferenceError|SyntaxError|not a function/.test(e)).length,0,errors.join('; '));
      console.log('HORSE_RETIRED_PULL_AND_EXPLICIT_RELOAD_OK',browserName,pagePath||'root');
      page.off('pageerror',onError);page.off('request',onRequest);
    }
    await page.close();
  }finally{await browser.close()}
}
(async()=>{await check(chromium,'chromium');await check(webkit,'webkit')})().catch(e=>{console.error(e);process.exit(1)});
