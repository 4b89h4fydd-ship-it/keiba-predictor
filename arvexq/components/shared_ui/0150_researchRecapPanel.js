function researchRecapPanel(r){return window.ARVEXQResearchView&&window.ARVEXQResearchView.renderRecap?
  window.ARVEXQResearchView.renderRecap(r,esc,isFinal(r)):''}

var CAREER_STATE_LABELS={'complete':'取得完了','complete-with-missing-fields':'取得完了・一部項目欠損','complete-no-starts':'既走なし（確認済）','partially-acquired':'一部取得','acquisition-unverified':'取得未確認','history-present-but-unusable':'履歴あり・分析不能','no-history':'履歴なし（取得未確認）','race-date-unverified':'レース日不明のため未確認'};
