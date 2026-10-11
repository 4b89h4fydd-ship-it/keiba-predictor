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
    var known=new Map(card.horses.map(function(h){return [Number(h.horseNumber),{name:name(h.name),rawName:h.name}]}));
    if(out.result&&Array.isArray(out.result.finishers)){
      var original=out.result.finishers,verified=[],invalid=0;
      original.forEach(function(h){
        if(!h||!Number.isInteger(Number(h.horseNumber))){invalid++;return}
        var expected=known.get(Number(h.horseNumber));
        if(!expected){invalid++;return}
        // Official result sources sometimes leave the finisher name empty.
        // A matching horse number can inherit the verified card identity;
        // a nonempty conflicting name must NEVER overwrite that identity.
        var observed=name(h.name);
        if(observed&&observed!==expected.name){invalid++;return}
        verified.push(observed?h:Object.assign({},h,{name:expected.rawName}))
      });
      if(invalid){
        out._resultIdentityError=true;
        if(!verified.length&&original.length){
          // Refuse an entirely foreign result, preserving the old guard.
          delete out.result;
        }else{
          // A single missing/mismatched finisher must not erase the
          // other authoritative placings or payout records.
          out.result=Object.assign({},out.result,{finishers:verified})
        }
      }else if(verified.some(function(h,i){return h!==original[i]})){
        out.result=Object.assign({},out.result,{finishers:verified})
      }
    }
    return out;
  }
  root.ARVEXQRaceIdentity=Object.freeze({remember:remember,sanitize:sanitize});
})(typeof window!=='undefined'?window:globalThis);
