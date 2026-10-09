/* ARVEXQ: independent trifecta strategy (internal model weights, not calibrated probabilities). */
(function(global){
'use strict';
function apply(ctx){
 const {ready,winClear,order,top12,top24,ordered,top,p1,add,result,hasHonmei}=ctx;
  // Every race is reviewed. Never add a mandatory trifecta for a grade/special race.
  var triAllowed=ready&&hasHonmei&&winClear&&order>=.42&&top12>=.115&&
      top24>0&&top12/top24>=.54&&ordered.length>=12;
  var chosen=ordered.filter(function(z){return z.combo[0]===top.no}).slice(0,12);
  // A wider winning-field set would require over-budget coverage; abstain.
  var winningMass=p1.filter(function(x){return x>=top.weight*.80}).length;
  if(winningMass>2)triAllowed=false;
  if(chosen.length<6)triAllowed=false;
  if(triAllowed){
    // Add only competitive orders. A low-concentration tail is not padded to
    // manufacture a six-ticket challenge.
    var cutoff=chosen[0].weight*.38;
    chosen=chosen.filter(function(z){return z.weight>=cutoff}).slice(0,12);
    if(chosen.length<6)triAllowed=false;
  }
  if(triAllowed){
    var triCombos=chosen.map(function(z){return z.combo});
    add('3連単チャレンジ','3連単',triCombos,
      '独立1着候補'+top.no+'、条件付き2着・3着、展開AIの局面適合、順序集中度が購入条件を通過。');
    result.trifectaDecision='採用';
    result.trifectaReason='1着'+top.no+'軸・2着/3着は別モデル。'+triCombos.length+'点で規定の集中度を満たすため採用。';
    result.trifectaFirst=[top.no];result.trifectaSecond=Array.from(new Set(triCombos.map(function(c){return c[1]})));
    result.trifectaThird=Array.from(new Set(triCombos.map(function(c){return c[2]})));
  }else{
    result.trifectaDecision='見送り';
    result.trifectaReason=!hasHonmei?'◎を置ける軸がないため3連単は見送り。':ready?(winClear?'展開・順序の集中度不足、または12点以内では有力な着順を絞れないため見送り。':'独立1着候補が十分に絞れず、固定のリスクが高いため見送り。'):ctx.reason;
    result.trifectaFirst=[];result.trifectaSecond=[];result.trifectaThird=[];
  }
 return triAllowed;
}

const old=global.ARVEXQBetStrategies||{};
global.ARVEXQBetStrategies=Object.freeze(Object.assign({},old,{trifecta:apply}));
})(window);
