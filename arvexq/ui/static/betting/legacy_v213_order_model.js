/* The original independent sequential race-order role model. */
(function(global){
'use strict';
function build(r,p,rows,featured,deps){
 const {n,clamp,strictSelectedRaceProfile,thirdRescueCandidateV312,appendRescueRankedV312,betComboText,captureExactaBetEvidence}=deps;
  function no(x){return x&&x.horse?n(x.horse.horseNumber):0}
  function ev(x){return x&&x.horse&&x.horse.integratedEvaluation||{}}
  function util(x,k){var e=ev(x);if(k===1&&e.v218P1Utility!=null)return Number(e.v218P1Utility);if(k===1&&e.v217P1Utility!=null)return Number(e.v217P1Utility);if(k===1&&e.v215P1Utility!=null)return Number(e.v215P1Utility);return Number(e['v213P'+k+'Utility'])}
  function entropy(ps){var z=0,den=Math.log(Math.max(2,ps.length));ps.forEach(function(q){q=Math.max(1e-12,n(q));z-=q*Math.log(q)});return den>0?z/den:1}
  function key2(a,b){a=n(a);b=n(b);return a<b?a+'-'+b:b+'-'+a}
  function pushMap(map,key,score,combo){if(!map[key])map[key]={combo:combo,score:0};map[key].score+=score}
  function rankMap(map){return Object.keys(map).map(function(k){return map[k]}).sort(function(a,b){return b.score-a.score})}
  function topCombos(list,max){var out=[],i;for(i=0;i<list.length&&out.length<max;i++)if(list[i]&&list[i].combo&&list[i].combo.every(function(v){return n(v)>0}))out.push(list[i].combo.slice());return out}
  function compactCombos(list,max,minRatio,minCount){var out=[],top=list&&list[0]?n(list[0].score):0,i;minCount=minCount||1;for(i=0;i<(list||[]).length&&out.length<max;i++){var z=list[i];if(!z||!z.combo||!z.combo.every(function(v){return n(v)>0}))continue;if(out.length>=minCount&&top>0&&n(z.score)<top*minRatio)break;out.push(z.combo.slice())}return out}
  function normWeights(ws){var sum=ws.reduce(function(a,b){return a+Math.max(0,n(b))},0)||1;return ws.map(function(v){return Math.max(0,n(v))/sum})}
  function audit(x){var e=ev(x);return e.v218Audit||e.v217Audit||x.v218Audit||x.v217Audit||{}}
  function roleFit(x,k){var e=ev(x),a=audit(x),legacy;if(k===2&&e.v218P2RoleFit!=null)legacy=clamp(n(e.v218P2RoleFit),0,1);else if(k===3&&e.v218P3RoleFit!=null)legacy=clamp(n(e.v218P3RoleFit),0,1);else legacy=clamp(n(k===2?a.secondRole:a.thirdRole,.5),0,1);var live=clamp(n(k===2?x.p2Strength:x.p3Strength,.5),0,1);return clamp(legacy*.58+live*.42,0,1)}
  function scenarioMix(x,role){
    var scenarios=(p.scenarios||[]),sum=0,den=0;
    if(!scenarios.length)return 1;
    scenarios.forEach(function(sc){var pr=Math.max(0,n(sc.prob)),title=String(sc.title||sc.code||''),fit=.5;
      if(/前|残|逃|スロー/.test(title))fit=role===1?clamp(n(x.frontStay,.5),0,1):(role===2?clamp(.55*n(x.posCons,.5)+.45*n(x.frontStay,.5),0,1):clamp(.55*n(x.posCons,.5)+.45*n(x.latePower,.5),0,1));
      else if(/差|崩|ハイ|消耗/.test(title))fit=role===1?clamp(n(x.comeFromBehind,.5),0,1):(role===2?clamp(.48*n(x.comeFromBehind,.5)+.52*n(x.posCons,.5),0,1):clamp(.62*n(x.latePower,.5)+.38*n(x.comeFromBehind,.5),0,1));
      else fit=role===1?clamp(n(x.paceScore,50)/100,0,1):(role===2?clamp(n(x.posCons,.5),0,1):clamp(.55*n(x.latePower,.5)+.45*n(x.posCons,.5),0,1));
      sum+=pr*fit;den+=pr
    });
    return .78+.44*(den?sum/den:.5)
  }
  function pairFactor(first,second){
    var a=audit(first),b=audit(second),f=scenarioMix(second,2)*(.84+.32*roleFit(second,2));
    var firstFront=clamp(n(first.frontStay,.5),0,1),secondFront=clamp(n(second.frontStay,.5),0,1);
    // Two highly aggressive runners are less likely to occupy 1-2 together when the winner already paid the early cost.
    if(firstFront>=.62&&secondFront>=.62)f*=.88;
    if(n(first.frontCost)>=.16&&n(second.goProb)>=.58)f*=.91;
    if(a.positionPressure&&a.positionPressure.sandwich&&secondFront>=.60)f*=.94;
    f*=.92+.16*clamp(n(second.posCons,.5),0,1);
    f*=.94+.12*clamp(n(b.trueRun,.5),0,1);
    return clamp(f,.62,1.48)
  }
  function thirdFactor(first,second,third){
    var c=audit(third),f=scenarioMix(third,3)*(.84+.32*roleFit(third,3));
    var firstFront=clamp(n(first.frontStay,.5),0,1),secondFront=clamp(n(second.frontStay,.5),0,1),thirdFront=clamp(n(third.frontStay,.5),0,1);
    // If the first two are both forward, leave more room for a late/position-gain horse in third.
    if(firstFront>=.56&&secondFront>=.56)f*=.88+.26*clamp(n(third.latePower,.5),0,1);
    // Avoid blindly stacking three identical front profiles in a pressured race.
    if(firstFront>=.62&&secondFront>=.62&&thirdFront>=.62)f*=.78;
    f*=.91+.17*clamp(n(third.latePower,.5),0,1);
    f*=.93+.14*clamp(n(c.trueRun,.5),0,1);
    return clamp(f,.58,1.55)
  }
  var p1=normWeights(rows.map(function(x){return Math.max(.0001,.84*n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,.0001)))+.16*n(x.paceOutcomeFirst,.5))})),
      p2=normWeights(rows.map(function(x){return Math.max(.0001,.82*n(x.p2Probability)+.18*n(x.paceOutcomeSecond,.5))})),
      p3=normWeights(rows.map(function(x){return Math.max(.0001,.82*n(x.p3Probability)+.18*n(x.paceOutcomeThird,.5))})),tri=[],i,j,k;
  // Sequential conditional-order model:
  // P(1st=i) * P(2nd=j | i) * P(3rd=k | i,j).
  for(i=0;i<rows.length;i++){
    var w2=rows.map(function(x,idx){return idx===i?0:p2[idx]*pairFactor(rows[i],x)}),c2=normWeights(w2);
    for(j=0;j<rows.length;j++)if(i!==j){
      var w3=rows.map(function(x,idx){return (idx===i||idx===j)?0:p3[idx]*thirdFactor(rows[i],rows[j],x)}),c3=normWeights(w3);
      for(k=0;k<rows.length;k++)if(k!==i&&k!==j){var q=p1[i]*c2[j]*c3[k];if(q>0)tri.push({combo:[no(rows[i]),no(rows[j]),no(rows[k])],score:q})}
    }
  }
  tri.sort(function(a,b){return b.score-a.score});
  var exactMap={},quinMap={},trioMap={},wideMap={};
  tri.forEach(function(z){var a=z.combo[0],b=z.combo[1],c=z.combo[2],tk=[a,b,c].slice().sort(function(x,y){return x-y}).join('-');pushMap(exactMap,a+'>'+b,z.score,[a,b]);pushMap(quinMap,key2(a,b),z.score,[a,b].sort(function(x,y){return x-y}));pushMap(trioMap,tk,z.score,[a,b,c].sort(function(x,y){return x-y}));pushMap(wideMap,key2(a,b),z.score,[a,b].sort(function(x,y){return x-y}));pushMap(wideMap,key2(a,c),z.score,[a,c].sort(function(x,y){return x-y}));pushMap(wideMap,key2(b,c),z.score,[b,c].sort(function(x,y){return x-y}))});
  var exactaRank=rankMap(exactMap),wideRank=rankMap(wideMap),quinRank=rankMap(quinMap),trioRank=rankMap(trioMap),p1Rows=rows.map(function(x,i){return{x:x,p:p1[i]}}).sort(function(a,b){return b.p-a.p}),p2Rows=rows.map(function(x,i){return{x:x,p:p2[i]}}).sort(function(a,b){return b.p-a.p}),p3Rows=rows.map(function(x,i){return{x:x,p:p3[i]}}).sort(function(a,b){return b.p-a.p}),p1vals=p1.slice().sort(function(a,b){return b-a}),p1Top=p1vals[0]||0,p1Second=p1vals[1]||0,p1Margin=p1Top-p1Second,top2mass=p1Top+p1Second,top3mass=top2mass+(p1vals[2]||0),ent=entropy(p1),sel=strictSelectedRaceProfile(r,p),autoSelected=!!(sel&&sel.selected),normalGate=top3mass>=.60&&ent<=.94,canIssue=featured||normalGate,strong=autoSelected,items=[];
  // All ticket types below are marginals of the SAME sequential joint distribution.
  // 馬単=P(1,2), 馬連=sum both 1-2 orders, ワイド=sum all top-3 placements,
  // 3連複=sum all 6 orders, 3連単=one exact ordered path.
  if(canIssue){
    var ec=compactCombos(exactaRank,strong?2:1,strong?.68:.78,1);if(ec.length)items.push({level:strong?'本線':'通常',kind:'馬単',combos:ec,confidence:strong?'高':'中'});
    var qc=compactCombos(quinRank,2,strong?.70:.78,1);if(qc.length)items.push({level:strong?'本線':'通常',kind:'馬連',combos:qc,confidence:strong?'高':'中'});
    var wc=compactCombos(wideRank,2,strong?.74:.82,1);if(wc.length)items.push({level:strong?'本線':'通常',kind:'ワイド',combos:wc,confidence:strong?'高':'中'});
    var tc=compactCombos(trioRank,strong?3:2,strong?.60:.72,strong?2:1),rescue3=thirdRescueCandidateV312(r,rows,[]);if(rescue3)appendRescueRankedV312(tc,trioRank,no(rescue3),1,strong?.34:.40,false);if(tc.length)items.push({level:strong?'押さえ':'通常',kind:'3連複',combos:tc,confidence:strong?'高':'中'});
  }
  var triVals=tri.map(function(z){return z.score}),triTop=tri[0]?tri[0].score:0,triSecond=tri[1]?tri[1].score:1e-9,triRatio=triTop/Math.max(1e-9,triSecond),triTop6=tri.slice(0,6).reduce(function(a,z){return a+n(z.score)},0),orderEntropy=entropy(triVals),orderConfidence=clamp((1-orderEntropy)*.45+Math.min(1,triTop6/.16)*.35+Math.min(1,triRatio/1.35)*.20,0,1),triGate=strong&&triTop>=.022&&triRatio>=1.10&&triTop6>=.095&&orderConfidence>=.39;
  if(triGate){var triMax=orderConfidence>=.55?4:6,triCut=orderConfidence>=.55?.56:.46,t3=compactCombos(tri,triMax,triCut,2);if(rescue3)appendRescueRankedV312(t3,tri,no(rescue3),orderConfidence>=.55?1:2,.27,true);if(t3.length)items.push({level:'3連単チャレンジ',kind:'3連単',combos:t3,confidence:orderConfidence>=.55?'高':'中'})}
  items.forEach(function(z){z.points=(z.combos||[]).length;z.combo=betComboText(z.kind,z.combos)});items=items.filter(function(z){return z.points>0});
  var decision=strong?'強く買う':(canIssue?'通常買い':'見送り'),quality=canIssue?Math.round(clamp(45+top3mass*42+(1-ent)*18+(strong?10:0),50,96)):0,reason=strong?'厳選ゲート通過。v220は共通の条件付き着順分布から5券種を生成し、上位確率が離れた地点で買い目を自動打ち切りします。3連単は順序信頼ゲート通過時のみ最大6点です。':(featured?'メイン・重賞・高知ファイナル等の対象レースなので、役割順位から本線を出します。':(canIssue?'通常ゲート通過。役割順位の集中度から買い目を作成。':'通常ゲート未通過。'));
  return{raceId:String(r.id||''),engineVersion:'arvexq-bets-2026.10-v317-consensus-rebuild',decision:decision,featuredRace:featured,betQuality:quality,scenario:((p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)})[0]||{title:'平均',prob:0}).title,scenarioProb:n(((p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)})[0]||{}).prob),trifectaReviewed:true,trifectaDecision:triGate?'採用':'見送り',trifectaReason:triGate?'v220条件付き順序ゲート通過・点数圧縮。':'1着→2着→3着の条件付き順序集中度が基準未満。',winnerModel:(String((r&&r.circuit)||'')==='中央'?'central-v317-consensus-rebuild':'local-v317-consensus-rebuild')+'+walkforward+precision-order',p2Model:'v245-v213+seven-axis-live-role+conditional',p3Model:'v245-v213+sectional-live-role+conditional',selectionAudit:sel,exactaEvidence:captureExactaBetEvidence(exactaRank,rows),roles:{p1:p1Rows.slice(0,4).map(function(z){return{no:no(z.x),p:z.p}}),p2:p2Rows.slice(0,5).map(function(z){return{no:no(z.x),p:z.p}}),p3:p3Rows.slice(0,6).map(function(z){return{no:no(z.x),p:z.p}})},audit:{field:rows.length,coverage:n(p.coverage),p1Top:p1Top,p1Margin:p1Margin,top2mass:top2mass,top3mass:top3mass,entropy:ent,exactaTop:exactaRank[0]?exactaRank[0].score:0,exactaRatio:(exactaRank[0]?n(exactaRank[0].score):0)/Math.max(1e-9,exactaRank[1]?n(exactaRank[1].score):1e-9),quinTop:quinRank[0]?quinRank[0].score:0,quinRatio:(quinRank[0]?n(quinRank[0].score):0)/Math.max(1e-9,quinRank[1]?n(quinRank[1].score):1e-9),wideTop:wideRank[0]?wideRank[0].score:0,wideRatio:(wideRank[0]?n(wideRank[0].score):0)/Math.max(1e-9,wideRank[1]?n(wideRank[1].score):1e-9),trioTop:trioRank[0]?trioRank[0].score:0,trioRatio:(trioRank[0]?n(trioRank[0].score):0)/Math.max(1e-9,trioRank[1]?n(trioRank[1].score):1e-9),triTop:triTop,triRatio:triRatio,triTop6:triTop6,orderEntropy:orderEntropy,orderConfidence:orderConfidence,selected:autoSelected,normalGate:normalGate,ticketDistribution:'sequential-joint-v300-winner-consensus'},items:items,reason:reason}
}


