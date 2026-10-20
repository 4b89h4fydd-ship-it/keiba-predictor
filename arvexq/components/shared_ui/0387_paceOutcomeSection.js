function paceOutcomeSection(r,p){
  var o=paceOutcomeModel(r,p);if(!o)return'';
  var winner=o.winner?rowName(o.winner):'—',lead=o.leader?rowName(o.leader):'—';
  return '<div class="ai-stage-event" style="margin:10px 0 12px;padding:12px;border:1px solid rgba(120,170,255,.32);border-radius:12px;background:rgba(8,18,36,.68)">'
    +'<div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><b style="font-size:15px">展開結論：'+esc(o.verdict)+'</b><span class="muted">'+esc(o.day&&o.day.active?o.day.flowLabel:'バイアス中立')+'</span></div>'
    +'<div style="margin-top:7px;font-size:13px;line-height:1.6">逃げ想定 <b>'+esc(lead)+'</b>　→　勝ち切り本線 <b>'+esc(winner)+'</b></div>'
    +'<div style="margin-top:8px;font-size:16px;font-weight:800;letter-spacing:.02em">'+esc(paceOutcomeNums(o.first))+' → '+esc(paceOutcomeNums(o.second))+' → '+esc(paceOutcomeNums(o.third))+'</div>'
    +'<div class="muted" style="margin-top:7px;line-height:1.55">'+esc(o.reason)+'</div>'
    
    +'</div>'
}
