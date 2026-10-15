/* Production and local iPhone-class pull gesture regression for horse racing. */
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
      const errors=[];
      page.on('pageerror',e=>errors.push(String(e)));
      await page.goto(base+'/'+pagePath+'/?pull-smoke='+Date.now(),{waitUntil:'domcontentloaded',timeout:50000});
      await page.locator('.arv-unified-hero').waitFor({state:'visible',timeout:45000});
      await page.waitForFunction(()=>window.ARVEXQPullRefresh&&document.querySelector('#arvexq-pull-refresh'),{timeout:15000});
      const first=await swipe(page);
      assert.equal(first.after,first.before+1,browserName+' '+pagePath+' first swipe not dispatched');
      assert.equal(first.label,'更新中…',browserName+' '+pagePath+' indicator not active');
      await page.waitForFunction(()=>{
        const el=document.querySelector('#arvexq-pull-refresh');
        return !!el&&!el.classList.contains('refreshing')&&el.querySelector('b')?.textContent==='下に引いて更新';
      },null,{timeout:25000});
      const second=await swipe(page);
      assert.equal(second.after,first.after+1,browserName+' '+pagePath+' second swipe not dispatched');
      await page.waitForFunction(()=>{
        const el=document.querySelector('#arvexq-pull-refresh');
        return !!el&&!el.classList.contains('refreshing')&&el.querySelector('b')?.textContent==='下に引いて更新';
      },null,{timeout:25000});
      assert.equal(await page.locator('#arvexq-pull-refresh').count(),1,'duplicate refresh indicator');
      assert.equal(errors.filter(e=>/ReferenceError|SyntaxError|not a function/.test(e)).length,0,errors.join('; '));

      console.log('HORSE_PULL_REFRESH_OK',browserName,pagePath||'root',second.after);
    }
    await page.close();
  }finally{await browser.close()}
}
(async()=>{await check(chromium,'chromium');await check(webkit,'webkit')})().catch(e=>{console.error(e);process.exit(1)});
