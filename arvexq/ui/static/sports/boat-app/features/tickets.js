/* MEDIUM: single canonical betting display, official odds and expansion. */
import {esc,usableForecast,validTicket,displayMark} from "../core/contract.js";
import {oddsQuote,summarizeFormation,expandFormation} from "../core/ticket-engine.js";
function money(n){return Number.isFinite(n)?n.toLocaleString("ja-JP"):"—"}
export function ticketPanel(r){
  const f=r?.forecast;
  if(!usableForecast(r)){
    return '<section class="boat-panel"><h2>AI 3連単買い目 <span class="boat-label">最大6点</span></h2>'+
      '<p class="boat-muted">発走前の検証済み予想はまだありません。実測データ未取得・試験モデルの買い目は配信しません。</p></section>';
  }
  const tickets=f.tickets.map(x=>typeof x==="string"?{combination:x}:x);
  const formation=summarizeFormation(tickets);
  let head=formation?'<div class="boat-formation"><span>3連単フォーメーション</span><strong>'+esc(formation)+'</strong>'+
    '<small>'+tickets.length+'点</small></div>':"";
  let oddsTime=r.odds3t?.verified&&r.odds3t.updatedAt?
    '<p class="boat-muted">オッズ更新 '+esc(r.odds3t.updatedAt)+'　※発売中は変動します</p>':
    '<p class="boat-muted">公式3連単オッズは未取得です。架空の倍率は表示しません。</p>';
  const rows=tickets.map((t,i)=>{
    const odd=oddsQuote(r,t.combination);
    const odds=odd===null?'—':odd.toFixed(1)+'倍';
    const stake=Number.isInteger(t.stakeYen)&&t.stakeYen>0?money(t.stakeYen)+'円':'—';
    const result=odd!==null&&Number.isInteger(t.stakeYen)&&t.stakeYen>0?
      money(odd*t.stakeYen)+'円':'—';
    return '<div class="boat-bet-row"><span class="boat-bet-rank">'+(i+1)+'</span>'+
      '<b class="boat-bet-combination">'+esc(t.combination)+'</b>'+
      '<strong class="boat-bet-odds'+(odd!==null&&odd>=15?' high':'')+'">'+odds+'</strong>'+
      '<span class="boat-bet-stake">'+stake+'</span><span class="boat-bet-return">'+result+'</span></div>';
  }).join("");
  return '<section class="boat-panel"><h2>AI 3連単買い目 <span class="boat-label">最大6点</span></h2>'+head+
    '<div class="boat-bet-header"><span>買い目</span><span>オッズ</span><span>購入額</span><span>想定払戻</span></div>'+
    '<div class="boat-bet-rows">'+rows+'</div>'+oddsTime+
    '<p class="boat-muted">発走前に保存した予想 '+esc(f.snapshotAt)+'。印と買い目は同じ予想データです。</p></section>';
}
export function compactMarks(r){
  if(!usableForecast(r))return "—";
  return Object.entries(r.forecast.marks||{}).map(([no,mark])=>esc(no+":"+displayMark(mark))).join(" ");
}
