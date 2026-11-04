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
function calibrationBucket(kind,points){
 const cal=global.ARVEXQTicketHitCalibration;
 if(!cal||cal.version!=='arvexq-empirical-ticket-hit-v1'||
    cal.modelVersion!=='arvexq-rewrite-v3-v9b'||
    !/^20\d{2}-\d{2}-\d{2}$/.test(String(cal.asOfDate||'')))return null;
 return (cal.buckets||{})[String(kind)+'|'+String(points)]||null;
}
function hitCalibration(kind,points){
 const row=calibrationBucket(kind,points);
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
const LANE_SOURCE='arvexq-morning-production-lane-v1';
function laneTicketKinds(plan){
 // Lane-scoped contract: the plan was built by the production lane
 // adapter from the stored ticket plan only, so it is recognised by
 // its source tag plus the v9b model pin — never by a purchase
 // decision, which the lane deliberately does not carry. Issued
 // kinds and point counts are taken faithfully: no legacy 12-point
 // cap, so a 36-point Formation B item stays a 36-point item.
 // Qualification is NOT decided here; requireMorningTickets still
 // gates on the measured calibration buckets alone.
 if(!plan||plan.source!==LANE_SOURCE||
    String(plan.modelVersion||'')!=='arvexq-rewrite-v3-v9b')return null;
 const widths={'ワイド':2,'馬連':2,'馬単':2,'3連複':3,'3連単':3};
 const valid=(plan.items||[]).filter(x=>x&&widths[x.kind]&&
   ['本線','保険','3連単チャレンジ'].includes(x.level)&&
   Array.isArray(x.combos)&&x.combos.length>=1&&
   x.combos.every(c=>Array.isArray(c)&&c.length===widths[x.kind]&&
      c.every(v=>Number.isInteger(Number(v))&&Number(v)>0)&&
      new Set(c.map(Number)).size===c.length));
 if(!valid.length||!valid.some(x=>x.level==='本線'))return [];
 return [...new Set(valid.map(x=>x.kind))];
}
function ticketKinds(plan){
 const lane=laneTicketKinds(plan);
 if(lane!==null)return lane;
 if(!plan||!['購入候補','通常買い','強く買う'].includes(String(plan.decision||''))||
    !plan.betInputGate||plan.betInputGate.ready!==true)return [];
 const widths={'ワイド':2,'馬連':2,'馬単':2,'3連複':3,'3連単':3};
 return [...new Set((plan.items||[]).filter(x=>x&&widths[x.kind]&&
   ['本線','保険','3連単チャレンジ'].includes(x.level)&&
   Array.isArray(x.combos)&&x.combos.length>=1&&x.combos.length<=12&&
   x.combos.every(c=>Array.isArray(c)&&c.length===widths[x.kind]&&
      c.every(v=>Number.isInteger(Number(v))&&Number(v)>0)&&
      new Set(c.map(Number)).size===c.length)).map(x=>x.kind))];
}
function requireMorningTickets(selection,plan){
 if(!selection||selection.selected!==true)return selection;
 const kinds=ticketKinds(plan),main=(plan&&plan.items||[]).find(x=>x.level==='本線');
 const bucket=main&&hitCalibration(main.kind,(main.combos||[]).length);
 const selected=!!bucket&&kinds.includes(main.kind);
 if(selected)return {...selection,selected:true,
   score:Math.round(bucket.hitRate*100),
   hitRate:bucket.hitRate,hitRateSamples:bucket.sample,
   hitRateWilsonLower:bucket.wilsonLower95,
   primaryType:'的中重視型',types:['的中重視型'],ticketKinds:kinds,
   reason:'本線'+main.kind+'の実測的中率'+(bucket.hitRate*100).toFixed(1)+'%｜'+bucket.sample+'レース'};
 // Not selected: when the bucket exists but misses the bar, state the
 // measured numbers so a rejection reads as evidence, not as a
 // missing-contract failure.
 const row=main&&calibrationBucket(main.kind,(main.combos||[]).length);
 const reason=row?('本線'+main.kind+'の実測的中率'+(Number(row.hitRate)*100).toFixed(1)+'%｜'+row.sample+'レース（合格条件に未達・厳選見送り）'):'本線買い目の的中率検証不足（厳選見送り）';
 return {...selection,selected:false,score:0,
   hitRate:null,hitRateSamples:0,hitRateWilsonLower:null,
   primaryType:'',types:[],ticketKinds:kinds,reason};
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
 ticketKinds,requireMorningTickets,hasMorningPlace,qualifyPlaceBet,selectionDisplayStatus,
 calibrationBucket,hitCalibration});
})(window);
