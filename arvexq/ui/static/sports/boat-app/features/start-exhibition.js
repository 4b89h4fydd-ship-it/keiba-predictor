// MEDIUM: start exhibition belongs to the real race detail, not a fabricated prediction.
import {esc} from "../core/contract.js";
import {validStartExhibition} from "../core/start-exhibition.js";
export function startExhibitionPanel(race){
  const data=validStartExhibition(race);
  let view='<p class="boat-muted">スタート展示は未取得です。正式な進入コースとSTが確認できると表示します。</p>';
  if(data){
    view='<div class="boat-start-grid" role="table" aria-label="スタート展示">'+
      '<div class="boat-start-head" role="row"><b>進入</b><b>艇番</b><b>展示ST</b></div>'+
      data.rows.map(row=>'<div class="boat-start-row" role="row"><span>'+row.course+'コース</span>'+
        '<b class="boat-no no-'+row.boatNo+'">'+row.boatNo+'</b>'+
        '<strong'+(row.st.startsWith("F")?' class="boat-st-f"':'')+'>'+esc(row.st)+'</strong></div>').join("")+
      '</div><p class="boat-muted">BOATRACE公式 / 観測 '+esc(data.observedAt)+'</p>';
  }
  return '<section class="boat-panel boat-start-panel"><h2>スタート展示</h2>'+view+
    '<p class="boat-muted">進入・展示STを確認。展示のFは本番のフライング違反を意味しません。展示と本番の進入は異なる場合があります。</p></section>';
}
