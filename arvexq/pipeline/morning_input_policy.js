/* Only the completeness of the published race schedule can block morning
 * membership freezing. Detailed horse data is assessed separately per race.
 * Never confuse all-career ingestion completeness with a usable pre-off model.
 */
'use strict';
function active(h){return !!(h&&Number(h.horseNumber)>0&&!h.scratched&&!h.withdrawn&&!/取消|除外|欠場/.test(String(h.status||'')))}
function hasRunEvidence(h){
 return !!(h&&(h.debutNoHistory===true||
   (Array.isArray(h.allPastRuns)&&h.allPastRuns.length)||
   (Array.isArray(h.recentRaces)&&h.recentRaces.length)||
   (h.integratedEvaluation&&Object.keys(h.integratedEvaluation).length)));
}
function status(summaries,details,day){
 const rows=(summaries||[]).filter(r=>r&&r.id);
 const valid=rows.length>0&&/^20\d{2}-\d{2}-\d{2}$/.test(String(day||''))&&
   rows.every(r=>String(r.date||day)===day&&
     Number(r.raceNumber)>0&&/^\d{1,2}:\d{2}$/.test(String(r.startTime||'').slice(0,5)));
 const assessedIds=new Set(),missingCards=[];
 for(const r of rows){
   const d=details.get(String(r.id)),hs=(d&&Array.isArray(d.horses)?d.horses:[]).filter(active),
         identified=hs.filter(h=>String(h.name||'').trim()).length,
         evidenced=hs.filter(hasRunEvidence).length;
   if(identified>=5&&evidenced>=Math.max(3,Math.ceil(hs.length*.50)))
     assessedIds.add(String(r.id));
   else missingCards.push(String(r.id));
 }
 return {scheduleReady:valid,assessedIds,missingCards,scope:rows.length};
}
module.exports=Object.freeze({status});
