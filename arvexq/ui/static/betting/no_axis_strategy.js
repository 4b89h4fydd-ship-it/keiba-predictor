/* ◎不在 or ◎信頼度C: never fix a weak axis. Model-relative weights are not hit probabilities. */
(function(global){
'use strict';
function apply(ctx){
 const {ready,lists,add,result,fieldSize}=ctx;
 const field=Math.max(5,Number(fieldSize)||8),
       wideFloor=Math.max(.085,6.0/(field*(field-1))),
       quinFloor=Math.max(.065,4.0/(field*(field-1))),
       trioFloor=Math.max(.042,16/(field*(field-1)*Math.max(1,field-2)));
 result.noAxis=true;result.primaryKind='';
 if(!ready){ctx.reason='◎の軸固定不可・購入に必要なデータが不足';return false;}
 const families=[{kind:'ワイド',min:wideFloor,cut:.69,max:3},
                 {kind:'馬連',min:quinFloor,cut:.72,max:2},
                 {kind:'3連複',min:trioFloor,cut:.72,max:3}];
 const choice=families.find(x=>(lists[x.kind]||[])[0]&&(lists[x.kind]||[])[0].weight>=x.min);
 if(!choice){ctx.reason='◎なし・着順を固定しない券種の相対集中度不足';return false;}
 const pool=lists[choice.kind]||[],floor=pool[0].weight*choice.cut;
 const combos=pool.filter(z=>z.weight>=floor&&Array.isArray(z.combo)&&
   z.combo.length===(choice.kind==='3連複'?3:2)&&
   z.combo.every(v=>Number.isInteger(v)&&v>0)&&new Set(z.combo).size===z.combo.length)
   .slice(0,choice.max).map(z=>z.combo.slice());
 if(!combos.length){ctx.reason='◎なし・有効な組み合わせが成立しない';return false;}
 add('本線',choice.kind,combos,'◎なし、または◎信頼度Cのため軸を固定しない。相対的な連対・3着内の組み合わせを比較。');
 result.primaryKind=choice.kind;result.noAxisPolicy='unordered-role-weights-v1';
 return true;
}
global.ARVEXQNoAxisBet=Object.freeze({apply,version:'unordered-role-weights-v1'});
})(window);