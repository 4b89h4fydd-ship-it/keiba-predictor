function aiBetExplanationHtml(plan){
  var d=plan&&plan.betExplanation||null;
  if(!d||!Array.isArray(d.lines)||!d.lines.length){
    if(plan&&plan.fixedAt)return '<section class="ai-bet-why"><b>買い目の根拠</b><p>この買い目は発走前に固定されています。当時の比較数値が保存されていないため、今の分析値による後付け説明はしません。</p></section>';
    return '';
  }
  return '<section class="ai-bet-why"><b>この買い目になった理由</b>'
    +d.lines.map(function(line){return '<p>'+esc(line)+'</p>'}).join('')
    +'<small>'+esc(d.note||'')+'</small></section>'
}
// Gate purchasable tickets separately from prediction display. A first-corner
// placing is a historical early-position proxy, NOT measured first-1F speed.
