'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const window={};new Function('window',fs.readFileSync('arvexq/ui/static/research/local_evidence.js','utf8'))(window);
new Function('window',fs.readFileSync('arvexq/ui/static/research/research_view.js','utf8'))(window);
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const detail={date:'2026-10-09',horses:[{horseNumber:3,name:'実測馬'}],
 biasProvenance:{official:{condition:'良',source:'official-announcement'},estimated:{frontBack:'中立'}}};
const horse={horseNumber:3,researchEvidence:{
 factors:{items:[{key:'speed',label:'走破能力',measurements:[{key:'ability_clock_speed_median',value:16.1}]}]},
 sectionals:{runs:[{date:'2026-10-01',distance:1400,early3FSeconds:36.1,middle3FSeconds:null,late3FSeconds:37.8}]}}};
const view=window.ARVEXQResearchView.renderHorse(detail,horse,esc);
assert.match(view,/14項目の能力根拠/);
assert.match(view,/36.1秒/);
assert.match(view,/実測/);
assert.match(view,/AI推定は公式発表ではありません/);
assert.doesNotMatch(view,/undefined|NaN/);
const incomplete=window.ARVEXQResearchView.renderHorse(detail,{horseNumber:4},esc);
assert.match(incomplete,/取得待ち/);
const fallback=window.ARVEXQResearchView.renderHorse({...detail,date:'2026-10-09'},
 {horseNumber:4,frameNumber:2,jockey:'テスト騎手',recentRaces:[{date:'2026-10-01',finish:2,fieldSize:9,distance:1400,cornerPositions:[2,3],first3FSeconds:36.0}]},esc);
assert.match(fallback,/直近着順/);
assert.match(fallback,/36秒/);
assert.match(fallback,/出走表・過去走から得た確認可能な範囲/);
const result={...detail,result:{finishers:[{horseNumber:3,finish:1},{horseNumber:2,finish:2},{horseNumber:1,finish:3}]}};
assert.equal(window.ARVEXQResearchView.renderRecap(result,esc,false),'','no pre-race replay');
assert.match(window.ARVEXQResearchView.renderRecap(result,esc,true),/映像・不利・騎手の意図は未確認/);
assert.doesNotMatch(window.ARVEXQResearchView.renderRecap(result,esc,true),/ペース想定通り/);
console.log('ARVEXQ_RESEARCH_VIEW_OK');
