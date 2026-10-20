/* Requirement 182: render historical race facts only, without prediction or mark dependencies. */
(function(root){
  'use strict';
  function visible(horse,race,limit){
    const unique=root.ARVEXQPastRunDeduplicate.merge(horse);
    return root.ARVEXQPastRunTemporal.beforeRace(unique,race,limit==null?5:limit);
  }
  function recentRows(horse,race,escapeText){
    const esc=escapeText||function(value){return String(value==null?'':value)};
    return visible(horse,race,5).map(function(run){
      return '<div class="recent">'+esc(run.date||'')+' '+
        esc(run.track||'')+' '+esc(run.distance||'')+'m '+
        esc(run.finish||'')+'着</div>';
    }).join('');
  }
  root.ARVEXQPastRunView=Object.freeze({visible:visible,recentRows:recentRows});
})(typeof window!=='undefined'?window:globalThis);
