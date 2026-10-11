// MEDIUM: venue and race cards. All labels originate from the verified daily feed.
import {VENUES,esc,usableForecast,displayMark} from "../core/contract.js";
import {startExhibitionPanel} from "./start-exhibition.js";
const digits=["","①","②","③","④","⑤","⑥"];
export function venueGrid(day,selected){
  const active=new Set(day.races.map(r=>r.venue));
  return '<div class="boat-venue-grid">'+VENUES.map(v=>
    '<button type="button" class="'+(v===selected?'selected':'')+'" data-venue="'+esc(v)+'" aria-pressed="'+(v===selected)+'">'+esc(v)+(active.has(v)?'<small>開催情報あり</small>':'<small>未取得</small>')+'</button>').join("")+'</div>';
}
export function raceList(day,venue){
  const list=day.races.filter(r=>r.venue===venue).sort((a,b)=>a.raceNo-b.raceNo);
  if(!list.length)return '<p class="boat-muted">この会場の検証済みレースは未取得です。開催の有無は未確認です。</p>';
  return '<div class="boat-race-grid">'+list.map(r=>'<button type="button" data-race="'+esc(r.id)+'">'+
    '<strong>'+r.raceNo+'R</strong><span>'+esc(r.title||"")+'</span><small>'+esc(r.closeTime||"締切時刻未取得")+'</small>'+
    (usableForecast(r)?'<em>AI予想あり</em>':'<em class="pending">分析待ち</em>')+'</button>').join("")+'</div>';
}
export function detail(r){
  if(!r)return "";
  const verified=usableForecast(r);
  const entrants=Array.isArray(r.entries)?r.entries.slice().sort((a,b)=>a.boatNo-b.boatNo):[];
  const entries=entrants.length?'<div class="boat-entry-list">'+entrants.map(e=>{
    const mark=verified?displayMark((r.forecast.marks||{})[e.boatNo]):"—";
    return '<div class="boat-entry"><b class="boat-no no-'+Number(e.boatNo)+'">'+digits[Number(e.boatNo)]||esc(e.boatNo)+'</b><span><b>'+esc(e.name)+'</b><small>'+esc(e.class||"")+' '+esc(e.motorNo?"M"+e.motorNo:"")+'</small></span><strong class="boat-mark">'+esc(mark)+'</strong></div>';
  }).join("")+'</div>':'<p class="boat-muted">出走選手のデータが揃っていません。</p>';
  let tickets='<p class="boat-muted">発走前に確定した検証済み予想がありません。仮の買い目は表示しません。</p>';
  if(verified)tickets='<div class="boat-ticket-grid">'+r.forecast.tickets.map(t=>{
    const combination=typeof t==="string"?t:t.combination;
    return '<div class="boat-ticket">'+esc(combination)+'</div>';
  }).join("")+'</div><p class="boat-muted">保存時刻 '+esc(r.forecast.snapshotAt)+' / '+r.forecast.tickets.length+'点</p>';
  return '<section class="boat-panel"><button type="button" data-back="races" class="boat-back">‹ レース一覧</button>'+
    '<h2>'+esc(r.venue)+' '+r.raceNo+'R <small>'+esc(r.title||"")+'</small></h2>'+entries+'</section>'+startExhibitionPanel(r)+
    '<section class="boat-panel"><h2>AI 3連単買い目 <span class="boat-label">最大6点</span></h2>'+tickets+'</section>'+
    '<section class="boat-panel"><h2>レース結果</h2>'+
    (r.result&&r.result.status==="confirmed"?'<p>確定 '+esc(r.result.trifecta||"—")+' / 3連単払戻 '+(Number.isFinite(r.result.trifectaPayoutYen)?r.result.trifectaPayoutYen.toLocaleString("ja-JP")+"円":"未取得")+'</p>':'<p class="boat-muted">結果未確定・未取得</p>')+'</section>';
}
