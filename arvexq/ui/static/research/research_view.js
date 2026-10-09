/* ARVEXQ research evidence presentation: historical facts only, not forecasts. */
(function(global){
'use strict';
function renderHorse(r,h,escapeText){
  var esc=escapeText||function(s){return String(s)},research=h&&h.researchEvidence,
      factors=research&&research.factors||{},items=Array.isArray(factors.items)?factors.items:[],
      sections=research&&research.sectionals||{},runs=sections.runs||[],
      bias=r&&r.biasProvenance||{},official=bias.official||{},estimate=bias.estimated||{};
  var rows=items.map(function(item){
    var values=(item.measurements||[]).map(function(m){return esc(m.key)+': '+esc(m.value)}).join(' / ');
    return '<div class="arv-research-item"><b>'+esc(item.label||item.key)+'</b>'
      +'<span>'+ (values||'未取得') +'</span></div>';
  }).join('');
  var history=runs.map(function(z){
    return '<div class="arv-research-sectional">'+esc(z.date||'')+'　'+esc(z.distance||'—')+'m'
      +'　前半3F '+esc(z.early3FSeconds==null?'—':z.early3FSeconds+'秒')
      +'　中盤3F '+esc(z.middle3FSeconds==null?'—':z.middle3FSeconds+'秒')
      +'　上がり3F '+esc(z.late3FSeconds==null?'—':z.late3FSeconds+'秒')
      +(z.last3FWithinRacePercentile==null?'':'　同レース上がり相対値 '+esc(z.last3FWithinRacePercentile))
      +'</div>'
  }).join('');
  var condition=official.condition==null?'未取得':esc(official.condition),
      source=official.source==='official-announcement'?'公式発表':'出走表由来・公式未確認';
  return '<section class="arv-research-card" aria-label="分析根拠">'
    +'<details><summary>14項目の能力根拠と区間実測（詳細）</summary>'
    +(items.length?'<div class="arv-research-grid">'+rows+'</div>':'<p>14項目の照合データ取得待ち。推定で補完しません。</p>')
    +'<p class="arv-research-foot">各指標は計測単位が異なり、そのまま加算した数値や的中率ではありません。</p>'
    +'<h4>過去走の区間実測</h4>'+(history||'<p>実測区間時計は未取得です。</p>')
    +'<p class="arv-research-foot">初角順位とテン3Fは別の指標です。異なる距離・馬場の秒数を単純比較しません。</p>'
    +'<h4>馬場情報の出典</h4><p>馬場状態 '+condition+'（'+source+'）'
    +' / AI推定 '+esc(estimate.frontBack==null?'未取得':estimate.frontBack)
    +'・内外 '+esc(estimate.insideOutside==null?'未取得':estimate.insideOutside)
    +'　※AI推定は公式発表ではありません。</p>'
    +'</details></section>';
}
function renderRecap(r,escapeText,isFinal){
  if(!isFinal||!r||!r.result)return '';
  var rows=r.result.finishers||[],esc=escapeText||String,
      finishers=rows.filter(function(x){return x&&Number(x.horseNumber)>0&&Number(x.finish||x.finishPosition)>0})
       .slice().sort(function(a,b){return Number(a.finish||a.finishPosition)-Number(b.finish||b.finishPosition)});
  if(finishers.length<3)return '<p class="arv-research-foot">確定着順データを確認できないため、自動回顧は未作成です。</p>';
  var top=finishers.slice(0,3).map(function(x){
    var h=(r.horses||[]).find(function(z){return Number(z.horseNumber)===Number(x.horseNumber)})||{};
    return esc(x.horseNumber)+'番'+esc(x.name||x.horseName||h.name||'');
  });
  return '<section class="arv-research-card"><h3>確定結果の自動回顧</h3><p>'+top.join('・')+' が1〜3着。</p>'
   +'<p class="arv-research-foot">確定着順に基づく機械的回顧。レース映像・不利・騎手の意図は未確認です。発走前の予想と印は変更しません。</p></section>';
}
global.ARVEXQResearchView=Object.freeze({renderHorse:renderHorse,renderRecap:renderRecap,version:'arvexq-research-view-v1'});
})(window);
