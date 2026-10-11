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
  function raceState(r,opts){
    if(cancelled(r))return "cancelled";
    if(terminal(r))return "finished";
    const time=clock(r);
    if(!time)return "unknown";
    if(opts.date>opts.today)return "future";
    if(opts.date<opts.today)return "pending";
    const match=/^(\d{1,2}):(\d{2})/.exec(time);
    const diff=Number(match[1])*60+Number(match[2])-Number(opts.nowMinutes||0);
    return diff<0?"pending":diff<=10?"soon":"upcoming";
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
        const chips=Array.from({length:12},(_,i)=>{
          const number=i+1,r=map.get(number);
          if(!r||cancelled(r)){
            const label=r?"中止":"未取得";
            return '<button type="button" disabled aria-disabled="true" class="arv-all-race unavailable">'+
              '<strong>'+number+'R</strong><small>'+esc(r&&clock(r)||label)+'</small></button>';
          }
          return '<button type="button" class="arv-all-race '+raceState(r,opts)+'" data-race="'+esc(r.id)+'" aria-label="'+esc(track)+' '+number+'レース '+esc(clock(r)||"時刻未取得")+'">'+
            '<strong>'+number+'R</strong><small>'+esc(clock(r)||"未取得")+'</small></button>';
        }).join("");
        return '<div class="arv-all-venue"><div class="arv-all-venue-thumb" aria-hidden="true">♞</div>'+header+'<div class="arv-all-races-grid">'+chips+'</div></div>';
      }).join("");
      return '<div class="arv-all-circuit"><div class="arv-all-circuit-label"><b>'+esc(circuit)+'競馬</b><small>'+tracks.length+'会場</small></div>'+
        (cards||'<p class="arv-all-empty">この日の開催データは未取得です。未取得を「開催なし」とは判定しません。</p>')+'</div>';
    };
    return '<section class="arv-all-panel" aria-label="各会場の全レース">'+
      '<header class="arv-all-title"><h2>各会場の全レース</h2><p>1R〜12Rを選択するとレース詳細へ</p></header>'+
      group("中央")+group("地方")+'</section>';
  }
  function home(rows,opts={}){return allRaces(rows,opts)}
  root.ARVEXQHorsePortal=Object.freeze({home,allRaces,raceState});
})(typeof window!=="undefined"?window:globalThis);
