/* Strict purchases v2, effective 2026-11-11. Legacy popularity records
 * remain readable by date; future purchases require same-model actual
 * tickets, source timestamps and independent policy validation.
 * v26-only signals never select production-v9b tickets.
 */
(function(global){
'use strict';
const MODEL_VERSION='arvexq-rank-selection-v1';
const PRODUCTION_MODEL='arvexq-rewrite-v3-v9b';
const POLICY_START='2026-11-11';
const POLICY_VERSION='arvexq-ticket-selection-v2';
function assess(detail,now){
 const uf=detail&&detail.unifiedForecast||{},e=detail&&detail.selectionDecision||uf.ticketPlan&&uf.ticketPlan.selectionEvaluation;
 if(!e)return {status:'unassessed',reasons:['購入条件の検証データ待ち']};
 const at=Date.parse(e.decidedAt),post=Date.parse(String(detail.date)+'T'+String(detail.scheduledStartTime||detail.startTime).slice(0,5)+':00+09:00'),
       captured=Date.parse(uf.capturedAt),observed=Date.parse(e.marketObservedAt);
 const proof=e.validationEvidence||{};
 if(e.version!==POLICY_VERSION||e.raceId!==detail.id||e.raceDate!==detail.date||
    e.modelVersion!==uf.modelVersion||e.modelHash!==uf.modelHash||
    !e.forecastReceipt||e.forecastReceipt!==uf.receiptSha256||
    e.forecastCapturedAt!==uf.capturedAt)
   return {status:'unassessed',reasons:['予想と購入判定の原本不一致']};
 if(e.selected!==true)return {status:e.status||'unassessed',reasons:e.reasons||[]};
 if(e.validationStatus!=='approved-out-of-sample'||proof.status!=='approved-out-of-sample'||
    proof.modelHash!==uf.modelHash||proof.policySha256!==e.policySha256||
    !proof.evidenceSha256||!proof.validatedThrough||proof.validatedThrough>=detail.date)
   return {status:'unassessed',reasons:['購入条件が未検証']};
 if(!Number.isFinite(at)||!Number.isFinite(post)||!Number.isFinite(captured)||!Number.isFinite(observed)||
    !(captured<=observed&&observed<=at&&at<post&&at<=(now||Date.now()))||
    at-captured>1800000||at-observed>600000)
   return {status:'unassessed',reasons:['予想またはオッズの時刻が購入条件外']};
 const active=new Set((detail.horses||[]).filter(h=>h&&!isScratch(h)).map(h=>num(h.horseNumber))),seen=new Set();
 if(!Array.isArray(e.items)||e.items.length<1||e.items.length>3||
    !(e.hitProbability>=0.70&&e.hitProbability<=1)||!(e.stressExpectedReturn>=1.05)||!e.marketSha256)
   return {status:'unassessed',reasons:['買い目条件の不一致']};
 for(const item of e.items){
   if(item.kind!=='ワイド'||!Array.isArray(item.combo)||item.combo.length!==2||
      item.combo[0]===item.combo[1]||item.combo.some(n=>!active.has(num(n)))||
      !(item.oddsLow>=1)||!(item.probability>=0&&item.probability<=1))
     return {status:'unassessed',reasons:['実買い目が不正']};
   const key=item.combo.slice().sort((a,b)=>a-b).join('-');
   if(seen.has(key))return {status:'unassessed',reasons:['買い目重複']};seen.add(key);
 }
 return {status:'selected',evaluation:e};
}
function num(v){const n=Number(v);return Number.isInteger(n)&&n>0?n:0}
function isScratch(h){
 return !!(h&&(h.scratched||h.withdrawn||/取消|除外|欠場/.test(String(h.status||''))));
}
function isProductionDetail(detail){
 if(!detail||!detail.id)return false;
 const uf=detail.unifiedForecast;
 if(!uf||uf.version!=='arvexq-unified-live-v1'||
    String(uf.modelVersion||'')!==PRODUCTION_MODEL||
    String(uf.raceId||'')!==String(detail.id)||
    !Array.isArray(uf.marks))return false;
 if(detail.predictionStatus!==undefined&&detail.predictionStatus!==null&&
    String(detail.predictionStatus)!==''&&String(detail.predictionStatus)!=='ready')return false;
 const lane=detail.preparedMeta&&detail.preparedMeta.rewritePublish&&
   detail.preparedMeta.rewritePublish.abilityLane;
 if(lane&&String(lane)!=='v9b-cal-market')return false;
 return true;
}
function honmeiNumber(detail){
 const list=Array.isArray(detail.predictionMarks)?detail.predictionMarks:null;
 if(list){
   for(const m of list){
     if(m&&String(m.mark||'')==='◎'){const no=num(m.horseNumber);if(no)return no}
   }
 }
 const uf=detail.unifiedForecast;
 if(uf&&Array.isArray(uf.marks)){
   for(const m of uf.marks){
     if(m&&String(m.markSymbol||'')==='◎'){const no=num(m.horseNumber);if(no)return no}
   }
 }
 return 0;
}
function activeOdds(detail){
 const rows=(Array.isArray(detail.horses)?detail.horses:[])
   .filter(h=>h&&num(h.horseNumber)&&!isScratch(h));
 if(rows.length<5)return null;
 const map={};
 for(const h of rows){
   const odds=Number(h.winOdds);
   if(!Number.isFinite(odds)||odds<=1.0)return null;
   map[num(h.horseNumber)]={horseNumber:num(h.horseNumber),
     name:String(h.name||''),odds:odds};
 }
 return map;
}
function rankOf(map,no){
 const target=map[no].odds;let rank=1;
 for(const k of Object.keys(map))if(map[k].odds<target)rank++;
 return rank;
}
function favouriteOf(map){
 let best=null;
 for(const k of Object.keys(map)){
   const e=map[k];
   if(!best||e.odds<best.odds||(e.odds===best.odds&&e.horseNumber<best.horseNumber))best=e;
 }
 return best?{horseNumber:best.horseNumber,horseName:best.name,odds:best.odds}:null;
}
function pickText(label,pick){
 return label+'◎ '+pick.horseNumber+'番 '+pick.horseName+'｜'+pick.rank+'番人気（単勝'+
   (Math.round(pick.odds*10)/10)+'倍）';
}
function judge(detail,race,v26Archive){
 if(!isProductionDetail(detail))return null;
 if(String(detail.date||'')>=POLICY_START){
   const decision=assess(detail);
   if(decision.status!=='selected')return null;
   const e=decision.evaluation,pno=honmeiNumber(detail),h=(detail.horses||[]).find(h=>num(h.horseNumber)===pno);
   return {systems:['prod'],prod:{horseNumber:pno,horseName:h&&h.name||'',rank:null,odds:null},v26:null,
     favourite:null,modelVersion:POLICY_VERSION,primaryType:'的中重視型',
     reason:'本番の保存買い目と同一モデル・実オッズ・検証済み購入条件',
     plan:{source:'arvexq-morning-production-lane-v1',modelVersion:PRODUCTION_MODEL,engineVersion:PRODUCTION_MODEL,
       items:[{level:'本線',kind:'ワイド',combos:e.items.map(i=>i.combo.slice()),points:e.items.length}]}};
 }
 const map=activeOdds(detail);
 if(!map)return null;
 const systems=[],out={prod:null,v26:null};
 const pno=honmeiNumber(detail);
 if(pno&&map[pno]){
   const rank=rankOf(map,pno);
   if(rank>=4){out.prod={horseNumber:pno,horseName:map[pno].name,rank:rank,odds:map[pno].odds};systems.push('prod')}
 }
 // A v26-only signal cannot select a v9b ticket. Historical frozen
 // archives remain readable through their original versioned record.
 if(!systems.length)return null;
 const parts=[];
 if(out.prod)parts.push(pickText('本番',out.prod));
 if(out.v26)parts.push(pickText('v26',out.v26));
 return {systems:systems,prod:out.prod,v26:out.v26,
   favourite:favouriteOf(map),
   reason:'◎が4番人気以下｜'+parts.join('／')};
}
global.ARVEXQMorningRankSelection=Object.freeze({MODEL_VERSION:MODEL_VERSION,POLICY_VERSION,POLICY_START,
 PRODUCTION_MODEL:PRODUCTION_MODEL,judge:judge,assess:assess,isProductionDetail:isProductionDetail});
})(window);
