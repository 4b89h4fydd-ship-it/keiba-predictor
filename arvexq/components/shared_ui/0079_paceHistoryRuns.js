function paceHistoryRuns(h,r){
  return historicalWindow(h,r).filter(validFirstCorner)
}
