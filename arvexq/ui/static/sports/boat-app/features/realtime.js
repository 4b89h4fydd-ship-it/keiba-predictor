// MEDIUM: closed-loop realtime schedule using only date-scoped verified boat feed.
// A snapshot without live odds or a confirmed result is never described as LIVE.
import {esc,todayJst} from "../core/contract.js";
const tms=x=>{const n=Date.parse(String(x||""));return Number.isFinite(n)?n:null};
function dueTime(r,date){
  const explicit=tms(r.closeAt);
  if(explicit!==null)return explicit;
  const hour=String(r.closeTime||"").match(/^(\d{1,2}):(\d{2})/);
  if(!hour)return null;
  return tms(date+"T"+hour[1].padStart(2,"0")+":"+hour[2]+":00+09:00");
}
export function realtimeRows(day,nowDate=new Date()){
  const target=Array.isArray(day?.races)?day.races:[];
  const now=nowDate.getTime(),date=String(day?.date||todayJst());
  const rows=target.filter(r=>r?.id&&r.venue&&Number.isInteger(r.raceNo)&&r.raceNo>=1&&r.raceNo<=12)
    .map(r=>({race:r,time:dueTime(r,date)})).filter(x=>x.time!==null);
  const future=rows.filter(x=>x.time>=now&&x.race.result?.status!=="confirmed")
    .sort((a,b)=>a.time-b.time);
  const recent=rows.filter(x=>x.time<now||x.race.result?.status==="confirmed")
    .sort((a,b)=>b.time-a.time);
  return [...future,...recent];
}
export function realtimeSection(day,{full=false,now=new Date()}={}){
  const rows=realtimeRows(day,now);
  const show=full?rows:rows.slice(0,6);
  let body="";
  if(show.length){
    body='<div class="boat-live-list">'+show.map(({race:r,time})=>{
      const finished=r.result?.status==="confirmed",d=Math.round((time-now.getTime())/60000);
      const status=finished?"確定":d<0?"結果待ち":d<=10?"まもなく":"締切前";
      const kind=finished?"finished":d<0?"pending":d<=10?"soon":"upcoming";
      return '<button type="button" class="boat-live-race '+kind+'" data-race="'+esc(r.id)+'">'+
        '<span class="boat-live-clock">'+esc(r.closeTime||new Date(time+9*3600000).toISOString().slice(11,16))+'</span>'+
        '<span class="boat-live-name"><b>'+esc(r.venue)+' '+r.raceNo+'R</b><small>'+esc(r.title||"レース情報")+'</small></span>'+
        '<span class="boat-live-badge">'+status+'</span><span>›</span></button>';
    }).join("")+'</div>';
  }else body='<p class="boat-muted">出走・締切時刻の確認済みデータがまだありません。データ接続後に実際のレースを表示します。</p>';
  return '<section class="boat-panel boat-live-panel"><div class="boat-row"><h2>リアルタイム</h2><span class="boat-status">締切時刻順</span></div>'+
    '<p class="boat-muted">レースを押すと予想・スタート展示・結果へ</p>'+body+
    (full?"":'<button type="button" class="boat-secondary" data-view="realtime">全レースの締切順を見る ›</button>')+
    '</section>';
}
