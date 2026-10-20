function openHorseDetailPage(no){
  no=n(no,0);if(!no||!state.race)return;
  state.detailHorseNo=no;
  state.subPageReturnPanel=state.openPanel||'entry';
  state.subPage='horse';
  state.horseModalNo=null;
  window.scrollTo(0,0);
  render()
}
