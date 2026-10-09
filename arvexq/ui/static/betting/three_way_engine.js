/* Independent three-way ticket generation, no DOM or storage. */
(function(global){
'use strict';
function composeThreeWayBetPolicy(base,r,p,deps){
 const {n,clamp,isScratchHorse,betComboText}=deps;
  if(!base)return base;
  var rows=((p&&p.rows)||[]).filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)&&n(x.horse.horseNumber)>0});
  var result=Object.assign({},base),audit=base.audit||{},g=base.betInputGate||{},
      selected=!!(base.selectionAudit&&base.selectionAudit.selected),
      ready=g.ready===true&&selected,hasHonmei=rows.some(z=>z.predMark==='◎'),
      stamp='arvexq-three-way-v346',
      reason=ready?'':'厳選品質または発走前データの購入条件未達';
  result.engineVersion=stamp;
  result.trifectaReviewed=true;
  result.trifectaDecision='見送り';
  result.trifectaReason='';
  result.insuranceDecision='見送り';
  result.insuranceReason='';
  result.expectedValue=null;
  result.expectedValueReason='券種別の実配当オッズと検証済み着順確率が揃わないため、期待値・回収率は算出しません。';
  result.roleMeaning={first:'独立1着予測と展開AI',second:'1着馬を除く条件付き2着予測',third:'1・2着馬を除く条件付き3着予測'};
  result.items=[];
  result.noAxis=!hasHonmei;
  if(rows.length<4){result.decision='見送り';result.trifectaReason='出走頭数・着順根拠が不足';result.insuranceReason='3連単不採用';return result}
  function num(x){return n(x&&x.horse&&x.horse.horseNumber,0)}
  function norm(values){var sum=values.reduce(function(a,b){return a+Math.max(0,n(b))},0);return values.map(function(v){return sum>0?Math.max(0,n(v))/sum:1/values.length})}
  function score(x,k){
    var e=x.horse.integratedEvaluation||{},z=k===1?n(x.ticketP1Probability,n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,0)))):k===2?n(x.ticketP2Probability,n(x.p2Probability,n(e.p2Score,0))):n(x.ticketP3Probability,n(x.p3Probability,n(e.p3Score,0)));
    return Math.max(.00001,z);
  }
  var p1=norm(rows.map(function(x){return score(x,1)})),
      p2=norm(rows.map(function(x){return score(x,2)})),
      p3=norm(rows.map(function(x){return score(x,3)})),
      outcome=p&&p.outcome||{},paceKeys={first:{},second:{},third:{}};
  ['first','second','third'].forEach(function(key){
    (outcome[key]||[]).forEach(function(x){var no=num(x);if(no)paceKeys[key][no]=true});
  });
  function paceFactor(x,role){
    var key=role===1?'first':role===2?'second':'third';
    return Object.keys(paceKeys[key]).length?(paceKeys[key][num(x)]?1.11:.97):1;
  }
  // A joint ordering model: each subsequent rank is conditioned on earlier picks.
  // Existing stage scores and pace-outcome lanes are consumed, but marks never
  // determine first/second/third mechanically.
  var ordered=[],i,j,k;
  for(i=0;i<rows.length;i++){
    var a=norm(rows.map(function(z,idx){return idx===i?0:p2[idx]*paceFactor(z,2)}));
    for(j=0;j<rows.length;j++)if(j!==i){
      var b=norm(rows.map(function(z,idx){return idx===i||idx===j?0:p3[idx]*paceFactor(z,3)}));
      for(k=0;k<rows.length;k++)if(k!==i&&k!==j){
        ordered.push({combo:[num(rows[i]),num(rows[j]),num(rows[k])],
          weight:p1[i]*paceFactor(rows[i],1)*a[j]*b[k]});
      }
    }
  }
  var sum=ordered.reduce(function(a,b){return a+b.weight},0)||1;
  ordered.forEach(function(z){z.weight/=sum});
  ordered.sort(function(a,b){return b.weight-a.weight});
  function merge(kind,combo,weight,map){
    var key=combo.join('-');
    if(!map[key])map[key]={combo:combo.slice(),weight:0};
    map[key].weight+=weight;
  }
  var wide={},quin={},exact={},trio={};
  ordered.forEach(function(z){
    var a=z.combo[0],b=z.combo[1],c=z.combo[2],pair=[a,b].sort(function(x,y){return x-y});
    merge('馬単',[a,b],z.weight,exact);
    merge('馬連',pair,z.weight,quin);
    merge('3連複',[a,b,c].sort(function(x,y){return x-y}),z.weight,trio);
    merge('ワイド',pair,z.weight,wide);
    merge('ワイド',[a,c].sort(function(x,y){return x-y}),z.weight,wide);
    merge('ワイド',[b,c].sort(function(x,y){return x-y}),z.weight,wide);
  });
  function ranked(obj){return Object.keys(obj).map(function(k){return obj[k]}).sort(function(a,b){return b.weight-a.weight})}
  var lists={'ワイド':ranked(wide),'馬連':ranked(quin),'馬単':ranked(exact),'3連複':ranked(trio)};
  var winners=rows.map(function(x,i){return{no:num(x),weight:p1[i]}}).sort(function(a,b){return b.weight-a.weight});
  var top=winners[0]||{no:0,weight:0},runner=winners[1]||{no:0,weight:0},
      clarity=top.weight-runner.weight,winClear=top.weight>=.22&&clarity>=.035,
      order=clamp(n(audit.orderConfidence),0,1),
      top12=ordered.slice(0,12).reduce(function(a,b){return a+b.weight},0),
      top24=ordered.slice(0,24).reduce(function(a,b){return a+b.weight},0);
  result.threeWayAudit={winner:top.no,runnerUp:runner.no,winnerMargin:clarity,
    orderConcentration:order,top12ModelMass:top12,top24ModelMass:top24,
    source:'non-calibrated-relative-order-model'};
  function add(level,kind,combos,why){
    if(!combos.length)return;
    var item={level:level,kind:kind,combos:combos.map(function(z){return z.slice()}),
      points:combos.length,confidence:'モデル比較',reason:why};
    item.combo=betComboText(kind,item.combos);
    result.items.push(item);
  }
  // Each purchase decision is independently owned; this file only prepares
  // the shared joint-order distribution and invokes isolated policies.
  if(!global.ARVEXQBetStrategies||
      !['main','trifecta','insurance'].every(function(k){return typeof global.ARVEXQBetStrategies[k]==='function'})){
    result.items=[];result.decision='見送り';result.trifectaDecision='未取得';
    result.trifectaReason='券種別判定モジュールの読み込み不足';
    result.insuranceDecision='見送り';result.insuranceReason='券種別判定モジュールの読み込み不足';
    result.captureStatus='engine-missing';return result;
  }
  var ctx={ready:ready,winClear:winClear,order:order,lists:lists,top:top,
     runner:runner,top12:top12,top24:top24,ordered:ordered,p1:p1,add:add,hasHonmei:hasHonmei,
     result:result,reason:reason};
  global.ARVEXQBetStrategies.main(ctx);
  ctx.triAllowed=global.ARVEXQBetStrategies.trifecta(ctx);
  global.ARVEXQBetStrategies.insurance(ctx);
  reason=ctx.reason;
  result.decision=result.items.length?'通常買い':'見送り';
  if(result.items.length&&!result.primaryKind){
    result.items=[];result.decision='見送り';
    result.trifectaDecision='見送り';result.trifectaReason='本線の品質条件未達につき3連単も購入対象外';
    result.insuranceDecision='見送り';
  }
  var total=result.items.reduce(function(a,z){return a+z.points},0);
  result.referenceBudget={unitYen:100,points:total,totalYen:100*total,
    note:'100円/点の参考額。購入額・配当・期待回収率を保証しません。'};
  result.reason=result.items.length?'本線・3連単チャレンジ・保険を独立判定。'+String(base.reason||''):reason||base.reason||'購入条件未達';
  result.betStrategy=stamp;
  return result
}
global.ARVEXQThreeWayBet=Object.freeze({compose:composeThreeWayBetPolicy,version:'arvexq-three-way-v346'});
})(window);
