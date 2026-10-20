function horseDisplayName(r,h){
  h=h||{};var no=n(h.horseNumber,0),pools=[r&&r.horses,r&&r.entries,r&&r.runners,r&&r.starters,r&&r.raceEntries,r&&r.aiEvaluation&&r.aiEvaluation.horses,r&&r.result&&r.result.finishers],i,j,z,nm;
  nm=String(h.name||h.horseName||'').trim();if(nm)return nm;
  for(i=0;i<pools.length;i++){var a=pools[i];if(!Array.isArray(a))continue;for(j=0;j<a.length;j++){z=a[j]||{};if(no&&n(z.horseNumber||z.number||z.no,0)!==no)continue;nm=String(z.name||z.horseName||z.hname||'').trim();if(nm)return nm}}
  return no?(no+'番 馬名取得中'):'馬名取得中';
}
// Research-only evidence is maintained in /research/research_view.js.
