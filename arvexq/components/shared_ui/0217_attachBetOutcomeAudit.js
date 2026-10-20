function attachBetOutcomeAudit(plan,r,p){
  if(!plan||!p||plan.fixedAt)return plan;
  var o=p.outcome||paceOutcomeModel(r,p);if(!o)return plan;
  function ids(xs){return (xs||[]).map(function(x){return n(x&&x.horse&&x.horse.horseNumber)}).filter(function(no){return no>0})}
  plan.outcomeLink={verdict:o.verdict,first:ids(o.first),second:ids(o.second),third:ids(o.third)};
  return plan
}
// Marks are explanatory annotations, not a competing ticket selector.
