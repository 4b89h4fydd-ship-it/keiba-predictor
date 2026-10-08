// Offline iPhone-width UI regression using actual betting subpage render functions.
// Requires Playwright (installed by ARVEXQ Webapp Race Smoke).
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium,webkit,devices}=require('playwright');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const css=fs.readFileSync('arvexq/ui/static/styles.css','utf8');
function extract(start,end){
  const a=src.indexOf('function '+start+'(');
  const b=src.indexOf('function '+end+'(',a+1);
  assert.ok(a>=0&&b>a,'missing function '+start);
  return src.slice(a,b);
}
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
const n=(v,f=0)=>v!==null&&v!==undefined&&Number.isFinite(Number(v))?Number(v):f;
const plan={decision:'見送り',scenario:'前残り',scenarioProb:.4,betQuality:0,
  items:[],trifectaReviewed:true,trifectaDecision:'見送り',orderScore:0,
  reason:'券種選択の条件を満たさなかったため買い目を見送りました。'};
const renderer=new Function('esc','n','buildAiBetPlan','officialRaceLinks','aiBetExplanationHtml','cinematicFooter',
  extract('aiBetRecommendation','aiMarksPanel')+
  extract('raceSubpageTopBar','horseDetailPage')+
  extract('betDetailPage','renderRace')+
  '\nreturn betDetailPage;');
const html=renderer(esc,n,()=>plan,()=>({vote:''}),
  ()=>'<section class="ai-bet-why"><b>この買い目になった理由</b><p>購入は見送り</p></section>',()=>'')(
    {track:'大井',raceNumber:7},{}
  );
assert.match(html,/smart-race-subpage-topbar/);
assert.match(html,/bet-detail-page-shell/);
assert.match(html,/内部評価/);
async function test(type,label){
  const browser=await type.launch({headless:true});
  try{
    for(const width of [320,375,390,430]){
      const context=await browser.newContext({
        ...devices['iPhone 15 Pro'],viewport:{width,height:844},
        isMobile:true,hasTouch:true,deviceScaleFactor:3
      });
      const page=await context.newPage();
      await page.setContent('<!doctype html><html lang="ja"><head><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+html+'</body></html>');
      await page.addStyleTag({content:css});
      const result=await page.evaluate(()=>{
        const r=selector=>document.querySelector(selector).getBoundingClientRect();
        const header=r('.smart-race-subpage-topbar');
        const title=r('.smart-race-subpage-topbar .smart-race-head-copy strong');
        const left=r('.smart-race-subpage-topbar .smart-race-step');
        const right=r('.smart-race-subpage-topbar .smart-race-close');
        const box=r('.bet-detail-page-shell .ai-bet-box');
        const pills=[...document.querySelectorAll('.bet-detail-page-shell .ai-bet-meta>span')].map(e=>e.getBoundingClientRect());
        return {width:innerWidth,scroll:document.documentElement.scrollWidth,
          header:{top:header.top},title:{x:title.x,right:title.right,width:title.width},
          left:{right:left.right},right:{x:right.x},box:{x:box.x,right:box.right},
          pills:pills.map(x=>({x:x.x,right:x.right})),
          titleText:document.querySelector('.smart-race-subpage-topbar .smart-race-head-copy strong').textContent};
      });
      const e=2;
      assert.equal(result.titleText,'買い目');
      assert.ok(result.title.width>=95,label+' '+width+' clipped title '+JSON.stringify(result));
      assert.ok(result.title.x>=result.left.right-e,label+' '+width+' title overlaps back');
      assert.ok(result.title.right<=result.right.x+e,label+' '+width+' title overlaps close');
      assert.ok(result.header.top>=-e,label+' '+width+' header off-screen');
      assert.ok(result.scroll<=result.width+e,label+' '+width+' document horizontal scroll');
      for(const pill of result.pills){
        assert.ok(pill.x>=result.box.x-e&&pill.right<=result.box.right+e,
          label+' '+width+' metadata off-screen '+JSON.stringify(result));
      }
      console.log('BET_MOBILE_LAYOUT_OK '+label+' '+width+'px');
      await context.close();
    }
  }finally{await browser.close();}
}
(async()=>{await test(chromium,'chromium');await test(webkit,'webkit')})().catch(error=>{
  console.error(error);process.exit(1);
});
