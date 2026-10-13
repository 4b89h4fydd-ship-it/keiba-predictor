const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function currentBetEnginePlan('),stop=src.indexOf('function frozenAiBetForRace(',start);
assert(start>=0&&stop>start);
const filter=new Function(src.slice(start,stop)+'return currentBetEnginePlan')();
const base={fixedAt:'2026-10-12T21:54:31.159Z',items:[{level:'本線',kind:'馬連',combos:[[8,11],[6,11]]}]};
assert.equal(filter({...base,engineVersion:'arvexq-old-v345'}),null);
assert.equal(filter({...base,engineVersion:'three-way-v346'}),null);
assert.equal(filter({...base,engineVersion:undefined}),null);
const modern={...base,engineVersion:'arvexq-true-run-pure-sectional-v2'};
assert.equal(filter(modern),modern);
const code=fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
const root={};new Function('window',code)(root);
const deps={buildAiBetPlan:()=>({...base,engineVersion:'arvexq-old-v345'}),
esc:String,n:Number,isFinal:()=>false,raceMarkClock:()=>({started:false}),
aiBetExplanationHtml:()=>'',betComboText:()=>''};
const html=root.ARVEXQBetView.render({}, {}, deps);
assert(!html.includes('8 - 11')&&!html.includes('6 - 11'));
assert(!html.includes('発走前保存済み買い目（旧方式）'));
assert(html.includes('旧方式の買い目は現在の予想に表示しません'));
console.log('RETIRED_BET_TICKETS_HIDDEN_FROM_LIVE_UI_OK');
