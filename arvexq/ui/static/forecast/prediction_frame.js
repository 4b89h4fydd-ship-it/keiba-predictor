/* Read-only production prediction status; no on-device forecasting. */
(function(root){
  'use strict';
  function render(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var note=live&&live.source==='saved-preoff'
      ?'<p class="muted">発走前保存の原本だけを表示しています。</p>'
      :'<p class="muted" data-forecast-status="unavailable">予想未生成：現在の予想モデルは停止中です。検証済みの発走前印・展開・買い目はまだ配信されていません。</p>';
    return '<section id="section-prediction" class="card"><h2>AI予想</h2><div class="ai-prediction-list">'+note+'</div></section>';
  }
  root.ARVEXQPredictionFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
