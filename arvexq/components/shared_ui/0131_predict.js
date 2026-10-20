function predict(r){
  // No assistant-created historical/reference forecast is allowed to be shown.
  return window.ARVEXQProductionPrediction.build(r);
}

