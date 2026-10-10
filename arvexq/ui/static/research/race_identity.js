/* Keep mismatched live/result rows out of a verified factual roster. */
(function(root){
  'use strict';
  var rosters=Object.create(null);
  var name=function(v){return String(v||'').replace(/\s+/g,'').trim()};
  function remember(r){
    if(!r||!r.id||!r.date||!Array.isArray(r.horses)||r.horses.length<2)return;
    rosters[r.id]={date:r.date,horses:r.horses.map(function(h){return {horseNumber:h.horseNumber,name:h.name,
      frameNumber:h.frameNumber,sex:h.sex,age:h.age,jockey:h.jockey,carriedWeight:h.carriedWeight,
      scratched:h.scratched,status:h.status}})};
  }
  function sanitize(r){
    if(!r)return r;
    var card=rosters[r.id];if(!card||card.date!==r.date)return r;
    var by={},changed=false;
    (r.horses||[]).forEach(function(h){by[h.horseNumber]=h});
    var horses=card.horses.map(function(h){
      var live=by[h.horseNumber];
      if(!live||name(live.name)!==name(h.name)){changed=true;return Object.assign({},h)}
      return live;
    });
    if((r.horses||[]).length!==horses.length)changed=true;
    var out=Object.assign({},r,{horses:horses,fieldSize:horses.length});
    if(changed)out._rosterIdentityError=true;
    var known=new Map(card.horses.map(function(h){return [h.horseNumber,name(h.name)]}));
    if(out.result&&Array.isArray(out.result.finishers)&&out.result.finishers.some(function(h){
      return !known.has(Number(h.horseNumber))||!h.name||known.get(Number(h.horseNumber))!==name(h.name);
    })){
      delete out.result;out._resultIdentityError=true;
    }
    return out;
  }
  root.ARVEXQRaceIdentity=Object.freeze({remember:remember,sanitize:sanitize});
})(typeof window!=='undefined'?window:globalThis);
