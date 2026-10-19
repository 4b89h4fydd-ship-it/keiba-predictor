function raceLiveBias(r,rows){
  rows=rows||[];
  var date=String(r&&r.date||state.date||''),circuit=String(r&&r.circuit||state.circuit||''),track=String(r&&r.track||state.track||''),raceNo=n(r&&r.raceNumber,99),
      completed=0,frameW=0,innerW=0,outerW=0,styleW=0,frontW=0,lateW=0,source=[];
  (state.races||[]).forEach(function(z){
    if(!z||String(z.date||date)!==date||String(z.circuit||'')!==circuit||String(z.track||'')!==track)return;
    if(n(z.raceNumber,99)>=raceNo)return;
    var d=resultDetailForTrend(z),fs=((d&&d.result||{}).finishers||[]).filter(function(x){return n(x&&x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});
    if(!fs.length)return;
    completed++;
    var gap=Math.max(1,raceNo-n(z.raceNumber,0)),rw=Math.pow(.86,Math.max(0,gap-1)),field=Math.max(1,n(d.fieldSize,(d.horses||[]).length||fs.length));
    source.push(n(z.raceNumber));
    fs.slice(0,3).forEach(function(f){
      var h,fr=n(f.frameNumber,0);if(!fr&&(d.horses||[]).length){h=(d.horses||[]).find(function(q){return n(q.horseNumber)===n(f.horseNumber)});fr=n(h&&h.frameNumber,0)}
      if(fr){var maxFrame=Math.max(2,Math.min(8,Math.ceil(field/2))),inside=clamp(1-(fr-1)/Math.max(1,maxFrame-1),0,1);frameW+=rw;innerW+=rw*inside;outerW+=rw*(1-inside)}
      var cp=(f.cornerPositions||[]).filter(function(v){return n(v)>0});
      if(cp.length){var pos=n(cp[0]),frontCut=Math.max(2,Math.ceil(field*.22)),lateCut=Math.max(frontCut+1,Math.ceil(field*.55));styleW+=rw;if(pos<=frontCut)frontW+=rw;else if(pos>=lateCut)lateW+=rw}
    })
  });
  var frameRaw=frameW?innerW/frameW:.5,frontRaw=styleW?frontW/styleW:.5,lateRaw=styleW?lateW/styleW:.25,
      evidence=clamp((completed/4)*.58+(Math.min(frameW,9)/9)*.22+(Math.min(styleW,9)/9)*.20,0,1),
      frameBias=.5+(frameRaw-.5)*evidence,frontBias=.5+(frontRaw-.5)*evidence,lateBias=.5+(lateRaw-.25)*evidence;
  var maxFrame=8;
  (r&&r.horses||[]).forEach(function(h){maxFrame=Math.max(maxFrame,n(h.frameNumber,0))});
  var byNo={};rows.forEach(function(x){
    var h=x.horse||{},fr=n(h.frameNumber,0),inside=fr?clamp(1-(fr-1)/Math.max(1,maxFrame-1),0,1):clamp(1-(n(h.horseNumber,1)-1)/Math.max(1,rows.length-1),0,1),
        rt=styleRates(h,r),early=clamp(rt.front*.52+rt.stalk*.28+rt.early3*.20,0,1),late=clamp(rt.mid*.30+rt.close*.48+rt.moved3*.22,0,1),
        drawFit=clamp(.5+(inside-.5)*(frameBias-.5)*4.0,0,1),
        styleSignal=frontBias-.5-(lateBias-.5)*.72,
        styleFit=clamp(.5+(early-late)*styleSignal*2.8,0,1);
    byNo[n(h.horseNumber)]={drawFit:drawFit,styleFit:styleFit,inside:inside,early:early,late:late}
  });
  return {completed:completed,evidence:evidence,frameBias:frameBias,frontBias:frontBias,lateBias:lateBias,byNo:byNo,sourceRaces:source}
}
// v313: same-day mark correction.  Only races that have already finished at the
// same venue/date are allowed to influence later marks.  One result is never enough:
// activation starts at two completed races and is strongly shrunk until 4-5 races.
