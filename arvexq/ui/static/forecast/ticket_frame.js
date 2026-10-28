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
/* Re-rank only already sealed picks by the saved Stage64 pre-off distribution.
   This never creates new combinations or consults finish results. */
function sealedFive(r,server){
 var total=server.reduce(function(n,item){return n+(Array.isArray(item.combos)?item.combos.length:0);},0);
 if(total<=5)return server;
 var probs=r&&r.prediction&&r.prediction.stages&&r.prediction.stages.probability&&r.prediction.stages.probability.value;
 var raw=probs&&probs.trifecta;
 if(!raw)return server;
 var joint=Array.isArray(raw)?raw.map(function(x){return {finish:x.combo,prob:Number(x.probability)};}):
   Object.keys(raw).map(function(key){return {finish:key.split(',').map(Number),prob:Number(raw[key])};});
 var ranked=[];
 server.forEach(function(item){
  (item.combos||[]).forEach(function(combo){
   var nums=combo.map(Number);
   var probability=joint.reduce(function(sum,row){
    var finish=row.finish||[];
    var matches=item.kind==='馬単'?finish[0]===nums[0]&&finish[1]===nums[1]:
      item.kind==='馬連'?finish.slice(0,2).every(function(n){return nums.indexOf(n)>=0;}):
      item.kind==='ワイド'?nums.every(function(n){return finish.slice(0,3).indexOf(n)>=0;}):
      item.kind==='3連複'?finish.slice(0,3).every(function(n){return nums.indexOf(n)>=0;}):
      item.kind==='3連単'?finish.slice(0,3).every(function(n,i){return n===nums[i];}):false;
    return sum+(matches&&Number.isFinite(row.prob)?row.prob:0);
   },0);
   ranked.push({item:item,combo:combo,probability:probability});
  });
 });
 ranked.sort(function(a,b){return b.probability-a.probability||
  String(a.item.kind).localeCompare(String(b.item.kind))||
  String(a.combo).localeCompare(String(b.combo));});
 var selected=[];
 ranked.slice(0,5).forEach(function(row){
  var group=selected.filter(function(x){return x.kind===row.item.kind;})[0];
  if(!group){group={kind:row.item.kind,combos:[],points:0,reason:'保存済み発走前確率・全券種合計上位5点'};selected.push(group);}
  group.combos.push(row.combo);group.points++;
 });
 return selected;
}
function contents(r,p){
 var server=r&&r.predictionStatus==='ready'&&Array.isArray(r.recommendedBets)?sealedFive(r,r.recommendedBets):null;
 if(server){
   if(!server.length)return '<div class="ai-bet-box"><p class="muted">発走前の実オッズと着順確率から、期待回収率の条件を満たす買い目がありません。</p></div>';
   var rows=server.map(function(item){return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'+esc(item.kind)+'</b><span class="arv-three-count">'+esc((item.combos||[]).length)+'点</span></div><strong class="arv-three-combos">'+(item.combos||[]).map(function(c){return '<span class="arv-three-combo">'+esc(c.join(' - '))+'</span>';}).join('')+'</strong><p class="arv-three-ticket-reason">'+esc(item.reason||'')+'</p></div>';}).join('');
   var kochiFinal=r&&r.track==='高知'&&/ファイナル/.test(String(r.title||''));
   var isFusion=r.prediction&&r.prediction.modelVersion==='arvexq-empirical-fusion-v1';
   var methodology=isFusion?'発走前の実オッズと期待回収率で選定・全券種合計最大5点':
     kochiFinal?'高知ファイナル：全出走馬から3着候補を評価・3連複と3連単の合計最大5点（未校正）':
     '旧方式の保存済み発走前買い目・全券種合計最大5点';
   return '<div class="ai-bet-box arv-three-bet"><div class="ai-bet-title">おすすめ買い目</div><p class="arv-three-fixed">'+esc(methodology)+'</p>'+rows+'</div>';
 }
 // Never mix an unrelated historical morning receipt into a ready Stage64
 // product when the server did not provide matching ticket evidence.
 if(r&&r.predictionStatus==='ready'&&r.prediction&&
    r.prediction.modelVersion==='arvexq-stage64-product-v1')
   return '<div class="ai-bet-box"><p class="muted">保存済み旧方式の買い目データが未取得です。</p></div>';
 var service=root.ARVEXQProductionTickets;
 var plan=r&&service?service.build(r,p):(service&&service.current?service.current():null);
 // The unified reference plan carries its pre-off capture time as
 // referenceCapturedAt instead of fixedAt; both mean the combinations
 // were fixed before the off (the unified gate enforces capturedAt<post).
 var fixedAt=plan&&(plan.fixedAt||plan.referenceCapturedAt);
 if(!plan||!fixedAt||!Array.isArray(plan.items)||!plan.items.length){
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
   '<p class="arv-three-fixed">発走前固定 '+esc(fixedAt)+'</p>'+
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
