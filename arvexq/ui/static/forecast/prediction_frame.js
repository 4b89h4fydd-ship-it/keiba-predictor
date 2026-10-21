/* Read-only production prediction status; no on-device forecasting. */
(function(root){
  'use strict';
  function render(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var note=live&&live.source==='saved-preoff'
      ?'<p class="muted">発走前保存の原本だけを表示しています。</p>'
      :(live&&live.source==='stage64-provisional'
        ?'<p class="muted">Stage64の能力・脚質・展開・確率・印・3連単研究候補を発走前に試行表示しています。◎【単】と◎【軸】は役割候補で、A/B/C評価・的中率は未検証です。正式な発走前保存原本ではありません。</p>'
        :'<p class="muted">予想に必要な過去走・脚質情報が足りないか、発走済みのため予想は未設定です。</p>');
    return '<section id="section-prediction" class="card"><h2>AI予想</h2><div class="ai-prediction-list">'+note+'</div></section>';
  }
  root.ARVEXQPredictionFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
