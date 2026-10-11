/* Independent trifecta decisions: ◎ role never invents an ordered finish. */
(function(global){
'use strict';
function apply(ctx){
 const {ready,winClear,order,top12,top24,ordered,top,p1,add,result,
   trifectaReady,fixedAxis,axisNo,axisRole,axisGrade}=ctx;
 // A/B axis is necessary, not sufficient. C retains an unordered main only.
 const winnerAligned=axisRole==='win'&&top.no===axisNo;
 const axisOtherWinner=axisRole==='axis'&&top.no!==axisNo;
 let triAllowed=ready&&trifectaReady&&fixedAxis&&winClear&&
   order>=(axisRole==='win'?.42:.50)&&top12>=.115&&
   top24>0&&top12/top24>=.54&&ordered.length>=12&&
   (winnerAligned||axisOtherWinner);
 // 1着向き uses ◎ in the first position. 3着内軸向き allows ◎ in 2nd/3rd
 // only when the independent first-place model identifies another winner.
 let chosen=ordered.filter(z=>z.combo[0]===(winnerAligned?axisNo:top.no)&&
    (winnerAligned||z.combo[1]===axisNo||z.combo[2]===axisNo)).slice(0,12);
 const winningMass=p1.filter(x=>x>=top.weight*.80).length;
 if(winningMass>2||chosen.length<6)triAllowed=false;
 if(triAllowed){
   const cutoff=chosen[0].weight*.38;
   chosen=chosen.filter(z=>z.weight>=cutoff).slice(0,12);
   if(chosen.length<6)triAllowed=false;
 }
 if(triAllowed){
   const combos=chosen.map(z=>z.combo);
   add('3連単チャレンジ','3連単',combos,
     '◎'+axisNo+'は'+(axisRole==='win'?'1着向きで1着固定':'3着内の軸向きで2/3着配置')+
     '。1着'+(winnerAligned?axisNo:top.no)+'は独立1着モデル、残りは条件付き着順で検証。');
   result.trifectaDecision='採用';
   result.trifectaReason='◎の役割と独立1着・2着・3着の根拠が一致。'+combos.length+'点で採用。';
   result.trifectaFirst=Array.from(new Set(combos.map(c=>c[0])));
   result.trifectaSecond=Array.from(new Set(combos.map(c=>c[1])));
   result.trifectaThird=Array.from(new Set(combos.map(c=>c[2])));
 }else{
   result.trifectaDecision='見送り';
   result.trifectaReason=!fixedAxis?
     (axisNo?'◎信頼度Cは軸固定できないため、3連単は見送り。':'◎を選べる根拠がないため3連単は見送り。'):
     !trifectaReady?'3連単の位置取り・順序根拠不足につき見送り。':
     axisRole==='axis'&&top.no===axisNo?'◎は3着内の軸向きであり、1着固定する根拠がないため見送り。':
     ready?(winClear?'展開・順序の集中度不足、または12点以内で絞れないため見送り。':
       '独立1着候補が十分に絞れず、固定のリスクが高いため見送り。'):ctx.reason;
   result.trifectaFirst=[];result.trifectaSecond=[];result.trifectaThird=[];
 }
 return triAllowed;
}
const old=global.ARVEXQBetStrategies||{};
global.ARVEXQBetStrategies=Object.freeze(Object.assign({},old,{trifecta:apply}));
})(window);
