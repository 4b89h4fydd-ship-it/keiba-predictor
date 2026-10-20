function paceStructureSection(r,p){
  var ctx=p&&p.minetaContext;if(!ctx)return'';
  var lead=(ctx.leadNos||[]).join('・')||'—',label=ctx.band==='前少なめ'?'前が少ない構成':(ctx.band==='前多め'?'先行争いが濃い構成':'中間の構成');
  return '<section class="ai-stage-event" style="margin:10px 0;padding:11px 13px;border:1px solid rgba(120,170,255,.22);border-radius:12px;background:rgba(8,18,36,.45)">'
    +'<div style="font-size:15px;font-weight:900;color:#8de9ff">'+esc(label)+'</div>'
    +'<div style="margin-top:7px;font-size:14px;line-height:1.75">先行占有 '+Math.round(ctx.rawOcc*100)+'%　/　距離補正後 '+Math.round(ctx.adjustedOcc*100)+'%　/　後方占有 '+Math.round(ctx.rearOcc*100)+'%　/　ハナ候補 '+esc(lead)+'</div>'
    +'<div class="muted" style="margin-top:6px;font-size:13px;line-height:1.65">'+esc(minetaStructureText(ctx))+'</div></section>'
}
