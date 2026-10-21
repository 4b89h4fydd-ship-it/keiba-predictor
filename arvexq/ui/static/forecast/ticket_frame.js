/* Display a pre-off sealed original unchanged; never calculate combinations here. */
(function(root){
'use strict';
function esc(x){
 return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;')
   .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function contents(r,p){
 var service=root.ARVEXQProductionTickets;
 var plan=r&&service?service.build(r,p):(service&&service.current?service.current():null);
 if(!plan||!plan.fixedAt||!Array.isArray(plan.items)||!plan.items.length){
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
