function resultPanel(r){
  var final=isFinal(r),flash=isFlash(r),any=hasAnyResultData(r);
  return '<section id="section-result" class="card result-panel-compact"><h2>レース結果</h2>'+
    (any?renderResult(r)+(final?renderPayouts(r):'<section class="card result-wait-card"><div class="section-title">払い戻し <span class="muted">確定待ち</span></div><div class="muted">確定後に自動反映します。</div></section>')+renderActualFlow(r):
      '<div class="muted result-status-compact">'+(final?'結果は確定扱いですが着順詳細は未取得です。':(String(r.date||'')<today()||String(r.date||'')===today()&&mins(r.startTime)<=nowMins()?'公式結果の反映待ちです。自動再確認しています。':'発走前・結果未確定'))+'</div><button type="button" data-detail-retry="'+esc(r.id)+'">結果を再確認</button>') +
  researchRecapPanel(r)+'</section>'
}
