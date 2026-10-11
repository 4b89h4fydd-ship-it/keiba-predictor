/* Horse homepage/realtime renderer. UI ONLY: consumes already acquired race rows.
   All navigation continues through existing data-home-page/data-track/data-race hooks. */
(function(root){
  "use strict";
  const esc=x=>String(x==null?"":x).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const fin=r=>["確定","中止","取止","取消","不成立"].includes(String(r&&((r.result||{}).status||r.raceStatus)||""));
  const validTime=r=>/^\d{1,2}:\d{2}/.test(String(r&&r.startTime||""));
  const minutes=r=>{const a=/^(\d{1,2}):(\d{2})/.exec(String(r&&r.startTime||""));return a?Number(a[1])*60+Number(a[2]):9999};
  const raceNum=r=>Number(r.raceNumber||r.raceNo||0);
  const sortByClock=(a,b)=>minutes(a)-minutes(b)||String(a.track||"").localeCompare(String(b.track||""),"ja")||raceNum(a)-raceNum(b);
  function status(r,date,today,now){
    if(fin(r))return {label:"確定",kind:"finished"};
    if(String(r&&((r.result||{}).status||r.raceStatus)||"")==="速報")return {label:"速報",kind:"running"};
    if(!validTime(r))return {label:"時刻未取得",kind:"unknown"};
    if(date<today)return {label:"結果未取得",kind:"pending"};
    if(date>today)return {label:"開催予定",kind:"future"};
    const diff=minutes(r)-now;
    if(diff<0)return {label:"結果待ち",kind:"pending"};
    if(diff<=10)return {label:"まもなく",kind:"soon"};
    return {label:"発走前",kind:"upcoming"};
  }
  function timeline(all,date,today,now,limit){
    const races=(all||[]).filter(r=>r&&r.id&&validTime(r));
    const pending=races.filter(r=>!fin(r)).sort(sortByClock);
    const future=pending.filter(r=>date!==today||minutes(r)>=now);
    const overdue=pending.filter(r=>date===today&&minutes(r)<now)
      .sort((a,b)=>minutes(b)-minutes(a));
    const finished=races.filter(fin).sort((a,b)=>minutes(b)-minutes(a));
    // Near-term races first; if no future races remain, show latest overdue/results.
    const ordered=date===today?[...future,...overdue,...finished]:
      date<today?[...finished,...pending]:[...pending,...finished];
    return limit?ordered.slice(0,limit):ordered;
  }
  function card(r,date,today,now){
    const s=status(r,date,today,now);
    return '<button type="button" class="arv-tb-race '+s.kind+'" data-race="'+esc(r.id)+'" aria-label="'+esc((r.track||"")+" "+raceNum(r)+"レース "+(r.startTime||"")+" "+s.label)+'">'+
      '<span class="arv-tb-race-time">'+esc(r.startTime||"--:--")+'</span>'+
      '<span class="arv-tb-race-info"><b>'+esc(r.track||"")+" "+raceNum(r)+'R</b><small>'+esc(r.title||"レース情報")+'</small></span>'+
      '<span class="arv-tb-race-state">'+esc(s.label)+'</span><b class="arv-tb-chevron">›</b></button>';
  }
  function realtime(rows,opts){
    opts=opts||{};
    const date=String(opts.date||""),today=String(opts.today||date),now=Number(opts.nowMinutes||0),full=opts.full===true;
    const source=timeline(rows,date,today,now,full?0:8);
    const circuits=["中央","地方"].map(name=>{
      const races=source.filter(r=>r.circuit===name);
      if(!races.length)return "";
      return '<div class="arv-tb-live-group"><div class="arv-tb-group-head"><b>'+name+'</b><small>'+races.length+'レース</small></div>'+
        '<div class="arv-tb-races">'+races.map(r=>card(r,date,today,now)).join("")+'</div></div>';
    }).join("");
    const more=full?"":'<button type="button" class="arv-tb-more" data-home-page="realtime">締切・発走時刻順をすべて見る ›</button>';
    return '<section class="arv-tb-panel arv-tb-live"><div class="arv-tb-title"><div><strong>リアルタイム</strong><small>発走順・結果反映順｜レースを押すと詳細へ</small></div><span class="arv-tb-tag">RACE</span></div>'+
      (circuits||'<p class="arv-tb-empty">開催・発走情報が未取得です。架空のレースは表示しません。</p>')+more+'</section>';
  }
  function venues(rows,circuit,opts){
    opts=opts||{};
    const group=(rows||[]).filter(r=>r.circuit===circuit&&r.track&&r.id);
    const tracks=[...new Set(group.map(r=>String(r.track)))].sort((a,b)=>a.localeCompare(b,"ja"));
    const tracksOut=opts.limit?tracks.slice(0,opts.limit):tracks;
    const now=Number(opts.nowMinutes||0);
    const html=tracksOut.map(track=>{
      const races=group.filter(r=>String(r.track)===track).sort(sortByClock);
      const coming=races.find(r=>!fin(r)&&minutes(r)>=now)||races.find(r=>!fin(r))||races[races.length-1];
      const first=races[0],last=races[races.length-1];
      return '<button type="button" class="arv-tb-venue" data-track="'+esc(track)+'" data-circuit="'+esc(circuit)+'">'+
        '<span class="arv-tb-venue-symbol">'+esc(track.slice(0,1))+'</span>'+
        '<span class="arv-tb-venue-name"><b>'+esc(track)+'</b><small>'+races.length+'レース　'+esc(first&&first.startTime||"--:--")+'～'+esc(last&&last.startTime||"--:--")+'</small></span>'+
        '<span class="arv-tb-venue-next">'+(coming?raceNum(coming)+'R':'—')+'<small>'+esc(coming&&coming.startTime||"")+'</small></span><span class="arv-tb-chevron">›</span></button>';
    }).join("");
    return '<section class="arv-tb-panel arv-tb-venues"><div class="arv-tb-title"><div><strong>'+esc(circuit)+'競馬</strong><small>開催一覧｜場を押すと1R～12Rへ</small></div><span class="arv-tb-tag">'+tracks.length+'場</span></div>'+
      (html?'<div class="arv-tb-venue-grid">'+html+'</div>':'<p class="arv-tb-empty">開催場情報がまだありません。</p>')+
      (opts.limit&&tracks.length>opts.limit?'<button type="button" data-home-page="'+(circuit==="中央"?"central":"local")+'" class="arv-tb-more">'+esc(circuit)+'の全開催場を見る ›</button>':'')+
      '</section>';
  }
  function home(rows,opts){
    opts=opts||{};
    const selected=opts.selected||{central:0,local:0},special=opts.special||{central:0,local:0};
    const cc=rows.filter(r=>r.circuit==="中央").length,lc=rows.filter(r=>r.circuit==="地方").length;
    const btn=(view,title,sub,main)=>'<button type="button" class="arv-tb-action '+(main?'major':'')+'" data-home-page="'+view+'"><b>'+title+'</b><small>'+sub+'</small><span>›</span></button>';
    return '<div class="arv-tb-hub"><div class="arv-tb-actions">'+
      btn("central","中央競馬",cc+'レース｜開催場',true)+btn("local","地方競馬",lc+'レース｜開催場',true)+
      btn("realtime","リアルタイム","発走順のレースへ",true)+
      btn("selected","本日の厳選",Number(selected.central||0)+Number(selected.local||0)+'レース',false)+
      btn("special","特別予想",Number(special.central||0)+Number(special.local||0)+'レース',false)+
      btn("ai-stats","AI成績","発走前予想の成績",false)+'</div>'+
      realtime(rows,{date:opts.date,today:opts.today,nowMinutes:opts.nowMinutes})+
      venues(rows,"中央",{limit:5,nowMinutes:opts.nowMinutes})+
      venues(rows,"地方",{limit:6,nowMinutes:opts.nowMinutes})+'</div>';
  }
  root.ARVEXQHorsePortal=Object.freeze({home,realtime,venues,status,timeline});
})(typeof window!=="undefined"?window:globalThis);
