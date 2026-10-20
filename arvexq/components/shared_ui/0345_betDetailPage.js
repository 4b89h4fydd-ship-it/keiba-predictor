function betDetailPage(r,p){
  return '<div class="smart-shell bet-detail-page-shell">'+raceSubpageTopBar(r,'おすすめ買い目')
    +'<main class="smart-main smart-race-page"><section class="card bet-card-clean">'+aiBetRecommendation(r,p)+'</section></main>'
    +cinematicFooter()+'</div>'
}
