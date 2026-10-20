function morningPickReady(){
  return (state.races||[]).some(function(r){return !!morningPickOf(r)})
}
