/* 121: Production ticket interface; no approved betting policy. */
(function(root){
  'use strict';
  var latestPlan=null;
  function matchesRoster(race,receipt){
    // An empty summary roster cannot contradict the dated original.
    if(!Array.isArray(race.horses)||race.horses.length===0)return true;
    if(!Array.isArray(receipt.marks)||receipt.marks.length!==race.horses.length)return false;
    var seen={},markNos={};
    for(var i=0;i<race.horses.length;i++){
      var raw=race.horses[i]&&race.horses[i].horseNumber;
      var number=Number(raw);
      if(!Number.isInteger(number)||number<=0||seen[number])return false;
      seen[number]=1;
    }
    for(var j=0;j<receipt.marks.length;j++){
      var markNo=Number(receipt.marks[j]&&receipt.marks[j].horseNumber);
      if(!Number.isInteger(markNo)||markNo<=0||!seen[markNo]||markNos[markNo])return false;
      markNos[markNo]=1;
    }
    return true;
  }
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
      if(candidates[i]&&source.verify(race,candidates[i])&&matchesRoster(race,candidates[i]))return candidates[i];
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
