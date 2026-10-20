function mergeHorseReflection(oldH,newH,liveH){
  oldH=oldH||{};newH=newH||{};liveH=liveH||{};
  var out=Object.assign({},oldH),richArrays=['recentRaces','allPastRuns'],k;
  Object.keys(newH).forEach(function(key){
    var v=newH[key];
    if(richArrays.indexOf(key)>=0){
      var a=Array.isArray(out[key])?out[key]:[],b=Array.isArray(v)?v:[];
      if(b.length>=a.length&&b.length)out[key]=b;
      return
    }
    // A roster/odds response must never replace a D1 learned mark with an
    // old integrated evaluation merely because the horse number matches.
    if(key==='integratedEvaluation'){
      var prior=out.integratedEvaluation||{},candidate=v||{};
      if(String(prior.markEngineVersion||prior.markSource||'').indexOf('arvexq-learned-whole-career')===0&&
         String(candidate.markEngineVersion||candidate.markSource||'').indexOf('arvexq-learned-whole-career')!==0)return;
    }
    if(key==='scratched'){
      if(v===true||out[key]!==true)out[key]=!!v;
      return
    }
    if(key==='status'&&isScratchHorse(out)&&!isScratchHorse(newH))return;
    if(reflectUseful(v))out[key]=v
  });
  ['winOdds','popularity','bodyWeight','bodyWeightChange','status','updatedAt'].forEach(function(key){
    if(liveH[key]!=null&&liveH[key]!==''){
      if(key==='status'&&isScratchHorse(out)&&!/欠場|出走取消|取消|競走除外|除外/.test(String(liveH[key])))return;
      out[key]=liveH[key]
    }
  });
  if(liveH.scratched===true){out.scratched=true;if(!isScratchHorse(out))out.status='出走取消'}
  if(liveH.horseNumber)out.horseNumber=liveH.horseNumber;
  return out
}
// Result updates can be sparse: newer racecard/poll payloads must not erase
// already verified finishers, payout rows, or a final status.
