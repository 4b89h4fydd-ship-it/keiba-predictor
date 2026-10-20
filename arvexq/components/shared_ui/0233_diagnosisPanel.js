function diagnosisPanel(r,p){
  var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.horse&&a.horse.horseNumber,999)-n(b.horse&&b.horse.horseNumber,999)});
  var details='<div class="diagnosis-merged-list">'+rows.map(function(x,i){
    var h=x.horse,e=x.evaluation||{},confidence=esc(e.confidence||'低'),rank=n(x.overallRank,i+1),bw=horseBodyWeightText(h),refbw=!bw?referenceBodyWeight(h):0,bwLabel=bw?bw:(refbw?('前走 '+refbw+'kg'):(isFinal(r)?'結果確認中':'計量待ち'));
    var reason=(x.overallReasons||[]).join(' / ')+(n(x.bombScore)>=65?' / BOMB '+n(x.bombScore)+' EDGE '+n(x.edgeScore)+' '+(x.upsetReasons||[]).slice(0,2).join('・'):'')+(x.predMark==='☆'&&x.attentionReason?' / ☆の根拠 '+x.attentionReason:'');
    return '<article class="horse-card diagnosis-merged-row">'
      +'<div class="diagnosis-merged-head">'
        +'<span class="diag-check-cell"><span class="rc-horse-check '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+'</span></span>'
        +'<button class="diagnosis-horse-main" data-horse-open="'+esc(h.horseNumber)+'">'+badge(h)+'<span class="diagnosis-horse-name"><b>'+esc(h.name)+'</b><small>総合'+rank+'位　馬体重 '+esc(bwLabel)+'</small></span></button>'
        +'<span class="diagnosis-eval"><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'C')+'</strong><b>'+esc(overallScoreText(x))+'</b><i class="diagnosis-ai-mark" data-ai-mark="'+esc(visiblePredictionMark(x))+'">'+esc(visiblePredictionMark(x)||'—')+'</i></span>'
      +'</div>'
      +'<div class="diag-confidence">データ信頼度 <strong>'+confidence+'</strong>　勝率 '+(n(x.winProbability)*100).toFixed(1)+'% / 市場 '+(n(x.marketProbability)*100).toFixed(1)+'%</div>'
      +'<p class="diag-explain">'+esc(reason||'総合バランス型')+'</p>'
    +'</article>'
  }).join('')+'</div>';
  return '<section id="section-diagnosis" class="card"><h2>全頭診断</h2><p class="muted diagnosis-tap-note">馬名をタップすると、直近5走・適性・騎手/調教師・血統までまとめて確認できます。</p>'+details+'</section>'
}
