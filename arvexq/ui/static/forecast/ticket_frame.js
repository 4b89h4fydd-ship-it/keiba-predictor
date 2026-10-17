/* 187: Betting frame layout only. */
(function(root){
  'use strict';
  function contents(){return '<div class="ai-bet-box"></div>';}
  function render(){return '<section id="section-bets" class="card bet-card-clean">'+contents()+'</section>';}
  root.ARVEXQTicketFrame=Object.freeze({render:render,contents:contents});
})(typeof window!=='undefined'?window:globalThis);
