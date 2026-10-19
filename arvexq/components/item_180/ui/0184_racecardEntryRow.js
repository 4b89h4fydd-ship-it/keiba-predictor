function racecardEntryRow(r,h,x){
  var scratch=isScratchHorse(h),no=n(h.horseNumber),name=horseDisplayName(r,h),
      fr=clamp(n(h.frameNumber,no),1,8),curBw=currentBodyWeight(h),
      deltaValue=currentBodyWeightChange(h),pastBw=!curBw?referenceBodyWeight(h):0,
      weightMain=scratch?'—':(curBw?String(curBw):(pastBw?('前'+pastBw):'—')),
      weightDelta=(!scratch&&curBw&&deltaValue!=null)?('('+(deltaValue>0?'+':'')+deltaValue+')'):'',
      weightHint=curBw?'馬体重':(pastBw?'前走馬体重':'馬体重未計量'),
      disabled=scratch?' disabled aria-disabled="true"':'',
      openAttr=scratch?'':(' data-horse-open="'+esc(no)+'"'),
      detailLabel=' aria-label="'+esc(name)+'の詳細を開く"';
  return '<div class="racecard-row rc-racecard-v336 rc-racecard-v339'+(scratch?' scratched':'')+'" '+(scratch?'aria-disabled="true"':'')+'>'
    +'<div class="rc-v336-mark"><span class="rc-mark-box rc-ai-mark" data-ai-mark="'+esc(visiblePredictionMark(x))+'" aria-label="'+esc(String(visiblePredictionMark(x)||'—').replace(/\+/g,'＋')+(markRoleLabel(x)?'、'+honmeiA11yText(x):'')+(x&&x.singleWinSuitable&&!scratch?'、単勝向き':''))+'"><span class="rc-mark-main">'+racecardMarkDisplay(visiblePredictionMark(x))+'</span>'+(markRoleLabel(x)?'<small style="display:block;font-size:9px">'+esc(markRoleLabel(x))+'</small>':'')+(x&&x.singleWinSuitable&&!scratch&&x.predMark!=='◎'?'<span class="rc-single-tip" title="単勝向き（1着狙い）" aria-hidden="true">単</span>':'')+'</span></div>'
    +'<button type="button" class="rc-v336-number"'+openAttr+detailLabel+disabled+'><span class="rc-number frame'+fr+'">'+esc(no)+'</span></button>'
    +'<div class="rc-v336-info"><button type="button" class="rc-horse-main"'+openAttr+detailLabel+disabled+'>'
      +'<span class="rc-horse-name">'+'<span class="rc-horse-title">'+esc(name)+'</span>'+(markRoleLabel(x)&&!scratch?' <small class="rc-honmei-role">'+markRoleLabel(x).replace('◎ 本命','<span class="arv-role-win arv-role-axis">◎ 本命</span>').replace('保存印：◎（旧単勝）','<span class="arv-role-win">保存印：◎（旧単勝）</span>').replace('保存印：◎（旧軸）','<span class="arv-role-axis">保存印：◎（旧軸）</span>')+'</small>':'')+'</span>'
      +'<span class="rc-v336-meta"><span class="rc-sexage">'+esc(h.sex||'—')+esc(h.age||'—')+'</span>'
      +'<span class="carry">'+esc(carriedWeightText(h))+'</span><span class="jockey">'+esc(h.jockey||'—')+'</span></span>'
    +'</button></div>'
    +'<div class="rc-v339-weight'+(curBw?'':' pending')+'" aria-label="'+esc(weightHint)+'">'
      +'<b>'+esc(weightMain)+'</b><span class="rc-weight-delta">'+esc(weightDelta||'　')+'</span>'
    +'</div>'
    +'<div class="rc-v336-odds rc-odds" data-odds-no="'+esc(no)+'">'+racecardOddsHtml(h,r)+'</div>'
    +'</div>';
}
