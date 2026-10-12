/* Horse home: one dense "all races by venue" display; existing race detail route.
   Render only races already acquired for the date. Never fabricate a meeting. */
(function(root){
  "use strict";
  const esc=value=>String(value==null?"":value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const n=x=>Number(x||0);
  const raceNo=r=>n(r.raceNumber||r.raceNo);
  const clock=r=>/^\d{1,2}:\d{2}/.test(String(r.startTime||""))?String(r.startTime).slice(0,5):"";
  const terminal=r=>/確定|中止|取止|取消|不成立/.test(String(r?.result?.status||r?.raceStatus||""));
  const cancelled=r=>/中止|取止|取消|不成立/.test(String(r?.result?.status||r?.raceStatus||""));
  function clockNow(opts={}){
    if(opts.now instanceof Date)return opts.now;
    if(/^\d{4}-\d{2}-\d{2}$/.test(String(opts.today||""))&&Number.isFinite(Number(opts.nowMinutes))){
      const minute=Math.max(0,Math.min(1439,Number(opts.nowMinutes)));
      return new Date(opts.today+"T"+String(Math.floor(minute/60)).padStart(2,"0")+":"+
        String(minute%60).padStart(2,"0")+":00+09:00");
    }
    return new Date();
  }
  function raceState(r,opts={}){
    const shared=root.ARVEXQUnifiedHome;
    if(shared?.raceStatus)return shared.raceStatus("horse",r,opts.date,clockNow(opts));
    if(cancelled(r))return "cancelled";
    if(terminal(r))return "finished";
    if(!clock(r))return "unknown";
    return opts.date<opts.today?"elapsed":"upcoming";
  }
  function liveLabel(code){
    return ({finished:"確定",elapsed:"発走時刻経過",soon:"まもなく",
      upcoming:"発走前",cancelled:"中止",unknown:"未取得"})[code]||"";
  }
  function allRaces(rows,opts={}){
    const source=(rows||[]).filter(r=>r&&r.id&&r.track&&(r.circuit==="中央"||r.circuit==="地方")&&
      Number.isInteger(raceNo(r))&&raceNo(r)>=1&&raceNo(r)<=12);
    const group=(circuit)=>{
      const circuits=source.filter(r=>r.circuit===circuit);
      const tracks=[...new Set(circuits.map(r=>String(r.track)))].sort((a,b)=>a.localeCompare(b,"ja"));
      const cards=tracks.map(track=>{
        const races=circuits.filter(r=>String(r.track)===track);
        const map=new Map(races.map(r=>[raceNo(r),r]));
        const times=races.map(clock).filter(Boolean).sort();
        const header='<div class="arv-all-venue-head"><div><b>'+esc(track)+'</b><span>1R〜12R</span></div>'+
          '<button type="button" data-track="'+esc(track)+'" data-circuit="'+esc(circuit)+'" class="arv-all-go">会場ページへ ›</button></div>';
        const shared=root.ARVEXQUnifiedHome;
        const liveRows=shared?.liveModel?shared.liveModel("horse",races,opts.date,clockNow(opts)):[];
        const liveById=new Map(liveRows.map(r=>[r.id,r]));
        const chips=Array.from({length:12},(_,i)=>{
          const number=i+1,r=map.get(number);
          if(!r||cancelled(r)){
            const label=r?"中止":"未取得";
            return '<button type="button" disabled aria-disabled="true" class="arv-all-race unavailable">'+
              '<strong>'+number+'R</strong><small>'+esc(r&&clock(r)||label)+'</small></button>';
          }
          const state=raceState(r,opts),next=liveById.get(r.id)?.next;
          return '<button type="button" class="arv-all-race '+esc(state)+(next?' next':'')+
            '" data-race="'+esc(r.id)+'" data-race-state="'+esc(state)+'" aria-label="'+esc(track+' '+number+'R '+clock(r)+' '+liveLabel(state))+'">'+
            '<strong>'+number+'R</strong><small>'+esc(clock(r)||"未取得")+'</small>'+
            '<em class="arv-race-state">'+esc(liveLabel(state))+'</em></button>';
        }).join("");
        return '<div class="arv-all-venue">'+header+'<div class="arv-all-races-grid">'+chips+'</div></div>';
      }).join("");
      return '<div class="arv-all-circuit"><div class="arv-all-circuit-label"><b>'+esc(circuit)+'競馬</b><small>'+tracks.length+'会場</small></div>'+
        (cards||'<p class="arv-all-empty">この日の開催データは未取得です。未取得を「開催なし」とは判定しません。</p>')+'</div>';
    };
    return '<section class="arv-all-panel" aria-label="各会場の全レース">'+
      '<header class="arv-all-title"><h2>各会場の全レース</h2><p>1R〜12Rを表示・自動更新　終了時刻を過ぎたレースは暗く表示</p></header>'+
      group("中央")+group("地方")+'</section>';
  }
  function home(rows,opts={}){return allRaces(rows,opts)}
  root.ARVEXQHorsePortal=Object.freeze({home,allRaces,raceState});
})(typeof window!=="undefined"?window:globalThis);
