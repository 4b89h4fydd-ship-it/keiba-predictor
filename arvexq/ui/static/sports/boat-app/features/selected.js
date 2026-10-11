// MEDIUM: only locked morning picks. No after-the-fact selection.
import {esc} from "../core/contract.js";
import {dailyRecommendations} from "../core/daily-selection.js";
export function selectedSection(day){
  const selected=dailyRecommendations(day.races,day.date).selected.sort((a,b)=>String(a.closeAt||"").localeCompare(String(b.closeAt||"")));
  if(!selected.length)return '<p class="boat-muted">1日1件以上を目標に審査します。高配当の可能性・校正済み確率・発走前保存の条件を満たす厳選レースはまだありません。</p>';
  return '<div class="boat-race-grid">'+selected.map(r=>
    '<button type="button" data-race="'+esc(r.id)+'"><strong>'+esc(r.venue)+' '+r.raceNo+'R</strong>'+
    '<small>朝の厳選確定</small><em>3連単 '+r.forecast.tickets.length+'点</em></button>'
  ).join("")+'</div>';
}
