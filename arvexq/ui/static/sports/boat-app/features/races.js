// MEDIUM: venue and race cards. All labels originate from the verified daily feed.
import {esc,usableForecast,displayMark} from "../core/contract.js";
import {startExhibitionPanel} from "./start-exhibition.js";
import {ticketPanel} from "./tickets.js";
import {racerAnalysisPanel} from "./entrant-analysis.js";
const digits=["","①","②","③","④","⑤","⑥"];
export function raceList(day,venue){
  const list=day.races.filter(r=>r.venue===venue).sort((a,b)=>a.raceNo-b.raceNo);
  if(!list.length)return '<p class="boat-muted">この会場の検証済みレースは未取得です。開催の有無は未確認です。</p>';
  // Same compact 1R–12R grid as the horse venue page. Missing cards are
  // disabled rather than falsely labelled cancelled.
  const byNo=new Map(list.map(r=>[r.raceNo,r]));
  const shared=globalThis.ARVEXQUnifiedHome;
  const when=new Date();
  const model=shared?.liveModel?shared.liveModel('boat',list,day.date,when):[];
  const byLive=new Map(model.map(r=>[r.id,r]));
  return '<div class="arv-all-races-grid boat-venue-race-grid">'+
    Array.from({length:12},(_,i)=>{
      const n=i+1,r=byNo.get(n);
      if(!r)return '<button class="arv-all-race unavailable" type="button" disabled>'+
        '<strong>'+n+'R</strong><small>未取得</small></button>';
      const cancelled=/cancelled|canceled|abandoned|中止|取止|取消|不成立/i.test(
        String(r.result?.status||r.status||''));
      if(cancelled)return '<button class="arv-all-race unavailable" type="button" disabled>'+
        '<strong>'+n+'R</strong><small>中止</small></button>';
      const live=byLive.get(r.id);
      const time=Date.parse(String(r.closeAt||''));
      const status=live?.status||(r.result?.status==="confirmed"?"finished":
        Number.isFinite(time)&&time<=when.getTime()?"elapsed":
        Number.isFinite(time)&&time-when.getTime()<=600000?"soon":
        Number.isFinite(time)?"upcoming":"unknown");
      const label={finished:"確定",elapsed:"締切経過",soon:"まもなく",
        upcoming:"締切前",unknown:"時刻未取得"}[status]||"";
      return '<button type="button" class="arv-all-race '+status+(live?.next?' next':'')+
        '" data-race="'+esc(r.id)+'" data-race-state="'+status+
        '" aria-label="'+esc(venue+' '+n+'R '+(r.closeTime||"時刻未取得")+' '+label)+'">'+
        '<strong>'+n+'R</strong><small>'+esc(r.closeTime||"未取得")+'</small>'+
        '<em class="arv-race-state">'+label+'</em></button>';
    }).join("")+'</div>';
}
export function detail(r){
  if(!r)return "";
  const verified=usableForecast(r);
  const entrants=Array.isArray(r.entries)?r.entries.slice().sort((a,b)=>a.boatNo-b.boatNo):[];
  const entries=entrants.length?'<div class="boat-entry-list">'+entrants.map(e=>{
    const markRow=verified?(r.forecast.marks||{})[e.boatNo]:null;
    const mark=markRow?displayMark(markRow):"—";
    const grade=markRow&&["A","B","C"].includes(markRow.grade)?markRow.grade:"";
    return '<div class="boat-entry"><b class="boat-no no-'+Number(e.boatNo)+'">'+(digits[Number(e.boatNo)]||esc(e.boatNo))+'</b><span><b>'+esc(e.name)+'</b><small>'+esc(e.class||"")+' '+esc(e.motorNo?"M"+e.motorNo:"")+'</small></span><span class="boat-mark-cell"><strong class="boat-mark">'+esc(mark)+'</strong>'+(grade?'<small>'+grade+'</small>':'')+'</span></div>';
  }).join("")+'</div>':'<p class="boat-muted">出走選手のデータが揃っていません。</p>';
  return '<section class="boat-panel"><button type="button" data-back="races" class="boat-back">‹ レース一覧</button>'+
    '<h2>'+esc(r.venue)+' '+r.raceNo+'R <small>'+esc(r.title||"")+'</small></h2>'+entries+'</section>'+racerAnalysisPanel(r)+startExhibitionPanel(r)+
    ticketPanel(r)+
    '<section class="boat-panel"><h2>レース結果</h2>'+
    (r.result&&r.result.status==="confirmed"?'<p>確定 '+esc(r.result.trifecta||"—")+' / 3連単払戻 '+(Number.isFinite(r.result.trifectaPayoutYen)?r.result.trifectaPayoutYen.toLocaleString("ja-JP")+"円":"未取得")+'</p>':'<p class="boat-muted">結果未確定・未取得</p>')+'</section>';
}
