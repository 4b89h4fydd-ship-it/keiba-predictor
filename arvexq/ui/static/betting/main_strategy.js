/* ARVEXQ: independent main strategy (internal model weights, not calibrated probabilities). */
(function(global){
'use strict';
function apply(ctx){
 const {ready,winClear,order,lists,top,add,result,hasHonmei,fieldSize}=ctx;
 const field=Math.max(5,Number(fieldSize)||8),
       wideFloor=Math.max(.095,9.9/(field*(field-1))),
       quinFloor=Math.max(.075,6.6/(field*(field-1))),
       trioFloor=Math.max(.055,27/(field*(field-1)*Math.max(1,field-2)));
 if(!hasHonmei){
   if(global.ARVEXQNoAxisBet&&typeof global.ARVEXQNoAxisBet.apply==='function')
     global.ARVEXQNoAxisBet.apply(ctx);
   else {result.primaryKind='';ctx.reason='軸なし買い目モジュール未取得'}
   return;
 }
  // One main ticket family: place reliability and ordered certainty decide
  // the type. No multiple identical opinions through several ticket kinds.
  if(ready){
    var kind='';
    if(winClear&&order>=.45&&lists['馬単'][0]&&lists['馬単'][0].weight>=.075)kind='馬単';
    else if(lists['馬連'][0]&&lists['馬連'][0].weight>=quinFloor)kind='馬連';
    else if(lists['3連複'][0]&&lists['3連複'][0].weight>=trioFloor&&top.weight<.30)kind='3連複';
    else if(lists['ワイド'][0]&&lists['ワイド'][0].weight>=wideFloor)kind='ワイド';
    if(kind){
      var pool=lists[kind],max=kind==='3連複'?3:2,cut=pool[0].weight*.70,combos=[];
      pool.some(function(z){if(combos.length>=max||combos.length>=1&&z.weight<cut)return true;combos.push(z.combo);return false});
      add('本線',kind,combos,'着順別モデルの相対集中度・点数を比較して'+kind+'を優先。配当オッズ未検証のため数値的な期待値は未算出。');
      result.primaryKind=kind;
    }else{result.primaryKind='';ctx.reason='本線に適した券種の集中度が不足'}
  }else result.primaryKind='';
}

const old=global.ARVEXQBetStrategies||{};
global.ARVEXQBetStrategies=Object.freeze(Object.assign({},old,{main:apply}));
})(window);
