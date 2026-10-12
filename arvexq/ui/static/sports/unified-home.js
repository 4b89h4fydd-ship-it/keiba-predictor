/* Shared home shell. Keep racing page behavior independent from the original prediction code. */
(function(root){
  'use strict';
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function hero(){
    return '<div class="arv-unified-hero">'+
      '<img src="/sports/arvexq-unified-hero.webp?v=20261012-hq1536" alt="ARVEXQ｜競馬・競艇 AI" width="1536" height="864" decoding="async" fetchpriority="high" '+
      'onerror="this.onerror=null;this.src=\'/arvexq-racing-hero.webp\'"></div>';
  }
  function dateBar(iso){
    const value=/^\d{4}-\d{2}-\d{2}$/.test(String(iso||''))?iso:'';
    return '<label class="arv-unified-date" title="日付を選択"><span>'+esc(value.replace(/-/g,'/'))+
      '</span><input id="date" type="date" value="'+esc(value)+'" aria-label="開催日を選択"></label>';
  }
  function buttons(mode){
    const horse=mode==='horse';
    const selected=horse?'data-home-page="selected"':'data-view="selected"';
    const special=horse?'data-home-page="special"':'data-view="special"';
    const stats=horse?'data-home-page="ai-stats"':'data-view="stats"';
    const button=(key,icon,text,attr)=>'<button type="button" class="arv-unified-action" data-action-kind="'+key+'" '+attr+'>'+
      '<span class="arv-unified-action-icon" aria-hidden="true">'+icon+'</span>'+
      '<span class="arv-unified-action-label">'+text+'</span><span aria-hidden="true">›</span></button>';
    return '<nav class="arv-unified-actions" aria-label="予想メニュー">'+
      button('selected','♛','厳選',selected)+button('special','♕','特別',special)+
      button('stats','▣','AI成績',stats)+'</nav>';
  }
  root.ARVEXQUnifiedHome=Object.freeze({hero,dateBar,buttons});
})(typeof window!=='undefined'?window:globalThis);
