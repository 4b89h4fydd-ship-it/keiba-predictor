/* Betting screen HTML only: no selection, betting or result mutation. */
(function(global){
'use strict';
// Present existing ticket strings as separate, legible choices; no recomputation.
function ticketCombos(z,esc,betComboText){
  var full=String(z.combo||betComboText(z.kind,z.combos||[]));
  var parts=full.split(/\s*\/\s*/).map(function(c){return c.trim()}).filter(Boolean);
  return '<strong class="arv-three-combos" aria-label="'+esc(full)+'">'
    +parts.map(function(c){return '<span class="arv-three-combo">'+esc(c)+'</span>'}).join('')
    +'</strong>';
}
function render(r,p,deps){
 const {buildAiBetPlan,esc,n,isFinal,raceMarkClock,aiBetExplanationHtml,betComboText}=deps;
  var plan=buildAiBetPlan(r,p);
  if(!plan)return '<div class="ai-bet-box"><div class="ai-bet-title">AI買い目</div><p class="muted">'+((isFinal(r)||raceMarkClock(r).started)?'発走前買い目未保存（発走後の後付け予想は作成しません）':'発走前予想を取得中。未保存の買い目は暫定判定です。')+'</p></div>';
  var dataUnavailable=plan.decision==='データ不足'||plan.decision==='未取得'||
      plan.dataStatus==='engine-unavailable'||plan.dataStatus==='insufficient-preoff-evidence';
  function renderGroup(level,label,reason){
    var items=(plan.items||[]).filter(function(z){return z.level===level});
    var body=items.map(function(z){
      return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'+esc(z.kind)+'</b><span class="arv-three-count">'+esc(z.points)+'点</span></div>'
        +(z.comboProbabilities&&z.comboProbabilities.length===(z.combos||[]).length
          ?(z.combos||[]).map(function(combo,i){return '<div class="arv-three-ticket-prob"><strong>'+esc(combo.join('-'))+'</strong><span>推定発生確率 '+esc(z.comboProbabilities[i])+'%</span></div>'}).join('')
          :ticketCombos(z,esc,betComboText))
        +(z.reason?'<p class="arv-three-ticket-reason">'+esc(z.reason)+'</p>':'')+'</div>'
    }).join('');
    return '<section class="arv-three-section"><h3>'+esc(label)+'</h3>'
      +(body||'<p class="arv-three-skip">'+(dataUnavailable?'データ不足・未取得：':'見送り：')+esc(dataUnavailable?(plan.dataMissing||[]).join('／')||plan.reason||reason||'発走前情報が揃っていません':reason||'購入条件を満たさず')+'</p>')+'</section>';
  }
  var total=plan.referenceBudget||{},status=plan.fixedAt?'発走前固定':'暫定・未保存',
      savedV346=!!plan.fixedAt&&String(plan.engineVersion||plan.betStrategy||'').includes('three-way-v346'),
      hon=plan.honmei||{},
      axisLabel=savedV346?'発走前に保存した本命と買い目を維持（役割を後付けしません）':hon.horseNumber?
       ('◎ '+hon.horseNumber+'番｜勝ち切る能力と3着内の安定性を兼ね備えた最有力馬（券種は全種類から比較）'):'高信頼の軸なし・買い目は券種別に判断',
      explanation=aiBetExplanationHtml(plan);
  return '<div class="ai-bet-box arv-three-bet">'
    +'<div class="ai-bet-head ai-bet-head-v224"><div class="ai-bet-title">AI買い目</div>'
    +'<div class="ai-bet-meta"><span class="arv-bet-quality"><small>3連単買い目の推定発生確率</small><b>'+esc(plan.trifectaOccurrenceProbability==null?'未算出':plan.trifectaOccurrenceProbability)+'<em>'+ (plan.trifectaOccurrenceProbability==null?'':'%') +'</em></b></span>'
    +'<span class="arv-bet-status">'+esc(status)+'</span></div><span class="ai-bet-brand">ARVEXQ</span></div>'
    +'<p class="arv-three-provisional">'+esc(axisLabel)+'</p>'
    +'<p class="arv-three-provisional">全券種を比較し、根拠のある組み合わせをおすすめとして選定します。推定確率は未校正で、目標の的中率80%以上（望成90%以上）を保証するものではありません。</p>'
    +(plan.noAxis&&!dataUnavailable?'<p class="arv-three-provisional">'+esc(savedV346?'保存時点の軸なし判定を維持。':'◎信頼度Cまたは◎不在：軸を固定せずワイド・馬連・3連複を比較。馬単・3連単は見送ります。')+'</p>':'')
    +(plan.referenceOnly?'<p class="arv-three-provisional">通常レースの参考買い目。朝固定の厳選レースではありません。</p>':'')
    +((plan.betWarnings||[]).length?'<div class="arv-three-check"><b>購入前に確認</b><p>条件未確認：'+esc(plan.betWarnings.join('／'))+'</p><small>オッズ・期待値を確認してから購入判断してください。</small></div>':'')
    +renderGroup('本線','本線｜的中重視',plan.reason)
    +renderGroup('3連単チャレンジ','3連単チャレンジ｜高配当重視',plan.trifectaReason)
    +renderGroup('保険','保険｜本線補完',plan.insuranceReason)
    +'<div class="arv-three-budget"><strong>合計 '+esc(total.points==null?(plan.items||[]).reduce(function(a,z){return a+n(z.points)},0):total.points)+'点</strong>'
    +(total.totalYen!=null?'<span>100円/点換算 '+esc(total.totalYen)+'円</span>':'')+'</div>'
    +'<p class="arv-three-budget-hint">購入額は投票時に指定</p>'
    +'<p class="arv-three-ev">'+esc(plan.expectedValueReason||'券種別の的中率・回収率・期待値は、保存済み実績を検証できるまで表示しません。')+'</p>'
    +(plan.fixedAt?'<p class="arv-three-fixed">保存 '+esc(plan.fixedAt)+'</p>':'<p class="arv-three-provisional">発走前の保存が完了するまでは暫定です。発走後に買い目を新規作成しません。</p>')
    +(plan.postLockNotice?'<p class="ai-bet-lock-notice">'+esc(plan.postLockNotice)+'</p>':'')
    +explanation
    +'<div class="bet-mark-guide"><b>'+esc(savedV346?'保存時点の印の見方':'印の見方（予想を基に評価）')+'</b><div class="bet-mark-grid">'
    +'<span><i>◎</i>勝ち切る能力と3着内の安定性を総合した最有力馬。単・軸で別の馬には分けません。</span>'
    +'<span><i>○</i>◎に最も匹敵し逆転を狙える相手</span><span><i>▲</i>◎・○に匹敵する実力馬</span>'
    +'<span><i>△</i>3着向き</span><span><i>☆</i>実測の追い上げ・前争いを評価</span><span><i>注</i>着差・同条件・相手関係などの見落とし注意馬</span>'
    +'</div></div><p class="arv-three-reason">'+esc(plan.reason||'')+'</p></div>'
}
global.ARVEXQBetView=Object.freeze({render:render});
})(window);
