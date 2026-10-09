// Offline iPhone-width UI regression using actual betting subpage render functions.
// Requires Playwright (installed by ARVEXQ Webapp Race Smoke).
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium,webkit,devices}=require('playwright');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const css=['arvexq/ui/static/styles.css','arvexq/ui/static/styles/legacy_v118_v221.css',
 'arvexq/ui/static/styles/race_v222_plus.css','arvexq/ui/static/betting/bet_ui.css']
 .map(p=>fs.readFileSync(p,'utf8')).join('\n');
const betView=fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
function extract(start,end){
  const a=src.indexOf('function '+start+'(');
  const b=src.indexOf('function '+end+'(',a+1);
  assert.ok(a>=0&&b>a,'missing function '+start);
  return src.slice(a,b);
}
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
const n=(v,f=0)=>v!==null&&v!==undefined&&Number.isFinite(Number(v))?Number(v):f;
const triCombos=[[4,6,2],[4,2,6],[4,7,2],[4,2,7],[4,6,8],[4,8,6],[4,7,8],[4,8,7],[4,2,8],[4,8,2],[4,6,7],[4,7,6]];
const plan={decision:'通常買い',scenario:'前残り',scenarioProb:.4,betQuality:72,
  items:[
    {level:'本線',kind:'馬連',combos:[[4,6],[4,2]],points:2,combo:'4 - 6 / 4 - 2',reason:'的中重視'},
    {level:'3連単チャレンジ',kind:'3連単',combos:triCombos,points:12,combo:triCombos.map(c=>c.join(' → ')).join(' / '),reason:'展開AIによる着順別比較'},
    {level:'保険',kind:'ワイド',combos:[[6,7]],points:1,combo:'6 - 7',reason:'1着固定の逆転補完'},
  ],trifectaReviewed:true,trifectaDecision:'採用',
  insuranceDecision:'採用',referenceBudget:{points:15,totalYen:1500},expectedValue:null,
  expectedValueReason:'未校正の的中確率から期待値は算出しません。',
  reason:'三方式のモデル別選定。'};
const renderer=new Function('window','esc','n','buildAiBetPlan','officialRaceLinks','aiBetExplanationHtml','cinematicFooter',
  betView+'\n'+
  "function aiBetRecommendation(r,p){return window.ARVEXQBetView.render(r,p,{buildAiBetPlan,esc,n,isFinal:()=>false,raceMarkClock:()=>({started:false}),aiBetExplanationHtml,betComboText:(k,cs)=>cs.map(c=>c.join(k===\'3連単\'?\' → \':\' - \')).join(\' / \')});}\n"+
  extract('raceSubpageTopBar','horseDetailPage')+
  extract('betDetailPage','renderRace')+
  '\nreturn betDetailPage;');
const html=renderer({},esc,n,()=>plan,()=>({vote:''}),
  ()=>'<section class="ai-bet-why"><b>この買い目になった理由</b><p>購入は見送り</p></section>',()=>'')(
    {track:'大井',raceNumber:7},{}
  );
assert.match(html,/smart-race-subpage-topbar/);
assert.match(html,/bet-detail-page-shell/);
assert.match(html,/内部評価/);
assert.match(html,/本線｜的中重視/);
assert.match(html,/3連単チャレンジ｜高配当重視/);
assert.match(html,/保険｜本線補完/);
assert.match(html,/class="arv-three-combos"/,'tickets should be visually separated');
assert.match(html,/class="arv-bet-quality"/,'bet confidence displayed clearly');
assert.match(html,/【単】/);
assert.match(html,/☆\+/);

const legacyPlan={...plan,engineVersion:'arvexq-bets-old-v317',
  fixedAt:'2026-10-08T10:20:00+09:00',
  items:[{level:'通常',kind:'馬連',points:1,combos:[[2,6]],combo:'2 - 6'}]};
const historical=renderer({},esc,n,()=>legacyPlan,()=>({vote:''}),
  ()=>'',()=>'')({track:'大井',raceNumber:7},{});
assert.match(historical,/発走前保存済み買い目（旧方式）/);
assert.match(historical,/2 - 6/,'old picks must not vanish when new sections replace legacy');
assert.doesNotMatch(historical,/本線｜的中重視/,'old ticket is not relabelled');

