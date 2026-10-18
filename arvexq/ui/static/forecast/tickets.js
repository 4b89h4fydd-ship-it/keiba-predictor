/* 121: Production ticket interface; no approved betting policy. */
(function(root){
  'use strict';
  var latestPlan=null;
  function build(race,prediction){
    latestPlan=null;
    var source=root.ARVEXQMorningEvidence;
    var receipt=race&&race.morningTicketEvidence;
    if(source&&receipt&&source.verify(race,receipt)){
      var plan=source.sealedPlan(race,receipt);
      if(plan){latestPlan=plan;return plan;}
    }
    return {decision:'未設定',items:[]};
  }
  function current(){return latestPlan;}
  root.ARVEXQProductionTickets=Object.freeze({build:build,current:current});
})(typeof window!=='undefined'?window:globalThis);
