/* ARVEXQ morning selection: all strict-quality qualifiers, no arbitrary daily cap.
 * Deterministic only; no live odds, results, DOM, or post-off selection.
 */
(function(global){
'use strict';
function allStrictQualifiers(rows,helpers){
 const n=helpers.n,chronological=helpers.chronological;
 return (rows||[]).filter(function(z){return !!(z&&z.race&&z.selection&&z.selection.selected===true&&n(z.race.raceNumber)>0)}).slice().sort(chronological);
}
global.ARVEXQMorningSelection=Object.freeze({allStrictQualifiers:allStrictQualifiers,version:'strict-unlimited-morning-v1'});
})(window);
