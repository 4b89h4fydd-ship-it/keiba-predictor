// MEDIUM: only locked morning picks. No after-the-fact selection.
import {esc,selectedRace} from "../core/contract.js";
export function selectedSection(day){
  const selected=day.races.filter(selectedRace).sort((a,b)=>String(a.closeAt||"").localeCompare(String(b.closeAt||"")));
  if(!selected.length)return '<p class="boat-muted">朝の審査で確定・保存された厳選レースはありません。未審査や未取得を厳選と表示しません。</p>';
  return '<div class="boat-race-grid">'+selected.map(r=>
    '<button type="button" data-race="'+esc(r.id)+'"><strong>'+esc(r.venue)+' '+r.raceNo+'R</strong>'+
    '<small>朝の厳選確定</small><em>3連単 '+r.forecast.tickets.length+'点</em></button>'
  ).join("")+'</div>';
}
