/* No confirmed ◎: independent unordered ticket gate. Model-relative weights are not hit probabilities. */
(function(global){
'use strict';
function apply(ctx){
 const {ready,lists,add,result}=ctx;
 result.noAxis=true;result.primaryKind='';
 if(!ready){ctx.reason='◎なし・購入に必要なデータが不足';return false;}
 const families=[{kind:'ワイド',min:.20,cut:.69,max:3},
                 {kind:'馬連',min:.16,cut:.72,max:2},
                 {kind:'3連複',min:.11,cut:.72,max:3}];
 const choice=families.find(x=>(lists[x.kind]||[])[0]&&(lists[x.kind]||[])[0].weight>=x.min);
 if(!choice){ctx.reason='◎なし・着順を固定しない券種の相対集中度不足';return false;}
 const pool=lists[choice.kind]||[],floor=pool[0].weight*choice.cut;
 const combos=pool.filter(z=>z.weight>=floor&&Array.isArray(z.combo)&&
   z.combo.length===(choice.kind==='3連複'?3:2)&&
   z.combo.every(v=>Number.isInteger(v)&&v>0)&&new Set(z.combo).size===z.combo.length)
   .slice(0,choice.max).map(z=>z.combo.slice());
 if(!combos.length){ctx.reason='◎なし・有効な組み合わせが成立しない';return false;}
 add('本線',choice.kind,combos,'◎は不在。2・3着内の相対的な組み合わせを比較。馬単・3連単は採用しない。');
 result.primaryKind=choice.kind;result.noAxisPolicy='unordered-role-weights-v1';
 return true;
}
global.ARVEXQNoAxisBet=Object.freeze({apply,version:'unordered-role-weights-v1'});
})(window);