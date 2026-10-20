function betItemHit(item,order){
  if(!item||!order||!order.length)return false;var t=order.slice(0,3).map(n);
  return (item.combos||[]).some(function(c){var a=(c||[]).map(n);if(item.kind==='単勝')return t[0]===a[0];if(item.kind==='馬単')return t[0]===a[0]&&t[1]===a[1];if(item.kind==='馬連')return a.length===2&&a.slice().sort().join('-')===t.slice(0,2).sort().join('-');if(item.kind==='ワイド')return a.length===2&&t.slice(0,3).indexOf(a[0])>=0&&t.slice(0,3).indexOf(a[1])>=0;if(item.kind==='3連複')return a.length===3&&a.slice().sort().join('-')===t.slice(0,3).sort().join('-');if(item.kind==='3連単')return a.length===3&&a[0]===t[0]&&a[1]===t[1]&&a[2]===t[2];return false})
}
