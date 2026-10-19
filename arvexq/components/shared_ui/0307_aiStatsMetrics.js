function aiStatsMetrics(rows){
  return '<div class="smart-ai-daily-grid arv-ai-metrics">'
    +aiStatsCell('◎3着以内',rows,'honPlaceHit',function(x){return x.honEligible})
    +aiStatsCell('◎1着',rows,'winHit',function(x){return x.honEligible})
    +aiStatsCell('印内1着',rows,'markHit')
    +aiStatsCell('印内3頭完全包含',rows,'fullPodiumHit')
    +aiStatsCell('3連単的中',rows,'triHit',function(x){return x.triEligible})
    +'</div>'
}
