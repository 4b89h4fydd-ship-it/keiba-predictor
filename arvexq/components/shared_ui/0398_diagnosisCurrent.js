function diagnosisCurrent(r){
  var pm=r&&r.preparedMeta||{};
  return pm.diagnosisReady===true&&pm.diagnosisVersion==='arvexq-edge-2026.10-v53-consensus-rebuild'
}
