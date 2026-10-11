/* Pure ARVEXQPaceSimulation calculations. Dependencies are explicit; no storage or UI state. */
(function(global){
'use strict';
function create(deps){
var clamp=deps.clamp;
var courseProfile=deps.courseProfile;
var courseTraits=deps.courseTraits;
var firstTurnDistance=deps.firstTurnDistance;
var mean=deps.mean;
var n=deps.n;
function pressureInfo(rows){var sorted=rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),p={},attacks=[],hot=[],segFor=[],segments=[],i,x,l,r,lp,rp,base,current=null;function attack(z){if(!z)return 0;base=z.goProbBase!=null?z.goProbBase:z.goProb;return clamp(base*(.46+.34*z.needLead+.20*z.ten),0,1.2)}for(i=0;i<sorted.length;i++){attacks[i]=attack(sorted[i]);hot[i]=attacks[i]>.50&&n(sorted[i].goProbBase,sorted[i].goProb)>=.44}for(i=0;i<sorted.length;i++){if(hot[i]){if(!current||i===0||!hot[i-1]||n(sorted[i].horse.horseNumber)-n(sorted[i-1].horse.horseNumber)!==1){current={idx:[]};segments.push(current)}current.idx.push(i);segFor[i]=current}else current=null}for(i=0;i<sorted.length;i++){x=sorted[i];l=i?sorted[i-1]:null;r=i<sorted.length-1?sorted[i+1]:null;lp=l&&n(x.horse.horseNumber)-n(l.horse.horseNumber)===1?attacks[i-1]:0;rp=r&&n(r.horse.horseNumber)-n(x.horse.horseNumber)===1?attacks[i+1]:0;var leftHot=lp>.50,rightHot=rp>.50,sandwich=leftHot&&rightHot?1:0,escapeSide=(leftHot||rightHot)&&!sandwich?1:0,adj=(leftHot?1:0)+(rightHot?1:0),near2=0;if(i>1&&n(x.horse.horseNumber)-n(sorted[i-2].horse.horseNumber)===2)near2+=attacks[i-2]*.14;if(i<sorted.length-2&&n(sorted[i+2].horse.horseNumber)-n(x.horse.horseNumber)===2)near2+=attacks[i+2]*.14;var seg=segFor[i]||null,clusterLen=seg?seg.idx.length:0,clusterPos=seg?seg.idx.indexOf(i):-1,lineMiddle=clusterLen>=3&&clusterPos>0&&clusterPos<clusterLen-1?1:0,lineEnd=clusterLen>=2&&(clusterPos===0||clusterPos===clusterLen-1)?1:0,innerEnd=lineEnd&&clusterPos===0?1:0,outerEnd=lineEnd&&clusterPos===clusterLen-1?1:0,lineEndRelief=lineEnd?(.05+.08*x.flexibility):0;if(outerEnd&&!rightHot)lineEndRelief+=.04;if(innerEnd&&!leftHot)lineEndRelief+=.025;var conflict=(lp+rp)*(.43+.38*x.needLead+.19*x.ten)*(1-.42*x.flexibility)+near2+lineMiddle*(.10+.10*x.needLead)+(clusterLen>=4?.04:0);conflict=Math.max(0,conflict-lineEndRelief*.42);var freeOuter=x.edge?(.055+.075*x.flexibility):0,lineRole=lineMiddle?'先行列中央':(outerEnd?'先行列外端':(innerEnd?'先行列最内':(lineEnd?'先行列端':'単独/飛び')));p[n(x.horse.horseNumber)]={adj:adj,sandwich:sandwich,escapeSide:escapeSide,conflict:clamp(conflict,0,1.7),freeOuter:freeOuter,left:lp,right:rp,leftHot:leftHot,rightHot:rightHot,selfAttack:attacks[i],clusterLen:clusterLen,lineMiddle:lineMiddle,lineEnd:lineEnd,innerEnd:innerEnd,outerEnd:outerEnd,lineEndRelief:lineEndRelief,lineRole:lineRole}}return p}

function frontArrangement(rows,pressure){pressure=pressure||pressureInfo(rows);var field=Math.max(1,rows.length),front=rows.filter(function(x){return x.minetaEarlyIntent||x.expected==='逃げ候補'||x.expected==='先行'||x.goProb>=.50}).sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),segments=[],cur=[],i,x,no,prev=0;for(i=0;i<front.length;i++){x=front[i];no=n(x.horse.horseNumber);if(!cur.length||no===prev+1)cur.push(x);else{segments.push(cur);cur=[x]}prev=no}if(cur.length)segments.push(cur);var adjacentPairs=0,longest=0;for(i=0;i<segments.length;i++){longest=Math.max(longest,segments[i].length);adjacentPairs+=Math.max(0,segments[i].length-1)}var pattern=!front.length?'前候補なし':(front.length===1?'単独':(adjacentPairs===0?'飛び飛び':(longest>=3?'連続':'一部連続'))),innerCut=Math.ceil(field*.35),outerCut=Math.floor(field*.65)+1,innerCount=front.filter(function(z){return n(z.horse.horseNumber)<=innerCut}).length,outerCount=front.filter(function(z){return n(z.horse.horseNumber)>=outerCut}).length,innerShare=front.length?innerCount/front.length:0,outerShare=front.length?outerCount/front.length:0,concentrationText=innerShare>=.60?'内枠に集中':(outerShare>=.60?'外枠に集中':'内外に分散'),scored=rows.slice();for(i=0;i<scored.length;i++){x=scored[i];var q=pressure[n(x.horse.horseNumber)]||{};x.canYield=clamp(x.flexibility*.62+x.stalk*.20+(1-x.needLead)*.18,0,1)>=.55;x.leaderScore=clamp(x.goProb*.38+x.ten*.20+x.needLead*.17+x.breakSkill*.13+x.jockeyFront*.05+x.front*.05+(q.lineEndRelief||0)*.05-(q.conflict||0)*.04,0,1.3);x.secondScore=clamp(x.goProb*.34+x.stalk*.22+x.flexibility*.16+x.holdFront*.12+x.ability*.08+(q.lineEndRelief||0)*.05-(q.conflict||0)*.04,0,1.3);x.positionScore=clamp(x.goProb*.23+x.stalk*.24+x.mid*.13+x.flexibility*.13+x.ability*.12+x.turnSkill*.09+(1-x.frontCost)*.06,0,1.2)}var leadOrder=scored.filter(function(z){return z.minetaEarlyIntent||z.goProb>=.48}).sort(function(a,b){var ar=n(a.minetaLeadRank,99),br=n(b.minetaLeadRank,99);if(ar!==br)return ar-br;return b.leaderScore-a.leaderScore||n(a.horse.horseNumber)-n(b.horse.horseNumber)}),leadMax=leadOrder.length?leadOrder[0].leaderScore:0,leadCandidates=leadOrder.filter(function(z,idx){return idx<3&&((n(z.minetaLeadRank,0)>0)||(z.leaderScore>=leadMax-.085&&z.goProb>=.53))}),leadTop=leadCandidates[0]||leadOrder[0]||null,secondCandidates=scored.filter(function(z){return !leadTop||n(z.horse.horseNumber)!==n(leadTop.horse.horseNumber)}).filter(function(z){return z.goProb>=.42||z.stalk>=.28}).sort(function(a,b){return b.secondScore-a.secondScore}).slice(0,3),positionCandidates=scored.filter(function(z){return z.goProb>=.34||z.stalk>=.30||z.mid>=.34}).sort(function(a,b){return b.positionScore-a.positionScore}).slice(0,4),escapeSide=leadCandidates.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.escapeSide}),sandwich=leadCandidates.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.sandwich}),middleFront=front.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.lineMiddle}),highFade=front.filter(function(z){return z.fade>=.50}),hardLead=leadCandidates.filter(function(z){return z.needLead>=.58&&z.canYield===false});return{front:front,segments:segments,pattern:pattern,longest:longest,adjacentPairs:adjacentPairs,innerShare:innerShare,outerShare:outerShare,concentrationText:concentrationText,leadCandidates:leadCandidates,secondCandidates:secondCandidates,positionCandidates:positionCandidates,escapeSide:escapeSide,sandwich:sandwich,middleFront:middleFront,highFade:highFade,hardLeadCount:hardLead.length}}

