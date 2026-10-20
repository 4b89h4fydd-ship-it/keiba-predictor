function validFirstCorner(rr){
  var p=n(rr&&rr.cornerPositions&&rr.cornerPositions[0],0),field=n(rr&&rr.fieldSize,0);
  return Number.isInteger(p)&&p>=1&&(!field||p<=field)
}
