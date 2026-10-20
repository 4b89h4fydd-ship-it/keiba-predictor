function resultStatus(r){
  // D1 may publish an official 確定 summary after the cached detail was 速報.
  // A stale detail must not downgrade the newer confirmed summary.
  var stored=String(r&&r.result&&r.result.status||""),
      summary=String(r&&r.raceStatus||"");
  if(stored==="確定"||summary==="確定")return "確定";
  if(stored==="速報"||summary==="速報")return "速報";
  return "";
}
