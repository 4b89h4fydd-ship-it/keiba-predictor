function alignBetPlanToMarks(plan,r,p){
  if(!plan||!p||!Array.isArray(plan.items)||plan.fixedAt)return plan;
  var marks={},axis=0,mismatches=[];
  (p.rows||[]).forEach(function(z){
    if(!z||!z.horse)return;
    var no=n(z.horse.horseNumber,0),mark=String(z.predMark||'').replace(/＋/g,'+');
    if(!no)return;
    marks[no]=mark;if(mark==='◎')axis=no;
  });
  (plan.items||[]).forEach(function(item){
    if(item.kind!=='馬単')return;
    (item.combos||[]).forEach(function(combo){
      var first=n(combo&&combo[0]),second=n(combo&&combo[1]),mark=marks[second]||'';
      if(first===axis&&(mark==='☆'||mark==='△'||mark==='注'))mismatches.push({first:first,second:second,mark:mark});
    });
  });
  plan.markAlignment={version:'v342-model-first-explain',axis:axis,mismatches:mismatches};
  return plan
}
// Every explanation is recorded with the candidate plan *before* it can be
// persisted. Historic locked plans never acquire explanations from live data.
