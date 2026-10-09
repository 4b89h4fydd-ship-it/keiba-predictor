/* ARVEXQ: race selection by ticket objective, frozen once in the morning.
   Relative model concentration is NOT a calibrated hit rate or expected return. */
(function(global){
'use strict';
const VERSION='arvexq-morning-ticket-lanes-v1';
const NAMES=['的中重視型','勝ち馬明確型','高配当狙い型'];
function num(x,d=0){return x===null||x===undefined||x===''||!Number.isFinite(Number(x))?d:Number(x)}
function clamp(x){return Math.max(0,Math.min(1,num(x)))}
function rankedRole(x,which){
 const keys=which===2?['ticketP2Probability','p2Probability']:['ticketP3Probability','p3Probability'];
 for(const k of keys){if(x&&x[k]!==undefined&&x[k]!==null&&Number.isFinite(Number(x[k])))return Math.max(0,Number(x[k]))}
 return null;
}
function classify(r,p,strict){
 const rows=((p&&p.rows)||[]).filter(z=>z&&z.horse&&num(z.horse.horseNumber)>0&&!z.horse.scratched&&!z.horse.withdrawn&&!/取消|除外|欠場/.test(String(z.horse.status||'')));
 const isCentral=String(r&&r.circuit||'')==='中央',field=rows.length,a=strict||{},
       ready=clamp(a.readiness&&a.readiness.prediction),
       coverage=clamp(p&&p.coverage),evidence=clamp(a.evidence),
       scenario=clamp(a.scenarioProb),top3=clamp(a.top3mass),
       margin=clamp(a.margin),winnerConf=clamp(a.winnerConfidence),
       axis=rows.find(z=>z.predMark==='◎');
 const basic={field:field>=5,readiness:ready>=(isCentral?.66:.59),
       coverage:coverage>=(isCentral?.47:.40),evidence:evidence>=(isCentral?.39:.33),
       honmei:!!axis};
 const basicOK=Object.keys(basic).every(k=>basic[k]);
 const ranking=rows.map(z=>({no:num(z.horse.horseNumber),p2:rankedRole(z,2),p3:rankedRole(z,3)}));
 const roleCoverage=field?ranking.filter(z=>z.p2!==null&&z.p3!==null).length/field:0;
 const place=ranking.map(z=>({...z,value:z.p2!==null&&z.p3!==null?z.p2+z.p3:0}))
   .sort((x,y)=>y.value-x.value||x.no-y.no);
 const placeSum=place.reduce((s,z)=>s+z.value,0);
 const placeTop2=placeSum?place.slice(0,2).reduce((s,z)=>s+z.value,0)/placeSum:0;
 const placeTop3=placeSum?place.slice(0,3).reduce((s,z)=>s+z.value,0)/placeSum:0;
 const axisTop3=!!axis&&place.slice(0,3).some(z=>z.no===num(axis.horse.horseNumber));
 const strongPlace=basicOK&&roleCoverage>=.70&&axisTop3&&
       placeTop3>=Math.max(.48,Math.min(.84,3/Math.max(field,1)*1.12))&&
       placeTop2>=Math.max(.31,Math.min(.64,2/Math.max(field,1)*1.10))&&
       scenario>=(isCentral?.24:.19)&&num(a.score)>=(isCentral?59:54);
 const clearWinner=basicOK&&(a.selected===true||(
       a.winnerStable===true&&winnerConf>=(isCentral?.65:.60)&&
       margin>=(isCentral?.035:.028)&&top3>=(isCentral?.61:.59)&&
       scenario>=(isCentral?.29:.22)&&num(a.score)>=(isCentral?66:60)&&
       a.multiHeadAgreement!==false));
 const holes=rows.filter(z=>z.predMark==='☆+'||z.predMark==='☆');
 const holeIndex=place.findIndex(z=>holes.some(h=>num(h.horse.horseNumber)===z.no));
 const longshot=basicOK&&holes.length>0&&roleCoverage>=.70&&
       holeIndex>=0&&holeIndex<=Math.min(5,field-1)&&a.winnerStable===true&&
       winnerConf>=(isCentral?.60:.56)&&margin>=(isCentral?.022:.018)&&
       scenario>=(isCentral?.29:.23)&&top3>=.55&&
       num(a.score)>=(isCentral?62:57)&&a.multiHeadAgreement!==false;
 let types=[];
 if(strongPlace)types.push(NAMES[0]);
 if(clearWinner)types.push(NAMES[1]);
 if(longshot)types.push(NAMES[2]);
 const selected=basicOK&&types.length>0;
 const primaryType=types.includes(NAMES[1])&&a.selected===true?NAMES[1]:
       types.includes(NAMES[0])?NAMES[0]:
       types.includes(NAMES[1])?NAMES[1]:types[0]||'';
 const explanation={
  '的中重視型':'2・3着の役割分布と軸の安定性を重視。ワイド・馬連・3連複を検討',
  '勝ち馬明確型':'勝ち馬の安定性と上位差を重視。馬単・3連単を検討',
  '高配当狙い型':'☆・☆+の相手適性と着順の筋を評価。高配当も的中も保証しない'
 };
 return {selected,score:selected?Math.max(0,Math.min(100,Math.round(num(a.score)))):0,
     primaryType,types,reason:selected?explanation[primaryType]:'券種別評価または基礎データ条件を満たさない',
     modelVersion:VERSION,metrics:{field,readiness:ready,coverage,evidence,scenario,
     roleCoverage,placeTop2,placeTop3,winnerConf,margin},
     gates:{...basic,strongPlace,clearWinner,longshot},
     note:'券種別モデル評価であり、的中率・期待配当・期待値を表しません。'};
}
// A public selected race must have a genuine, actionable morning recommendation.
// Prediction quality alone is not a promise that a purchasable ticket exists.
function ticketKinds(plan){
 if(!plan||!['通常買い','強く買う'].includes(String(plan.decision||''))||
    !plan.betInputGate||plan.betInputGate.ready!==true)return [];
 const kinds=[];
 for(const item of (Array.isArray(plan.items)?plan.items:[])){
  if(!item||!['本線','保険','3連単チャレンジ'].includes(String(item.level||''))||
     !['ワイド','馬連','馬単','3連複','3連単'].includes(String(item.kind||'')))continue;
  const combos=Array.isArray(item.combos)?item.combos:[];
  if(!combos.length||!combos.every(c=>Array.isArray(c)&&
      c.length===(item.kind==='3連単'||item.kind==='3連複'?3:2)&&
      c.every(v=>Number.isInteger(Number(v))&&Number(v)>0)&&new Set(c.map(Number)).size===c.length))continue;
  if(item.kind==='3連単'&&(combos.length<6||combos.length>12))continue;
  if(!kinds.includes(item.kind))kinds.push(item.kind);
 }
 return kinds;
}
function requireMorningTickets(selection,plan){
 if(!selection||selection.selected!==true)return selection;
 const kinds=ticketKinds(plan),has=kinds.length>0;
 return {...selection,selected:has,ticketKinds:kinds,
    reason:has?selection.reason+'｜朝の買い目成立：'+kinds.join('・'):
      '朝の買い目がすべて見送り・未取得のため厳選対象外'};
}
// Allow a quality-qualified place lane to reach the real bet engine without
// falsely claiming the first-place winner is dominant.
function hasMorningPlace(r,frozen){
 const pending=r&&r._arvexqMorningLaneCandidate;
 return !!((pending&&pending.selected===true&&Array.isArray(pending.types)&&pending.types.includes(NAMES[0]))||
    (frozen&&frozen.selected===true&&Array.isArray(frozen.types)&&frozen.types.includes(NAMES[0])));
}
function qualifyPlaceBet(base,r,frozen){
 if(!base||!base.selectionAudit||base.selectionAudit.selected===true||!hasMorningPlace(r,frozen))return base;
 return {...base,selectionAudit:{...base.selectionAudit,selected:true,
    strictWinnerSelected:false,morningPlaceLane:true,
    reason:'朝の的中重視型の券種別品質ゲート通過（勝ち馬明確型ではない）'}};
}
global.ARVEXQMorningTicketLanes=Object.freeze({VERSION,NAMES,classify,
 ticketKinds,requireMorningTickets,hasMorningPlace,qualifyPlaceBet});
})(window);
