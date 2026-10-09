/* ARVEXQ: independent insurance strategy (internal model weights, not calibrated probabilities). */
(function(global){
'use strict';
function apply(ctx){
 const {result,runner,lists,top,add,triAllowed}=ctx;
  if(triAllowed&&result.primaryKind){
    // Hedge specifically against a different winner, not the same first-place
    // opinion. Do not duplicate a combination already present in the main.
    var main=result.items.filter(function(z){return z.level==='本線'})[0],
        isDuplicate=function(kind,combo){return !!(main&&main.kind===kind&&main.combos.some(function(x){return x.join('-')===combo.join('-')}))},
        backup=runner.no,insurance=null;
    ['馬連','ワイド'].some(function(kind){
      var hits=lists[kind].filter(function(z){return z.combo.indexOf(backup)>=0&&!isDuplicate(kind,z.combo)&&!(main&&main.combos.some(function(c){return c.length===2&&c.slice().sort(function(a,b){return a-b}).join('-')===z.combo.slice().sort(function(a,b){return a-b}).join('-')}))});
      if(!hits.length)return false;
      // Hedge against 1st reversal; still need a high-ranked complement.
      if(hits[0].weight<(kind==='ワイド'?.13:.09))return false;
      insurance={kind:kind,combos:[hits[0].combo]};return true
    });
    if(insurance){
      add('保険',insurance.kind,insurance.combos,'3連単の1着'+top.no+'固定が崩れ、'+backup+'が勝ち負けする分岐を補完。既存本線との組み合わせ重複なし。');
      result.insuranceDecision='採用';
      result.insuranceReason='1着逆転の別展開を最小1点で補完';
    }else result.insuranceReason='本線と重複するか、独立した補完根拠が不足するため見送り';
  }else result.insuranceReason='3連単未採用、または本線不成立のため保険を追加しない';
}

const old=global.ARVEXQBetStrategies||{};
global.ARVEXQBetStrategies=Object.freeze(Object.assign({},old,{insurance:apply}));
})(window);
