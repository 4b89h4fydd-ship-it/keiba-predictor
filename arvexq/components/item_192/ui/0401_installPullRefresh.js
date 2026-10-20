function installPullRefresh(){
  // The shared sport module owns the touch listeners and indicator.
  window.ARVEXQPullRefresh.mount({refresh:reloadCurrent});
}
