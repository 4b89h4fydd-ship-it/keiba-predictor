function currentBetEnginePlan(plan){
  // The historical receipt is view-only. The caller already verified its
  // race identity and strictly pre-off timestamp. Engine migration must not
  // erase previously frozen tickets or recalculate them using final results.
  return plan&&Array.isArray(plan.items)&&(plan.items.length||plan.decision==='見送り')?plan:null
}