function tacticalContext(r,rows){var pressure=pressureInfo(rows),arr=frontArrangement(rows,pressure),collapseWatch=arr.highFade.length>=2,i,x,q;for(i=0;i<rows.length;i++){x=rows[i];q=pressure[n(x.horse.horseNumber)]||{};x.frontLineRole=q.lineRole||'単独/飛び';x.collapseBeneficiary=collapseWatch&&x.goProb<.58?clamp(x.comeFromBehind*.42+x.latePower*.22+x.move*.15+x.trafficTol*.12+x.ability*.09,0,1):0}arr.collapseWatch=collapseWatch;arr.collapseRecheck=collapseWatch?rows.filter(function(z){return z.goProb<.58&&(z.mid+z.close)>=.45}).sort(function(a,b){return b.collapseBeneficiary-a.collapseBeneficiary||b.comeFromBehind-a.comeFromBehind}).slice(0,2):[];return{pressure:pressure,arrangement:arr}}

function scenarioModel(r,rows,pressure,arr){pressure=pressure||pressureInfo(rows);arr=arr||frontArrangement(rows,pressure);var front=rows.slice().sort(function(a,b){return b.goProb-a.goProb}),active=arr.front,top=active.slice().sort(function(a,b){return b.goProb-a.goProb}).slice(0,Math.min(5,active.length)),fade=top.length?mean(top.map(function(x){return x.fade})):0,hold=top.length?mean(top.map(function(x){return x.holdFront})):0,conf=top.length?mean(top.map(function(x){return (pressure[n(x.horse.horseNumber)]||{}).conflict||0})):0,sand=top.length?mean(top.map(function(x){return (pressure[n(x.horse.horseNumber)]||{}).sandwich||0})):0,flex=top.length?mean(top.map(function(x){return x.flexibility})):0,ct=rows.length?rows[0].course:courseTraits(r),cp=courseProfile(r),firstTurnRush=clamp(1-firstTurnDistance(r)/650,0,1),lead=arr.leadCandidates||[],leadGap=lead.length>1?Math.max(0,lead[0].leaderScore-lead[1].leaderScore):.20,clear=lead.length?clamp(leadGap*2.0+lead[0].holdFront*.10+(lead[0].lineEndRelief||0)*.08,0,.42):.12,cluster=clamp((arr.longest-1)/3,0,1),outerLoad=arr.outerShare*firstTurnRush*ct.turnLoad,frontVolume=clamp(active.length/Math.max(1,rows.length),0,1),stableLead=lead.length?clamp(lead[0].holdFront*.45+(1-lead[0].fade)*.30+lead[0].ten*.15+(lead[0].canYield?.10:0),0,1):0,hardMulti=Math.max(0,(arr.hardLeadCount||0)-1),spreadRelief=arr.pattern==='飛び飛び'?.08:(arr.pattern==='一部連続'?.035:0),A=.28+ct.frontBias*.24+clear*.20+hold*.12+(1-fade)*.075+(1-clamp(conf,0,1))*.05+flex*.03+stableLead*.045+spreadRelief*.035,C=.16+(1-ct.frontBias)*.09+ct.moveRoom*.09+fade*.17+clamp(conf,0,1)*.13+sand*.09+cluster*.06+outerLoad*.055+hardMulti*.055,B=.34+flex*.075+(1-Math.abs(A-C))*.035+spreadRelief*.03;if(arr.highFade.length>=2)C+=.045+Math.min(.055,(arr.highFade.length-2)*.018);if(frontVolume>.52)C+=cluster>.20?Math.min(.045,(frontVolume-.52)*.16):Math.min(.015,(frontVolume-.52)*.08);if(lead.length>1&&hardMulti===0)B+=.025;if(lead.length===1&&stableLead>.62)A+=.035;if(arr.pattern==='飛び飛び'&&flex>.52)C-=.025;A=clamp(A,.15,.68);B=clamp(B,.20,.52);C=clamp(C,.12,.60);var sum=A+B+C;A/=sum;B/=sum;C/=sum;return[{code:"A",title:"前残り",prob:A},{code:"B",title:"平均",prob:B},{code:"C",title:"前崩れ・差し届く",prob:C}]}

