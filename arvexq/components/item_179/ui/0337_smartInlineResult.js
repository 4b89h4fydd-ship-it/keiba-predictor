function smartInlineResult(r){
  var final=isFinal(r),flash=isFlash(r),any=hasAnyResultData(r),ready=hasResultData(r),f=((r.result||{}).finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)}).slice(0,3),nums=ready&&f.length?f.map(function(x){return n(x.horseNumber)}).join(' - '):'';
  return '<button type="button" class="smart-inline-result '+(final?'final':(flash?'flash':''))+'" data-panel="result"><span>レース結果</span><strong>'+(final?(ready?'確定':'着順未取得'):(flash?(any?'速報':'速報待ち'):(String(r.date||'')<today()?'結果未取得':'未確定')))+'</strong></button>'
}
