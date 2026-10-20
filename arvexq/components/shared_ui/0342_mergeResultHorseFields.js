function mergeResultHorseFields(r){
  if(typeof window!=='undefined'&&window.ARVEXQRaceIdentity)r=window.ARVEXQRaceIdentity.sanitize(r);
  if(!r)return r;
  var fs=r.result&&r.result.finishers||[],by={};
  fs.forEach(function(f){var no=n(f&&f.horseNumber,0);if(no)by[no]=f});
  (r.horses||[]).forEach(function(h){var f=by[n(h.horseNumber,0)];if(!f)return;['bodyWeight','bodyWeightChange','popularity','winOdds'].forEach(function(k){if((h[k]==null||h[k]==='')&&f[k]!=null&&f[k]!=='')h[k]=f[k]})});
  return r
}
