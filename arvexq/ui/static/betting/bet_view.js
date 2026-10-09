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
  // Preserve the original recorded ticket types/marks even when it was frozen
  // under the pre-v346 engine. Never relabel historical "通常"/"押さえ"
  // as a v346 main/challenge/insurance decision after the off.
  if(plan.fixedAt&&String(plan.engineVersion||plan.betStrategy||'').indexOf('three-way-v346')<0){
    var legacyItems=(plan.items||[]).map(function(z){
      return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'
        +esc(z.level||'旧方式')+'｜'+esc(z.kind||'券種')+'</b><span>'+esc(z.points||((z.combos||[]).length))+'点</span></div>'
        +'<strong>'+esc(z.combo||betComboText(z.kind,z.combos||[]))+'</strong></div>'
    }).join('');
    return '<div class="ai-bet-box arv-three-bet"><div class="ai-bet-title">発走前保存済み買い目（旧方式）</div>'
      +'<p class="arv-three-fixed">保存 '+esc(plan.fixedAt)+'</p>'
      +(legacyItems||'<p class="arv-three-skip">'+esc(plan.decision==='未取得'?'発走前の買い目保存に失敗。予想・購入は未取得です。':plan.reason||'当時の買い目は見送りでした。')+'</p>')
      +'<p class="arv-three-provisional">旧方式で保存された買い目は改変しません。新しい3方式への事後変換・的中結果を見た後の追加は禁止しています。</p>'
      +(plan.postLockNotice?'<p class="ai-bet-lock-notice">'+esc(plan.postLockNotice)+'</p>':'')
      +aiBetExplanationHtml(plan)+'</div>';
  }
  var dataUnavailable=plan.decision==='データ不足'||plan.decision==='未取得'||
      plan.dataStatus==='engine-unavailable'||plan.dataStatus==='insufficient-preoff-evidence';
  function renderGroup(level,label,reason){
    var items=(plan.items||[]).filter(function(z){return z.level===level});
    var body=items.map(function(z){
      return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'+esc(z.kind)+'</b><span class="arv-three-count">'+esc(z.points)+'点</span></div>'
        +ticketCombos(z,esc,betComboText)
        +(z.reason?'<p class="arv-three-ticket-reason">'+esc(z.reason)+'</p>':'')+'</div>'
    }).join('');
    return '<section class="arv-three-section"><h3>'+esc(label)+'</h3>'
      +(body||'<p class="arv-three-skip">'+(dataUnavailable?'データ不足・未取得：':'見送り：')+esc(dataUnavailable?(plan.dataMissing||[]).join('／')||plan.reason||reason||'発走前情報が揃っていません':reason||'購入条件を満たさず')+'</p>')+'</section>';
  }
  var total=plan.referenceBudget||{},status=plan.fixedAt?'発走前固定':'暫定・未保存',
      explanation=aiBetExplanationHtml(plan);
  return '<div class="ai-bet-box arv-three-bet">'
    +'<div class="ai-bet-head ai-bet-head-v224"><div class="ai-bet-title">AI買い目</div>'
    +'<div class="ai-bet-meta"><span class="arv-bet-quality"><small>内部評価（的中率ではありません）</small><b>'+esc(plan.betQuality==null?'未算出':plan.betQuality)+'<em>/100</em></b></span>'
    +'<span class="arv-bet-status">'+esc(status)+'</span></div><span class="ai-bet-brand">ARVEXQ</span></div>'
    +(plan.noAxis&&!dataUnavailable?'<p class="arv-three-provisional">◎なし：連対・3着内の組み合わせを比較。ワイド・馬連・3連複を検討し、馬単・3連単は見送ります。</p>':'')
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
    +'<div class="bet-mark-guide"><b>印の見方（券種ごとに役割を再判定）</b><div class="bet-mark-grid">'
    +'<span><i>◎</i>3着以内の軸。1着固定を意味しない</span><span><i>【単】</i>独立した1着・単勝向き評価</span>'
    +'<span><i>○</i>連対の本線候補</span><span><i>▲</i>上位有力候補</span>'
    +'<span><i>☆+</i>1着逆転も狙う強穴</span><span><i>☆</i>能力面の穴・相手候補</span>'
    +'<span><i>△</i>3着・押さえ</span><span><i>注</i>条件が合うときのみ採用</span>'
    +'</div></div><p class="arv-three-reason">'+esc(plan.reason||'')+'</p></div>'
}
global.ARVEXQBetView=Object.freeze({render:render});
})(window);
