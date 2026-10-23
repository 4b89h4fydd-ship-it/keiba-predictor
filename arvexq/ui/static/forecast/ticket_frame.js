/* Display a pre-off sealed original unchanged; never calculate combinations here. */
(function(root){
'use strict';
function esc(x){
 return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;')
   .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function revisionStatus(r){
 var live=root.ARVEXQProductionPrediction&&root.ARVEXQProductionPrediction.current();
 var rev=r&&r._forecastRevisionView,plan=rev&&rev.betPlan;
 if(!live||!/^learned-revision-/.test(live.source||'')||!rev||rev.raceId!==r.id||rev.raceDate!==r.date||!plan)return '';
 var note=live.source==='learned-revision-retrospective'?'事後再分析の買い目比較':'発走前の仮予想の買い目比較';
 var rows=Array.isArray(plan.comparisons)?plan.comparisons:[];
 return '<div class="revision-bet-status"><p>'+esc(note)+'：'+esc(plan.decision||'見送り')+'</p><p class="muted">'+esc(plan.reason||'')+'</p>'+rows.map(function(row){
   return '<p><b>'+esc(row.kind)+'</b>：'+esc(row.decision||'見送り')+' — '+esc(row.reason||'')+'</p>';
 }).join('')+'</div>';
}
function contents(r,p){
 var server=r&&r.predictionStatus==='ready'&&Array.isArray(r.recommendedBets)?r.recommendedBets:null;
 if(server){
   var rows=server.map(function(item){return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'+esc(item.kind)+'</b><span class="arv-three-count">'+esc((item.combos||[]).length)+'点</span></div><strong class="arv-three-combos">'+(item.combos||[]).map(function(c){return '<span class="arv-three-combo">'+esc(c.join(' - '))+'</span>';}).join('')+'</strong><p class="arv-three-ticket-reason">'+esc(item.reason||'')+'</p></div>';}).join('');
   return '<div class="ai-bet-box arv-three-bet"><div class="ai-bet-title">おすすめ買い目</div><p class="arv-three-fixed">Stage64確率順・全印考慮・各券種最大5点</p>'+rows+'</div>';
 }
 var service=root.ARVEXQProductionTickets;
 var plan=r&&service?service.build(r,p):(service&&service.current?service.current():null);
 if(!plan||!plan.fixedAt||!Array.isArray(plan.items)||!plan.items.length){
   return '<div class="ai-bet-box"><p class="muted">発走前に検証・保存されたおすすめ買い目が未取得です。後付けで作りません。</p>'+revisionStatus(r)+'</div>';
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
