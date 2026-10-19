function mergeOddsPayload(body){
  if(!state.race||!body)return false;
  var changed=false,predictionInputChanged=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h,old;
  for(i=0;i<rows.length;i++){
    z=rows[i]||{};
    if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z
  }
  for(i=0;i<hs.length;i++){
    h=hs[i];z=map[n(h.horseNumber)];
    if(!z)continue;
    var wasScratch=isScratchHorse(h);
    // An odds-only refresh must carry the withdrawal state even when its
    // updated horse has no odds and no body weight.
    var liveScratch=z.scratched===true||z.withdrawn===true||
      /欠場|出走取消|取消|競走除外|除外/.test(String(z.status||z.horse_status||''));
    if(liveScratch&&!wasScratch){
      h.scratched=true;
      h.status=String(z.status||z.horse_status||'出走取消');
      h.winOdds=null;h.popularity=null;
      changed=true;predictionInputChanged=true
    }
    if(wasScratch||liveScratch)continue;
    if(z.winOdds!=null&&String(z.winOdds)!==''){
      if(String(h.winOdds||'')!==String(z.winOdds))changed=true;
      h.winOdds=z.winOdds
    }
    if(z.popularity!=null&&String(z.popularity)!==''){
      if(String(h.popularity||'')!==String(z.popularity))changed=true;
      h.popularity=z.popularity
    }
    if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){
      old=String(h.bodyWeight||'');
      if(old!==String(z.bodyWeight)){changed=true;predictionInputChanged=true}
      h.bodyWeight=z.bodyWeight
    }
    if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){
      old=String(h.bodyWeightChange||'');
      if(old!==String(z.bodyWeightChange)){changed=true;predictionInputChanged=true}
      h.bodyWeightChange=z.bodyWeightChange
    }
    if(z.status!=null&&String(z.status)!==''){
      if(String(h.status||'')!==String(z.status)){changed=true;predictionInputChanged=true}
      h.status=z.status
    }
    if(z.oddsSource)h.oddsSource=z.oddsSource;
    if(z.oddsForecast===false)h.oddsForecast=false
  }
  if(body.oddsSource)state.race.oddsSource=body.oddsSource;
  if(body.sourcePublishedAt)state.race.sourcePublishedAt=body.sourcePublishedAt;
  if(body.popularitySource)state.race.popularitySource=body.popularitySource;
  if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;
  if(predictionInputChanged){
    try{delete state.race._prediction}catch(e){}
    state.pred=null;state.analysisSaved={}
  }
  return changed
}
