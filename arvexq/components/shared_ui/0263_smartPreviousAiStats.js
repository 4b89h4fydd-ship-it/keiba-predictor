function smartPreviousAiStats(){
  var s=previousAiStats,date=s.date||previousDateKey(today()),p=String(date||'').split('-'),label=(n(p[1])&&n(p[2]))?(n(p[1])+'月'+n(p[2])+'日'):'前日';
  if(!s.done&&!s.loading){setTimeout(schedulePreviousAiStats,0);return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日のAI成績</b><small>全レース集計準備中</small></div></section>'}
  if(s.loading)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>前日の全レースを集計中…</small></div></section>';
  if(s.error)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>'+esc(s.error)+'</small></div></section>';
  if(!s.total)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>前日のレースデータなし</small></div></section>';
  function rate(hit){return Math.round(hit/s.total*100)}
  function markText(row){var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};var txt=(row.marks||[]).slice().sort(function(a,b){return n(order[a.mark],99)-n(order[b.mark],99)||n(a.no)-n(b.no)}).map(function(x){return x.mark+x.no}).join(' ');return txt||'印なし'}
  var rows=(s.rows||[]).map(function(x){
    var result=(x.podiumNos||[]).slice(0,3).join('-')||'—',cls=x.fullPodiumHit?'hit':(x.markHit?'partial':'miss'),judge;
    if(x.loadError)judge='詳細取得失敗';
    else if(!x.resultReady)judge='結果未取得';
    else if(!x.hasMarks)judge='印なし';
    else judge=x.fullPodiumHit?'3頭完全':(x.markHit?'1着印内':'1着印外');
    return '<div class="smart-ai-race-row '+cls+'"><span class="smart-ai-race-name"><b>'+esc(x.track)+' '+esc(x.raceNumber)+'R</b><small>'+esc(x.title||'')+'</small></span><span class="smart-ai-race-marks">'+esc(markText(x))+'</span><span class="smart-ai-race-result">結果 '+esc(result)+'</span><strong>'+esc(judge)+'</strong></div>'
  }).join('');
  return '<section class="smart-ai-daily smart-ai-previous"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>前日の全'+s.total+'レース</small></div><div class="smart-ai-daily-grid">'+
    '<div><small>AI印内1着</small><strong>'+rate(s.markHits)+'%</strong><em>'+s.markHits+'/'+s.total+'</em></div>'+
    '<div><small>◎1着</small><strong>'+rate(s.winHits)+'%</strong><em>'+s.winHits+'/'+s.total+'</em></div>'+
    '<div><small>印内3頭完全</small><strong>'+rate(s.fullPodiumHits)+'%</strong><em>'+s.fullPodiumHits+'/'+s.total+'</em></div>'+
  '</div><div class="smart-ai-race-list">'+rows+'</div><p>※分母は前日の全レース。事前AI印が無いレースも除外せず「印なし」として表示します。</p></section>'
}
