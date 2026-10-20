function mergeHorseReflection(oldH,newH,liveH,cutoff){
  oldH=oldH||{};newH=newH||{};liveH=liveH||{};
  // Race-scoped numbers cannot establish a horse's identity across snapshots.
  var oldName=String(oldH.name||oldH.horseName||'').replace(/[\s\u3000]+/g,''),
      newName=String(newH.name||newH.horseName||'').replace(/[\s\u3000]+/g,'');
  if(oldName&&newName&&oldName!==newName)oldH={};
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
  // Existing history modules handle duplicate observations and race-day cutoff.
  // Neither a thin API response nor a stale browser cache may erase starts.
  if(cutoff&&typeof window!=='undefined'&&window.ARVEXQPastRunDeduplicate&&window.ARVEXQPastRunTemporal){
    var combined=window.ARVEXQPastRunDeduplicate.merge({
      recentRaces:[].concat(newH.recentRaces||[],oldH.recentRaces||[]),
      allPastRuns:[].concat(newH.allPastRuns||[],oldH.allPastRuns||[])
    });
    var prior=window.ARVEXQPastRunTemporal.beforeRace(combined,{date:cutoff},combined.length);
    if(prior.length){out.allPastRuns=prior;out.recentRaces=prior.slice(0,5)}
  }
  // A historical unverified debut flag cannot override fetched career evidence.
  var audit=out._careerHistoryAudit||{};
  if(out.debutNoHistory&&!(
      audit.complete===true&&audit.reportedStarts===0&&audit.requestedAtRaceDate===cutoff&&
      !(out.allPastRuns||[]).length&&!(out.recentRaces||[]).length
    ))delete out.debutNoHistory;
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
