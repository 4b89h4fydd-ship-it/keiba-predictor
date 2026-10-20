function raceHeadCountText(r){
  var count=Number(r.fieldSize),hs=r.horses||[],st=detailState(r.id);
  if(r.fieldSize!=null&&isFinite(count)&&count>0)return count+'頭';
  if(hs.length)return hs.length+'頭';
  return st.entry==='empty'?'0頭':'頭数取得中'
}
