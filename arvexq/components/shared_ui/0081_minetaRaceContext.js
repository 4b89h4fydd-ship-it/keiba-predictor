function minetaRaceContext(rows,r){
  rows=rows||[];var active=rows.filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)}),field=Math.max(1,active.length),raw=0,adjusted=0,rear=0,leadPool=[],
      av=active.map(function(x){return n(x.ability,.5)}).sort(function(a,b){return a-b}),abilityMed=av.length?av[Math.floor(av.length/2)]:.5;
  active.forEach(function(z){
    var p=z.minetaPast||minetaPastProfile(z.horse,r);z.minetaPast=p;
    var early=!!p.prevEarly||(p.firstCornerSamples>=2&&n(p.earlyRate)>=.48),
        forwardEvidence=!!p.prevLeader||p.bucket==='準先行'||p.midRaceLead>=.20||p.moveHistory>=.35||
          (n(z.ten,.5)>=.58&&n(z.breakSkill,.5)>=.52)||
          (n(z.ability,.5)>=abilityMed&&p.rearHistory<.45&&n(z.positionTrend,.5)>=.50),
        adjustedEarly=early||(!!z.lengthen&&p.samples>0&&forwardEvidence&&p.rearHistory<.70);
    z.minetaEarlyIntent=adjustedEarly;z.minetaRawEarly=early;z.minetaLengthenForward=!!(adjustedEarly&&!early);
    if(early)raw++;if(adjustedEarly)adjusted++;if(p.prevRear)rear++
  });
  leadPool=active.filter(function(z){var q=z.minetaPast||{};return (q.prevLeader&&n(q.earlyRate)>=.25)||(q.firstCornerSamples>=2&&n(q.leadRate)>=.22)||z.rawFront>=.18||z.goProbBase>=.50||z.lengthen}).sort(function(a,b){
    var ap=a.minetaPast||{},bp=b.minetaPast||{};
    if(n(bp.leadRate)!==n(ap.leadRate))return n(bp.leadRate)-n(ap.leadRate);
    if(n(bp.earlyRate)!==n(ap.earlyRate))return n(bp.earlyRate)-n(ap.earlyRate);
    if(!!b.lengthen!==!!a.lengthen)return b.lengthen?1:-1;
    if(n(b.rawFront)!==n(a.rawFront))return n(b.rawFront)-n(a.rawFront);
    if(n(b.ten)!==n(a.ten))return n(b.ten)-n(a.ten);
    if(n(b.breakSkill)!==n(a.breakSkill))return n(b.breakSkill)-n(a.breakSkill);
    if(n(b.needLead)!==n(a.needLead))return n(b.needLead)-n(a.needLead);
    if(n(b.ability)!==n(a.ability))return n(b.ability)-n(a.ability);
    return n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  leadPool.slice(0,3).forEach(function(z,k){z.minetaLeadRank=k+1});
  var rawOcc=raw/field,adjustedOcc=adjusted/field,rearOcc=rear/field,band=rawOcc<=.25?'前少なめ':(rawOcc>=.45?'前多め':'中間');
  return{field:field,rawFrontCount:raw,adjustedFrontCount:adjusted,rearCount:rear,rawOcc:rawOcc,adjustedOcc:adjustedOcc,rearOcc:rearOcc,band:band,
    firstTurn:firstTurnDistance(r),leadNos:leadPool.slice(0,3).map(function(z){return n(z.horse.horseNumber)})}
}
