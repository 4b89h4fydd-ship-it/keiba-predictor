/* Read-only production prediction status; no on-device forecasting. */
(function(root){
  'use strict';
  function render(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var note=live&&live.source==='postrace-reference'?'<p class="muted">10/18の事後参考再計算です。結果・払戻は入力せず、既存のモデルで計算。発走前保存予想ではありません。</p>':
      live&&live.source==='saved-preoff'?'<p class="muted">発走前に保存された予想印です。結果を使った後付け予想ではありません。</p>':
      (live&&live.active?'<p class="muted">発走前の暫定予想です。確率は未校正で、的中率・回収率の目標達成を保証するものではありません。</p>':'');
    if(live&&live.unavailable)note='<p class="muted">10月18日は必要な過去走データが不足しているため、事後参考印を算出できません。以前の予想を代わりに表示しません。</p>';
    return '<section id="section-prediction" class="card"><h2>AI予想</h2><div class="ai-prediction-list">'+note+'</div></section>';
  }
  root.ARVEXQPredictionFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
