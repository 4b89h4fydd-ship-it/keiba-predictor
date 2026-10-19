function smartDailyAiStats(){
  var dayRaces=(state.races||[]).filter(function(r){return r&&r.id});
  var allFinished=dayRaces.length>0&&dayRaces.every(function(r){return isFinal(r)});
  if(!allFinished)return '';
  var s=dailyAiStats,title=aiStatsDayTitle();if(s.date!==state.date)resetDailyAiStats(state.date),s=dailyAiStats;
  if(s.loading&&!s.total)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>全レース終了・集計中…</small></div></section>';
  if(!s.done)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>集計準備中</small></div></section>';
  if(!s.total){
    var msg=s.finalCount?'当時の事前AI印が保存されているレースなし':'まだ集計対象の確定レースなし';
    return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>'+msg+'</small></div><p>※結果を見てから予想を作り直したレースは成績に含めません。</p></section>'
  }
  function rate(hit){return Math.round(hit/s.total*100)}
  var miss=Math.max(0,s.total-s.winHits),reasonRows=Object.keys(s.reasons||{}).map(function(k){return[k,n(s.reasons[k])]}).sort(function(a,b){return b[1]-a[1]}).slice(0,3),reasonText=reasonRows.length?reasonRows.map(function(z){return z[0]+' '+z[1]}).join(' / '):'なし',hc=s.highConfTotal?(Math.round(s.highConfHits/s.highConfTotal*100)+'% '+s.highConfHits+'/'+s.highConfTotal):'対象なし',avgB=s.total?(s.brierSum/s.total).toFixed(3):'—',avgPod=s.total?(s.markedPodiumSum/s.total).toFixed(2):'—',centralPod=s.centralPodiumTotal?(Math.round(s.centralPodiumHits/s.centralPodiumTotal*100)+'% '+s.centralPodiumHits+'/'+s.centralPodiumTotal):'対象なし',localPod=s.localPodiumTotal?(Math.round(s.localPodiumHits/s.localPodiumTotal*100)+'% '+s.localPodiumHits+'/'+s.localPodiumTotal):'対象なし';
  return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>'+s.total+'レース集計 / 目標 3頭完全包含83%</small></div><div class="smart-ai-daily-grid">'+
    '<div><small>印内3頭完全</small><strong>'+rate(s.fullPodiumHits)+'%</strong><em>'+s.fullPodiumHits+'/'+s.total+'</em></div>'+ 
    '<div><small>◎1着</small><strong>'+rate(s.winHits)+'%</strong><em>'+s.winHits+'/'+s.total+'</em></div>'+ 
    '<div><small>AI印内1着</small><strong>'+rate(s.markHits)+'%</strong><em>'+s.markHits+'/'+s.total+'</em></div>'+ 
  '</div><div class="smart-ai-review"><b>候補抽出KPI</b><span>中央 3頭完全 '+centralPod+'　地方 '+localPod+'</span><span>平均 '+avgPod+'/3頭を印内　☆・注3着内 '+rate(s.holePlaceHits)+'%</span><span>◎外れ '+miss+'　順位ミス '+s.candidateOrderMisses+' / 候補外 '+s.candidateMisses+'</span><span>高信頼◎ '+hc+'　Brier '+avgB+'</span><small>主なズレ　'+esc(reasonText)+'</small></div><p>※当日補正を含む発走前固定の印だけで集計。目標は12Rなら10R前後で1〜3着を全頭印内に含めること。発走後の再計算は混ぜません。</p></section>'
}

