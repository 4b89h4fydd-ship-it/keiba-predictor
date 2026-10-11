/* Verify the sport switch is actually tappable ABOVE the horse hero on iPhone. */
const {chromium,webkit,devices}=require("playwright");
const assert=require("node:assert/strict");
const base=process.env.ARVEXQ_BASE_URL||"http://127.0.0.1:8788";
async function check(type,name){
  const browser=await type.launch({headless:true});
  try{
    const page=await browser.newPage({...devices["iPhone 15 Pro"],locale:"ja-JP"});
    await page.goto(base+"/keiba/?smoke=boat-nav",{waitUntil:"domcontentloaded",timeout:50000});
    const link=page.locator('.arvexq-sport-nav a[href="/kyotei/"]');
    await link.waitFor({state:"visible",timeout:45000});
    const isTop=await link.evaluate(el=>{
      const b=el.getBoundingClientRect();
      if(b.top<0||b.bottom>innerHeight||b.width<50)return false;
      const target=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);
      return el===target||el.contains(target);
    });
    assert.equal(isTop,true,name+" boat switch is obscured by horse hero/overlay");
    await link.click({timeout:15000});
    await page.waitForURL(/\/kyotei\//,{timeout:30000});
    await page.locator(".boat-home-hero").waitFor({state:"visible",timeout:30000});
    await page.locator('.boat-home-actions button[data-view="stats"]').click();
    await page.locator(".boat-stat-grid").waitFor({state:"visible",timeout:10000});
    await page.locator('.boat-subheader button[data-view="home"]').click();
    await page.locator('.boat-home-actions button[data-view="selected"]').click();
    await page.locator(".boat-panel").first().waitFor({state:"visible",timeout:10000});
    await page.locator('.boat-subheader button[data-view="home"]').click();
    await page.locator('.boat-home-actions button[data-view="venues"]').click();
    await page.locator('.boat-venue-grid button[data-venue="桐生"]').click();
    await page.locator(".boat-subheader").waitFor({state:"visible",timeout:10000});
    const boatLink=page.locator('.arvexq-sport-nav a[href="/keiba/"]');
    assert.equal(await boatLink.evaluate(el=>{
      const b=el.getBoundingClientRect(),t=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);
      return t===el||el.contains(t);
    }),true,name+" horse switch is obscured on boat page");
    console.log(name+" DUAL_SPORT_UI_SMOKE_OK");
  }finally{await browser.close()}
}
(async()=>{await check(chromium,"Chromium");await check(webkit,"WebKit")})().catch(err=>{console.error(err);process.exit(1)});
