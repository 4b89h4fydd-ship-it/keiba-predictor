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
  // This is a delivery adapter, not a model. The serving API must attach
  // approvedForecast only after authenticating its independent pre-off source
  // and deployment-controlled model approval at the storage boundary.
  function approvedForecast(race){
    var f=race&&race.approvedForecast;
    if(!f||f.version!=='arvexq-approved-forecast-v1'||
       f.publicationStatus!=='approved-calibrated-preoff'||!f.modelId||
       f.raceId!==race.id||f.raceDate!==race.date||f.circuit!==race.circuit||
       f.modelFamily!==(race.circuit==='中央'?'jra-flat':'nar-flat'))return null;
    var epoch=Number(f.capturedAtEpoch),post=Number(f.postAtEpoch);
    var scheduled=Date.parse(String(race.date)+'T'+
      String(race.scheduledStartTime||race.startTime||'').slice(0,5)+':00+09:00');
    if(!Number.isFinite(epoch)||!Number.isFinite(post)||!Number.isFinite(scheduled)||
       epoch>=post||Math.abs(post*1000-scheduled)>60000||
       Math.abs(Date.parse(f.fixedAt)-epoch*1000)>1000)return null;
    if(!/^[0-9a-f]{64}$/i.test(String(f.snapshotHash||''))||
       !f.modelEvidence||
       !/^[0-9a-f]{64}$/i.test(String(f.modelEvidence.holdoutArtifactSha256||''))||
       !/^[0-9a-f]{64}$/i.test(String(f.modelEvidence.calibrationArtifactSha256||'')))return null;
    var horses=(race.horses||[]).filter(function(h){
      return h&&Number.isInteger(Number(h.horseNumber))&&Number(h.horseNumber)>0;
    }),nos=horses.map(function(h){return Number(h.horseNumber)});
    if(nos.length<5||new Set(nos).size!==nos.length||
       !Array.isArray(f.horseNumbers)||f.horseNumbers.length!==nos.length||
       f.horseNumbers.some(function(no){return !nos.includes(no)}))return null;
    var probs=f.probabilities||[],seen={},w=0,t2=0,t3=0;
    if(probs.length!==nos.length)return null;
    for(var i=0;i<probs.length;i++){
      var row=probs[i],no=Number(row&&row.horseNumber);
      if(!nos.includes(no)||seen[no]||!['','◎','○','▲','△','☆','注'].includes(row.mark))return null;
      seen[no]=true;
      if(![row.win,row.top2,row.top3].every(function(p){return typeof p==='number'&&Number.isFinite(p)&&p>=0&&p<=1})||
         row.win>row.top2+1e-6||row.top2>row.top3+1e-6)return null;
      w+=row.win;t2+=row.top2;t3+=row.top3;
    }
    if(Math.abs(w-1)>1e-4||Math.abs(t2-2)>1e-4||Math.abs(t3-3)>1e-4)return null;
    if(!Array.isArray(f.scenarios)||!f.scenarios.length||!f.pace||
       !Array.isArray(f.pace.stages)||f.pace.stages.length!==4)return null;
    var sum=0,keys=new Set();
    for(var j=0;j<f.scenarios.length;j++){
      var z=f.scenarios[j],a=z&&z.horses,p=z&&z.probability;
      if(!Array.isArray(a)||a.length!==3||new Set(a).size!==3||
         a.some(function(no){return !nos.includes(no)})||
         typeof p!=='number'||!Number.isFinite(p)||p<0)return null;
      var key=a.join('-');if(keys.has(key))return null;keys.add(key);sum+=p;
    }
    if(Math.abs(sum-1)>1e-6)return null;
    var stageKeys=new Set(['start','turn3','turn4','straight']);
    for(var k=0;k<4;k++){
      var stage=f.pace.stages[k],pack=stage&&stage.pack;
      if(!stageKeys.delete(stage&&stage.key)||!Array.isArray(pack)||pack.length!==nos.length||
         new Set(pack.map(function(x){return x.no})).size!==nos.length||
         pack.some(function(x){return !nos.includes(x.no)}))return null;
    }
    if(!Array.isArray(f.tickets))return null;
    for(var q=0;q<f.tickets.length;q++){
      var bet=f.tickets[q];
      if(!bet||bet.kind!=='3連単'||!Array.isArray(bet.combos)||
         bet.combos.some(function(c){return !Array.isArray(c)||c.length!==3||
           new Set(c).size!==3||c.some(function(n){return !nos.includes(n)})})||
         !(bet.quotedOdds>1)||!(bet.hitProbability>0)||
         !(bet.expectedReturn>1))return null;
    }
    return f;
  }
  function build(race,prediction){
    latestPlan=null;
    var source=root.ARVEXQMorningEvidence;
    var receipt=validatedReceipt(race);
    if(source&&receipt){
      var plan=source.sealedPlan(race,receipt);
      if(plan){latestPlan=plan;return plan;}
    }
    var model=approvedForecast(race);
    if(model&&model.tickets.length){
      latestPlan={raceId:race.id,raceDate:race.date,fixedAt:model.fixedAt,
        engineVersion:model.modelId,decision:'通常買い',items:model.tickets.map(function(x){
          return {kind:x.kind,level:x.level,combos:x.combos,reason:x.reason};
        }),source:'approved-model'};
      return latestPlan;
    }
    return {decision:'未設定',items:[]};
  }
  function current(){return latestPlan;}
  root.ARVEXQProductionTickets=Object.freeze({build:build,current:current,validatedReceipt:validatedReceipt,approvedForecast:approvedForecast});
})(typeof window!=='undefined'?window:globalThis);
