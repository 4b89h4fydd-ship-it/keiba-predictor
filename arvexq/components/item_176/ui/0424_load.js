function load(force){
  var d=state.date,seq=++state.requestSeq,detailsStarted=false,listInFlight=false,detailsInFlight=false,lastDetailsAt=0,
      embedded=(!force&&window.__ARVEXQ_BOOTSTRAP__&&window.__ARVEXQ_BOOTSTRAP__.date===d)?window.__ARVEXQ_BOOTSTRAP__:null,
      full=force?null:loadFullBundle(d),
      listCache=force?null:loadRaceCache(d,'__ALL__');
  state.error=null;state.bootstrapReady=false;state.bootstrapProgress=null;
  if(selectedRacePreload.timer){clearTimeout(selectedRacePreload.timer);selectedRacePreload.timer=null}
  if(selectedRacePreload.date!==d){selectedRacePreload={date:d,busy:{},done:{},timer:null,fullLoaded:false,fullLoading:false,loadedCount:0,expectedCount:0,lastError:''}}

  // 1) Paint anything we already have immediately.
  if(embedded&&(embedded.races||[]).length){
    state.races=mergeBootstrap(embedded);
    saveRaceCache(d,'__ALL__',state.races);
    state.loading=false;
    state.bootstrapReady=!!embedded.displayComplete||!!embedded.complete;
    render()
  }else if(full&&(full.races||[]).length){
    state.races=mergeBootstrap(full);
    saveRaceCache(d,'__ALL__',state.races);
    state.loading=false;state.bootstrapReady=!!full.displayComplete||!!full.complete;
    render()
  }else if(listCache&&listCache.length){
    state.races=listCache;
    hydrateInstantFromDevice(listCache);
    state.loading=false;
    render()
  }else{
    state.races=[];
    instantTrackDetails={};
    state.loading=true;
    render()
  }

  // Morning selections are an immutable dated static artifact, independent
  // of live odds, late diagnosis, and mutable D1 summary schemas.
  function requestMorningArchive(){
    fetch('/morning-picks/'+encodeURIComponent(d)+'.json?day='+encodeURIComponent(d),{cache:'no-store'})
      .then(function(response){return response.ok?response.json():null})
      .then(async function(payload){
        if(window.ARVEXQSavedTicketReceipt)await window.ARVEXQSavedTicketReceipt.load(d,edgeFetchJson);
        if(seq!==state.requestSeq||state.date!==d)return;
        if(!payload||payload.version!=='v1'||payload.date!==d||!payload.fixedAt||
          !Array.isArray(payload.races)||payload.races.length!==n(payload.scope))return;
        var seen={},valid=payload.races.every(function(x){
          if(!x||!x.id||seen[x.id]||typeof x.selected!=='boolean'||typeof x.special!=='boolean')return false;
          seen[x.id]=true;return true
        });
        if(!valid)return;
        state.morningArchive=payload;
        if(state.races&&state.races.length){
          applyMorningArchive(state.races);
          saveRaceCache(d,'__ALL__',state.races);
          render()
        }
      }).catch(function(){/* No post-off reconstruction on missing file. */})
  }
  if(state.morningArchive&&state.morningArchive.date!==d)state.morningArchive=null;
  requestMorningArchive();
  // No retrospective forecast fetching: user withdrew the generated model.
    setTimeout(scheduleDailyAiStats,900);
  function startDetails(){if(detailsStarted)return;detailsStarted=true;setTimeout(function(){requestDetails(0)},80)}
  // If summaries were already painted from cache, allow selection preload after first paint.
  setTimeout(function(){if(state.races.length)startDetails()},450);

  // 2) Race summaries: Cloudflare/D1 first, Render only as fallback.
  function requestList(attempt){
    attempt=n(attempt,0);
    if(listInFlight)return;
    listInFlight=true;

    fetch(
      'https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='
      +encodeURIComponent(d)
      +'&details=0&t='+Date.now(),
      {cache:'no-store'}
    )
    .then(function(res){
      if(!res.ok)throw Error('cloudflare-list '+res.status);
      return res.json()
    })
    .then(function(body){
      var rows=Array.isArray(body)?body:(body.races||[]);
      if(!rows.length)throw Error('cloudflare-list-empty');
      if(seq!==state.requestSeq||state.date!==d)return null;
      state.bootstrapReady=true;
      return rows
    })
    .catch(function(){
      return window.ARVEXQStaticRacecard?window.ARVEXQStaticRacecard.list(d,edgeFetchJson):null
    })
    .then(function(rows){
      if(seq!==state.requestSeq||state.date!==d)return;
      if(!Array.isArray(rows)||!rows.length){
        // Never leave an iPhone open on the initial empty D1 day forever:
        // the first official schedule can be published after app startup.
        if(!state.races.length){
          state.loading=false;
          state.error='開催一覧はサーバー公開待ち・自動再取得中';
          render();
          var retryDelay=attempt<8?Math.min(12000,1500*(attempt+1)):45000;
          setTimeout(function(){
            if(seq===state.requestSeq&&state.date===d&&document.visibilityState!=='hidden')
              requestList(Math.min(8,attempt+1))
          },retryDelay)
        }
        return
      }

      if(rows.length){
        var old={};
        state.races.forEach(function(r){
          if(r&&r.id)old[String(r.id)]=r
        });

        rows.forEach(function(r){
          var z=old[String(r.id)];
          if(!z)return;
          var prior=morningPickOf(z),fresh=morningPickOf(r);
          if(prior&&!fresh){
            r.volatility=Object.assign({},r.volatility||{},{morningPicks:prior});
            r.environmentMeta=Object.assign({},r.environmentMeta||{},{morningPicks:prior})
          }
          ['weather','condition','oddsUpdatedAt']
            .forEach(function(k){
              if(z[k]!=null&&z[k]!==''&&z[k]!=='不明')r[k]=z[k]
            })
        });

        // A delayed static/D1 list must not roll a verified official final
        // back into 結果待ち when the page reloads or date summaries refresh.
        if(window.ARVEXQUnifiedHome&&window.ARVEXQUnifiedHome.mergePublishedStatuses)
          window.ARVEXQUnifiedHome.mergePublishedStatuses(rows,state.races);
        state.races=applyMorningArchive(rows);
        saveRaceCache(d,'__ALL__',state.races);
        state.loading=false;
        render();
        startDetails();
        setTimeout(scheduleDailyAiStats,500)
      }else if(!state.races.length&&attempt<8){
        setTimeout(function(){requestList(attempt+1)},700)
      }
    })
    .catch(function(){
      if(seq!==state.requestSeq||state.date!==d)return;
      if(!state.races.length&&attempt<8){
        setTimeout(function(){requestList(attempt+1)},900)
      }
    })
    .finally(function(){listInFlight=false})
  }

  // 3) Load the entire day's D1 detail pack in the background. This powers
  // strict selection / value selection on TOP before any race is opened.
  function requestDetails(attempt){
    attempt=n(attempt,0);
    if(seq!==state.requestSeq||state.date!==d||detailsInFlight)return;
    var ids=(state.races||[]).filter(function(r){return r&&r.id}).map(function(r){return String(r.id)});
    if(!ids.length)return;
    detailsInFlight=true;
    selectedRacePreload.date=d;selectedRacePreload.fullLoading=true;selectedRacePreload.lastError='';
    selectedRacePreload.expectedCount=ids.length;

    function scheduleTopRefresh(){
      if(selectedRacePreload.timer){clearTimeout(selectedRacePreload.timer);selectedRacePreload.timer=null}
      if(d===today())selectedRacePreload.timer=setTimeout(function(){
        if(liveCenterOpen){scheduleTopRefresh();return}
        if(seq===state.requestSeq&&state.date===d&&!state.race&&!state.track&&!state.picker)requestDetails(0)
      },300000)
    }

    var cursor=0,loaded=0,analysisReady=0,failed=0,summaryBy={};
    (state.races||[]).forEach(function(x){if(x&&x.id)summaryBy[String(x.id)]=x});

    function worker(){
      if(cursor>=ids.length)return Promise.resolve();
      var id=ids[cursor++];
      return fetchEdgeRace(id,attempt>0)
        .then(function(z){
          if(seq!==state.requestSeq||state.date!==d)return;
          if(z&&raceDisplayCoreReady(z,summaryBy[id]||z)){
            loaded++;
            instantTrackDetails[id]=mergeRaceReflection(instantTrackDetails[id]||loadDetailCache(id)||null,z,null,summaryBy[id]||null);
            saveDetailCache(id,instantTrackDetails[id]);
            if(isFinal(z)||diagnosisCurrent(z))analysisReady++
          }else failed++
        })
        .catch(function(){failed++})
        .then(worker)
    }

    var workers=[],concurrency=Math.min(4,ids.length);
    for(var i=0;i<concurrency;i++)workers.push(worker());
    Promise.all(workers)
      .then(function(){
        if(seq!==state.requestSeq||state.date!==d)return;
        selectedRacePreload.loadedCount=loaded;
        selectedRacePreload.fullLoaded=loaded>=ids.length;
        selectedRacePreload.fullLoading=false;
        selectedRacePreload.analysisReady=analysisReady;
        selectedRacePreload.lastError=failed?('race-detail failures '+failed):'';
        lastDetailsAt=Date.now();
        prebuildSpecialForecastPlans();
        render();
        scheduleTopRefresh();
        if(failed&&attempt<1)setTimeout(function(){requestDetails(1)},1200)
      })
      .finally(function(){detailsInFlight=false})
  }

  fastTopRefresh=function(){
    if(seq!==state.requestSeq||state.date!==d)return;
    requestList(0);
    if(!lastDetailsAt||Date.now()-lastDetailsAt>=240000)requestDetails(0)
  };
  requestList(0)
}
var arvexqBootPainted=false;window.onerror=function(msg,src,line,col,err){try{console.error('ARVEXQ runtime error',msg,src,line,col,err||'')}catch(_e){};try{if(app&&!arvexqBootPainted&&app.querySelector&&app.querySelector('.boot')){var where=(src?String(src).split('/').pop():'')+(line?':'+line:'');app.innerHTML='<div class="notice" style="margin:20px">起動エラー：'+esc(msg||'不明なエラー')+(where?'<br><small>'+esc(where)+'</small>':'')+'<br><button onclick="location.reload()">再読み込み</button></div>'}}catch(_e){};return false};
