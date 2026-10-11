// MEDIUM: displayed AI record is computed from immutable verified saved bets.
import {summarize} from "../core/stats.js";
import {esc} from "../core/contract.js";
export function statsSection(day){
  const m=summarize(day.races);
  const fmtPct=x=>x===null?"集計対象なし":(100*x).toFixed(1)+"%";
  const roi=m.roi===null?"算出不可":m.roi.toFixed(1)+"%";
  let rows='<div class="boat-stat-grid"><div><small>事前予想保存</small><strong>'+m.published+'R</strong></div>'+
    '<div><small>結果確定</small><strong>'+m.settled+'R</strong></div>'+
    '<div><small>3連単的中</small><strong>'+m.hits+'R</strong></div>'+
    '<div><small>的中率</small><strong>'+fmtPct(m.hitRate)+'</strong></div>'+
    '<div><small>回収率</small><strong>'+roi+'</strong></div>'+
    '<div><small>回収率対象</small><strong>'+m.payable+'R</strong></div></div>';
  if(m.history.length)rows+='<div class="boat-history">'+m.history.map(x=>
    '<div><span>'+esc(x.venue)+' '+x.raceNo+'R　'+esc(x.combination)+'</span><strong>'+(x.hit?'的中':'不的中')+'</strong></div>'
  ).join("")+'</div>';
  else rows+='<p class="boat-muted">結果と照合できる発走前予想がありません。</p>';
  rows+='<p class="boat-muted">発走前に保存された最大6点の買い目のみ集計。賭け金・公式払戻が揃わないレースは回収率から除外せず、全体の回収率を「算出不可」と表示します。</p>';
  return rows;
}
