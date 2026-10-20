function captureExactaBetEvidence(ranked,rows){
  var axis=(rows||[]).find(function(z){return z&&z.horse&&z.predMark==='◎'})||null,
      axisNo=n(axis&&axis.horse&&axis.horse.horseNumber,0);
  if(!axisNo)return null;
  var arr=(ranked||[]).filter(function(z){return z&&z.combo&&n(z.combo[0])===axisNo})
    .map(function(z){return {second:n(z.combo[1]),joint:Math.max(0,n(z.score,0))}})
    .sort(function(a,b){return b.joint-a.joint||a.second-b.second});
  var total=arr.reduce(function(sum,z){return sum+z.joint},0);
  if(!total)return null;
  return {version:'exacta-conditional-v342',axis:axisNo,pairs:arr.map(function(z){
    return {second:z.second,joint:z.joint,p2GivenFirst:z.joint/total};
  })};
}
// Marks represent general 1st-to-3rd role, while an exacta requires
// the actual conditional 2nd-place model. Do not silently rewrite that model.
