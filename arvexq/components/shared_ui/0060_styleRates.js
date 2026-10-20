function styleRates(h,r){
  var rs=historicalWindow(h,r),w=recencyWeights(rs.length),a=[0,0,0,0],
      den=0,early3=0,moved3=0,ten=0,samples=0;
  rs.forEach(function(rr,i){
    if(!validFirstCorner(rr))return;
    var first=n(rr.cornerPositions[0]),fs=raceField(rr),
        norm=(first-1)/Math.max(1,fs-1),delta=Math.abs(n(rr.distance)-n(r.distance)),
        rel=1,last=(rr.cornerPositions||[]).slice(1);
    if(delta<=100)rel*=1.22;
    else if(delta<=300)rel*=1.08;
    else if(delta>=700)rel*=.74;
    if(rr.track===r.track)rel*=1.10;
    if(rr.condition&&r.condition&&sameCondition(rr.condition,r.condition))rel*=1.05;
    var weight=w[i]*rel;den+=weight;samples++;
    if(first===1)a[0]+=weight;
    else if(first<=3||norm<=.22)a[1]+=weight;
    else if(norm<=.62)a[2]+=weight;
    else a[3]+=weight;
    if(first<=3)early3+=weight;
    if(first>3&&last.some(function(v){return n(v)>0&&n(v)<=3}))moved3+=weight;
    ten+=weight*clamp(1-(first-1)/Math.max(3,fs-1),0,1)
  });
  if(!den)return{front:0,stalk:0,mid:0,close:0,early3:0,moved3:0,
    ten:.5,samples:0,availableRuns:rs.length,unknown:true,source:'recent5'};
  return{front:a[0]/den,stalk:a[1]/den,mid:a[2]/den,close:a[3]/den,
    early3:early3/den,moved3:moved3/den,ten:ten/den,samples:samples,
    availableRuns:rs.length,unknown:false,source:'recent5'}
}
