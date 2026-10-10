/* Distinguishes prediction-source readiness from publication of odds/weights.
   Any ticket without real odds is model-only, not an EV assertion. */
(function(global){
'use strict';
const VERSION='arvexq-bet-readiness-v1';
const v=(x,d=0)=>x==null||x===''||!Number.isFinite(Number(x))?d:Number(x);
function evaluate(r,p,evidence,rd){
 const central=String(r&&r.circuit||'')==='中央',missing=[],warnings=[],
       rows=((p&&p.rows)||[]),field=rows.length,
       top=rows.slice().sort((a,b)=>v(b.winnerDecisionProbability,v(b.p1Probability))-v(a.winnerDecisionProbability,v(a.p1Probability)))[0],
       topNo=v(top&&top.horse&&top.horse.horseNumber),
       topMissing=evidence&&evidence.topMissing||[],leadMissing=evidence&&evidence.leaderMissing||[],
       paceCoverage=v(evidence&&evidence.coverage);
 if(field<5)missing.push('出走頭数');
 if(!r||!r.careerReadiness||r.careerReadiness.ready!==true)missing.push('全出走履歴');
 if(v(rd.card)<.90)missing.push('出馬表・騎手');
 if(v(rd.history)<.55)missing.push('近走データ');
 if(v(rd.analysis)<.45||v(rd.prediction)<(central?.62:.58))missing.push('能力診断');
 // Evidence for the candidate most likely to win is not optional; limited
 // omissions in secondary runners should not block all unordered tickets.
 if(paceCoverage<.45||topMissing.length>1||leadMissing.length>1||
    (topNo>0&&topMissing.map(Number).includes(topNo)))missing.push('位置取りの観測根拠');
 if(!r||!r.date)missing.push('開催日');
 if(v(rd.actualOdds)<.65)warnings.push('実オッズ未充足（期待値未検証）');
 if(v(rd.bodyWeight)<.70)warnings.push('馬体重未発表・未充足');
 if(v(rd.environment)<1)warnings.push('馬場・天候の一部未取得');
 if(evidence&&evidence.ready!==true)warnings.push('先行位置推定に欠損あり');
 const ready=missing.length===0,
       trifectaReady=ready&&evidence&&evidence.ready===true&&
         v(rd.history)>=.70&&v(rd.environment)>=.5&&
         v(rd.prediction)>=(central?.68:.62);
 return Object.freeze({version:VERSION,ready,modelReady:ready,
   trifectaReady:!!trifectaReady,missing,warnings,
   oddsVerified:v(rd.actualOdds)>=.65,pace:evidence,readiness:rd,
   disclosure:'モデル比較による参考買い目。オッズ・的中確率・期待値は未検証'});
}
function promoteReference(base,r,p,rd){
 if(!base||!base.selectionAudit||base.selectionAudit.selected===true||!r||!p)return base;
 const a=base.selectionAudit,central=String(r.circuit||'')==='中央',
       field=((p.rows)||[]).length;
 if(!r.careerReadiness||r.careerReadiness.ready!==true||field<5||r._entryOnly||v(rd.card)<.90||v(rd.history)<.55||
    v(rd.analysis)<.45||v(rd.prediction)<(central?.62:.58)||
    v(p.coverage)<(central?.44:.38)||v(a.score)<(central?50:48)||
    v(a.evidence)<.30)return base;
 return {...base,referenceOnly:true,
   selectionAudit:{...a,selected:true,referenceOnly:true,strictWinnerSelected:false,
     reason:'通常レースのモデル参考買い目。朝の厳選判定とは別'}};
}
global.ARVEXQBetReadiness=Object.freeze({VERSION,evaluate,promoteReference});
})(window);
