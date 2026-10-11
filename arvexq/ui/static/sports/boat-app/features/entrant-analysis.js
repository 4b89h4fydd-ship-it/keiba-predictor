/* MEDIUM: six-racer inspection with provenance-preserving factual statistics. */
import {esc} from "../core/contract.js";
const point=(v,unit="")=>typeof v==="number"&&Number.isFinite(v)?v.toFixed(2)+unit:"未取得";
const ratio=v=>typeof v==="number"&&Number.isFinite(v)?v.toFixed(1)+"%":"未取得";
export function racerAnalysisPanel(race){
  const entrants=Array.isArray(race?.entries)?[...race.entries].sort((a,b)=>a.boatNo-b.boatNo):[];
  if(entrants.length!==6)return '<section class="boat-panel"><h2>全艇診断</h2><p class="boat-muted">6艇分の出走表は未取得です。</p></section>';
  const items=entrants.map(e=>{
    const p=e.player||{},m=e.motor||{},b=e.boat||{},ex=e.exhibition||{};
    const summary='<b class="boat-no no-'+e.boatNo+'">'+e.boatNo+'</b><strong>'+esc(e.name||"選手情報未取得")+'</strong>'+
      '<small>'+esc(e.class||"級別未取得")+'</small>';
    const stats=[
      ["全国勝率",point(p.winRate)],["当地勝率",point(p.localWinRate)],
      ["3連対率",ratio(p.top3Rate)],["平均ST",point(p.avgST,"秒")],
      ["モーター2連率",ratio(m.top2Rate)],["ボート2連率",ratio(b.top2Rate)],
      ["展示タイム",point(ex.time,"秒")],["進入想定",Number.isInteger(e.expectedCourse)?e.expectedCourse+"コース":"未取得"]
    ];
    const label=stats.map(([k,v])=>'<div><small>'+k+'</small><b>'+esc(v)+'</b></div>').join("");
    return '<details class="boat-racer-analysis"><summary>'+summary+'<span>数値 ›</span></summary>'+
      '<div class="boat-racer-metrics">'+label+'</div></details>';
  }).join("");
  const env=race.environment||{};
  const water=['風速 '+point(env.windSpeed,"m/s"),'波高 '+point(env.waveHeight,"cm"),'水温 '+point(env.waterTemperature,"℃")]
    .map(esc).join(" ／ ");
  return '<section class="boat-panel"><h2>全艇診断・公式実測指標</h2>'+
    '<p class="boat-muted">'+water+'</p>'+items+
    '<p class="boat-muted">出所が確認できた実測値のみ表示します。数値未取得は推測で補完しません。</p></section>';
}
