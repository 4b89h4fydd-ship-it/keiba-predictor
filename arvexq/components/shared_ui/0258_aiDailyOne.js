function aiDailyOne(detail){
  if(!detail||!isFinal(detail))return null;
  var fs=((detail.result||{}).finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)}).slice(0,3),
      nums=fs.map(function(x){return n(x.horseNumber)});
  if(fs.map(function(x){return n(x.finish)}).join(',')!=='1,2,3'||nums.some(function(v){return v<1})||new Set(nums).size!==3)return null;
  var marks=aiStoredMarks(detail);if(!marks.length)return null;
  var hon=marks.find(function(x){return x.mark==='◎'}),marked={};marks.forEach(function(x){if(['◎','○','▲','☆+','☆','△','注'].indexOf(x.mark)>=0)marked[x.no]=x.mark});
  var winner=nums[0],podium={},markedCount=nums.filter(function(no){return !!marked[no]}).length;
  nums.forEach(function(no){podium[no]=1});
  var honPlaceHit=!!(hon&&podium[hon.no]),winHit=!!(hon&&hon.no===winner),markHit=!!marked[winner],fullPodiumHit=markedCount===3,
      frozenBet=frozenAiBetForRace(detail),triItems=((frozenBet&&frozenBet.items)||[]).filter(function(x){return x.kind==='3連単'&&Array.isArray(x.combos)&&x.combos.length>0}),
      triEligible=triItems.length>0,triHit=triItems.some(function(x){return betItemHit(x,nums)}),
      ranked=marks.filter(function(x){return n(x.p,0)>0}).slice().sort(function(a,b){return n(b.p)-n(a.p)}),
      wr=ranked.findIndex(function(x){return x.no===winner})+1;
  return {raceId:String(detail.id||''),track:String(detail.track||''),raceNumber:n(detail.raceNumber),title:String(detail.title||''),circuit:String(detail.circuit||''),
    winHit:winHit,honPlaceHit:honPlaceHit,honEligible:!!hon,markHit:markHit,fullPodiumHit:fullPodiumHit,triEligible:triEligible,triHit:triHit,
    markedPodiumCount:markedCount,holePlace:marks.some(function(x){return ['☆','☆+','注'].indexOf(x.mark)>=0&&podium[x.no]}),
    top2:wr>0&&wr<=2,top3:wr>0&&wr<=3,candidateOrderMiss:!winHit&&markHit,candidateMiss:!markHit,
    highConf:!!(hon&&hon.confidence>=.70),highConfHit:!!(hon&&hon.confidence>=.70&&winHit),brier:0,logLoss:0,
    reason:winHit?'◎1着':(markHit?'印内の1着順位':'1着候補外'),
    winner:winner,winnerMark:String(marked[winner]||''),podiumNos:nums,marks:marks.filter(function(x){return !!x.mark}).map(function(x){return {no:x.no,mark:x.mark}}),
    hasMarks:true,resultReady:true,eligible:true,betSaved:!!frozenBet}
}
