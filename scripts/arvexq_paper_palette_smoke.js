/* Contrast regression against the actual ARVEXQ browser CSS cascade. */
const {chromium,webkit,devices}=require('playwright');
const assert=require('node:assert/strict');
const base=(process.env.ARVEXQ_BASE_URL||'http://127.0.0.1:8790').replace(/\/$/,'');
const FOCUS=new Set((process.env.ARVEXQ_PAPER_FOCUS||'').split(',').filter(Boolean));
const focus=k=>!FOCUS.size||FOCUS.has(k);
const fixture=[
 '<div class="smart-shell paper-race"><header class="smart-topbar smart-topbar-clean smart-race-topbar"><div class="smart-head-copy"><strong>園田 1R</strong></div></header><main class="smart-main smart-race-page"><div class="race-nav-v230"><div class="race-nav-v230-row race-nav-v230-top"><button class="race-nav-v230-btn active"><span class="race-nav-v230-label">出走表</span></button></div></div></main></div>',
 '<div class="smart-shell paper-special"><header class="smart-topbar smart-section-topbar arv-dated-subbar"><div class="smart-head-copy"><strong>地方 特別予想</strong></div></header><main class="smart-main smart-home-subpage"><section class="smart-fixed-picks arv-direct-picks"><div class="smart-fixed-picks-head"><span><b>地方 特別予想</b><small>メイン・重賞</small></span></div><div class="fixed-pick-box-body"><button class="fixed-pick-row arv-direct-pick-row"><span><b>園田11R</b><small>開催レース</small></span><time>16:05</time></button></div></section></main></div>',
 '<div class="smart-shell pace-stage-shell paper-pace"><header class="smart-topbar smart-race-topbar pace-stage-topbar"><div class="pace-stage-top-title"><strong>スタート</strong></div></header><main class="smart-main smart-race-page pace-stage-page"><section class="pace-stage-explain"><h2>スタート直後</h2><p class="pace-stage-narrative">隊列予想</p></section><section class="pace-formation-card"><div class="pace-formation-track">隊列図</div></section></main></div>',
 '<div class="smart-shell horse-detail-page-shell paper-horse"><header class="smart-topbar smart-race-topbar horse-detail-topbar"><div class="horse-detail-top-title"><strong>馬詳細</strong></div></header><main class="smart-main smart-race-page horse-detail-page"><section class="card"><div class="horse-detail"><div class="runner-overall-box"><div class="runner-overall-head"><span class="label">AI総合評価</span></div></div><div class="horse-info-grid"><div class="horse-info-cell"><small>騎手</small><b>未取得</b></div></div></div></section></main></div>',
 '<div class="smart-shell bet-detail-page-shell paper-bet"><main class="smart-main smart-race-page"><section class="card bet-card-clean"><div class="arv-three-bet"><div class="arv-three-section"><h3>本線</h3></div></div></section></main></div>'
].join('');
const selectors={
 raceHeader:'.paper-race>header',raceHeaderTitle:'.paper-race .smart-head-copy strong',
 raceTabFrame:'.paper-race .race-nav-v230-top',raceTab:'.paper-race .race-nav-v230-btn',
 specialHeader:'.paper-special>header',specialText:'.paper-special .smart-fixed-picks-head b',
 specialSubtitle:'.paper-special .smart-fixed-picks-head small',
 specialRowText:'.paper-special .fixed-pick-row small',
 paceHeader:'.paper-pace>header',paceExplanation:'.paper-pace .pace-stage-explain',
 paceDiagram:'.paper-pace .pace-formation-card',paceTrack:'.paper-pace .pace-formation-track',
 horseHeader:'.paper-horse>header',horseOverall:'.paper-horse .runner-overall-head',
 horseInfo:'.paper-horse .horse-info-cell',betSection:'.paper-bet .arv-three-bet'
};
function brightness(rgb){const m=String(rgb||'').match(/\d+(?:\.\d+)?/g);return m&&m.length>=3?m.slice(0,3).reduce((s,v)=>s+Number(v),0):0}
async function run(browserType,name){
 const browser=await browserType.launch({headless:true});
 try{
  const page=await browser.newPage({...devices['iPhone 15 Pro'],locale:'ja-JP'});
  await page.goto(base+'/?paper-probe='+Date.now(),{waitUntil:'domcontentloaded',timeout:50000});
  const actualTheme=await page.locator('meta[name="theme-color"]').getAttribute('content');
  assert.equal(actualTheme,'#f6f2e8','Browser chrome must use the approved paper background');
  // PWA can replace the document after domcontentloaded; retry only navigation races.
  let output;
  for(let attempt=0;attempt<4;attempt++){
   try{
    output=await page.evaluate(({fixture,selectors})=>{
   const root=document.createElement('div');root.style.cssText='position:absolute;top:0;left:-9999px;width:393px';
   root.innerHTML=fixture;document.body.appendChild(root);
   const values={};
   for(const [k,selector] of Object.entries(selectors)){
    const el=root.querySelector(selector);if(!el){values[k]=null;continue}
    const css=getComputedStyle(el);values[k]={bg:css.backgroundColor,text:css.color,opacity:css.opacity};
   }
   root.remove();return values;
    },{fixture,selectors});
    break;
   }catch(error){
    if(attempt===3||!/Execution context was destroyed|most likely because of a navigation/i.test(String(error)))throw error;
    await page.waitForLoadState('domcontentloaded',{timeout:30000});
   }
  }
  for(const k of ['raceHeader','raceTabFrame','raceTab','specialHeader','paceHeader','paceExplanation','paceDiagram','paceTrack','horseHeader','horseOverall','horseInfo','betSection']){
   if(!focus(k))continue;
   assert.ok(output[k]&&brightness(output[k].bg)>490,'Dark background '+name+'/'+k+': '+JSON.stringify(output[k]));
  }
  for(const k of ['raceHeaderTitle','specialText','specialSubtitle','specialRowText']){
   if(!focus(k))continue;
   assert.ok(output[k]&&brightness(output[k].text)<200,'Pale text '+name+'/'+k+': '+JSON.stringify(output[k]));
   assert.equal(output[k].opacity,'1','Low-opacity text '+name+'/'+k);
  }
  console.log('PAPER_THEME_COMPUTED_BROWSER_OK',name);
 }finally{await browser.close()}
}
(async()=>{await run(chromium,'chromium');await run(webkit,'webkit')})().catch(e=>{console.error(e);process.exit(1)});
