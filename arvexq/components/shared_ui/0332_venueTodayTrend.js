function venueTodayTrend(){
  var rows=venueRows(),completed=0,frameCount={},frameSamples=0,inner=0,outer=0,front=0,mid=0,close=0,styleSamples=0;
  rows.forEach(function(r){
    var d=resultDetailForTrend(r),fs=((d.result||{}).finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});
    if(!fs.length)return;completed++;
    var field=Math.max(1,n(d.fieldSize,(d.horses||[]).length||fs.length));
    fs.slice(0,3).forEach(function(f){
      var fr=n(f.frameNumber,0),h;
      if(!fr&&(d.horses||[]).length){h=(d.horses||[]).find(function(z){return n(z.horseNumber)===n(f.horseNumber)});fr=n(h&&h.frameNumber,0)}
      if(fr){frameCount[fr]=(frameCount[fr]||0)+1;frameSamples++;if(fr<=4)inner++;else outer++}
      var cp=(f.cornerPositions||[]).filter(function(v){return n(v)>0});
      if(cp.length){var pos=n(cp[0]),frontCut=Math.max(2,Math.ceil(field*.22)),midCut=Math.max(4,Math.ceil(field*.45));if(pos<=frontCut)front++;else if(pos<=midCut)mid++;else close++;styleSamples++}
    })
  });
  var bias='集計中';
  if(frameSamples>=3){var share=inner/frameSamples;bias=share>=.62?'内有利':(share<=.38?'外有利':'フラット')}
  var style='集計中';
  if(styleSamples>=3){var fp=front/styleSamples,cp=close/styleSamples;style=fp>=.55?'逃げ・先行':(cp>=.45?'差し・追込':'フラット')}
  var frames=Object.keys(frameCount).sort(function(a,b){return frameCount[b]-frameCount[a]||n(a)-n(b)}).slice(0,2),good=frames.length?frames.join('・')+'枠':'集計中';
  return {completed:completed,bias:bias,style:style,frames:good}
}