function startOrder(rows){var p=pressureInfo(rows);return rows.slice().sort(function(a,b){function s(x){var q=p[n(x.horse.horseNumber)]||{};return x.goProb+x.needLead*.12+(q.freeOuter||0)-q.conflict*.035}return s(b)-s(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)})}

function scenarioSuit(x,code,pressure){var q=pressure[n(x.horse.horseNumber)]||{},earlyCost=(q.conflict||0)*x.goProb*(.34+.42*x.needLead)*(1-.34*x.flexibility)+x.outerStress*.06+(q.lineMiddle||0)*x.goProb*.045-(q.lineEndRelief||0)*.025,frontStay=x.goProb*.27+x.holdFront*.31+(1-x.fade)*.12+x.ability*.18+x.stamina*.07+x.course.frontBias*.05-earlyCost*.16+(q.lineEndRelief||0)*.025,balanced=x.ability*.34+x.holdFront*.14+x.latePower*.13+x.move*.10+x.stamina*.10+x.goProb*.08+x.flexibility*.06+(1-x.fade)*.05+(q.lineEndRelief||0)*.015,close=x.ability*.26+x.latePower*.27+x.move*.17+x.mid*.08+x.close*.09+x.course.moveRoom*.07+x.trafficTol*.06+x.collapseBeneficiary*.10-x.goProb*.015;if(code==="A")return clamp(frontStay,0,1.25);if(code==="C")return clamp(close,0,1.25);return clamp(balanced,0,1.25)}

function suitability(rows,sc,pressure){var out={};pressure=pressure||pressureInfo(rows);var i,x,win,place,show,j,q,scenarioScores=[],frontFadePenalty,baseWin,basePlace,baseShow;for(i=0;i<rows.length;i++){x=rows[i];win=place=show=0;scenarioScores=[];frontFadePenalty=x.goProb>=.50?Math.max(0,x.fade-.38)*x.goProb:0;for(j=0;j<sc.length;j++){q=scenarioSuit(x,sc[j].code,pressure);scenarioScores.push({code:sc[j].code,score:q});baseWin=q*.72+x.ability*.20+x.hold*.08-frontFadePenalty*.18;basePlace=q*.57+x.ability*.20+(1-x.fade)*.13+x.flexibility*.06+x.hold*.04-frontFadePenalty*.065;baseShow=q*.46+x.ability*.20+(1-x.fade)*.14+x.move*.09+x.flexibility*.06+x.hold*.05-frontFadePenalty*.030;if(x.goProb>=.52&&x.fade<=.25){baseWin+=.025;basePlace+=.018;baseShow+=.012}if(sc[j].code==='C'&&x.collapseBeneficiary>.60){basePlace+=.035;baseShow+=.025}win+=sc[j].prob*baseWin;place+=sc[j].prob*basePlace;show+=sc[j].prob*baseShow}win=clamp(win,0,1.25);place=clamp(place,0,1.25);show=clamp(show,0,1.25);var overall=win*.54+place*.29+show*.17;out[n(x.horse.horseNumber)]={win:win,place:place,show:show,overall:overall,rankScore:win*.62+place*.24+show*.14,scenario:scenarioScores}}return out}

