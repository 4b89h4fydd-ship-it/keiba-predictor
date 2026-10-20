function fetchRacecardOnly(id){
  var url='https://kraiz-api.4b89h4fydd.workers.dev/api/racecard/'+encodeURIComponent(id)+'?t='+Date.now();
  traceRaceDetail(id,'racecard-request',{url:url});
  return edgeFetchJson(url,6500).then(function(body){
    var d=body&&body.detail;
    if(!body||!body.ok||!d||String(d.id)!==String(id))throw Error('racecard unavailable or id mismatch');
    if(!entryDataAvailable(d)&&!(body.entry_state==='empty'&&Number(d.fieldSize)===0))throw Error('racecard incomplete');
    d=Object.assign({},d,{_entryOnly:true});return d
  }).catch(function(error){
    traceRaceDetail(id,'racecard-failed',{url:url,message:String(error&&error.message||error)});
    var loader=window.ARVEXQStaticRacecard;
    if(!loader||typeof loader.available!=='function')return null;
    var summary=(state.races||[]).find(function(r){return String(r&&r.id||'')===String(id)})||state.race||{},
        date=String(summary.date||state.date||'');
    return loader.available(date,id,function(path){return edgeFetchJson(path,6500)}).then(function(card){
      if(card)traceRaceDetail(id,'racecard-static-backup',{date:date,horses:(card.horses||[]).length});
      return card
    }).catch(function(){return null})
  })
}
