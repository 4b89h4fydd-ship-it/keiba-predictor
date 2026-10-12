/* iPhone Chromium/WebKit smoke: the ONLY home listings are per-venue 1R-12R. */
const {chromium,webkit,devices}=require("playwright");
const assert=require("node:assert/strict");
const base=process.env.ARVEXQ_BASE_URL||"http://127.0.0.1:8788";
async function check(type,name){
  const browser=await type.launch({headless:true});
  try{
    const page=await browser.newPage({...devices["iPhone 15 Pro"],locale:"ja-JP"});
    await page.goto(base+"/keiba/?smoke=all-races",{waitUntil:"domcontentloaded",timeout:50000});
    const link=page.locator('.arvexq-sport-nav a[href="/kyotei/"]');
    await link.waitFor({state:"visible",timeout:45000});
    assert.equal(await link.evaluate(el=>{
      const b=el.getBoundingClientRect();
      if(b.top<0||b.bottom>innerHeight)return false;
      const found=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);
      return el===found||el.contains(found);
    }),true,name+" horse sport switch overlapped");
    await page.locator(".arv-all-panel").waitFor({state:"visible",timeout:35000});
    assert.equal(await page.locator(".arv-all-panel").getByText("各会場の全レース").count(),1);
    assert.equal(await page.locator(".arv-tb-live,.arv-tb-venues").count(),0);
    assert.equal(await page.locator(".arv-unified-hero img").count(),1);
    assert.equal(await page.locator(".arv-unified-date input[type=date]").count(),1);
    assert.equal(await page.locator(".arv-unified-actions button").count(),3);
    const horseOrder=await page.locator('.smart-home .arv-unified-body').evaluate(el=>
      [...el.children].map(x=>x.className).slice(0,3));
    assert.deepEqual(horseOrder,['arv-unified-date','arv-unified-actions','arv-all-panel'],
      name+' horse AI shortcuts must be DIRECTLY after date');
    await link.click({timeout:15000});
    await page.waitForURL(/\/kyotei\//,{timeout:30000});
    await page.locator(".arv-unified-hero").waitFor({state:"visible",timeout:30000});
    await page.locator(".arv-all-panel").waitFor({state:"visible",timeout:15000});
    assert.equal(await page.locator(".boat-venue-grid,.boat-live-panel").count(),0);
    assert.equal(await page.locator(".boat-home-actions").count(),0);
    assert.equal(await page.locator(".arv-unified-hero img").count(),1);
    assert.equal(await page.locator(".arv-unified-date input[type=date]").count(),1);
    assert.equal(await page.locator(".arv-unified-actions button").count(),3);
    const boatOrder=await page.locator('.boat-page .arv-unified-body').evaluate(el=>
      [...el.children].map(x=>x.className).slice(0,3));
    assert.deepEqual(boatOrder,['arv-unified-date','arv-unified-actions','arv-all-panel'],
      name+' BOAT AI shortcuts must be DIRECTLY after date');
    assert.equal(await page.locator(".boat-page-head").count(),0);
    await page.locator('.arv-unified-actions button[data-view="stats"]').click();
    await page.locator(".boat-stat-grid").waitFor({state:"visible",timeout:12000});
    await page.locator('.boat-subheader button[data-view="home"]').click();
    await page.locator('.arv-unified-actions button[data-view="special"]').click();
    await page.locator('.boat-panel').first().waitFor({state:"visible",timeout:12000});
    await page.locator('.boat-subheader button[data-view="home"]').click();
    await page.locator('.arv-unified-actions button[data-view="selected"]').click();
    await page.locator(".boat-panel").first().waitFor({state:"visible",timeout:12000});
    await page.locator('.boat-subheader button[data-view="home"]').click();
    const horseLink=page.locator('.arvexq-sport-nav a[href="/keiba/"]');
    assert.equal(await horseLink.evaluate(el=>{
      const b=el.getBoundingClientRect(),target=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);
      return target===el||el.contains(target);
    }),true,name+" boat sport switch overlapped");
    console.log(name+" ALL_RACES_ONLY_UI_OK");
  }finally{await browser.close()}
}
(async()=>{await check(chromium,"Chromium");await check(webkit,"WebKit")})().catch(error=>{console.error(error);process.exit(1)});
