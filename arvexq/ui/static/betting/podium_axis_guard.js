/* Conservative podium axis gate. This is NOT a calibrated top-3 probability.
 * Release v1: fewer unsupported ◎; no forced replacement axis.
 * Prior frozen opinions remain immutable; new gating applies pre-off only. */
(function(global){
'use strict';
const VERSION='arvexq-axis-reliability-v1';
function n(x,d=0){return x==null||x===''||!Number.isFinite(Number(x))?d:Number(x)}
function inspect(candidate,runner){
 const h=candidate&&candidate.podiumAxisHistory||{},starts=n(h.starts),top3=n(h.top3),
       rate=starts>0?top3/starts:0,
       gap=n(candidate&&candidate.podiumAxisScore)-n(runner&&runner.podiumAxisScore),
       evidence=n(candidate&&candidate.edgeEvidence,n(candidate&&candidate.coverage)),
       coverage=n(candidate&&candidate.coverage),
       winRank=n(candidate&&candidate.winnerDecisionRank,99);
 const checks={
   eligibleRunner:!!candidate&&!!runner&&n(candidate.horse&&candidate.horse.horseNumber)>0,
   historicalPodium:starts>=3&&top3>=2&&rate>=.60&&(starts<5||top3>=3),
   axisStrength:n(candidate&&candidate.podiumAxisScore)>=.62,
   clearSeparation:gap>=.03,
   broadConsensus:n(candidate&&candidate.axisRank,99)<=2&&
                  n(candidate&&candidate.podiumRecallRank,99)<=3,
   winningChance:winRank<=3,
   observedEvidence:evidence>=.42&&coverage>=.50
 };
 const failures=Object.keys(checks).filter(k=>!checks[k]);
 return {version:VERSION,eligible:failures.length===0,failures,checks,
   observedStarts:starts,observedTop3:top3,observedTop3Rate:rate,
   axisGap:gap,winRank:winRank,
   disclaimer:'selection guard only; not a calibrated place or win probability'};
}
global.ARVEXQPodiumAxisGuard=Object.freeze({VERSION,inspect});
})(window);
