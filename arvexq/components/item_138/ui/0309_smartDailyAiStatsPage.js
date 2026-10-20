function smartDailyAiStatsPage(){
  var s=dailyAiStats;if(s.date!==state.date)resetDailyAiStats(state.date),s=dailyAiStats;
  if(!s.done&&!s.loading)setTimeout(scheduleDailyAiStats,0);
  if(state.aiStatsTrack){
    var rows=(s.rows||[]).filter(function(x){return String(x.track||'')===String(state.aiStatsTrack||'')});
    return '<div class="smart-shell">'+smartTopBar(true,state.aiStatsTrack+' AI成績','発走前の保存予想のみ')+'<main class="smart-main smart-home-subpage"><section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(state.aiStatsTrack)+'</b><small>集計対象 '+rows.filter(function(x){return x.eligible}).length+' / '+rows.length+'レース</small></div>'+aiStatsMetrics(rows)+'<div class="smart-ai-race-list">'+(rows.length?rows.map(aiStatsRaceRow).join(''):'<div class="smart-empty">確定レースを集計中です</div>')+'</div></section></main>'+cinematicFooter()+'</div>'
  }
  if(s.loading&&!s.rows.length)return '<div class="smart-shell">'+smartTopBar(true,'本日のAI成績','保存済み予想を照合')+'<main class="smart-main smart-home-subpage"><div class="smart-loading"><span class="smart-loading-dot"></span><b>AI成績を集計中</b></div></main>'+cinematicFooter()+'</div>';
  var groups={},keys=[];
  (s.rows||[]).forEach(function(x){var k=String(x.circuit||'')+'|'+String(x.track||'');if(!groups[k]){groups[k]={circuit:x.circuit||'',track:x.track||'',rows:[]};keys.push(k)}groups[k].rows.push(x)});
  keys.sort(function(a,b){var x=groups[a],y=groups[b],c=String(x.circuit).localeCompare(String(y.circuit),'ja');return c||String(x.track).localeCompare(String(y.track),'ja')});
  var venues=keys.map(function(k){var g=groups[k],eligible=g.rows.filter(function(x){return x.eligible}),hits=eligible.filter(function(x){return x.honPlaceHit}).length;return '<button type="button" class="arv-ai-venue-card" data-ai-stats-track="'+esc(g.track)+'"><span><small>'+esc(g.circuit)+'</small><b>'+esc(g.track)+'</b></span><em>◎3着内 '+hits+'/'+eligible.length+'（対象 '+eligible.length+'R）</em><strong>›</strong></button>'}).join('');
  return '<div class="smart-shell">'+smartTopBar(true,'本日のAI成績','発走前固定の予想だけ')+'<main class="smart-main smart-home-subpage"><section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>全レースAI成績</b><small>集計対象 '+s.total+' / 確定 '+s.finalCount+'レース</small></div>'+aiStatsMetrics(s.rows||[])+'<p class="muted">結果未取得・発走前予想未保存は分母から除外。3連単は発走前に3連単買い目を保存したレースだけが対象です。</p></section><section class="arv-ai-venues"><div class="smart-section-title"><div><b>開催場ごとのAI成績</b><small>開催場を押すと各レースへ</small></div></div>'+(venues||'<div class="smart-empty">確定レースを集計中です</div>')+'</section></main>'+cinematicFooter()+'</div>'
}
// Shared by the horse-only home and the selected/special subpages.
