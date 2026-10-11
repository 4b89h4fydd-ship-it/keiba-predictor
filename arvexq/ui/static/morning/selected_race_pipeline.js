/* Morning elite selection only. Acquisition and special-race membership are
 * separate; buying decisions are delegated to the existing betting engine.
 */
(function(global){
'use strict';
const VERSION='arvexq-selected-race-pipeline-v1';
function select(races,ops){
 if(!ops||!ops.lanes||typeof ops.lanes.classify!=='function'||
    typeof ops.lanes.requireMorningTickets!=='function'||
    !ops.evidence||typeof ops.evidence.capture!=='function')
   throw Error('morning selection dependencies missing');
 const selected=new Map();
 for(const r of (Array.isArray(races)?races:[])){
  if(!r||!r.id)continue;
  let detail=null;
  try{
   detail=ops.getDetail(r);
   // A fetch-in-progress lifetime is not a selection veto; require a real
   // racecard and let the model/data gate determine whether it can bet.
   if(!detail||ops.isFinal(detail)||!Array.isArray(detail.horses)||
      detail.horses.filter(h=>h&&!ops.isScratch(h)&&Number(h.horseNumber)>0&&String(h.name||'').trim()).length<5)continue;
   const forecast=ops.predict(detail),audit=ops.evaluateQuality(detail,forecast);
   let lane=ops.lanes.classify(detail,forecast,audit);
   if(!lane.selected)continue;
   detail._arvexqMorningLaneCandidate=lane;
   const tickets=ops.makeTicket(detail,forecast);
   lane=ops.lanes.requireMorningTickets(lane,tickets);
   if(!lane.selected)continue;
   const receipt=ops.evidence.capture(detail,forecast,tickets,lane);
   if(!receipt){ops.warn('MORNING_SELECTED_NO_CONCRETE_TICKET',detail.id);continue}
   lane.evidence=receipt;
   selected.set(String(r.id),{race:r,tags:['厳選'],selection:lane});
  }catch(err){ops.warn('MORNING_TICKET_DECISION_UNAVAILABLE',r.id,String(err&&err.message||err))}
  finally{if(detail)delete detail._arvexqMorningLaneCandidate}
 }
 return ops.cut(Array.from(selected.values()));
}
global.ARVEXQSelectedRacePipeline=Object.freeze({VERSION,select});
})(window);
