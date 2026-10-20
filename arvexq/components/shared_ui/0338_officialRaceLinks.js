function officialRaceLinks(r){
  var central=String((r&&r.circuit)||state.circuit||'')==='中央';
  return central?{
    live:'https://www.jra.go.jp/tvradio/racelive/',
    vote:'https://www.ipat.jra.go.jp/sp/',
    liveLabel:'JRA LIVE',voteLabel:'JRA 投票'
  }:{
    live:'https://www.keiba.go.jp/live/index.html',
    vote:'https://www.spat4.jp/keiba/pc',
    liveLabel:'地方 LIVE',voteLabel:'SPAT4 投票'
  }
}
