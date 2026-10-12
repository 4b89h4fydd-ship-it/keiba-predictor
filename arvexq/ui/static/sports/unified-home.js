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

  // Shared real-time race selector. Uses scheduled start/close, never invents
  // confirmation that a race is running or has finished.
  const jstDate=now=>new Date(now.getTime()+9*3600000).toISOString().slice(0,10);
  function normalizedRace(mode,r,day){
    if(!r||!r.id)return null;
    const isBoat=mode==='boat',venue=String(isBoat?r.venue:r.track||'');
    const number=Number(isBoat?r.raceNo:r.raceNumber||r.raceNo);
    if(!venue||!Number.isInteger(number)||number<1||number>12)return null;
    const circuit=isBoat?'競艇':r.circuit==='中央'?'中央':r.circuit==='地方'?'地方':'';
    if(!circuit)return null;
    const status=String(r.result?.status||r.raceStatus||r.status||'');
    if(/cancelled|canceled|abandoned|中止|取止|取消|不成立/i.test(status))return null;
    const time=String(isBoat?r.closeTime:r.startTime||r.scheduledStartTime||'');
    const clock=/^([01]?\d|2[0-3]):([0-5]\d)/.exec(time);
    const stamp=isBoat?Date.parse(String(r.closeAt||'')):NaN;
    const schedule=Number.isFinite(stamp)?stamp:
      clock?Date.parse(day+'T'+clock[1].padStart(2,'0')+':'+clock[2]+':00+09:00'):NaN;
    if(!Number.isFinite(schedule))return null;
    return {id:String(r.id),circuit,venue,number,
      title:String(r.title||''),time:clock?clock[1].padStart(2,'0')+':'+clock[2]:
        new Date(schedule+9*3600000).toISOString().slice(11,16),
      timestamp:schedule};
  }
  function liveModel(mode,rows,day,now=new Date()){
    if(!/^(horse|boat)$/.test(mode)||day!==jstDate(now))return [];
    const current=now.getTime(),groups=new Map();
    for(const raw of Array.isArray(rows)?rows:[]){
      const r=normalizedRace(mode,raw,day);
      if(!r||r.timestamp<current)continue; // Advance to the NEXT race immediately.
      const key=r.circuit+'|'+r.venue;
      const old=groups.get(key);
      if(!old||r.timestamp<old.timestamp||
           r.timestamp===old.timestamp&&r.number<old.number)groups.set(key,r);
    }
    return [...groups.values()].sort((a,b)=>
      a.circuit.localeCompare(b.circuit,'ja')||a.timestamp-b.timestamp||
      a.venue.localeCompare(b.venue,'ja'));
  }
  function liveSignature(mode,rows,day,now=new Date()){
    return liveModel(mode,rows,day,now).map(r=>
      r.id+':'+Math.max(0,Math.ceil((r.timestamp-now.getTime())/60000))).join('|');
  }
  function liveRaces(mode,rows,day,now=new Date()){
    const selected=liveModel(mode,rows,day,now);
    const current=day===jstDate(now),title='リアルタイム';
    const html=selected.map(r=>{
      const left=Math.max(0,Math.ceil((r.timestamp-now.getTime())/60000));
      const status=left<=10?'まもなく':'あと'+left+'分';
      return '<button type="button" class="arv-realtime-race'+(left<=10?' soon':'')+
        '" data-race="'+esc(r.id)+'" aria-label="'+esc(r.venue+' '+r.number+'R '+r.time)+'">'+
        '<span class="arv-realtime-venue">'+esc(r.circuit==='競艇'?'':r.circuit+' ') +esc(r.venue)+'</span>'+
        '<b>'+r.number+'R</b><span class="arv-realtime-clock">'+esc(r.time)+'</span>'+
        '<small>'+esc(status)+'</small></button>';
    }).join('');
    const caption=selected.length?'各会場の次レースへ自動切替':'';
    const empty=!current?'当日分のみ表示します':
      Array.isArray(rows)&&rows.length?'本日の次レースはありません':'開催データはまだ未取得です';
    return '<section class="arv-realtime-section" data-live-signature="'+esc(liveSignature(mode,rows,day,now))+
      '" aria-label="'+title+'"><header><b>'+title+'</b><small>'+caption+'</small></header>'+
      (selected.length?'<div class="arv-realtime-grid">'+html+'</div>':
        '<p class="arv-realtime-empty">'+empty+'</p>')+'</section>';
  }
  root.ARVEXQUnifiedHome=Object.freeze({hero,dateBar,buttons,liveModel,liveSignature,liveRaces});
})(typeof window!=='undefined'?window:globalThis);
