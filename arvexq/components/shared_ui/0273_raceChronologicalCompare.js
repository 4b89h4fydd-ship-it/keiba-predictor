function raceChronologicalCompare(a,b){
  var ra=(a&&a.race)||a||{},rb=(b&&b.race)||b||{},ta=mins(ra.startTime),tb=mins(rb.startTime);
  if(ta!==tb)return ta-tb;
  var tc=String(ra.track||'').localeCompare(String(rb.track||''),'ja');if(tc)return tc;
  return n(ra.raceNumber)-n(rb.raceNumber)
}
// Strict selection is performed in strictSelectedRaceProfile; there is no top-1 cap.
