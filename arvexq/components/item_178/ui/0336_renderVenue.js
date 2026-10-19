function renderVenue(){
  var hi=venueHeaderInfo();
  return '<div class="smart-shell smart-venue-page">'+
    venueTopBar(hi)+
    '<main class="smart-main">'+
      (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
      venueRaceRows()+
    '</main>'+ 
    cinematicFooter()+
  '</div>'
}
