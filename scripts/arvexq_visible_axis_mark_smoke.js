'use strict';
// Regression for screenshot: a live ◎【軸】 candidate must not display "—"
// in the leftmost racecard mark cell. This is presentation-only; do not
// rewrite official core marks, locked originals or betting inputs.
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
function span(start,end){
  const a=src.indexOf('function '+start+'('),b=src.indexOf('function '+end+'(',a+1);
  assert(a>=0&&b>a,start+' function boundaries');
  return src.slice(a,b);
}
const isScratchHorse=h=>!!(h&&(h.scratched||h.withdrawn||/取消|除外|欠場/.test(h.status||'')));
const roleFactory=new Function('window','isScratchHorse',
  span('markRoleLabel','racecardMarkLegend')+
  'return {markRoleLabel,visiblePredictionMark,honmeiA11yText}');
const {markRoleLabel,visiblePredictionMark,honmeiA11yText}=roleFactory(require('./test_support/production_ui.cjs').window,isScratchHorse);
const horse={horseNumber:6,name:'ホウオウバトラー',frameNumber:5,
  sex:'牡',age:3,jockey:'小笠鈴'};
const x={horse,predMark:'',preOffAxisCandidate:true,markFrozen:false};
assert.equal(markRoleLabel(x),'');
assert.equal(visiblePredictionMark(x),'');
assert.equal(x.predMark,'','original marks must not be mutated by display');
assert.equal(visiblePredictionMark({...x,preOffAxisCandidate:false}),'');
assert.equal(visiblePredictionMark({...x,predMark:'△'}),'',
  'retired mark cannot be restored');
assert.equal(visiblePredictionMark({...x,horse:{...horse,scratched:true}}),'',
  'scratched runners cannot display fabricated marks');
assert.equal(visiblePredictionMark({...x,markFrozen:true,preOffAxisCandidate:false,
  podiumAxisEligible:false,honmeiRole:'axis'}),'',
  'do not fabricate marks from legacy frozen axis metadata');
// Actually execute the production racecard renderer, including its mark box.
const render=new Function('isScratchHorse','n','horseDisplayName','clamp',
  'currentBodyWeight','currentBodyWeightChange','referenceBodyWeight','esc',
  'markRoleLabel','visiblePredictionMark','honmeiA11yText','racecardMarkDisplay',
  'racecardOddsHtml','carriedWeightText',
  fs.readFileSync('arvexq/components/item_180/routes.js','utf8')+'\n'+
  span(src.includes('function _arvexq_original_racecardEntryRow(')?
    '_arvexq_original_racecardEntryRow':'racecardEntryRow','morningSavedMarkRows')+
  'return racecardEntryRow')(
  isScratchHorse,(n,d=0)=>Number(n)||d,(_,h)=>h.name,(v,a,b)=>Math.max(a,Math.min(b,v)),
  ()=>0,()=>null,()=>0,s=>String(s),markRoleLabel,visiblePredictionMark,honmeiA11yText,
  m=>String(m||'—'),()=>'<em>odds</em>',()=> '55kg');
const html=render({},horse,x);
assert.match(html,/class="rc-mark-box rc-ai-mark" data-ai-mark=""/);
assert.match(html,/<span class="rc-mark-main">—<\/span>/);
assert.doesNotMatch(html,/class="rc-honmei-role"/);
assert.equal(x.predMark,'','HTML rendering cannot rewrite underlying score');
const off=render({},horse,{...x,preOffAxisCandidate:false});
assert.match(off,/data-ai-mark=""/);
assert.match(off,/<span class="rc-mark-main">—<\/span>/);
const scratch=render({},{...horse,scratched:true},{...x,horse:{...horse,scratched:true}});
assert.doesNotMatch(scratch,/data-ai-mark="◎"/);
for(const target of [
  "racecardMarkDisplay(visiblePredictionMark(x))",
  "window.ARVEXQMarkFrame.render()",
  "data-ai-mark=\"'+esc(visiblePredictionMark(x))",
])assert(src.includes(target),'display authority missing '+target);
console.log('UNIFIED_VISIBLE_HONMEI_OK no_independent_axis_promotion existing_marks_untouched frozen_immutable');