function cornerScores(r,rows,sc,suit){var pressure=pressureInfo(rows),top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0].code,out=[],i,x,z,q,s,earlyCost;for(i=0;i<rows.length;i++){x=rows[i];z=suit[n(x.horse.horseNumber)]||{overall:.5};q=pressure[n(x.horse.horseNumber)]||{};earlyCost=q.conflict*x.goProb*(.4+.4*x.needLead);s=x.goProb*.25+x.hold*.20+x.ability*.21+x.move*.11+(1-x.fade)*.11+z.overall*.12-earlyCost*.10;if(top==="A")s+=x.goProb*.11+x.hold*.07;if(top==="C")s+=x.move*.12+x.mid*.06+x.close*.08-x.goProb*.02;out.push({row:x,s:s})}return out.sort(function(a,b){return b.s-a.s}).map(function(z){return z.row})}

function seedHash(v){var s=String(v||"race"),h=2166136261,i;for(i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}

function prng(seed){var a=seed>>>0;return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}

function jitter(rng){return(rng()+rng()+rng()+rng()+rng()+rng()-3)/3}

function chooseScenario(sc,rng){var u=rng(),c=0,i;for(i=0;i<sc.length;i++){c+=sc[i].prob;if(u<=c)return sc[i].code}return sc.length?sc[sc.length-1].code:"B"}

function packStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,visualRankGap,scoreGap,lane,cp=courseProfile(r);for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);visualRankGap=(stage<2?.0048:(stage<5?.0065:.0085))*i;scoreGap=diff*(stage<2?.030:(stage<5?.043:.060));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&visualRankGap<.02)lane+=((i%3)-1);out.push({no:no,gap:clamp(visualRankGap+scoreGap,0,.42),lane:clamp(lane,-3,3)})}return out}

function stageMap(pack){var o={},i;for(i=0;i<pack.length;i++)o[pack[i].no]=pack[i];return o}

function stageByNo(pack,no){for(var i=0;i<pack.length;i++)if(n(pack[i].no)===n(no))return pack[i];return null}