function arvexqRaceType(base,p){
  var a=base&&base.audit||{},field=Math.max(4,n(a.field,(p&&p.rows||[]).length)),
      p1=n(a.p1Top),margin=n(a.p1Margin),top2=n(a.top2mass),top3=n(a.top3mass),ent=clamp(n(a.entropy,.94),0,1),order=clamp(n(a.orderConfidence),0,1),code='standard',label='標準';
  if(p1>=Math.max(.28,1/field*2.45)&&margin>=Math.max(.045,1/field*.35)){code='dominant';label='1強'}
  else if(top2>=.54&&margin<=Math.max(.075,1/field*.55)){code='two-strong';label='2強'}
  else if(top3>=.68&&ent<=.90){code='clustered';label='上位集中'}
  else if(ent>=.945||top3<.50){code='chaos';label='混戦'}
  return{code:code,label:label,orderReadable:order>=.50,orderScore:Math.round(order*100),p1Top:p1,margin:margin,top2:top2,top3:top3,entropy:ent}
}

// v243: bet construction is a separate decision engine with an explicit axis-safety gate.
// The joint-order model may generate several ticket marginals internally, but the
// customer-facing plan uses one primary ticket type and, only in unusually strong
// cases, one complementary secondary type. This avoids buying the same opinion five ways.
global.ARVEXQLegacyOrderModel=Object.freeze({build:build});
})(window);
