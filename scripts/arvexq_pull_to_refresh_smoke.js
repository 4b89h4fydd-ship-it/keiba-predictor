/* Production and local iPhone-class pull gesture regression for both sports.
 * Does not assert a BOAT feed exists without a commercial license.
 */
const {chromium,webkit,devices}=require('playwright');
const assert=require('node:assert/strict');
const base=(process.env.ARVEXQ_BASE_URL||'http://127.0.0.1:8788').replace(/\/$/,'');
async function swipe(page){
  return page.evaluate(()=>{
    scrollTo(0,0);
    const target=document.querySelector('.arv-unified-hero img')||document.body;
    const touch=(y)=>new Touch({identifier:31,target,clientX:120,clientY:y,pageX:120,pageY:y,screenX:120,screenY:y});
    function fire(type,now){
      target.dispatchEvent(new TouchEvent(type,{bubbles:true,cancelable:true,
        touches:type==='touchend'?[]:[touch(now)],
        targetTouches:type==='touchend'?[]:[touch(now)],
        changedTouches:[touch(now)]}));
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
    for(const sport of ['keiba','kyotei']){
      const errors=[];
      page.on('pageerror',e=>errors.push(String(e)));
      await page.goto(base+'/'+sport+'/?pull-smoke='+Date.now(),{waitUntil:'domcontentloaded',timeout:50000});
      await page.locator('.arv-unified-hero').waitFor({state:'visible',timeout:45000});
      await page.waitForFunction(()=>window.ARVEXQPullRefresh&&document.querySelector('#arvexq-pull-refresh'),{timeout:15000});
      const first=await swipe(page);
      assert.equal(first.after,first.before+1,browserName+' '+sport+' first swipe not dispatched');
      assert.equal(first.label,'更新中…',browserName+' '+sport+' indicator not active');
      await page.waitForFunction(()=>!document.querySelector('#arvexq-pull-refresh')?.classList.contains('refreshing'),{timeout:25000});
      const second=await swipe(page);
      assert.equal(second.after,first.after+1,browserName+' '+sport+' second swipe not dispatched');
      await page.waitForFunction(()=>!document.querySelector('#arvexq-pull-refresh')?.classList.contains('refreshing'),{timeout:25000});
      assert.equal(await page.locator('#arvexq-pull-refresh').count(),1,'duplicate refresh indicator');
      assert.equal(errors.filter(e=>/ReferenceError|SyntaxError|not a function/.test(e)).length,0,errors.join('; '));
      if(sport==='kyotei'){
        // Missing licensed feed must have an explicit status on the top page.
        const raceCount=await page.locator('.arv-all-race[data-race]').count();
        if(raceCount===0)assert.match(await page.locator('.boat-notice').first().innerText(),/未配信|確認|未接続/);
      }
      console.log('PRODUCTION_PULL_REFRESH_OK',browserName,sport,second.after);
    }
    await page.close();
  }finally{await browser.close()}
}
(async()=>{await check(chromium,'chromium');await check(webkit,'webkit')})().catch(e=>{console.error(e);process.exit(1)});
