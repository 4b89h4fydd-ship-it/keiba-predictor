function markMandatoryTrifectaReview(plan,r){
  if(plan&&mandatoryTrifectaRace(r))plan.mandatoryTrifectaReviewed=plan.trifectaReviewed===true;
  return plan
}
