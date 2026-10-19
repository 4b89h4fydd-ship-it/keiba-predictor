function attachAiBetExplanation(plan,r,p){
  if(!plan||plan.fixedAt)return plan;
  var rows=(p&&p.rows||[]).filter(function(z){return z&&z.horse}),marks={};
  rows.forEach(function(z){
    var no=n(z.horse.horseNumber,0);
    if(no)marks[no]=String(z.predMark||'').replace(/＋/g,'+');
  });
  var evidence=plan.exactaEvidence||null,
      pairs=evidence&&Array.isArray(evidence.pairs)?evidence.pairs:[],
      pairByNo={},axis=n(evidence&&evidence.axis,0),lines=[];
  pairs.forEach(function(x){pairByNo[n(x.second)]=Math.max(0,n(x.p2GivenFirst,0))});
  function has(no){return Object.prototype.hasOwnProperty.call(pairByNo,no)}
  function pct(v){return (Math.max(0,Math.min(1,n(v,0)))*100).toFixed(1)+'%'}
  var betItems=(plan.items||[]).filter(function(z){return z&&z.kind==='馬単'&&(z.combos||[]).length});
  betItems.forEach(function(item){
    var actual=(item.combos||[]).filter(function(c){return c&&n(c[0])>0&&n(c[1])>0}).slice(0,4);
    actual.forEach(function(c){
      var first=n(c[0]),second=n(c[1]),mark=marks[second]||'無印';
      if(first===axis&&has(second)){
        lines.push('馬単 '+first+'→'+second+'（'+mark+'）：'+first+'を1着とした場合の、'+second+'の条件付き2着推定は'+pct(pairByNo[second])+'。');
      }else{
        lines.push('馬単 '+first+'→'+second+'（'+mark+'）：着順AIの選択候補。発走前の条件付き比較スコアが残っていないため、確率差は断定しません。');
      }
    });
    var used=actual.filter(function(c){return n(c[0])===axis}).map(function(c){return n(c[1])}),
        excluded=rows.filter(function(z){
          var no=n(z.horse.horseNumber),mark=marks[no];
          return no!==axis&&used.indexOf(no)<0&&(mark==='○'||mark==='☆+');
        }).sort(function(a,b){
          return (marks[n(a.horse.horseNumber)]==='○'?0:1)-(marks[n(b.horse.horseNumber)]==='○'?0:1);
        }),
        selectedLower=used.filter(function(no){return marks[no]==='☆'||marks[no]==='△'||marks[no]==='注'});
    if(!excluded.length||!selectedLower.length)return;
    var omitted=n(excluded[0].horse.horseNumber),om=marks[omitted],kept=selectedLower[0],km=marks[kept];
    if(has(kept)&&has(omitted)&&pairByNo[kept]>pairByNo[omitted]){
      lines.push('印と異なる理由：'+km+kept+'の条件付き2着推定 '+pct(pairByNo[kept])+' が、'+om+omitted+'の '+pct(pairByNo[omitted])+' を上回ります。☆＋は1着逆転を含めた総合評価のため、2着専用の順位とは一致しない場合があります。');
    }else if(has(kept)&&has(omitted)){
      lines.push('印との不整合を検出：'+om+omitted+'の条件付き2着推定 '+pct(pairByNo[omitted])+' が、採用した'+km+kept+'の '+pct(pairByNo[kept])+' 以上です。展開や買い目選択ゲートで候補が外れた可能性があり、根拠の再点検が必要です。');
    }else{
      lines.push('印との違い：'+om+omitted+'を外して'+km+kept+'を採用。両馬の着順比較スコアが保存されていないため、どちらの方が2着確率が高いか断定できません。');
    }
  });
  if(!betItems.length&&(plan.items||[]).length){
    var main=(plan.items||[])[0],kind=String(main.kind||'');
    if(['馬連','ワイド','3連複'].indexOf(kind)>=0)lines.push(kind+'を選択：今回の予測では着順の固定より、上位候補を順不同で組み合わせることを優先しました。');
    else if(kind==='3連単')lines.push('3連単を選択：1〜3着順序の集中度と券種選択条件を通過した組み合わせです。');
  }
  if(!lines.length&&plan.decision==='見送り')lines.push('券種選択の条件を満たさなかったため買い目を見送りました。');
  if(lines.length&&plan.outcomeLink&&plan.outcomeLink.verdict)lines.push('展開判定：'+String(plan.outcomeLink.verdict)+'。展開と着順の役割を併せて検討しています。');
  plan.betExplanation={version:'v342-conditional-second',axis:axis,lines:lines.slice(0,7),
    note:'表示％はAIモデル内の条件付き2着推定で、実際の的中率や馬券の回収率を保証しません。発走前に固定した買い目と根拠は変更しません。'};
  return plan
}
