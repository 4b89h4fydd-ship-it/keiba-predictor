function mergePublishedResult(oldResult,newResult){
  var prev=oldResult&&typeof oldResult==='object'?oldResult:{},
      next=newResult&&typeof newResult==='object'?newResult:{};
  if(!reflectUseful(next))return prev;
  var out=Object.assign({},prev),
      priorFinal=String(prev.status||'')==='確定',newFinal=String(next.status||'')==='確定';
  Object.keys(next).forEach(function(k){
    if(k==='status'||k==='finishers'||k==='payouts')return;
    if(reflectUseful(next[k]))out[k]=next[k]
  });
  var oldFs=Array.isArray(prev.finishers)?prev.finishers:[],
      freshFs=Array.isArray(next.finishers)?next.finishers:[],
      oldRanked=oldFs.filter(function(x){return x&&n(x.finish)>0}).length,
      newRanked=freshFs.filter(function(x){return x&&n(x.finish)>0}).length;
  if(freshFs.length&&(newRanked>=oldRanked)&&(!priorFinal||newFinal)){
    var oldBy={};
    oldFs.forEach(function(x){if(x&&n(x.horseNumber)>0)oldBy[n(x.horseNumber)]=x});
    out.finishers=freshFs.map(function(x){
      var merged=Object.assign({},oldBy[n(x&&x.horseNumber)]||{});
      Object.keys(x||{}).forEach(function(k){if(reflectUseful(x[k]))merged[k]=x[k]});
      return merged
    });
  }
  if(Array.isArray(next.payouts)&&next.payouts.length){
    var oldPay=Array.isArray(prev.payouts)?prev.payouts:[];
    if(next.payouts.length>=oldPay.length)out.payouts=next.payouts
  }
  if(newFinal)out.status='確定';
  else if(!priorFinal&&reflectUseful(next.status))out.status=next.status;
  return out
}
