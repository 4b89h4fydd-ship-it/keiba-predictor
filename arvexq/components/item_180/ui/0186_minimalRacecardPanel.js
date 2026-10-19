function minimalRacecardPanel(r){
  var receiptRows=morningSavedMarkRows(r);
  return '<div id="section-entry" class="accordion-panel"><section class="card"><h2>出走表</h2>'+racecardMarkLegend(r)+'<div class="diagnosis-refresh-note busy" style="margin:7px 0">AI解析はバックグラウンドで再取得します。出走表は先に表示しています。</div><div class="racecard-table">'
    +(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){var z=receiptRows.find(function(x){return n(x.horse&&x.horse.horseNumber)===n(h.horseNumber)});return racecardEntryRow(r,h,z)}).join('')
    +'</div></section></div>';
}
