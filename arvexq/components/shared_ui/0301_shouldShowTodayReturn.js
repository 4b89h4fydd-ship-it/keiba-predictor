function shouldShowTodayReturn(){
  var d=state.race&&state.race.date?String(state.race.date):String(state.date||'');
  return !!d&&d!==today()
}
