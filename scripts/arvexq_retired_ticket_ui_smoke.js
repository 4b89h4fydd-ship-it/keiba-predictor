const assert=require('node:assert/strict'),fs=require('node:fs');
// 2026-11-28 shell migration (commit 827df37): the entry-table shell has
// no bet UI and no in-app bet engine filter (currentBetEnginePlan /
// frozenAiBetForRace were removed with the rich UI), so retired tickets
// cannot be displayed by the shell at all. That absence is now pinned
// directly; the isolated bet_view.js renderer contract below is
// unchanged from the original smoke.
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['function currentBetEnginePlan(','function frozenAiBetForRace(',
  'function buildAiBetPlan(','ARVEXQBetView'])
  assert(!src.includes(retired),'retired bet UI wiring must stay removed: '+retired);
const code=fs.readFileSync('arvexq/ui/static/betting/bet_view.js','utf8');
const root={};new Function('window',code)(root);
const base={fixedAt:'2026-10-12T21:54:31.159Z',items:[{level:'本線',kind:'馬連',combos:[[8,11],[6,11]]}]};
const deps={buildAiBetPlan:()=>({...base,engineVersion:'arvexq-old-v345'}),
esc:String,n:Number,isFinal:()=>false,raceMarkClock:()=>({started:false}),
aiBetExplanationHtml:()=>'',betComboText:()=>''};
const html=root.ARVEXQBetView.render({}, {}, deps);
assert(html.includes('おすすめ買い目'));
assert(!html.includes('発走前保存済み買い目（旧方式）'));
assert(!html.includes('旧方式の買い目は現在の予想に表示しません'));
console.log('RETIRED_BET_TICKETS_HIDDEN_FROM_LIVE_UI_OK');
