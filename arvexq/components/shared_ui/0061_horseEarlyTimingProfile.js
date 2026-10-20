function horseEarlyTimingProfile(h,r){
  // This is a pre-race, five-run evidence adapter. Race-wide leader laps and
  // unreferenced estimates must never become individual measured values.
  var runs=historicalWindow(h,r),samples=[],weights=recencyWeights(runs.length),i;
  for(i=0;i<runs.length;i++){
    var raw=runs[i]&&runs[i].earlyTiming||{},kind=String(raw.sourceKind||''),
        source=String(raw.sourceRef||'').trim(),a=Number(raw.first200mSeconds),
        g=Number(raw.gateReactionSeconds),acc=Number(raw.acceleration0to100Mps2),
        has200=raw.first200mSeconds!=null&&isFinite(a)&&a>=7&&a<=25,
        hasGate=raw.gateReactionSeconds!=null&&isFinite(g)&&g>=.05&&g<=3,
        hasAcc=raw.acceleration0to100Mps2!=null&&isFinite(acc)&&acc>=.1&&acc<=10;
    if((kind!=='individual_sensor'&&kind!=='video_estimate')||!source||(!has200&&!hasGate&&!hasAcc))continue;
    // Visual estimates remain estimates even if derived from a frame index.
    samples.push({kind:kind,source:source,date:String(runs[i].date||''),weight:(weights[i]||1)*(kind==='individual_sensor'?1:.55),
      first200mSeconds:has200?a:null,gateReactionSeconds:hasGate?g:null,acceleration0to100Mps2:hasAcc?acc:null});
  }
  function weighted(key,transform){
    var sum=0,w=0; samples.forEach(function(z){if(z[key]==null)return;sum+=z.weight*transform(z[key]);w+=z.weight});return{score:w?clamp(sum/w,0,1):null,weight:w}
  }
  // Capped qualitative normalization, NOT a calibrated speed probability.
  var first=weighted('first200mSeconds',function(v){return(16.2-v)/5.2}),
      gate=weighted('gateReactionSeconds',function(v){return(1-v)/.85}),
      accel=weighted('acceleration0to100Mps2',function(v){return v/5.5}),
      scores=[],ws=[];
  if(first.score!=null){scores.push(first.score);ws.push(.72)}
  if(gate.score!=null){scores.push(gate.score);ws.push(.18)}
  if(accel.score!=null){scores.push(accel.score);ws.push(.10)}
  var sum=ws.reduce(function(a,b){return a+b},0),value=sum?scores.reduce(function(a,v,i){return a+v*ws[i]},0)/sum:null,
      reliability=Math.min(1,samples.reduce(function(a,z){return a+z.weight},0)/2),
      timingWeight=value==null?0:clamp(.14+.23*reliability,0,.37),
      gateWeight=gate.score==null?0:clamp(.12+.23*reliability,0,.35);
  return{samples:samples,sourceKind:samples.some(function(x){return x.kind==='individual_sensor'})?'individual_sensor':(samples.length?'video_estimate':'none'),
    first200Score:first.score,gateScore:gate.score,accelerationScore:accel.score,
    timingScore:value,timingWeight:timingWeight,gateWeight:gateWeight,
    measuredSamples:samples.filter(function(x){return x.kind==='individual_sensor'}).length,
    videoSamples:samples.filter(function(x){return x.kind==='video_estimate'}).length}
}
