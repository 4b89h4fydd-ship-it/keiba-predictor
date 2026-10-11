/* MEDIUM: special forecast only from a separately verified, pre-start published entry. */
import {esc,usableForecast} from "../core/contract.js";
export function specialSection(day){
  const races=(day?.races||[]).filter(r=>r?.special?.approved===true&&
    r.special.snapshotAt===r.forecast?.snapshotAt&&usableForecast(r));
  return races.length?'<div class="boat-race-grid">'+races.map(r=>
    '<button type="button" data-race="'+esc(r.id)+'"><strong>'+esc(r.venue)+' '+r.raceNo+'R</strong>'+
    '<span>'+esc(r.title||'特別予想')+'</span><small>3連単 '+r.forecast.tickets.length+'点</small></button>').join('')+'</div>':
    '<p class="boat-muted">発走前に確定・保存された特別予想はありません。未取得データから架空の予想を作りません。</p>';
}