function simulateOne(r,rows,sc,suit,seed){var rng=prng(seed),code=chooseScenario(sc,rng),pressure=pressureInfo(rows),cp=courseProfile(r),ct=courseTraits(r),dist=n(r.distance,1200),distanceLoad=clamp((dist-1000)/1800,0,1),firstTurnRush=clamp(1-firstTurnDistance(r)/650,0,1),paceHeat=0,i,x,no,q,noise;var S0={},S1={},S2={},S3={},S4={},S5={},S6={},S7={},L0={},L1={},L2={},L3={},L4={},L5={},L6={},L7={},energy={};
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);S0[no]=x.breakSkill*.50+x.goProb*.30+x.needLead*.08+x.jockeyFront*.05+(q.freeOuter||0)-q.conflict*.035+noise*.07;L0[no]=clamp(Math.round((x.draw-.5)*5),-3,3);energy[no]=1;if(x.goProb>.50)paceHeat+=x.goProb*(.45+.55*x.needLead)}
paceHeat=clamp((paceHeat-1.10)/Math.max(.8,rows.length*.18),0,1.55);
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var rushCost=(q.conflict||0)*(.08+.11*x.needLead)+paceHeat*x.goProb*.045+firstTurnRush*x.outer*.045;energy[no]-=rushCost;S1[no]=S0[no]*.56+x.goProb*.20+x.breakSkill*.10+x.flexibility*.05-x.collapse*.035-rushCost*.22+noise*.065;L1[no]=clamp(L0[no]+(x.edge&&x.goProb>.55?-1:0)+(q.sandwich&&x.flexibility<.45?1:0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var turnCost=Math.abs(L1[no])*.012*ct.turnLoad+x.outer*firstTurnRush*.025+(q.sandwich||0)*(.035-.020*x.trafficTol);energy[no]-=turnCost;S2[no]=S1[no]*.48+x.hold*.16+x.turnSkill*.12+x.ability*.12+x.flexibility*.06-turnCost*.32+noise*.06;L2[no]=clamp(L1[no]+(x.inner&&x.goProb<.35?0:Math.round((x.flexibility-.5)*-1)),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var draft=(x.stalk*.045+x.mid*.025)*(1-x.needLead),leaderDrain=paceHeat*x.goProb*(.045+.055*x.needLead)*(1+.45*distanceLoad);energy[no]-=leaderDrain;S3[no]=S2[no]*.43+x.ability*.18+x.hold*.13+x.stamina*.10+draft+x.move*.05+noise*.065;L3[no]=clamp(L2[no]+(x.move>.45&&x.goProb<.45?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var moveKick=x.move*(.08+.07*ct.moveRoom)+x.latePower*.055,wideCost=Math.max(0,Math.abs(L3[no])-1)*.018*ct.turnLoad;energy[no]-=wideCost;S4[no]=S3[no]*.42+x.ability*.17+x.stamina*.12+x.turnSkill*.09+moveKick-wideCost*.30+noise*.07;L4[no]=clamp(L3[no]+(x.move>.50?Math.round((rng()-.42)*2):0),-3,3)}
var pack4=packStage(r,rows,S4,L4,4),map4=stageMap(pack4);
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var pos4=map4[no]||{gap:.2,lane:0},blocked=0;if(pos4.gap>.025&&Math.abs(pos4.lane)<=1&&x.trafficTol<.55&&rng()>.48)blocked=(.02+.06*(1-x.trafficTol));var scFit=scenarioSuit(x,code,pressure),fatigue=(1-energy[no])*.16+x.collapse*.07+paceHeat*x.goProb*.035*distanceLoad;S5[no]=S4[no]*.37+scFit*.16+x.ability*.15+x.stamina*.11+x.turnSkill*.07+x.latePower*.07-blocked-fatigue+noise*.075;L5[no]=clamp(L4[no]+(blocked>0?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var straightBoost=x.latePower*(.10+.12*ct.straight)+x.move*.055*ct.moveRoom,frontKick=(code==="A"?x.goProb*.055+x.hold*.035:0),closeKick=(code==="C"?x.close*.07+x.move*.055:0),fatigue2=(1-energy[no])*.12+x.fade*.08;S6[no]=S5[no]*.34+x.ability*.20+x.stamina*.12+straightBoost+frontKick+closeKick-fatigue2+noise*.085;L6[no]=clamp(L5[no]+(x.latePower>.58&&Math.abs(L5[no])<3?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var suitx=suit[no]||{overall:.5},uncert=(1-x.coverage)*.070*jitter(rng);S7[no]=S6[no]*.34+suitx.overall*.24+x.ability*.18+x.latePower*.10+x.stamina*.08+(1-x.fade)*.05-q.conflict*.015+noise*.09+uncert;L7[no]=L6[no]}
var packs=[packStage(r,rows,S0,L0,0),packStage(r,rows,S1,L1,1),packStage(r,rows,S2,L2,2),packStage(r,rows,S3,L3,3),packStage(r,rows,S4,L4,4),packStage(r,rows,S5,L5,5),packStage(r,rows,S6,L6,6),packStage(r,rows,S7,L7,7)],maps=packs.map(stageMap),finish=packs[7];return{scenario:code,checkpoints:packs,maps:maps,start:packs[1],corner:packs[5],finish:finish,startMap:maps[1],cornerMap:maps[5],finishMap:maps[7],podium:finish.slice(0,3).map(function(z){return z.no}),paceHeat:paceHeat}}

function generateSimulations(r,rows,sc,suit,count){var runs=[],stats={},scenarioCount={A:0,B:0,C:0},combo={},i,j,no,run,key;for(i=0;i<rows.length;i++){no=n(rows[i].horse.horseNumber);stats[no]={horse:rows[i].horse,win:0,second:0,third:0,top3:0,startRank:0,cornerRank:0,finishRank:0}}var base=seedHash([r.id,r.date,r.track,r.raceNumber,r.distance,(r.horses||[]).length].join("|"));for(i=0;i<count;i++){run=simulateOne(r,rows,sc,suit,(base+Math.imul(i+1,2654435761))>>>0);runs.push(run);scenarioCount[run.scenario]=(scenarioCount[run.scenario]||0)+1;key=run.podium.join("-");combo[key]=(combo[key]||0)+1;for(j=0;j<run.start.length;j++)stats[run.start[j].no].startRank+=j+1;for(j=0;j<run.corner.length;j++)stats[run.corner[j].no].cornerRank+=j+1;for(j=0;j<run.finish.length;j++)stats[run.finish[j].no].finishRank+=j+1;if(run.podium[0]){stats[run.podium[0]].win++;stats[run.podium[0]].top3++}if(run.podium[1]){stats[run.podium[1]].second++;stats[run.podium[1]].top3++}if(run.podium[2]){stats[run.podium[2]].third++;stats[run.podium[2]].top3++}}var summary=Object.keys(stats).map(function(k){var z=stats[k];z.no=n(k);z.winRate=z.win/count;z.secondRate=z.second/count;z.thirdRate=z.third/count;z.top3Rate=z.top3/count;z.avgStart=z.startRank/count;z.avgCorner=z.cornerRank/count;z.avgFinish=z.finishRank/count;z.markScore=z.winRate*.53+z.secondRate*.24+z.thirdRate*.13+z.top3Rate*.10;return z}).sort(function(a,b){return b.markScore-a.markScore||a.avgFinish-b.avgFinish});var first=summary[0]||null,rest=summary.slice(1),second=rest.slice().sort(function(a,b){return b.secondRate-a.secondRate||b.top3Rate-a.top3Rate})[0]||summary[1]||null,thirdPool=summary.filter(function(z){return(!first||z.no!==first.no)&&(!second||z.no!==second.no)}),third=thirdPool.slice().sort(function(a,b){return b.thirdRate-a.thirdRate||b.top3Rate-a.top3Rate})[0]||summary[2]||null,podium=[first,second,third].filter(Boolean),exact=0,setHit=0,target=podium.map(function(z){return z.no}),targetKey=target.join("-");exact=combo[targetKey]||0;for(i=0;i<runs.length;i++){var a=runs[i].podium.slice().sort(function(a,b){return a-b}),b=target.slice().sort(function(a,b){return a-b});if(a.length===b.length&&a.join("-")===b.join("-"))setHit++}return{count:count,runs:runs,summary:summary,podium:podium,exactRate:exact/count,setRate:setHit/count,scenarioCount:scenarioCount}}

function avgOrder(rows,sim,key){var prop=key==="start"?"avgStart":(key==="corner"?"avgCorner":"avgFinish"),sm={};for(var i=0;i<sim.summary.length;i++)sm[sim.summary[i].no]=sim.summary[i][prop];return rows.slice().sort(function(a,b){return sm[n(a.horse.horseNumber)]-sm[n(b.horse.horseNumber)]})}

function packScenarioStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,rankGap,scoreGap,lane;for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);rankGap=(stage<=1?.010:(stage<=3?.013:.016))*i;scoreGap=diff*(stage<=1?.06:(stage<=3?.08:.10));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&i%3===0)lane+=1;if(i>0&&i%4===0)lane-=1;out.push({no:no,gap:clamp(rankGap+scoreGap,0,.34),lane:clamp(lane,-3,3),score:scoreMap[no]})}return out}

function rowsFromPack(rows,pack){var map={};for(var i=0;i<rows.length;i++)map[n(rows[i].horse.horseNumber)]=rows[i];return pack.map(function(z){return map[n(z.no)]}).filter(Boolean)}

function eventOrderPack(rows,order,laneMap,stage){
  var field=Math.max(1,order.length),out=[];
  for(var i=0;i<order.length;i++){
    var x=order[i],no=n(x.horse.horseNumber),lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4),
        pos=field<=1?1:1-i/(field-1),gap=clamp((stage<=1?.012:(stage<=3?.016:.020))*i,0,.34);
    out.push({no:no,gap:gap,lane:clamp(lane,-3,3),score:pos})
  }
  return out
}

function scenarioPlan(r,rows,sc,suit,pressure,arr){
  var scenario=sc.slice().sort(function(a,b){return b.prob-a.prob})[0]||{code:'B',title:'平均',prob:1},code=scenario.code;
  pressure=pressure||pressureInfo(rows);arr=arr||frontArrangement(rows,pressure);
  var p=pressure,lanes={},i,x,no,q,ct=courseTraits(r),
      firstRush=clamp(1-firstTurnDistance(r)/650,0,1),
      longDistance=clamp((n(r.distance,1400)-1400)/1200,0,1),
      frontRunners=(arr.front||[]).length,hardLeaders=Math.max(0,n(arr.hardLeadCount,0)-1),
      paceHeat=clamp(Math.max(0,frontRunners-1)*.060+hardLeaders*.095+
        (arr.middleFront||[]).length*.035+firstRush*Math.max(0,frontRunners-2)*.028,0,.65);
  function exposure(z){
    var qq=p[n(z.horse.horseNumber)]||{};
    return clamp(paceHeat*(.18+n(z.goProb,.5)*.28+n(z.needLead,.3)*.18+
      n(qq.conflict,0)*.22+n(z.frontCost,0)*.55)*(1+longDistance*.35),0,.52)
  }
  // Pre-race pace and ability only: neither odds nor results enter here.
  function finishStrength(z){
    var early=exposure(z),fade=n(z.fade,.25),late=n(z.latePower,.5);
    return n(z.ability,.5)*.27+n(z.stamina,.5)*.18+late*.21+
      n(z.comeFromBehind,.5)*.12+n(z.holdFront,.5)*.12+
      n(z.lateGain,.5)*.05+n(z.trafficTol,.5)*.05-
      early*.42-fade*(.055+early*.20)+
      (code==='A'?n(z.frontStay,.5)*.07:0)+
      (code==='C'?late*.05:0)
  }
  rows.forEach(function(z){lanes[n(z.horse.horseNumber)]=clamp(Math.round((z.draw-.5)*5),-3,3)});

  function lex(list,keys){
    return list.slice().sort(function(a,b){
      for(var k=0;k<keys.length;k++){
        var fn=keys[k],av=n(fn(a),0),bv=n(fn(b),0);
        if(bv!==av)return bv-av
      }
      return n(a.horse.horseNumber)-n(b.horse.horseNumber)
    })
  }
  function uniq(groups){
    var seen={},out=[];
    groups.forEach(function(g){(g||[]).forEach(function(z){var k=n(z.horse.horseNumber);if(!seen[k]){seen[k]=1;out.push(z)}})});
    rows.forEach(function(z){var k=n(z.horse.horseNumber);if(!seen[k]){seen[k]=1;out.push(z)}});
    return out
  }
  function idx(order,row){return order.indexOf(row)}
  function move(order,row,delta){
    var i=idx(order,row);if(i<0||!delta)return;
    var ni=clamp(i+delta,0,order.length-1);
    if(ni===i)return;
    order.splice(i,1);order.splice(ni,0,row)
  }
  function moveTo(order,row,target){
    var i=idx(order,row);if(i<0)return;
    target=clamp(target,0,order.length-1);
    if(i===target)return;
    order.splice(i,1);order.splice(target,0,row)
  }
  function topRank(order,row){var i=idx(order,row);return i<0?999:i+1}
  function isFront(z){return z.goProb>=.50||z.expected==='逃げ候補'||z.expected==='先行'}
  function isStalk(z){return z.expected==='好位'||z.stalk>=.30}
  function isCloser(z){return z.expected==='後方'||z.close>=.38||z.comeFromBehind>=.58}

  // START: distinguish "who contests the lead" from "where they settle after losing it".
  // A horse strong enough to be named in the lead battle cannot jump straight to midfield
  // unless a concrete retreat / pressure event occurs.
  var leaderPool=(arr.leadCandidates||[]).length?(arr.leadCandidates||[]):rows.filter(function(z){return z.goProb>=.50});
  // Real first-corner lead and break/ten evidence decide the front battle.
  leaderPool=leaderPool.slice().sort(function(a,b){
    function score(z){
      var past=z.minetaPast||{},sample=clamp(n(z.styleSamples,0)/3,0,1);
      return n(z.goProb,.5)*.25+n(z.breakSkill,.5)*.21+n(z.ten,.5)*.18+
        n(z.needLead,.5)*.12+n(z.jockeyFront,0)*.04+
        (n(past.leadRate)*.12+n(past.earlyRate)*.045+(past.prevLeader?.04:0))*sample+
        n(z.holdFront,.5)*.06+n(z.minetaLeadRank,0)*-.002
    }
    return score(b)-score(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  var leader=leaderPool[0]||lex(rows,[function(z){return z.goProb},function(z){return z.breakSkill}])[0]||null,
      leadBattlers=leaderPool.filter(function(z){return z!==leader}),
      front=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&isFront(z)}),[function(z){return z.goProb},function(z){return z.ten},function(z){return z.needLead}]),
      stalk=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&!isFront(z)&&isStalk(z)}),[function(z){return z.stalk},function(z){return z.posCons},function(z){return z.breakSkill}]),
      middle=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&!isFront(z)&&!isStalk(z)&&!isCloser(z)}),[function(z){return z.mid},function(z){return z.posCons}]),
      rear=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&!isFront(z)&&!isStalk(z)&&isCloser(z)}),[function(z){return z.close},function(z){return z.latePower}]),
      orders=[];
  // At the instant of the break, all genuine lead battlers stay in the front cluster.
  orders[0]=uniq([[leader],leadBattlers,front,stalk,middle,rear]);

  // FIRST TURN: predict the settling order after the lead battle.
  // This is where a horse such as 7 can go from "challenged for the lead" to 2nd/3rd,
  // rather than incorrectly being thrown into midfield.
  orders[1]=orders[0].slice();
  if(leader){
    var settlePool=uniq([leadBattlers,(arr.secondCandidates||[]),front,stalk]).filter(function(z){return z&&z!==leader}).slice(0,Math.min(6,rows.length-1));
    function settleScore(z){
      var qq=p[n(z.horse.horseNumber)]||{},wasLead=leadBattlers.indexOf(z)>=0?1:0,
          yieldPenalty=wasLead*n(z.needLead)*(1-n(z.canYield,.5))*.16;
      return n(z.secondScore,.5)*.38+n(z.stalk,.3)*.15+n(z.flexibility,.5)*.12+n(z.breakSkill,.5)*.09+
        n(z.ten,.5)*.08+n(z.ability,.5)*.08+n(z.posCons,.5)*.06+wasLead*.08+
        (z.minetaEscapeOutside?.035:0)-(n(z.outerStress)*.06+n(qq.conflict)*.06+yieldPenalty)
    }
    settlePool.sort(function(a,b){return settleScore(b)-settleScore(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
    var settleTop=settlePool.slice(0,Math.min(4,settlePool.length)),
        rest=orders[1].filter(function(z){return z!==leader&&settleTop.indexOf(z)<0});
    orders[1]=[leader].concat(settleTop,rest)
  }
  orders[1].slice(0,Math.min(6,orders[1].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    var explicitRetreat=(z.fade>=.58&&z.frontCost>=.14)||(z.outerStress>=.68&&z.goProb>=.46)||
      (q.lineMiddle&&z.needLead>=.66&&z.flexibility<.40)||(q.sandwich&&z.flexibility<.38);
    if(explicitRetreat)move(orders[1],z,1);
    if(z.minetaEscapeOutside&&z.expected!=='逃げ候補'&&q.conflict<.55)move(orders[1],z,-1);
    if(z.minetaDifferentStyleNeighbor&&q.conflict<.55)move(orders[1],z,-1)
  });
  if(leader&&topRank(orders[1],leader)>1)moveTo(orders[1],leader,0);

  // BACKSTRETCH: mostly preserve established positions. Only obvious over-racing /
  // early-pressure horses concede a place; flexible stalkers can tuck in.
  orders[2]=orders[1].slice();
  orders[2].slice(0,Math.min(6,orders[2].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    if(z.fade>=.58&&z.frontCost>=.14&&z.needLead>=.50)move(orders[2],z,1);
    else if(z.canYield&&z.needLead>=.45&&topRank(orders[2],z)<=3&&q.conflict>=.55)move(orders[2],z,1)
  });

  // 3C: movers begin advancing. They gain only a small number of positions per
  // phase; this is a transition, not a wholesale re-ranking.
  orders[3]=orders[2].slice();
  var movers3=lex(rows.filter(function(z){return z.move>=.55&&z.latePower>=.50&&topRank(orders[3],z)>3}),[
    function(z){return z.move*.40+n(z.turnSkill,.5)*.22+z.latePower*.23+n(z.ability,.5)*.15},
    function(z){return z.comeFromBehind}
  ]);
  movers3.slice(0,code==='C'?3:2).forEach(function(z){
    var gain=(code==='C'&&paceHeat>=.22&&n(z.turnSkill,.5)>=.56)?2:1;
    move(orders[3],z,-gain)
  });
  orders[3].slice(0,Math.min(5,orders[3].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    if(z.fade>=.62&&z.frontCost>=.15&&(q.sandwich||q.conflict>=.60))move(orders[3],z,1)
  });

  // 4C: commit moves, but maintain continuity. A closer cannot teleport from last
  // to first in one step, and a leader does not collapse without fatigue evidence.
  orders[4]=orders[3].slice();
  var movers4=lex(rows.filter(function(z){return z.move>=.58&&z.latePower>=.56&&topRank(orders[4],z)>2}),[
    function(z){return z.move*.38+z.latePower*.30+n(z.turnSkill,.5)*.17+n(z.ability,.5)*.15},
    function(z){return z.comeFromBehind}
  ]);
  movers4.slice(0,code==='C'?3:2).forEach(function(z){
    var gain=(code==='C'&&paceHeat>=.20&&ct.moveRoom>=.45)?2:1;
    move(orders[4],z,-gain)
  });
  orders[4].slice(0,Math.min(5,orders[4].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    var severe=z.fade>=.68&&z.frontCost>=.18&&(q.sandwich||q.conflict>=.65);
    if(severe)move(orders[4],z,1)
  });

  // STRAIGHT: resolve hold / fade / pass events. Position changes require a reason.
  orders[5]=orders[4].slice();
  var frontAt4=orders[4].slice(0,Math.min(4,orders[4].length));
  frontAt4.forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    var stress=exposure(z),
        severeFade=z.fade>=.67&&(stress>=.19||z.frontCost>=.18||q.conflict>=.70||q.sandwich),
        moderateFade=z.fade>=.56&&(stress>=.13||z.frontCost>=.12||q.conflict>=.52),
        strongHold=z.frontStay>=.66&&z.holdFront>=.56&&z.fade<.52&&stress<.24;
    if(severeFade)move(orders[5],z,code==='C'?3:2);
    else if(moderateFade)move(orders[5],z,1);
    else if(strongHold&&topRank(orders[5],z)>topRank(orders[4],z))moveTo(orders[5],z,topRank(orders[4],z)-1)
  });

  var closers=lex(rows.filter(function(z){return isCloser(z)&&z.latePower>=.56&&z.comeFromBehind>=.56}),[
    function(z){return z.comeFromBehind},function(z){return z.latePower},function(z){return z.move}
  ]);
  // Runners have finite overtaking capacity: each pass needs superiority to
  // the horse directly ahead. No fixed -5 rank leap or magic lead restoration.
  var straightRoom=clamp(ct.straight*.68+ct.moveRoom*.32,0,1);
  closers.slice(0,code==='C'?3:2).sort(function(a,b){return finishStrength(b)-finishStrength(a)}).forEach(function(z){
    var cap=1+(straightRoom>=.58?1:0)+(n(z.latePower,0)>=.69&&straightRoom>=.55?1:0);
    if(code==='A')cap=Math.max(1,cap-1);
    if(code==='C'&&paceHeat>=.26&&straightRoom>=.58)cap+=1;
    for(var pass=0;pass<cap;pass++){
      var at=orders[5].indexOf(z);if(at<=0)break;
      var rival=orders[5][at-1];
      var gap=topRank(orders[4],z)-topRank(orders[4],rival);
      var required=.018+Math.max(0,gap-2)*.010+(code==='A'?.020:0);
      if(finishStrength(z)<finishStrength(rival)+required)break;
      move(orders[5],z,-1)
    }
  });
  if(leader){
    q=p[n(leader.horse.horseNumber)]||{};
    var leaderCollapse=leader.fade>=.66&&(exposure(leader)>=.19||leader.frontCost>=.18||q.conflict>=.68||q.sandwich),
        leaderHold=leader.frontStay>=.64&&leader.holdFront>=.54&&leader.fade<.55&&exposure(leader)<.24,
        challenger=orders[5].slice(0,Math.max(1,topRank(orders[5],leader)-1)).some(function(z){
          return finishStrength(z)>finishStrength(leader)+.025
        });
    if(leaderHold&&!leaderCollapse&&!challenger){
      var cap=(code==='C'&&leader.frontStay<.72)?2:1;
      if(topRank(orders[5],leader)>cap)moveTo(orders[5],leader,cap-1)
    }
  }

  // Build display stages from actual state order. score is only a normalized
  // screen-position rank for downstream compatibility; it is NOT the pace model.
  var labels=['スタート','1コーナー','向正面','3コーナー','4コーナー','直線'],
      keys=['start','first','back','turn3','turn4','straight'],packs=[],stages=[],markScore={};
  for(i=0;i<6;i++){
    packs[i]=eventOrderPack(rows,orders[i],lanes,i);
    stages.push({key:keys[i],label:labels[i],pack:packs[i],model:'event-transition-v2'})
  }
  orders[5].forEach(function(z,idx){markScore[n(z.horse.horseNumber)]=orders[5].length<=1?1:1-idx/(orders[5].length-1)});
  return{scenario:scenario,stages:stages,start:orders[0],corner:orders[4],straight:orders[5],markScore:markScore,model:'event-transition-v2'}
}
return Object.freeze({pressureInfo:pressureInfo,frontArrangement:frontArrangement,tacticalContext:tacticalContext,scenarioModel:scenarioModel,startOrder:startOrder,scenarioSuit:scenarioSuit,suitability:suitability,cornerScores:cornerScores,seedHash:seedHash,prng:prng,jitter:jitter,chooseScenario:chooseScenario,packStage:packStage,stageMap:stageMap,stageByNo:stageByNo,simulateOne:simulateOne,generateSimulations:generateSimulations,avgOrder:avgOrder,packScenarioStage:packScenarioStage,rowsFromPack:rowsFromPack,eventOrderPack:eventOrderPack,scenarioPlan:scenarioPlan});
}
global.ARVEXQPaceSimulation=Object.freeze({create:create});
})(window);
