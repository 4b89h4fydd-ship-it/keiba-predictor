/* Lossless/factual roster fallback from publicly deployed static racecards.
 * Never supplies bets, official odds, marks, results, or training evidence.
 * API detail always wins when healthy. One dated JSON fetch per view.
 */
(function(root){
  "use strict";
  var jobs=Object.create(null);
  function validDay(value){return /^\d{4}-\d{2}-\d{2}$/.test(String(value||''))}
  function available(date,id,fetchJson){
    if(!validDay(date)||!String(id||''))return Promise.resolve(null);
    var key=String(date);
    if(!jobs[key]){
      var url='/racecards/'+encodeURIComponent(key)+'.json';
      jobs[key]=Promise.resolve().then(function(){return fetchJson(url)}).then(function(data){
        if(!data||data.version!=='arvexq-static-entry-v1'||data.date!==key||
           !Array.isArray(data.races))throw Error('static racecard archive unavailable');
        return data;
      }).catch(function(){delete jobs[key];return null});
    }
    return jobs[key].then(function(data){
      if(!data)return null;
      var d=data.races.find(function(x){return x&&String(x.id)===String(id) && x.date===key});
      if(!d||!Array.isArray(d.horses)||d.horses.length<2)return null;
      var seen=Object.create(null);
      for(var i=0;i<d.horses.length;i++){
        var h=d.horses[i]||{},no=Number(h.horseNumber),name=String(h.name||'').trim();
        if(!(no>0)||!Number.isInteger(no)||!name||seen[no])return null;
        seen[no]=1;
      }
      if(Number(d.fieldSize||0)>d.horses.length)return null;
      return Object.assign({},d,{_entryOnly:true,_staticRacecardFallback:true});
    });
  }
  root.ARVEXQStaticRacecard={available:available};
})(typeof window!=='undefined'?window:globalThis);
