/* MEDIUM: compact 1R-12R panels per venue, using only verified race records.
   A missing date feed is UNKNOWN, never treated as a cancelled meeting. */
import {esc,VENUES} from "../core/contract.js";
function isCancelled(r){
  const status=String(r?.result?.status||r?.status||"").toLowerCase();
  return ["cancelled","canceled","abandoned","中止","取止","取消","不成立"].some(k=>status.includes(k));
}
function timeText(r){
  if(/^\d{1,2}:\d{2}/.test(String(r?.closeTime||"")))return String(r.closeTime).slice(0,5);
  const t=Date.parse(String(r?.closeAt||""));
  return Number.isFinite(t)?new Date(t+9*3600000).toISOString().slice(11,16):"";
}
export function allBoatRaces(day,{now=new Date()}={}){
  const races=Array.isArray(day?.races)?day.races:[];
  const active=VENUES.filter(venue=>races.some(r=>r.venue===venue));
  const jstDay=new Date(now.getTime()+9*3600000).toISOString().slice(0,10);
  const cards=active.map(venue=>{
    const byNo=new Map(races.filter(r=>r?.venue===venue&&Number.isInteger(r.raceNo))
      .map(r=>[r.raceNo,r]));
    const cells=Array.from({length:12},(_,idx)=>{
      const no=idx+1,r=byNo.get(no);
      if(!r||isCancelled(r))return '<button type="button" disabled aria-disabled="true" class="arv-all-race unavailable">'+
        '<strong>'+no+'R</strong><small>'+esc(r&&timeText(r)||"未取得")+'</small></button>';
      const time=timeText(r),t=Date.parse(String(r.closeAt||""));
      const diff=Number.isFinite(t)?Math.ceil((t-now.getTime())/60000):null;
      const result=r.result?.status==="confirmed"?"finished":diff!==null&&diff<0?"pending":
        diff!==null&&diff<=10&&day.date===jstDay?"soon":"upcoming";
      return '<button type="button" data-race="'+esc(r.id)+'" class="arv-all-race '+result+'"'+
        ' aria-label="'+esc(venue+' '+no+'レース '+(time||"締切未取得"))+'">'+
        '<strong>'+no+'R</strong><small>'+esc(time||"未取得")+'</small></button>';
    }).join("");
    return '<div class="arv-all-venue"><div class="arv-all-venue-head"><div><b>'+esc(venue)+'</b><span>1R〜12R</span></div>'+
      '<button type="button" data-venue="'+esc(venue)+'" class="arv-all-go">会場ページへ ›</button></div>'+
      '<div class="arv-all-races-grid">'+cells+'</div></div>';
  }).join("");
  // Do not print 24 inactive venues as a giant list. Without confirmed schedule
  // feed they are unknown, not proof that a race meeting was cancelled.
  return '<section class="arv-all-panel" aria-label="各会場の全レース">'+
    '<header class="arv-all-title"><h2>各会場の全レース</h2><p>締切時刻とレース番号から直接詳細へ</p></header>'+
    '<div class="arv-all-circuit"><div class="arv-all-circuit-label"><b>競艇</b><small>データ確認 '+active.length+'場</small></div>'+
    (cards||'<p class="arv-all-empty">開催・出走データは未取得です。未取得を「開催なし」とは判定しません。</p>')+
    '</div></section>';
}
