function minetaPastProfile(h,r){
  var rs=paceHistoryRuns(h,r),last=rs[0]||null,
      lp=(last&&last.cornerPositions||[]).map(function(v){return n(v,0)}).filter(function(v){return v>0}),
      field=last?raceField(last):12,first=lp.length?lp[0]:0,prevEarly=first>0&&first<=3,prevLeader=first===1,
      prevRear=first>=Math.max(6,Math.ceil(field*.66)),w=recencyWeights(rs.length),
      moveW=0,moveDen=0,leadW=0,leadDen=0,earlyW=0,rearW=0,rearDen=0,i,rr,p,j,best,ww,fs,midLead;
  for(i=0;i<rs.length;i++){
    rr=rs[i]||{};p=(rr.cornerPositions||[]).map(function(v){return n(v,0)}).filter(function(v){return v>0});
    if(!p.length)continue;
    fs=raceField(rr);ww=(w[i]||1)*(String(rr.track||'')===String(r&&r.track||'')?1.10:1)*
      (Math.abs(n(rr.distance,0)-n(r&&r.distance,0))<=200?1.12:1);
    best=99;for(j=1;j<p.length;j++)if(p[j]<best)best=p[j];
    moveDen+=ww;if(p[0]>3&&best<=Math.max(3,p[0]-2))moveW+=ww;
    leadDen+=ww;if(p[0]===1)leadW+=ww;if(p[0]<=3)earlyW+=ww;
    midLead=p[0]>1&&p.slice(1).some(function(v){return v===1});if(midLead)moveW+=ww*.25;
    rearDen+=ww;if(p[0]>=Math.max(6,Math.ceil(fs*.66)))rearW+=ww
  }
  var norm=first?((first-1)/Math.max(1,field-1)):1,bucket='不明';
  if(lp.length){if(prevEarly)bucket='先行';else if(norm<=.38)bucket='準先行';else if(norm<=.68)bucket='準後方';else bucket='後方'}
  // Recompute true midrace-takeover share separately from 3C move rate.
  var midLeadW=0;for(i=0;i<rs.length;i++){
    rr=rs[i];p=rr.cornerPositions||[];
    if(n(p[0],0)>1&&p.slice(1).some(function(v){return n(v,0)===1})){
      ww=(w[i]||1)*(String(rr.track||'')===String(r&&r.track||'')?1.10:1)*
        (Math.abs(n(rr.distance,0)-n(r&&r.distance,0))<=200?1.12:1);
      midLeadW+=ww
    }
  }
  return{samples:rs.length,firstCornerSamples:rs.length,prevEarly:prevEarly,prevLeader:prevLeader,
    prevRear:prevRear,firstPos:first,lastPositions:lp,bucket:bucket,
    leadRate:leadDen?leadW/leadDen:0,earlyRate:leadDen?earlyW/leadDen:0,
    moveHistory:moveDen?moveW/moveDen:0,midRaceLead:leadDen?midLeadW/leadDen:0,
    rearHistory:rearDen?rearW/rearDen:0}
}
