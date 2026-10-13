/* ARVEXQ morning selection: only hit-first 80+ ticket-backed qualifiers, no arbitrary daily cap.
 * Deterministic only; no live odds, results, DOM, or post-off selection.
 */
(function(global){
'use strict';
function allStrictQualifiers(rows,helpers){
 const n=helpers.n,chronological=helpers.chronological;
 return (rows||[]).filter(function(z){return !!(z&&z.race&&z.selection&&z.selection.selected===true&&z.selection.hitRate!=null&&Number(z.selection.hitRate)>=.80&&Number(z.selection.hitRateSamples)>=30&&Number(z.selection.hitRateWilsonLower)>=.65&&String(z.selection.primaryType||'')==='的中重視型'&&Array.isArray(z.selection.types)&&z.selection.types.includes('的中重視型')&&n(z.race.raceNumber)>0)}).slice().sort(chronological);
}
global.ARVEXQMorningSelection=Object.freeze({allStrictQualifiers:allStrictQualifiers,version:'empirical-ticket-hit-v1'});
})(window);
