/* Independent three-way ticket generation, no DOM or storage. */
(function(global){
'use strict';
function composeThreeWayBetPolicy(base,r,p,deps){
 const {n,clamp,isScratchHorse,betComboText}=deps;
  if(!base)return base;
  var rows=((p&&p.rows)||[]).filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)&&n(x.horse.horseNumber)>0});
  var result=Object.assign({},base),audit=base.audit||{},g=base.betInputGate||{},
      selected=!!(base.selectionAudit&&base.selectionAudit.selected),
      ready=g.ready===true&&selected,stamp='arvexq-three-way-v346',
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
  // One main ticket family: place reliability and ordered certainty decide
  // the type. No multiple identical opinions through several ticket kinds.
  if(ready){
    var kind='';
    if(winClear&&order>=.45&&lists['馬単'][0]&&lists['馬単'][0].weight>=.075)kind='馬単';
    else if(lists['馬連'][0]&&lists['馬連'][0].weight>=.16)kind='馬連';
    else if(lists['3連複'][0]&&lists['3連複'][0].weight>=.12&&top.weight<.30)kind='3連複';
    else if(lists['ワイド'][0]&&lists['ワイド'][0].weight>=.20)kind='ワイド';
    if(kind){
      var pool=lists[kind],max=kind==='3連複'?3:2,cut=pool[0].weight*.70,combos=[];
      pool.some(function(z){if(combos.length>=max||combos.length>=1&&z.weight<cut)return true;combos.push(z.combo);return false});
      add('本線',kind,combos,'着順別モデルの相対集中度・点数を比較して'+kind+'を優先。配当オッズ未検証のため数値的な期待値は未算出。');
      result.primaryKind=kind;
    }else{result.primaryKind='';reason='本線に適した券種の集中度が不足'}
  }else result.primaryKind='';
  // Every race is reviewed. Never add a mandatory trifecta for a grade/special race.
  var triAllowed=ready&&winClear&&order>=.42&&top12>=.115&&
      top24>0&&top12/top24>=.54&&ordered.length>=12;
  var chosen=ordered.filter(function(z){return z.combo[0]===top.no}).slice(0,12);
  // A wider winning-field set would require over-budget coverage; abstain.
  var winningMass=p1.filter(function(x){return x>=top.weight*.80}).length;
  if(winningMass>2)triAllowed=false;
  if(chosen.length<6)triAllowed=false;
  if(triAllowed){
    // Add only competitive orders. A low-concentration tail is not padded to
    // manufacture a six-ticket challenge.
    var cutoff=chosen[0].weight*.38;
    chosen=chosen.filter(function(z){return z.weight>=cutoff}).slice(0,12);
    if(chosen.length<6)triAllowed=false;
  }
  if(triAllowed){
    var triCombos=chosen.map(function(z){return z.combo});
    add('3連単チャレンジ','3連単',triCombos,
      '独立1着候補'+top.no+'、条件付き2着・3着、展開AIの局面適合、順序集中度が購入条件を通過。');
    result.trifectaDecision='採用';
    result.trifectaReason='1着'+top.no+'軸・2着/3着は別モデル。'+triCombos.length+'点で規定の集中度を満たすため採用。';
    result.trifectaFirst=[top.no];result.trifectaSecond=Array.from(new Set(triCombos.map(function(c){return c[1]})));
    result.trifectaThird=Array.from(new Set(triCombos.map(function(c){return c[2]})));
  }else{
    result.trifectaDecision='見送り';
    result.trifectaReason=ready?(winClear?'展開・順序の集中度不足、または12点以内では有力な着順を絞れないため見送り。':'独立1着候補が十分に絞れず、固定のリスクが高いため見送り。'):reason;
    result.trifectaFirst=[];result.trifectaSecond=[];result.trifectaThird=[];
  }
  if(triAllowed&&result.primaryKind){
    // Hedge specifically against a different winner, not the same first-place
    // opinion. Do not duplicate a combination already present in the main.
    var main=result.items.filter(function(z){return z.level==='本線'})[0],
        isDuplicate=function(kind,combo){return !!(main&&main.kind===kind&&main.combos.some(function(x){return x.join('-')===combo.join('-')}))},
        backup=runner.no,insurance=null;
    ['馬連','ワイド'].some(function(kind){
      var hits=lists[kind].filter(function(z){return z.combo.indexOf(backup)>=0&&!isDuplicate(kind,z.combo)&&!(main&&main.combos.some(function(c){return c.length===2&&c.slice().sort(function(a,b){return a-b}).join('-')===z.combo.slice().sort(function(a,b){return a-b}).join('-')}))});
      if(!hits.length)return false;
      // Hedge against 1st reversal; still need a high-ranked complement.
      if(hits[0].weight<(kind==='ワイド'?.13:.09))return false;
      insurance={kind:kind,combos:[hits[0].combo]};return true
    });
    if(insurance){
      add('保険',insurance.kind,insurance.combos,'3連単の1着'+top.no+'固定が崩れ、'+backup+'が勝ち負けする分岐を補完。既存本線との組み合わせ重複なし。');
      result.insuranceDecision='採用';
      result.insuranceReason='1着逆転の別展開を最小1点で補完';
    }else result.insuranceReason='本線と重複するか、独立した補完根拠が不足するため見送り';
  }else result.insuranceReason='3連単未採用、または本線不成立のため保険を追加しない';
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