function extractFunction(name){
  const a=src.indexOf('function '+name+'('),b=src.indexOf('\n}',a);
  assert.ok(a>=0&&b>a,'missing function '+name);
  return src.slice(a,b+2);
}
const navFactory=new Function('state',extractFunction('cinematicTabs')+'\nreturn cinematicTabs;');
const navHtml=navFactory({openPanel:'entry'})({});
assert.equal((navHtml.match(/data-panel="/g)||[]).length,3);
assert.match(navHtml,/data-panel="bets"/);
const stagePages=[
  {key:'start',visualKey:'first',label:'スタート',index:0},
  {key:'turn3',visualKey:'turn3',label:'3C',index:1},
  {key:'turn4',visualKey:'turn4',label:'4C',index:2},
  {key:'straight',visualKey:'straight',label:'ラスト',index:3},
];
const diagramFactory=new Function('paceStagePack','n','clamp','esc','PACE_STAGE_PAGES',
  extractFunction('paceFormationDiagram')+'\nreturn paceFormationDiagram;');
const diagrams=stagePages.map((cfg)=>{
  return diagramFactory(
    ()=>[1,2,3,4,5].map((no,i)=>({no,lane:i-2})),
    n,(v,a,b)=>Math.max(a,Math.min(b,v)),esc,stagePages
  )({horses:[1,2,3,4,5].map(no=>({horseNumber:no,frameNumber:no,name:'テスト馬'+no}))},{},cfg);
});
assert.deepEqual(diagrams.map(x=>Number((x.match(/data-pace-next="(\d+)"/)||[])[1])),[1,2,3,0]);
assert.ok(!src.includes('data-action="open-bets-page" class="race-nav-v230-btn active"'));
assert.ok(src.includes("els=document.querySelectorAll('[data-pace-next]')"));

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
          tickets:[...document.querySelectorAll('.arv-three-ticket>strong')].map(e=>({x:e.getBoundingClientRect().x,right:e.getBoundingClientRect().right})),
          combos:[...document.querySelectorAll('.arv-three-combo')].map(e=>({x:e.getBoundingClientRect().x,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})),
          markBadges:[...document.querySelectorAll('.bet-mark-grid i')].filter(e=>['【単】','☆+'].includes(e.textContent)).map(e=>{
            const b=e.getBoundingClientRect();return {text:e.textContent,width:b.width,height:b.height,whiteSpace:getComputedStyle(e).whiteSpace};
          }),
          titleText:document.querySelector('.smart-race-subpage-topbar .smart-race-head-copy strong').textContent};
      });
      const e=2;
      assert.equal(result.titleText,'買い目');
      assert.ok(result.title.width>=95,label+' '+width+' clipped title '+JSON.stringify(result));
      assert.ok(result.title.x>=result.left.right-e,label+' '+width+' title overlaps back');
      assert.ok(result.title.right<=result.right.x+e,label+' '+width+' title overlaps close');
      assert.ok(result.header.top>=-e,label+' '+width+' header off-screen');
      assert.ok(result.scroll<=result.width+e,label+' '+width+' document horizontal scroll');
      for(const ticket of result.tickets){assert.ok(ticket.x>=result.box.x-e&&ticket.right<=result.box.right+e,label+' '+width+' ticket overflow '+JSON.stringify(result));}
      assert.equal(result.markBadges.length,2,label+' '+width+' missing mark badges');
      for(const mark of result.markBadges){
        assert.ok(mark.width>=50&&mark.height<=45&&mark.whiteSpace==='nowrap',
          label+' '+width+' mark badge wraps '+JSON.stringify(mark));
      }
      assert.ok(result.combos.length>=2,label+' '+width+' missing separate ticket combinations');
      for(const combo of result.combos){
        assert.ok(combo.x>=result.box.x-e&&combo.right<=result.box.right+e,
          label+' '+width+' ticket combination off-screen '+JSON.stringify(combo));
      }
      for(const pill of result.pills){
        assert.ok(pill.x>=result.box.x-e&&pill.right<=result.box.right+e,
          label+' '+width+' metadata off-screen '+JSON.stringify(result));
      }
      // Three race tabs plus tappable formation are also checked at every width.
      for(let stage=0;stage<4;stage++){
        const app='<div class="smart-shell"><main class="smart-main smart-race-page">'+navHtml+diagrams[stage]+'</main></div>';
        await page.setContent('<!doctype html><html lang="ja"><head><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'+app+'</body></html>');
        await page.addStyleTag({content:css});
        const resultStage=await page.evaluate(()=>{
          const el=document.querySelector('.pace-formation-next');
          const tabs=[...document.querySelectorAll('.race-nav-v230-top .race-nav-v230-btn')];
          return {width:innerWidth,scroll:document.documentElement.scrollWidth,
            next:el&&Number(el.getAttribute('data-pace-next')),
            buttonWidth:el&&el.getBoundingClientRect().width,
            tabWidths:tabs.map(t=>t.getBoundingClientRect().width)};
        });
        assert.equal(resultStage.next,(stage+1)%4,label+' '+width+' stage cycle '+stage);
        assert.equal(resultStage.tabWidths.length,3);
        assert.ok(resultStage.tabWidths.every(w=>w>60),label+' '+width+' tab labels too narrow');
        assert.ok(resultStage.buttonWidth>200,label+' '+width+' diagram too narrow');
        assert.ok(resultStage.scroll<=resultStage.width+2,label+' '+width+' stage overflow '+JSON.stringify(resultStage));
      }
      console.log('BET_STAGE_TABS_CYCLE_LAYOUT_OK '+label+' '+width+'px');
            console.log('BET_MOBILE_LAYOUT_OK '+label+' '+width+'px');
      await context.close();
    }
  }finally{await browser.close();}
}
(async()=>{await test(chromium,'chromium');await test(webkit,'webkit')})().catch(error=>{
  console.error(error);process.exit(1);
});
