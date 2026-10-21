/* Display a pre-off sealed original unchanged; never calculate combinations here. */
(function(root){
'use strict';
function esc(x){
 return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;')
   .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function contents(r,p){
 // renderRace is locked by the approved UI design and invokes render()
 // with no arguments. Reuse only the current six-stage preoff adapter input.
 if(!r){
   var forecast=root.ARVEXQProductionPrediction;
   r=forecast&&forecast.currentTrialRace?forecast.currentTrialRace():null;
 }
 var service=root.ARVEXQProductionTickets;
 var plan=r&&service?service.build(r,p):(service&&service.current?service.current():null);
 if(!plan||!plan.fixedAt||!Array.isArray(plan.items)||!plan.items.length){
   // Stage64 supplies a fixed-count research candidate, not a paid-bet recommendation.
   // Do not invent odds, staking, confidence A/B/C, or an authenticated preoff seal.
   var forecaster=root.ARVEXQProductionPrediction,
       trial=forecaster&&forecaster.trial?forecaster.trial(r):null,
       stages=trial&&trial.stages||{},tickets=stages.tickets&&stages.tickets.value;
   if(trial&&tickets&&Array.isArray(tickets.hypotheticalTrifectaTop10)){
     var proposals=tickets.hypotheticalTrifectaTop10.map(function(combo){
       return '<span class="arv-three-combo">'+esc(combo.join(' - '))+'</span>';
     }).join('');
     return '<div class="ai-bet-box arv-three-bet"><div class="ai-bet-title">おすすめ買い目</div>'+
       '<p class="muted">最新Stage64の3連単おすすめ候補（検証中）です。的中率・回収率は未検証です。</p>'+
       '<section class="arv-three-section"><h3>3連単おすすめ候補 '+esc(tickets.hypotheticalTrifectaTop10.length)+'点</h3>'+
       '<strong class="arv-three-combos">'+proposals+'</strong></section></div>';
   }
   return '<div class="ai-bet-box"><p class="muted">発走前に検証・保存されたおすすめ買い目が未取得です。後付けで作りません。</p></div>';
 }
 var list=plan.items.map(function(item){
   var combos=(item.combos||[]).map(function(combo){
     return '<span class="arv-three-combo">'+esc((combo||[]).join(' - '))+'</span>';
   }).join('');
   return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'+
      esc(item.kind)+'</b><span class="arv-three-count">'+esc((item.combos||[]).length)+'点</span></div>'+
      '<strong class="arv-three-combos">'+combos+'</strong>'+
      (item.reason?'<p class="arv-three-ticket-reason">'+esc(item.reason)+'</p>':'')+'</div>';
 }).join('');
 return '<div class="ai-bet-box arv-three-bet">'+
   '<div class="ai-bet-title">おすすめ買い目</div>'+
   '<p class="arv-three-fixed">発走前固定 '+esc(plan.fixedAt)+'</p>'+
   '<section class="arv-three-section"><h3>おすすめ買い目</h3>'+list+'</section>'+
   '<p class="arv-three-provisional">保存された組み合わせをそのまま表示。発走後の再計算はしていません。</p>'+
   '</div>';
}
function render(r,p){
 return '<section id="section-bets" class="card bet-card-clean"><h2>おすすめ買い目</h2>'+
   contents(r,p)+'</section>';
}
root.ARVEXQTicketFrame=Object.freeze({render:render,contents:contents});
})(typeof window!=='undefined'?window:globalThis);
