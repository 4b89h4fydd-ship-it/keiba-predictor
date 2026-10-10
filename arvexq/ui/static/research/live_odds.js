/* Independent official odds transport. Never recalculates a saved forecast. */
(function(root){
  'use strict';
  var pending=Object.create(null);
  function normalize(body,id){
    if(!body||body.ok!==true||String(body.race_id)!==String(id)||!Array.isArray(body.odds))
      throw Error('odds unavailable or race identity mismatch');
    var seen=Object.create(null),latest=0;
    var horses=body.odds.map(function(z){
      var no=Number(z.horseNumber!=null?z.horseNumber:z.horse_no);
      if(!Number.isInteger(no)||no<1||seen[no])throw Error('invalid odds runner');
      seen[no]=true;
      var stamp=z.updatedAt!=null?z.updatedAt:z.updated_at;
      var at=Number(stamp);if(!Number.isFinite(at))at=Date.parse(String(stamp||''))/1000;
      if(at>1e12)at/=1000;
      if(Number.isFinite(at)&&at>0)latest=Math.max(latest,at);
      var value=z.winOdds!=null?z.winOdds:z.win_odds,pop=Number(z.popularity);
      return {horseNumber:no,winOdds:Number(value)>0?Number(value):null,
        popularity:Number.isInteger(pop)&&pop>0?pop:null,
        bodyWeight:z.bodyWeight!=null?z.bodyWeight:z.body_weight,
        bodyWeightChange:z.bodyWeightChange!=null?z.bodyWeightChange:z.body_weight_change,
        status:z.status!=null?z.status:z.horse_status,
        scratched:z.scratched===true||z.withdrawn===true,
        oddsSource:body.oddsSource||z.oddsSource||'official-api',oddsForecast:false};
    });
    return {horses:horses,oddsSource:body.oddsSource||'official-api',
      oddsUpdatedAt:latest?new Date(latest*1000).toISOString():body.oddsUpdatedAt||''};
  }
  function fetch(id,fetchJson){
    var key=String(id||'');if(!key)return Promise.reject(Error('race id required'));
    if(!pending[key])pending[key]=Promise.resolve().then(function(){
      return fetchJson('https://kraiz-api.4b89h4fydd.workers.dev/api/odds/'+encodeURIComponent(key)+'?t='+Date.now(),6500);
    }).then(function(body){return normalize(body,key)}).finally(function(){delete pending[key]});
    return pending[key];
  }
  function status(r){
    var at=Number(r&&r.oddsUpdatedAt),raw=r&&r.oddsUpdatedAt;
    if(at>0)at=at>1e12?at:at*1000;else at=Date.parse(String(raw||''));
    return Number.isFinite(at)&&at>0?'オッズ取得 '+new Date(at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false}):'オッズ取得時刻 未取得';
  }
  root.ARVEXQLiveOdds=Object.freeze({fetch:fetch,normalize:normalize,status:status});
})(typeof window!=='undefined'?window:globalThis);
