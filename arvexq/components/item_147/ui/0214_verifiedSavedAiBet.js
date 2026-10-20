function verifiedSavedAiBet(r,plan){
  if(!r||!r.id||!plan||!plan.fixedAt)return null;
  // Failed server captures carry a timestamp too. They are retry receipts,
  // never immutable original tickets and must not block a pre-off retry.
  if(plan.captureStatus==='failed'||plan.captureStatus==='engine-missing'||
     plan.decision==='未取得'||plan.decision==='エラー'||plan.decision==='データ不足'||
     (plan.betInputGate&&plan.betInputGate.ready===false))return null;
  if(plan.raceId&&String(plan.raceId)!==String(r.id))return null;
  if(plan.raceDate&&String(plan.raceDate)!==String(r.date))return null;
  var off=Date.parse(String(r.date||'')+'T'+String(r.scheduledStartTime||r.startTime||'').slice(0,5)+':00+09:00');
  var at=Date.parse(String(plan.fixedAt||''));
  if(!isFinite(off)||!isFinite(at)||at>=off)return null;
  return plan
}
