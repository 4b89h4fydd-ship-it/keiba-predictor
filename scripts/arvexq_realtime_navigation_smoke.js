/* iPhone/WebKit + Chromium UI regression. Stubbed BOAT input is TEST-ONLY.
 * Never serves, commits, or deploys fabricated racecards.
 */
const {chromium,webkit,devices}=require('playwright');
const assert=require('node:assert/strict');

const base=(process.env.ARVEXQ_BASE_URL||'http://127.0.0.1:8790').replace(/\/$/,'');
const day=new Date(Date.now()+9*3600000).toISOString().slice(0,10);
const tm=(clock)=>day+'T'+clock+':00+09:00';
const records=[
 {id:'boat-'+day+'-桐生-01',venue:'桐生',raceNo:1,closeTime:'10:30',closeAt:tm('10:30'),title:'テスト予選',
  entries:Array.from({length:6},(_,i)=>({boatNo:i+1,name:'検証専用'+(i+1)}))},
 {id:'boat-'+day+'-桐生-02',venue:'桐生',raceNo:2,closeTime:'11:30',closeAt:tm('11:30'),title:'テスト予選',
  entries:Array.from({length:6},(_,i)=>({boatNo:i+1,name:'検証専用'+(i+1)}))},
 {id:'boat-'+day+'-大村-01',venue:'大村',raceNo:1,closeTime:'10:50',closeAt:tm('10:50'),title:'テスト予選',
  entries:Array.from({length:6},(_,i)=>({boatNo:i+1,name:'検証専用'+(i+1)}))}
];
const mock={version:'arvexq-boat-day-v1',verified:true,verifiedAt:tm('09:00'),date:day,races:records};
async function check(kind,name){
  const browser=await kind.launch({headless:true});
  try{
    const page=await browser.newPage({...devices['iPhone 15 Pro'],locale:'ja-JP'});
    const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/sports/boat-data/*.json*',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify(mock)
    }));
    await page.goto(base+'/kyotei/?date='+day+'&ui-test='+Date.now(),{waitUntil:'domcontentloaded',timeout:45000});
    const portal=page.locator('.boat-page .arv-all-panel');
    await portal.waitFor({state:'visible',timeout:30000});
    const cells=portal.locator('button.arv-all-race');
    await page.waitForFunction(()=>document.querySelectorAll('.boat-page .arv-all-panel button[data-race]').length===3,{timeout:20000});
    assert.equal(await cells.count(),24,name+' expected two 12R venue grids');
    assert.equal(await portal.locator('button.arv-all-race[data-race]').count(),3);
    assert.equal(await page.locator('.arv-realtime-section').count(),0);
    assert.equal(await page.locator('.arv-all-panel').count(),1);
    assert.equal(await page.getByText('開催場一覧',{exact:true}).count(),0);
    const timeline=await page.evaluate(([records,day])=>{
      const x=window.ARVEXQUnifiedHome;
      const start=new Date(day+'T10:20:00+09:00');
      const after=new Date(day+'T10:40:00+09:00');
      const a=x.liveModel('boat',records,day,start);
      const b=x.liveModel('boat',records,day,after);
      const before=a.find(z=>z.venue==='桐生'&&z.next);
      const afterNext=b.find(z=>z.venue==='桐生'&&z.next);
      const firstState=b.find(z=>z.venue==='桐生'&&z.number===1)?.status;
      x.syncLiveUI('boat',records,day,document,after);
      const firstButton=document.querySelector('button[data-race="'+records[0].id+'"]');
      return {first:before?.number,next:afterNext?.number,
        firstState,buttonElapsed:firstButton?.classList.contains('elapsed'),
        buttonLabel:firstButton?.querySelector('.arv-race-state')?.textContent,
        opacity:firstButton?Number(getComputedStyle(firstButton).opacity):1,
        allRaceButtons:document.querySelectorAll('.boat-page .arv-all-panel button.arv-all-race').length};

    },[records,day]);
    assert.equal(timeline.first,1);assert.equal(timeline.next,2);
    assert.equal(timeline.firstState,'elapsed');
    assert.equal(timeline.buttonElapsed,true);
    assert.equal(timeline.buttonLabel,'締切経過');
    assert.ok(timeline.opacity<0.8,name+' elapsed race was not visually darkened');
    assert.equal(timeline.allRaceButtons,24);
    await portal.locator('button[data-race="'+records[0].id+'"]').click({timeout:20000});
    await page.locator('.boat-entry-list .boat-entry').first().waitFor({state:'visible',timeout:20000});
    assert.equal(await page.locator('.boat-entry-list .boat-entry').count(),6);
    await page.locator('button[data-back="races"]').first().click();
    await page.locator('.boat-venue-race-grid').waitFor({state:'visible',timeout:20000});
    assert.equal(await page.locator('.boat-venue-race-grid button').count(),12);
    await page.locator('.boat-subheader button[data-view="home"]').click();
    await page.locator('.arv-all-panel').waitFor({state:'visible'});
    assert.equal(await page.locator('.arv-realtime-section').count(),0);
    assert.equal(errors.filter(x=>/ReferenceError|SyntaxError|TypeError/.test(x)).length,0,errors.join(';'));
    console.log('REALTIME_RACE_ROUTE_IOS_PARITY_OK',name);
  }finally{await browser.close()}
}
(async()=>{await check(chromium,'chromium');await check(webkit,'webkit')})().catch(e=>{console.error(e);process.exit(1)});
