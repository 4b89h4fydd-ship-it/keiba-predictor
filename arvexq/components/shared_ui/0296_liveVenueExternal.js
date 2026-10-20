function liveVenueExternal(circuit,track){
  if(String(circuit||'')==='中央')return 'https://www.youtube.com/@jraofficial/live';
  var slug=ARVEXQ_LOCAL_LIVE_SLUG[String(track||'')]||'';
  return slug?'https://simple.keiba-lv-st.jp/?track='+encodeURIComponent(slug):'https://simple.keiba-lv-st.jp/'
}
