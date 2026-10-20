function bodyWeightConditionScore(h){
  var bw=currentBodyWeight(h);if(!bw)return .5;
  var ch=currentBodyWeightChange(h),base=.55;
  if(ch!=null){var a=Math.abs(ch);base=a<=6?.60:(a<=12?.55:(a<=20?.48:.42))}
  var rs=(h.allPastRuns||h.recentRaces||[]).slice(0,5),past=[];
  for(var i=0;i<rs.length;i++){var w=n(rs[i]&&rs[i].bodyWeight,0);if(w>250)past.push(w)}
  if(past.length){var avg=mean(past),pct=Math.abs(bw-avg)/Math.max(300,avg),hist=clamp(.62-pct*2.4,.38,.62);base=base*.58+hist*.42}
  return clamp(base,.38,.64)
}
