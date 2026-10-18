/* 121: Production ticket interface; no approved betting policy. */
(function(root){
  'use strict';
  var latestPlan=null;
  function validatedReceipt(race){
    if(!race||!race.id||!race.date)return null;
    var source=root.ARVEXQMorningEvidence;
    if(!source||typeof source.verify!=='function')return null;
    var candidates=[
      race.morningTicketEvidence,
      race.volatility&&race.volatility.morningPicks&&race.volatility.morningPicks.ticketEvidence,
      race.environmentMeta&&race.environmentMeta.morningPicks&&race.environmentMeta.morningPicks.ticketEvidence
    ];
    for(var i=0;i<candidates.length;i++){
      if(candidates[i]&&source.verify(race,candidates[i]))return candidates[i];
    }
    return null;
  }
  function build(race,prediction){
    latestPlan=null;
    var source=root.ARVEXQMorningEvidence;
    var receipt=validatedReceipt(race);
    if(source&&receipt){
      var plan=source.sealedPlan(race,receipt);
      if(plan){latestPlan=plan;return plan;}
    }
    return {decision:'未設定',items:[]};
  }
  function current(){return latestPlan;}
  root.ARVEXQProductionTickets=Object.freeze({build:build,current:current,validatedReceipt:validatedReceipt});
})(typeof window!=='undefined'?window:globalThis);
