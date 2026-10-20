function finishingEvidence(h,r){
 var rs=historicalWindow(h,r),w=recencyWeights(rs.length),
     holdW=0,held=0,closeW=0,converted=0,hs=0,cs=0,hw=0,cw=0;
 rs.forEach(function(rr,i){
   var ps=rr.cornerPositions||[],fs=raceField(rr),first=n(ps[0],0),
       last=n(ps[ps.length-1],0),fin=n(rr.finish,n(rr.finishPosition,0));
   if(ps.length<2||!Number.isInteger(last)||last<1||last>fs||
      !Number.isInteger(fin)||fin<1||fin>fs)return;
   if(first>0&&first<=4){
     holdW+=w[i];hs++;
     if(last<=4&&fin<=4){held+=w[i];hw++}
   }
   if(last>=4){
     closeW+=w[i];cs++;
     if(fin<=3&&fin<last){converted+=w[i];cw++}
   }
 });
 return {hold:holdW?held/holdW:.5,closing:closeW?converted/closeW:.5,
   holdSamples:hs,closingSamples:cs,holdWins:hw,closingWins:cw,window:rs.length}
}
