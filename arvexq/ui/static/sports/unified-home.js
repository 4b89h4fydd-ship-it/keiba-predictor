/* ARVEXQ horse-only home and venue-level live race states. */
(function(root){
'use strict';
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function hero(){return '<div class="arv-unified-hero"><img src="/arvexq-racing-hero.webp?v=horse-v361" alt="ARVEXQ 競馬AI" width="1536" height="864" decoding="async" fetchpriority="high"></div>'}
function dateBar(iso){const value=/^\d{4}-\d{2}-\d{2}$/.test(String(iso||''))?iso:'';return '<label class="arv-unified-date" title="日付を選択"><span>'+esc(value.replace(/-/g,'/'))+'</span><input id="date" type="date" value="'+esc(value)+'" aria-label="開催日を選択"></label>'}
function buttons(){const btn=(key,symbol,title,view)=>'<button type="button" class="arv-unified-action" data-action-kind="'+key+'" data-home-page="'+view+'"><span class="arv-unified-action-icon" aria-hidden="true">'+symbol+'</span><span class="arv-unified-action-label">'+title+'</span>'+((key==='selected'||key==='special')?'<span class="arv-unified-alert" aria-hidden="true">!</span>':'')+'<span class="arv-unified-chevron" aria-hidden="true">›</span></button>';return '<nav class="arv-unified-actions" aria-label="予想メニュー">'+btn('selected','♛','厳選','selected')+btn('special','♕','特別','special')+btn('stats','▣','AI成績','ai-stats')+btn('favorites','★','お気に入り','favorites')+'</nav>'}
function normalizedRace(_mode,r,day){
 if(!r||!r.id||!r.track||!['中央','地方'].includes(r.circuit))return null;
 const number=Number(r.raceNumber||r.raceNo);if(!Number.isInteger(number)||number<1||number>12)return null;
 const status=String(r.result?.status||r.raceStatus||r.status||'');
 const clock=/^([01]?\d|2[0-3]):([0-5]\d)/.exec(String(r.startTime||r.scheduledStartTime||''));
 const timestamp=clock&&/^\d{4}-\d{2}-\d{2}$/.test(String(day||''))?Date.parse(day+'T'+clock[1].padStart(2,'0')+':'+clock[2]+':00+09:00'):NaN;
 return {id:String(r.id),circuit:r.circuit,venue:String(r.track),number,timestamp,
   cancelled:/cancelled|canceled|abandoned|中止|取止|取消|不成立|除外/i.test(status),
   confirmed:/confirmed|final|settled|finished|completed|確定|速報|終了/i.test(status),
   running:/running|started|発走中|進行中/i.test(status)};
}
function raceStatus(mode,r,day,now=new Date()){const x=normalizedRace(mode,r,day);if(!x)return 'unknown';if(x.cancelled)return 'cancelled';if(x.confirmed)return 'finished';if(x.running)return 'running';if(!Number.isFinite(x.timestamp))return 'unknown';const delta=x.timestamp-now.getTime();return delta<=-300000?'elapsed':delta<=0?'running':delta<=600000?'soon':'upcoming'}
const labelFor=code=>({finished:'確定',elapsed:'結果待ち',running:'進行中',soon:'まもなく',upcoming:'発走前',cancelled:'中止',unknown:'時刻未取得'}[code]||'');
function liveModel(mode,rows,day,now=new Date()){
 const all=(Array.isArray(rows)?rows:[]).map(r=>{const v=normalizedRace(mode,r,day);return v?{...v,status:raceStatus(mode,r,day,now),next:false}:null}).filter(Boolean);
 const nextByVenue=new Map();for(const v of all){if(v.status!=='soon'&&v.status!=='upcoming')continue;const key=v.circuit+'|'+v.venue,old=nextByVenue.get(key);if(!old||v.timestamp<old.timestamp||v.timestamp===old.timestamp&&v.number<old.number)nextByVenue.set(key,v)}
 const nextIds=new Set([...nextByVenue.values()].map(v=>v.id));for(const v of all)v.next=nextIds.has(v.id);
 return all.sort((a,b)=>a.circuit.localeCompare(b.circuit,'ja')||a.venue.localeCompare(b.venue,'ja')||a.number-b.number);
}
function liveSignature(mode,rows,day,now=new Date()){return liveModel(mode,rows,day,now).map(v=>v.id+':'+v.status+(v.next?':next':'')).join('|')}
function syncLiveUI(mode,rows,day,scope,now=new Date()){
 const node=scope||root.document;if(!node?.querySelectorAll)return;const byId=new Map(liveModel(mode,rows,day,now).map(v=>[v.id,v]));
 for(const el of node.querySelectorAll('button.arv-all-race[data-race],button.smart-race-row[data-race-state],button.arv-favorite-home-open[data-race-state]')){
  const v=byId.get(el.getAttribute('data-race'));if(!v)continue;
  if(el.classList.contains('arv-all-race')){
    for(const cls of ['elapsed','finished','running','soon','upcoming','future','pending','next'])
      el.classList.toggle(cls,cls===v.status||cls==='next'&&v.next);
  }
  el.setAttribute('data-race-state',v.status);
  const label=el.querySelector('.arv-race-state');if(label)label.textContent=labelFor(v.status);
 }
}
root.ARVEXQUnifiedHome=Object.freeze({hero,dateBar,buttons,liveModel,liveSignature,raceStatus,labelFor,syncLiveUI});
})(typeof window!=='undefined'?window:globalThis);
