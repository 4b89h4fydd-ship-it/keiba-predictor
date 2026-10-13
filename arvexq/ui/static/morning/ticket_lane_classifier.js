/* ARVEXQ: race selection by ticket objective, frozen once in the morning.
   Relative model concentration is NOT a calibrated hit rate or expected return. */
(function(global){
'use strict';
const VERSION='arvexq-empirical-ticket-lanes-v1';
const NAMES=['的中重視型','勝ち馬明確型','高配当狙い型'];
function num(x,d=0){return x===null||x===undefined||x===''||!Number.isFinite(Number(x))?d:Number(x)}
function clamp(x){return Math.max(0,Math.min(1,num(x)))}
function rankedRole(x,which){
 const keys=which===2?['ticketP2Probability','p2Probability']:['ticketP3Probability','p3Probability'];
 for(const k of keys){if(x&&x[k]!==undefined&&x[k]!==null&&Number.isFinite(Number(x[k])))return Math.max(0,Number(x[k]))}
 return null;
}
function hitCalibration(kind,points){
 const cal=global.ARVEXQTicketHitCalibration;
 if(!cal||cal.version!=='arvexq-empirical-ticket-hit-v1'||
    cal.modelVersion!=='arvexq-true-run-pure-sectional-v2'||
    !/^20\d{2}-\d{2}-\d{2}$/.test(String(cal.asOfDate||'')))return null;
 const row=(cal.buckets||{})[String(kind)+'|'+String(points)];
 if(!row||row.qualified!==true||Number(row.sample)<30||
    Number(row.hitRate)<.80||Number(row.wilsonLower95)<.65)return null;
 return row;
}
function classify(r,p,strict){
 const rows=((p&&p.rows)||[]).filter(z=>z&&z.horse&&!z.horse.scratched&&!z.horse.withdrawn);
 const good=rows.length>=5&&rows.filter(z=>Number(z.threeFactorCoverage)>=2).length>=Math.ceil(rows.length*.70);
 return {selected:good,score:0,primaryType:'的中重視型',
   types:good?['的中重視型']:[],reason:good?'券種別実測的中率検証待ち':'近走実測データ不足',
   modelVersion:'arvexq-empirical-ticket-hit-v1',metrics:{coverage:good},
   note:'厳選には保存済み買い目と確定結果の券種別的中率のみ使用。能力点は印専用。'};
}
// A public selected race must have a genuine, actionable morning recommendation.
// Prediction quality alone is not a promise that a purchasable ticket exists.
function ticketKinds(plan){
 if(!plan||!['購入候補','通常買い','強く買う'].includes(String(plan.decision||''))||
    !plan.betInputGate||plan.betInputGate.ready!==true)return [];
 return [...new Set((plan.items||[]).filter(x=>x&&x.kind&&Array.isArray(x.combos)&&x.combos.length).map(x=>x.kind))];
}
function requireMorningTickets(selection,plan){
 if(!selection||selection.selected!==true)return selection;
 const kinds=ticketKinds(plan),main=(plan&&plan.items||[]).find(x=>x.level==='本線');
 const bucket=main&&hitCalibration(main.kind,(main.combos||[]).length);
 const selected=!!bucket&&kinds.includes(main.kind);
 return {...selection,selected,score:selected?Math.round(bucket.hitRate*100):0,
   hitRate:selected?bucket.hitRate:null,hitRateSamples:selected?bucket.sample:0,
   hitRateWilsonLower:selected?bucket.wilsonLower95:null,
   primaryType:selected?'的中重視型':'',types:selected?['的中重視型']:[],
   ticketKinds:kinds,reason:selected?('本線'+main.kind+'の実測的中率'+(bucket.hitRate*100).toFixed(1)+'%｜'+bucket.sample+'レース'):'本線買い目の的中率検証不足（厳選見送り）'};
}
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
// Historical first-write-wins archives remain intact, but unverified
// older selections are not currently purchasable recommendations.
function selectionDisplayStatus(m,r){
 if(m&&m.selected===true&&m.selectionModelVersion!=='arvexq-empirical-ticket-hit-v1')return 'legacy-unverified';
 if(!m||m.selected!==true)return 'not-selected';
 const kinds=Array.isArray(m.ticketKinds)?m.ticketKinds:[],
       types=Array.isArray(m.types)?m.types:[],
       supports=t=>t===NAMES[0]&&kinds.some(k=>['ワイド','馬連','3連複'].includes(k))||
         t===NAMES[1]&&kinds.some(k=>['馬単','3連単'].includes(k))||
         t===NAMES[2]&&kinds.includes('3連単');
 if(!types.length||!kinds.length)return 'legacy-unverified';
 if(!NAMES.includes(String(m.primaryType||''))||!types.includes(m.primaryType)||
    !types.every(t=>NAMES.includes(t)&&supports(t)))return 'inconsistent';
 const evidence=global.ARVEXQMorningEvidence;
 if(!r||!m.ticketEvidence||!evidence||!evidence.verify(r,m.ticketEvidence))
   return 'ticket-original-missing';
 if(kinds.slice().sort().join('|')!==(m.ticketEvidence.ticketKinds||[]).slice().sort().join('|'))
   return 'ticket-original-mismatch';
 return 'actionable';
}
global.ARVEXQMorningTicketLanes=Object.freeze({VERSION,NAMES,classify,
 ticketKinds,requireMorningTickets,hasMorningPlace,qualifyPlaceBet,selectionDisplayStatus});
})(window);
