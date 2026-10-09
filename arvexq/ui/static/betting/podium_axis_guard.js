/* A dated, de-duplicated five-run context gate for new pre-off ◎.
 * No historical odds, post-off data, or invented observations. */
(function(global){
'use strict';
const VERSION='arvexq-axis-reliability-v2-past-context';
function n(x,d=0){return x==null||x===''||!Number.isFinite(Number(x))?d:Number(x)}
function parseDate(x){
 const v=String(x||'').trim().replace(/\//g,'-').replace(/\./g,'-');
 const t=/^\d{8}$/.test(v)?v.slice(0,4)+'-'+v.slice(4,6)+'-'+v.slice(6,8):v.slice(0,10);
 return /^\d{4}-\d{2}-\d{2}$/.test(t)&&Number.isFinite(Date.parse(t+'T00:00:00Z'))?t:'';
}
function recent(horse,race){
 const cutoff=parseDate(race&&(race.date||race.raceDate)),entries=[],seen=new Set();
 if(!cutoff)return [];
 ['recentRaces','allPastRuns','pastRaces','history','runs'].forEach(function(key){
  ((horse&&horse[key])||[]).forEach(function(run){
   if(!run||typeof run!=='object')return;
   const date=parseDate(run.date||run.raceDate||run['日付']),
         finish=n(run.finish||run.finishPosition||run.rank||run['着順']),
         field=n(run.fieldSize||run.runners||run['頭数']),
         track=String(run.track||run.venue||run.course||run['競馬場']||''),
         dist=n(run.distance||run.distanceM||run['距離']),
         title=String(run.title||run.raceName||run.name||run['レース名']||''),
         key=[date,track,dist,title,finish].join('|');
   if(!date||date>=cutoff||finish<1||field<2||finish>field||seen.has(key))return;
   seen.add(key);entries.push({run:run,date:date,finish:finish,field:field,track:track,dist:dist});
  });
 });
 return entries.sort((a,b)=>b.date.localeCompare(a.date)).slice(0,5);
}
function positions(x){
 if(Array.isArray(x))return x.map(v=>n(v)).filter(v=>v>0);
 return (String(x||'').match(/\d+/g)||[]).map(v=>n(v)).filter(v=>v>0);
}
function analyzePast(horse,race){
 const rows=recent(horse,race),field=rows.length,track=String(race&&race.track||''),
       distance=n(race&&(race.distance||race.distanceM)),
       surface=String(race&&race.surface||''),
       going=String(race&&(race.condition||race.going)||''),
       weights=[5,4,3,2,1];
 let top3=0,comparableRuns=0,comparableTop3=0,frontFadeCount=0,
     matchedTrack=0,matchedGoing=0,quality=0,totalWeight=0,compareQuality=0;
 const metrics=rows.map(function(x,i){
  const run=x.run,passing=positions(run.cornerPositions||run.passing||run['通過順位']),
        first=passing[0]||0,front=first>0&&first<=Math.max(2,Math.floor((x.field+2)/3)),
        fade=front&&x.finish>Math.max(3,Math.floor((x.field*2)/3)),
        q=(x.field-x.finish)/(x.field-1),
        raceSurface=String(run.surface||run.trackType||run['馬場']||''),
        dist=n(run.distance||run.distanceM||run['距離']),
        comparable=!!(distance&&dist&&surface&&raceSurface&&Math.abs(distance-dist)<=150&&raceSurface===surface),
        matchTrack=!!(track&&x.track===track),
        matchGoing=!!(going&&(run.condition||run.going||run['馬場状態'])&&
                   String(run.condition||run.going||run['馬場状態'])===going);
  top3+=x.finish<=3?1:0;frontFadeCount+=fade?1:0;
  matchedTrack+=matchTrack?1:0;matchedGoing+=matchGoing?1:0;
  quality+=weights[i]*q;totalWeight+=weights[i];
  if(comparable){comparableRuns++;comparableTop3+=x.finish<=3?1:0;compareQuality+=q}
  return {date:x.date,finish:x.finish,fieldSize:x.field,firstCorner:first||null,
          comparable:comparable,top3:x.finish<=3,frontFaded:!!fade,quality:q};
 });
 const flags=[];
 if(comparableRuns>=2&&comparableTop3===0)flags.push('same-surface-distance-no-podium');
 if(frontFadeCount>=2)flags.push('repeated-front-fade');
 if(field>=4&&metrics.slice(0,2).every(x=>!x.top3)&&metrics.slice(2).filter(x=>x.top3).length>=2)
  flags.push('recent-form-downturn');
 return {version:VERSION,starts:field,datedRuns:field,top3:top3,rate:field?top3/field:0,
         comparableRuns:comparableRuns,comparableTop3:comparableTop3,
         comparableQuality:comparableRuns?compareQuality/comparableRuns:null,
         recentFormQuality:field?quality/totalWeight:null,
         trackMatchedRuns:matchedTrack,goingMatchedRuns:matchedGoing,
         frontFadeCount:frontFadeCount,riskFlags:flags,
         status:field?'dated-observed':'missing-dated-past-runs'};
}
function inspect(candidate,runner){
 const h=candidate&&(candidate.podiumPastFive||candidate.podiumAxisHistory)||{},
       starts=n(h.starts),top3=n(h.top3),rate=starts>0?top3/starts:0,
       gap=n(candidate&&candidate.podiumAxisScore)-n(runner&&runner.podiumAxisScore),
       evidence=n(candidate&&candidate.edgeEvidence,n(candidate&&candidate.coverage)),
       coverage=n(candidate&&candidate.coverage),
       winRank=n(candidate&&candidate.winnerDecisionRank,99),
       risk=h.riskFlags||[];
 const checks={
   eligibleRunner:!!candidate&&!!runner&&n(candidate.horse&&candidate.horse.horseNumber)>0,
   historyVerified:starts>=3&&h.status==='dated-observed',
   historicalPodium:starts>=3&&top3>=2&&rate>=.60&&(starts<5||top3>=3),
   matchingConditionEvidence:n(h.comparableRuns)<2||n(h.comparableTop3)>=1,
   noRepeatedFrontFade:!risk.includes('repeated-front-fade'),
   recentFormNotDeteriorating:!risk.includes('recent-form-downturn'),
   axisStrength:n(candidate&&candidate.podiumAxisScore)>=.62,
   clearSeparation:gap>=.03,
   broadConsensus:n(candidate&&candidate.axisRank,99)<=2&&
                  n(candidate&&candidate.podiumRecallRank,99)<=3,
   winningChance:winRank<=3,
   observedEvidence:evidence>=.42&&coverage>=.50
 };
 const failures=Object.keys(checks).filter(k=>!checks[k]);
 return {version:VERSION,eligible:failures.length===0,failures,checks,
   observedStarts:starts,observedTop3:top3,observedTop3Rate:rate,
   axisGap:gap,winRank:winRank,
   pastContext:{datedRuns:starts,comparableRuns:n(h.comparableRuns),
     comparableTop3:n(h.comparableTop3),frontFadeCount:n(h.frontFadeCount),
     riskFlags:risk.slice()},
   disclaimer:'dated pre-off five-run evidence, not calibrated win/place probability'};
}
global.ARVEXQPodiumAxisGuard=Object.freeze({VERSION,inspect,analyzePast});
})(window);