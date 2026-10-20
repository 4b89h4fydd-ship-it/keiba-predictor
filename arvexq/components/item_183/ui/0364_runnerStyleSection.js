function runnerStyleSection(r,p){
  var diagnosisReady=diagnosisCurrent(r),
      cadenceText=window.ARVEXQLiveOdds.status(r);
  // Only current three-factor marks are displayed; no V313 correction badge.
  return '<section class="card"><h2>出走表</h2>'+racecardMarkLegend(r)+'<button data-action="odds-update">オッズ・馬体重更新</button><span id="odds-status" role="status"> '+cadenceText+'</span>'
    +(!diagnosisReady?'<div class="diagnosis-refresh-note busy" style="margin:7px 0">'+(r._entryOnly?'出走表を先に表示しています。履歴・能力評価を取得中です。':'取得済みデータでAI評価を先に計算中。更新後は馬名タップの詳細と展開予想へ反映します。')+'</div>':'')
    +'<div class="racecard-table">'
    +(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){
      var x=(p.rows||[]).find(function(z){return z&&z.horse&&n(z.horse.horseNumber)===n(h.horseNumber)});
      return racecardEntryRow(r,h,x);
    }).join('')
    +'</div></section>';
}
