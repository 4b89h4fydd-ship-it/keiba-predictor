/* Read-only production prediction status; no on-device forecasting. */
(function(root){
  'use strict';
  function render(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var note=live&&live.active?'<p class="muted">発走前の暫定予想です。確率は未校正で、的中率・回収率の目標達成を保証するものではありません。</p>':'';
    return '<section id="section-prediction" class="card"><h2>AI予想</h2><div class="ai-prediction-list">'+note+'</div></section>';
  }
  root.ARVEXQPredictionFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
