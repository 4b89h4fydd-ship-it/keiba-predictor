const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync('arvexq/ui/static/research/static_racecard.js','utf8');
const ctx={};new Function('window',source)(ctx);
const get=ctx.ARVEXQStaticRacecard.available;
const fixture={version:'arvexq-static-entry-v1',date:'2026-10-10',
  races:[{id:'jra-2026-10-10-東京-01',date:'2026-10-10',fieldSize:2,
    horses:[{horseNumber:1,name:'甲'},{horseNumber:2,name:'乙'}]}]};
(async()=>{
  let calls=0;
  const load=async path=>{calls++;assert.equal(path,'/racecards/2026-10-10.json');return fixture};
  let d=await get('2026-10-10','jra-2026-10-10-東京-01',load);
  assert.equal(d.horses.length,2);assert.equal(d._entryOnly,true);
  assert.equal(d._staticRacecardFallback,true);
  assert.equal(d.preRacePrediction,undefined);
  assert.equal(d.result,undefined);
  assert.equal(await get('2026-10-10','not-a-race',load),null);
  assert.equal(await get('invalid','jra-2026-10-10-東京-01',load),null);
  assert.equal(calls,1,'deduplicate dated JSON request');
  assert.equal(await get('2026-10-11','jra-2026-10-10-東京-01',
      async()=>({...fixture,date:'2026-10-11'})),null);
  console.log('STATIC_RACECARD_RESCUE_BROWSER_PASS');
})().catch(err=>{console.error(err);process.exitCode=1});
