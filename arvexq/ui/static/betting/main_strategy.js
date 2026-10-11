/* ARVEXQ independent main ticket owner: ◎ role changes the purchase lane. */
(function(global){
'use strict';
function apply(ctx){
 const {ready,winClear,order,lists,top,add,result,fixedAxis,axisNo,axisRole,axisGrade,fieldSize}=ctx;
 const field=Math.max(5,Number(fieldSize)||8),
       wideFloor=Math.max(.085,6/(field*(field-1))),
       quinFloor=Math.max(.065,4/(field*(field-1))),
       trioFloor=Math.max(.042,16/(field*(field-1)*Math.max(1,field-2)));
 if(!fixedAxis){
   // Grade C is a relative favourite, not a bankable fixed axis.
   if(global.ARVEXQNoAxisBet&&typeof global.ARVEXQNoAxisBet.apply==='function')
     global.ARVEXQNoAxisBet.apply(ctx);
   else {result.primaryKind='';ctx.reason='軸固定できない買い目モジュール未取得'}
   return;
 }
 result.noAxis=false;result.primaryKind='';
 if(!ready)return;
 function candidates(kind){
   return (lists[kind]||[]).filter(z=>Array.isArray(z.combo)&&z.combo.includes(axisNo)&&
     (kind!=='馬単'||axisRole==='win'&&z.combo[0]===axisNo));
 }
 // 1着向き: 1着固定を検討できるのは勝ちモデルとも一致した場合だけ。
 // 軸向き: 同じ◎を勝手に1着固定せず、3連複/ワイド/馬連を優先。
 const families=axisRole==='win'?[
   {kind:'馬単',min:.075,allowed:winClear&&top.no===axisNo&&order>=.45,max:2},
   {kind:'馬連',min:quinFloor,allowed:true,max:2},
   {kind:'ワイド',min:wideFloor,allowed:true,max:3},
   {kind:'3連複',min:trioFloor,allowed:true,max:3}
 ]:[
   {kind:'3連複',min:trioFloor,allowed:axisGrade==='A',max:3},
   {kind:'ワイド',min:wideFloor,allowed:true,max:3},
   {kind:'馬連',min:quinFloor,allowed:true,max:2},
   {kind:'3連複',min:trioFloor,allowed:true,max:3}
 ];
 for(const family of families){
   if(!family.allowed)continue;
   const pool=candidates(family.kind);
   if(!pool.length||pool[0].weight<family.min)continue;
   const floor=pool[0].weight*.70;
   const combos=pool.filter(z=>z.weight>=floor).slice(0,family.max).map(z=>z.combo.slice());
   if(!combos.length)continue;
   add('本線',family.kind,combos,
     '◎'+axisNo+'は'+(axisRole==='win'?'1着向き':'3着内の軸向き')+
     '・信頼度'+axisGrade+'。'+family.kind+'の独立着順モデルで組み合わせを選出。');
   result.primaryKind=family.kind;
   return;
 }
 ctx.reason='◎'+axisNo+'の役割とモデル集中度を満たす本線の組み合わせが不足';
}
const old=global.ARVEXQBetStrategies||{};
global.ARVEXQBetStrategies=Object.freeze(Object.assign({},old,{main:apply}));
})(window);
