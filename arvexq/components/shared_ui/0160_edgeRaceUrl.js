function edgeRaceUrl(id){
  return 'https://kraiz-api.4b89h4fydd.workers.dev/api/race/'
    +encodeURIComponent(id)
    +'?view=display&t='+Date.now()
}

// v240 data-integrity merge. D1 /api/race returns the saved detail and a separate
// odds_current array. Older clients ignored the separate live rows and could also
// let a sparse incoming snapshot overwrite a richer cached one. Keep the richest
// horse/history/diagnosis data while allowing newer live fields to win.
