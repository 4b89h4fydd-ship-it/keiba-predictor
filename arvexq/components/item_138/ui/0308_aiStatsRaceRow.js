function aiStatsRaceRow(x){
  var result=(x.podiumNos||[]).slice(0,3).join('-')||'—',
      cls=!x.eligible?'pending':(x.fullPodiumHit?'hit':(x.markHit?'partial':'miss')),
      judge=x.loadError?'再取得待ち':(!x.resultReady?'結果未取得':(!x.hasMarks?'発走前予想未保存':(x.fullPodiumHit?'3頭完全包含':(x.markHit?'1着印内':'1着印外'))));
  var detail=x.eligible?'<small>◎3着内 '+(x.honEligible?(x.honPlaceHit?'○':'×'):'対象外')+' ／ ◎1着 '+(x.honEligible?(x.winHit?'○':'×'):'対象外')+' ／ 印内1着 '+(x.markHit?'○':'×')+' ／ 印内3頭 '+(x.fullPodiumHit?'○':'×')+' ／ 3連単 '+(x.triEligible?(x.triHit?'的中':'不的中'):'未保存・対象外')+'</small>':'<small>集計対象外（不的中には算入しません）</small>';
  return '<div class="smart-ai-race-row '+cls+'"><span class="smart-ai-race-name"><b>'+esc(x.raceNumber)+'R</b><small>'+esc(x.title||'')+'</small></span><span class="smart-ai-race-marks">'+esc(aiStatsMarkText(x))+'</span><span class="smart-ai-race-result">結果 '+esc(result)+'</span><strong>'+esc(judge)+'</strong>'+detail+'</div>'
}
