function minetaAssignRoles(rows,r,ctx,pressure){
  rows=rows||[];ctx=ctx||minetaRaceContext(rows,r);pressure=pressure||pressureInfo(rows);
  var byNo={},abilityVals=rows.map(function(z){return n(z.ability,.5)}).sort(function(a,b){return a-b}),abilityMed=abilityVals.length?abilityVals[Math.floor(abilityVals.length/2)]:.5;
  rows.forEach(function(z){byNo[n(z.horse.horseNumber)]=z});
  rows.forEach(function(x){
    var no=n(x.horse.horseNumber),p=x.minetaPast||minetaPastProfile(x.horse,r),q=pressure[no]||{},
        left=byNo[no-1],left2=byNo[no-2],right=byNo[no+1],right2=byNo[no+2],role='不明',notes=[];
    if(!p.firstPos){x.expected='不明';x.minetaRole='不明';x.minetaNotes=['初角通過順位不足'];return}
    if((p.firstCornerSamples>=2&&p.leadRate>=.26)||
       (p.prevLeader&&n(x.rawFront,x.front)>=.22))role='逃げ候補';
    else if(p.prevEarly||p.bucket==='先行')role='先行';
    else if(p.bucket==='準先行')role='好位';
    else if(p.bucket==='準後方')role='中団';
    else role='後方';

    if(p.midRaceLead>=.20||p.moveHistory>=.35){if(role==='後方')role='中団';else if(role==='中団'&&n(x.ability)>=abilityMed)role='好位';notes.push(p.midRaceLead>=.20?'道中先頭歴':'道中進出歴')}
    if(x.lengthen&&x.minetaLengthenForward){if(role==='後方'&&(n(x.move)>=.28||n(x.ability)>=abilityMed))role='中団';else if(role==='中団'&&ctx.rawOcc<=.33)role='好位';notes.push('距離延長＋前進根拠あり')}
    if(x.shorten&&ctx.rawOcc>=.45){if(role==='好位'&&!p.prevEarly)role='中団';if(role==='中団'&&n(x.rawClose,x.close)>=.35)role='後方';notes.push('前多め＋距離短縮で脚ため')}
    if(ctx.rawOcc<=.25&&ctx.rearOcc>=.45){if(role==='中団'&&(n(x.ability)>=abilityMed||n(x.move)>=.30))role='好位';else if(role==='後方'&&n(x.move)>=.45)role='中団';notes.push('後方馬多く相対的に前')}

    x.minetaEscapeOutside=!!(left&&n(left.minetaLeadRank,0)>0&&n(left.minetaLeadRank)<=2&&!x.minetaEarlyIntent);
    x.minetaStrongLeaderOutside=!!(left&&n(left.minetaLeadRank,0)===1&&n(left.ability,.5)>=abilityMed&&!x.minetaEarlyIntent);
    x.minetaEscapeSandwich=!!(left&&right&&left.minetaEarlyIntent&&right.minetaEarlyIntent&&!x.minetaEarlyIntent);
    x.minetaSameStyleCrowd=!!((left&&left.minetaPast&&left.minetaPast.bucket===p.bucket)||(right&&right.minetaPast&&right.minetaPast.bucket===p.bucket));
    x.minetaDifferentStyleNeighbor=!!(
      (left&&left2&&left.minetaPast&&left2.minetaPast&&left.minetaPast.bucket===left2.minetaPast.bucket&&left.minetaPast.bucket!==p.bucket)||
      (right&&right2&&right.minetaPast&&right2.minetaPast&&right.minetaPast.bucket===right2.minetaPast.bucket&&right.minetaPast.bucket!==p.bucket)
    );
    if(x.minetaEscapeSandwich)notes.push('逃げ挟み');
    if(x.minetaStrongLeaderOutside)notes.push('強い先行馬の外');
    else if(x.minetaEscapeOutside)notes.push('逃げ馬の外');
    if(x.minetaSameStyleCrowd)notes.push('同脚質並び');
    if(x.minetaDifferentStyleNeighbor)notes.push('同脚質の塊の隣');
    if(p.prevEarly)notes.push('前走3番手以内');
    if(ctx.rawOcc>=.45&&x.minetaEarlyIntent&&x.outer)notes.push('前多め＋外で先行負荷');
    if(ctx.firstTurn<300&&x.minetaEarlyIntent&&x.inner)notes.push('初角近く内で先行しやすい');

    if(n(x.minetaLeadRank,0)===1&&role!=='不明')role='逃げ候補';
    else if(n(x.minetaLeadRank,0)>1&&role==='逃げ候補')role='先行';

    x.expected=role;x.minetaRole=role;x.minetaNotes=notes.slice(0,5);
    if(role==='逃げ候補')x.goProb=Math.max(n(x.goProb),.64);
    else if(role==='先行')x.goProb=Math.max(n(x.goProb),.53);
    else if(role==='好位')x.goProb=clamp(n(x.goProb),.38,.56);
    else if(role==='中団')x.goProb=Math.min(n(x.goProb),.44);
    else if(role==='後方')x.goProb=Math.min(n(x.goProb),.34);
    if(x.minetaEscapeOutside){x.flexibility=clamp(n(x.flexibility,.5)+.05,0,1);x.trafficTol=clamp(n(x.trafficTol,.5)+.05,0,1)}
    if(x.minetaStrongLeaderOutside){x.latePower=clamp(n(x.latePower,.5)+.035,0,1);x.move=clamp(n(x.move,.2)+.035,0,1)}
    if(x.minetaEscapeSandwich){x.trafficTol=clamp(n(x.trafficTol,.5)+.08,0,1);x.latePower=clamp(n(x.latePower,.5)+.04,0,1)}
    if(x.minetaDifferentStyleNeighbor){x.flexibility=clamp(n(x.flexibility,.5)+.035,0,1);x.trafficTol=clamp(n(x.trafficTol,.5)+.035,0,1)}
    if(ctx.firstTurn<300&&x.minetaEarlyIntent&&x.inner){x.goProb=clamp(n(x.goProb,.5)+.04,0,1);x.frontStay=clamp(n(x.frontStay,.5)+.025,0,1)}
    if(x.minetaSameStyleCrowd&&!x.minetaEscapeOutside&&!x.minetaEscapeSandwich&&!x.minetaDifferentStyleNeighbor)x.frontCost=clamp(n(x.frontCost,0)+.025,0,.30)
  });
  return ctx
}
