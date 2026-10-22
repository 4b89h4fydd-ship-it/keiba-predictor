/* Read-only production prediction status; no on-device forecasting. */
(function(root){
  'use strict';
  function render(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var note=live&&live.source==='saved-preoff'
      ?'<p class="muted">発走前保存の原本だけを表示しています。</p>'
      :live&&live.source==='learned-revision-preoff-candidate'
      ?'<p class="muted">既存の学習モデルによる発走前の仮予想（未検証）。保存済みの発走前原本・確定買い目ではありません。</p>'
      :live&&live.source==='learned-revision-retrospective'
      ?'<p class="muted">過去レースの事後再分析です。発走前の予想成績には含めません。</p>'
      :'<p class="muted">このレースの学習済み予想印は未取得です。確認できない印は生成しません。</p>';
    var scenarios=live&&live.scenarios||[];
    var extra=scenarios.length?'<p class="muted">比較展開：'+scenarios.map(function(s){
      return String(s.label||s.id||'').replace(/[&<>"']/g,'');
    }).filter(Boolean).join('／')+'</p>':'';
    return '<section id="section-prediction" class="card"><h2>AI予想</h2><div class="ai-prediction-list">'+note+extra+'</div></section>';
  }
  root.ARVEXQPredictionFrame=Object.freeze({render:render});
})(typeof window!=='undefined'?window:globalThis);
