function smartSelectedRaces(forceOpen){
  var central=selectedRaceCandidates('中央'),local=selectedRaceCandidates('地方'),open=forceOpen?true:!!selectedSectionsOpen.selected,total=central.length+local.length;
  return '<details class="smart-fixed-picks" data-selected-section="selected" '+(open?'open':'')+'><summary class="smart-fixed-picks-head"><span><b>厳選レース</b><small>朝固定・券種別／点数別の実測的中率80%以上（検証不足は厳選対象外）</small></span><span class="smart-fixed-summary-right"><em>'+total+'レース</em><i>⌄</i></span></summary><div class="smart-fixed-pick-grid">'+fixedSelectedBox('中央',central)+fixedSelectedBox('地方',local)+'</div></details>'
}
