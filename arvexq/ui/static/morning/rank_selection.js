/* ARVEXQ morning 厳選 lane: popularity-rank selection (2026-11-07 rule
 * change, owner decision). A race is selected when the ◎ of the
 * production stored forecast (v9b) sits at win-odds popularity rank 4
 * or lower. Local (地方) races are additionally selected when the v26
 * shadow lane's ◎ (from that day's published v26-marks archive) sits
 * at rank 4 or lower; each selection records which system picked it.
 *
 * The popularity rank is computed from the SAME stored detail's win
 * odds: rank = 1 + (number of active runners with strictly lower
 * odds), so a tie at the top counts as rank 1. Only races whose stored
 * detail is a complete production forecast are judged: production
 * identity must match, a ◎ must exist, at least 5 active runners must
 * be present, and every active runner must carry win odds > 1.0.
 * Anything else is not judged and never selected — incomplete races
 * are excluded, never silently mixed in. Banei is excluded upstream
 * (it never enters the morning scope).
 *
 * This module is the ONLY selection rule for the lane. The ticket-hit
 * calibration table is no longer read for selection; it is still
 * published separately as data.
 */
(function(global){
'use strict';
const MODEL_VERSION='arvexq-rank-selection-v1';
const PRODUCTION_MODEL='arvexq-rewrite-v3-v9b';
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
 const map=activeOdds(detail);
 if(!map)return null;
 const systems=[],out={prod:null,v26:null};
 const pno=honmeiNumber(detail);
 if(pno&&map[pno]){
   const rank=rankOf(map,pno);
   if(rank>=4){out.prod={horseNumber:pno,horseName:map[pno].name,rank:rank,odds:map[pno].odds};systems.push('prod')}
 }
 if(race&&String(race.circuit||'')==='地方'&&v26Archive&&v26Archive.races){
   const entry=v26Archive.races[String(detail.id)];
   const marks=entry&&entry.marks;
   if(marks&&typeof marks==='object'){
     let vno=0;
     for(const k of Object.keys(marks))if(String(marks[k])==='◎')vno=num(k);
     if(vno&&map[vno]){
       const rank=rankOf(map,vno);
       if(rank>=4){out.v26={horseNumber:vno,horseName:map[vno].name,rank:rank,odds:map[vno].odds};systems.push('v26')}
     }
   }
 }
 if(!systems.length)return null;
 const parts=[];
 if(out.prod)parts.push(pickText('本番',out.prod));
 if(out.v26)parts.push(pickText('v26',out.v26));
 return {systems:systems,prod:out.prod,v26:out.v26,
   favourite:favouriteOf(map),
   reason:'◎が4番人気以下｜'+parts.join('／')};
}
global.ARVEXQMorningRankSelection=Object.freeze({MODEL_VERSION:MODEL_VERSION,
 PRODUCTION_MODEL:PRODUCTION_MODEL,judge:judge,isProductionDetail:isProductionDetail});
})(window);
