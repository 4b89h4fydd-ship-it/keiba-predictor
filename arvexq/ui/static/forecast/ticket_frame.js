/* Read-only ticket status; never construct a new bet from bare marks. */
(function(root){
  'use strict';
  function contents(){
    var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
    var message=live&&live.active?
      '<p class="muted">おすすめ買い目は検証済みの発走前データが揃うまで見送りです。印から馬券を自動作成しません。</p>':'';
    return '<div class="ai-bet-box">'+message+'</div>';
  }
  function render(){return '<section id="section-bets" class="card bet-card-clean"><h2>おすすめ買い目</h2>'+contents()+'</section>';}
  root.ARVEXQTicketFrame=Object.freeze({render:render,contents:contents});
})(typeof window!=='undefined'?window:globalThis);
