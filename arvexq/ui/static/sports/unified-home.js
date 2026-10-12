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

  // All scheduled races are retained. Live status updates every 10 seconds
  // in the existing venue's 1R-12R grid, not just one upcoming race.
  const jstDate=now=>new Date(now.getTime()+9*3600000).toISOString().slice(0,10);
  const cancelledStatus=status=>/cancelled|canceled|abandoned|中止|取止|取消|不成立|除外/i.test(String(status||''));
  const confirmedStatus=status=>/confirmed|final|settled|finished|completed|確定|終了/i.test(String(status||''));
  function normalizedRace(mode,r,day){
    if(!r||!r.id)return null;
    const isBoat=mode==='boat',venue=String(isBoat?r.venue:r.track||'');
    const number=Number(isBoat?r.raceNo:r.raceNumber||r.raceNo);
    if(!venue||!Number.isInteger(number)||number<1||number>12)return null;
    const circuit=isBoat?'競艇':r.circuit==='中央'?'中央':r.circuit==='地方'?'地方':'';
    if(!circuit)return null;
    const status=String(r.result?.status||r.raceStatus||r.status||'');
    const time=String(isBoat?r.closeTime:r.startTime||r.scheduledStartTime||'');
    const clock=/^([01]?\d|2[0-3]):([0-5]\d)/.exec(time);
    const stamp=isBoat?Date.parse(String(r.closeAt||'')):NaN;
    const schedule=Number.isFinite(stamp)?stamp:
      clock?Date.parse(day+'T'+clock[1].padStart(2,'0')+':'+clock[2]+':00+09:00'):NaN;
    const renderedTime=clock?clock[1].padStart(2,'0')+':'+clock[2]:
      Number.isFinite(schedule)?new Date(schedule+9*3600000).toISOString().slice(11,16):'';
    return {id:String(r.id),circuit,venue,number,title:String(r.title||''),
      time:renderedTime,timestamp:schedule,confirmed:confirmedStatus(status),
      cancelled:cancelledStatus(status)};
  }
  function raceStatus(mode,r,day,now=new Date()){
    const row=normalizedRace(mode,r,day);
    if(!row)return 'unknown';
    if(row.cancelled)return 'cancelled';
    if(row.confirmed)return 'finished';
    if(!Number.isFinite(row.timestamp))return 'unknown';
    const delta=row.timestamp-now.getTime();
    if(delta<=0)return 'elapsed'; // Clock passed; do not invent a confirmed result.
    return delta<=600000?'soon':'upcoming';
  }
  const labelFor=(status,mode)=>({
    finished:'確定',elapsed:mode==='boat'?'締切経過':'発走時刻経過',
    soon:'まもなく',upcoming:'発走前',unknown:'時刻未取得',
    cancelled:'中止'
  }[status]||'');
  function liveModel(mode,rows,day,now=new Date()){
    if(!/^(horse|boat)$/.test(mode))return [];
    const data=(Array.isArray(rows)?rows:[]).map(raw=>{
      const r=normalizedRace(mode,raw,day);
      return r?{...r,status:raceStatus(mode,raw,day,now),next:false}:null;
    }).filter(Boolean);
    const nextByVenue=new Map();
    for(const race of data){
      if(race.status!=='upcoming'&&race.status!=='soon')continue;
      const key=race.circuit+'|'+race.venue,old=nextByVenue.get(key);
      if(!old||race.timestamp<old.timestamp||
         race.timestamp===old.timestamp&&race.number<old.number)nextByVenue.set(key,race);
    }
    const ids=new Set([...nextByVenue.values()].map(x=>x.id));
    for(const r of data)r.next=ids.has(r.id);
    return data.sort((a,b)=>a.circuit.localeCompare(b.circuit,'ja')||
      a.venue.localeCompare(b.venue,'ja')||a.number-b.number);
  }
  function liveSignature(mode,rows,day,now=new Date()){
    return liveModel(mode,rows,day,now).map(r=>
      r.id+':'+r.status+(r.next?':next':'')).join('|');
  }
  function liveRaces(mode,rows,day,now=new Date()){
    const all=liveModel(mode,rows,day,now);
    const ended=all.filter(r=>r.status==='elapsed'||r.status==='finished').length;
    const active=all.filter(r=>r.status==='soon').length;
    const pending=all.filter(r=>r.next).length;
    const desc=all.length?
      '全'+all.length+'R / 時刻経過 '+ended+'R / まもなく '+active+'R / 次レース '+pending+'場':
      '開催・出走情報は未取得です';
    return '<section class="arv-realtime-section" data-live-signature="'+esc(liveSignature(mode,rows,day,now))+
      '" aria-label="リアルタイム"><header><b>リアルタイム</b><small>全会場・全レース自動更新</small></header>'+
      '<p class="arv-realtime-summary">'+esc(desc)+'</p>'+
      '<p class="arv-realtime-legend"><span>青＝次レース</span><span>金＝まもなく</span><span>暗色＝時刻経過・確定</span></p></section>';
  }
  function syncLiveUI(mode,rows,day,scope,now=new Date()){
    const rootNode=scope||root.document;
    if(!rootNode||!rootNode.querySelectorAll)return;
    const all=liveModel(mode,rows,day,now);
    const lookup=new Map(all.map(r=>[r.id,r]));
    for(const el of rootNode.querySelectorAll('button.arv-all-race[data-race]')){
      const r=lookup.get(el.getAttribute('data-race'));
      if(!r)continue;
      const code=r.status;
      for(const cls of ['elapsed','finished','soon','upcoming','future','pending','next'])
        el.classList.toggle(cls,cls===code||cls==='next'&&r.next);
      el.setAttribute('data-race-state',code);
      const stateLabel=el.querySelector('.arv-race-state');
      if(stateLabel)stateLabel.textContent=labelFor(code,mode);
    }
    const section=rootNode.querySelector('.arv-realtime-section');
    if(section){
      const signature=liveSignature(mode,rows,day,now);
      if(section.getAttribute('data-live-signature')!==signature){
        section.outerHTML=liveRaces(mode,rows,day,now);
      }
    }
  }
  root.ARVEXQUnifiedHome=Object.freeze({hero,dateBar,buttons,liveModel,liveSignature,liveRaces,raceStatus,labelFor,syncLiveUI});
})(typeof window!=='undefined'?window:globalThis);
