function tenScore(h,r){
  // First-corner position proxy: not a measured individual opening furlong.
  var x=styleRates(h,r);return x.samples?clamp(x.ten,0,1):.5
}
