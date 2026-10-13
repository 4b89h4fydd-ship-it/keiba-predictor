window.ARVEXQ_BUILD="v329";

(function(){
"use strict";
var CENTRAL=["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"];
var LOCAL=["門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"];
var COURSE={
"帯広":{lap:200,straight:200,dir:1,shape:"straight",turn:"直線",firstTurn:999},
"門別":{lap:1600,straight:330,dir:-1,shape:"wide",turn:"右",firstTurn:350},
"盛岡":{lap:1600,straight:300,dir:1,shape:"wide",turn:"左",firstTurn:300},
"水沢":{lap:1200,straight:245,dir:-1,shape:"compact",turn:"右",firstTurn:250},
"浦和":{lap:1200,straight:220,dir:1,shape:"compact",turn:"左",firstTurn:250},
"船橋":{lap:1400,straight:308,dir:1,shape:"boxy",turn:"左",firstTurn:300},
"大井":{lap:1600,straight:386,dir:-1,shape:"wide",turn:"右",firstTurn:350},
"川崎":{lap:1200,straight:300,dir:1,shape:"compact",turn:"左",firstTurn:250},
"金沢":{lap:1200,straight:236,dir:-1,shape:"pocket",turn:"右",firstTurn:250},
"笠松":{lap:1100,straight:201,dir:-1,shape:"compact",turn:"右",firstTurn:230},
"名古屋":{lap:1180,straight:240,dir:-1,shape:"spiral",turn:"右",firstTurn:250},
"園田":{lap:1051,straight:213,dir:-1,shape:"compact",turn:"右",firstTurn:220},
"姫路":{lap:1200,straight:230,dir:-1,shape:"boxy",turn:"右",firstTurn:260},
"高知":{lap:1100,straight:200,dir:-1,shape:"egg",turn:"右",firstTurn:220},
"佐賀":{lap:1100,straight:200,dir:-1,shape:"compact",turn:"右",firstTurn:230},
"札幌":{lap:1641,straight:266,dir:-1,shape:"round",turn:"右",firstTurn:300},
"函館":{lap:1627,straight:262,dir:-1,shape:"compact",turn:"右",firstTurn:270},
"福島":{lap:1600,straight:292,dir:-1,shape:"boxy",turn:"右",firstTurn:300},
"新潟":{lap:2223,straight:659,dir:1,shape:"long",turn:"左",firstTurn:450},
"東京":{lap:2084,straight:526,dir:1,shape:"long",turn:"左",firstTurn:400},
"中山":{lap:1667,straight:310,dir:-1,shape:"boxy",turn:"右",firstTurn:300},
"中京":{lap:1706,straight:413,dir:1,shape:"wide",turn:"左",firstTurn:350},
"京都":{lap:1783,straight:328,dir:-1,shape:"wide",turn:"右",firstTurn:350},
"阪神":{lap:1689,straight:357,dir:-1,shape:"wide",turn:"右",firstTurn:330},
"小倉":{lap:1615,straight:293,dir:-1,shape:"compact",turn:"右",firstTurn:280}
};
function courseProfile(r){
  r=r||{};
  return COURSE[r.track]||{lap:1400,straight:300,dir:-1,shape:"wide",turn:"右",firstTurn:300}
}
function firstTurnDistance(r){r=r||{};var direct=n(r.firstTurnDistance||r.startToFirstTurn||r.firstCornerDistance||r.firstCornerMeters,0);return direct>0?direct:n(courseProfile(r).firstTurn,300)}
function coursePathD(p){if(p.shape==="straight")return "M18 92 L182 92";if(p.shape==="round")return "M174 90 C174 42 142 18 97 18 C50 18 22 46 22 90 C22 134 50 162 97 162 C142 162 174 138 174 90 Z";if(p.shape==="long")return "M184 90 C184 53 160 34 126 34 L67 34 C34 34 16 54 16 90 C16 126 34 146 67 146 L126 146 C160 146 184 127 184 90 Z";if(p.shape==="boxy")return "M178 90 C178 57 158 36 130 32 L66 32 C36 36 20 58 20 90 C20 122 36 144 66 148 L130 148 C158 144 178 123 178 90 Z";if(p.shape==="pocket")return "M176 91 C176 52 151 29 116 27 L69 30 C36 33 18 56 20 91 C21 126 40 147 73 151 L124 147 C157 142 176 122 176 91 Z";if(p.shape==="spiral")return "M178 91 C178 52 154 31 118 29 L72 31 C38 33 18 56 20 91 C22 128 44 148 78 149 L125 145 C157 140 178 120 178 91 Z";if(p.shape==="egg")return "M177 91 C177 49 147 25 106 24 C66 23 31 43 21 78 C11 113 31 146 71 154 C115 162 158 142 174 111 C178 103 179 97 177 91 Z";return "M176 90 C176 51 151 28 116 28 L72 28 C38 28 20 51 20 90 C20 129 38 152 72 152 L116 152 C151 152 176 129 176 90 Z"}
function normFrac(x){x=x%1;return x<0?x+1:x}
function courseStageFrac(r,st){
  r=r||{};
  var p=courseProfile(r);
  if(p.shape==="straight")return st===0?.05:(st===1?.67:.92);
  var laps=Math.max(.1,n(r.distance,1200)/p.lap),start=normFrac(.965-p.dir*(laps%1)),prog=st===0?.015:(st===1?.81:.965);
  return normFrac(start+p.dir*laps*prog)
}
var app=document.getElementById("app");
var state={date:today(),circuit:"地方",races:[],track:null,race:null,raceLoading:null,picker:false,loading:false,error:null,timer:null,anim:null,simSpeed:5,simTarget:20,simRunning:false,simPaused:false,simStopped:false,simIndex:0,simDone:0,simCounts:null,simCurrentT:0,pred:null,requestSeq:0,detailSeq:0,raceReturnPicker:false,historyTimer:null,raceStack:[],historyPrefetch:{},paceStage:0,horseModalNo:null,detailHorseNo:null,subPage:null,subPageReturnPanel:null,collectingHorse:null,collectTimer:null,scenarioCode:null,analysisSaved:{},openPanel:null,oddsBusy:false,oddsRefreshAt:{},oddsTimer:null,environmentTimer:null,environmentBusy:false,bootstrapReady:false,bootstrapProgress:null,resultTimer:null,homePage:null,aiStatsTrack:null,pickCircuit:null,raceReturnHomePage:null,raceReturnPickCircuit:null};
var dailyAiStats={date:"",loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,centralPodiumHits:0,centralPodiumTotal:0,localPodiumHits:0,localPodiumTotal:0,markedPodiumSum:0,holePlaceHits:0,top2Hits:0,top3Hits:0,candidateOrderMisses:0,candidateMisses:0,highConfHits:0,highConfTotal:0,brierSum:0,logLossSum:0,reasons:{},rows:[],error:""},dailyAiStatsJob=0;
var previousAiStats={date:"",loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,markedPodiumSum:0,rows:[],error:""},previousAiStatsJob=0;
var liveCenterOpen=false,liveCenterTrack="",liveCenterCircuit="";

var ARVEXQ_RACE_CACHE_SCHEMA="horse-race-source-v362";
function cacheKey(d,c){return "arvexq:"+ARVEXQ_RACE_CACHE_SCHEMA+":races:"+d+":"+(c||state.circuit||"")}
function loadRaceCache(d,c){try{var raw=localStorage.getItem(cacheKey(d,c));if(!raw)return null;var x=JSON.parse(raw);if(!x||!Array.isArray(x.rows))return null;if(d>=today()&&Date.now()-n(x.ts)>2*60000)return null;return x.rows}catch(e){return null}}
function saveRaceCache(d,c,rows){try{localStorage.setItem(cacheKey(d,c),JSON.stringify({ts:Date.now(),rows:rows}))}catch(e){}}
function fullBundleKey(d){return "arvexq:"+ARVEXQ_RACE_CACHE_SCHEMA+":fullbundle:"+String(d||"")}
function saveFullBundle(d,body){
  try{
    if(!body||body.complete!==true||!(body.races||[]).length||!(body.details||[]).length)return;
    localStorage.setItem(fullBundleKey(d),JSON.stringify({ts:Date.now(),body:body}))
  }catch(e){}
}
function loadFullBundle(d){
  try{
    var raw=localStorage.getItem(fullBundleKey(d));if(!raw)return null;
    var x=JSON.parse(raw);if(!x||!x.body||x.body.complete!==true)return null;
    var age=Date.now()-n(x.ts);
    if(d>=today()&&age>5*60000)return null;
    return x.body
  }catch(e){return null}
}
function detailCacheKey(id){return "arvexq:"+ARVEXQ_RACE_CACHE_SCHEMA+":detail:"+String(id||"")}
function loadDetailCache(id,allowStale){try{var raw=localStorage.getItem(detailCacheKey(id));if(!raw)return null;var x=JSON.parse(raw);if(!x||!x.row)return null;var age=Date.now()-n(x.ts);if(!allowStale&&x.row.date>=today()&&age>2*60000)return null;var r=x.row;if(!raceDisplayCoreReady(r,r))return null;return r}catch(e){return null}}
function saveDetailCache(id,row){try{if(!id||!row||!raceDisplayCoreReady(row,row))return;localStorage.setItem(detailCacheKey(id),JSON.stringify({ts:Date.now(),row:row}))}catch(e){}}
// On upgrade, discard only obsolete device race data, never saved forecasts.
function evictRetiredRaceCaches(){
  try{
    var marker="arvexq:race-source-schema";
    if(localStorage.getItem(marker)===ARVEXQ_RACE_CACHE_SCHEMA)return;
    for(var i=localStorage.length-1;i>=0;i--){
      var key=String(localStorage.key(i)||"");
      if(/^arvexq:[^:]+:(races|fullbundle|detail):/.test(key))localStorage.removeItem(key);
    }
    localStorage.setItem(marker,ARVEXQ_RACE_CACHE_SCHEMA)
  }catch(e){}
}
function installPwaCache(){
  // Online-first stability: stale service workers were intercepting fresh v329
  // assets/API navigation on iPhone. Unregister them and use normal HTTP cache.
  try{
    if("serviceWorker" in navigator){
      navigator.serviceWorker.getRegistrations().then(function(rs){
        return Promise.all(rs.map(function(r){try{return r.unregister()}catch(e){return false}}))
      }).catch(function(){})
    }
    if("caches" in window){
      caches.keys().then(function(keys){
        return Promise.all(keys.map(function(k){return caches.delete(k)}))
      }).catch(function(){})
    }
  }catch(e){}
}
function today(){var d=new Date(Date.now()+9*3600000);return d.toISOString().slice(0,10)}
function previousDateKey(iso){var p=String(iso||today()).split('-'),y=n(p[0]),m=n(p[1]),d=n(p[2]);if(!y||!m||!d)return'';return new Date(Date.UTC(y,m-1,d)-86400000).toISOString().slice(0,10)}
function esc(v){return String(v==null?"":v).replace(/[&<>\"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]})}
function n(v,d){var x=Number(v);return isFinite(x)?x:(d||0)}
function clamp(x,a,b){return Math.max(a,Math.min(b,x))}
function pct(v){return Math.round(clamp(n(v),0,1)*100)+"%"}
function mean(a){if(!a.length)return 0;var s=0,i;for(i=0;i<a.length;i++)s+=a[i];return s/a.length}
function placeRate(s){s=s||{};var starts=n(s.starts);return starts?(n(s.wins)+n(s.seconds)+n(s.thirds))/starts:0}
function season(iso){var m=n(String(iso||"").split("-")[1]);if(m>=3&&m<=5)return"春";if(m>=6&&m<=8)return"夏";if(m>=9&&m<=11)return"秋";return"冬"}
function fmtMoney(v){try{return new Intl.NumberFormat("ja-JP").format(n(v))}catch(e){return String(n(v))}}
function fmtTime(v){v=n(v);if(!v)return"—";var m=Math.floor(v/60),s=(v-m*60).toFixed(1);if(m===0)return s;return m+":"+(Number(s)<10?"0":"")+s}
function derivedFrame(no,total){no=n(no,0);total=n(total,0);if(no<1)return 1;if(total<=0)total=Math.max(8,no);if(total<=8)return clamp(no,1,8);if(total<=16){var singles=16-total;if(no<=singles)return clamp(no,1,8);return clamp(singles+Math.ceil((no-singles)/2),1,8)}var tripleFrames=Math.min(2,Math.max(0,total-16)),doubleFrames=8-tripleFrames,doubleHorseMax=doubleFrames*2;if(no<=doubleHorseMax)return clamp(Math.ceil(no/2),1,8);return clamp(doubleFrames+Math.ceil((no-doubleHorseMax)/3),1,8)}
function raceHasBrokenFrames(r){var hs=(r&&r.horses)||[];if(hs.length<=8)return false;for(var i=0;i<hs.length;i++){var no=n(hs[i].horseNumber,0),f=n(hs[i].frameNumber,0);if(f>8||(no>8&&f===no))return true}return false}
function frame(h){var raw=n(h&&h.frameNumber,0),no=n(h&&h.horseNumber,0),r=state&&state.race?state.race:null,total=r&&r.horses?(r.horses.length||0):0;if(raceHasBrokenFrames(r))return derivedFrame(no,total);if(raw>=1&&raw<=8)return raw;return derivedFrame(no,total)}
function badge(h){return '<span class="frame-badge frame'+frame(h)+'">'+esc(h&&h.horseNumber)+'</span>'}
function winOddsText(h){var v=h&&h.winOdds;if(v==null||v===''||Number(v)<=0)return'—';var x=Number(v);return isFinite(x)?(Math.round(x*10)/10).toFixed(1):String(v)}
function popularityText(h){var p=n(h&&h.popularity,0);return p>0?p+'人気':'—'}
function smartVal(v){if(v==null||v==='')return'—';var x=Number(v);if(isFinite(x))return (Math.round(x*10)/10).toString();return String(v)}
function sourceCollectionSection(h,r){var src=(r.dataSources||[]).filter(function(z){return String(z)!=='SmartRc'}),es=h.collectionState||{},ped=h&&h.pedigree||{},busy=es.status==='running',hasBase=!!(h&&(h.name||h.jockey||h.trainer)),hasRich=!!(h&&((h.recentRaces||[]).length||ped.sire||ped.dam||ped.damsire||h.owner||h.producer||h.debutNoHistory||Object.keys(h.extraSources||{}).length)),txt=busy?'取得中':(hasRich||es.status==='complete'?'取得済':(es.status==='error'?'再取得可':(hasBase?'基本情報取得済':'未取得')));return'<div class="detail-heading">情報取得</div><button type="button" class="horse-fetch-btn" data-horse-fetch="'+esc(h.horseNumber)+'">'+(busy?'取得中…':'この馬の情報取得')+'</button><div class="horse-fetch-note">予想はJRA/NAR公式の直近5走・通過順を中心に使用。Smart出走表のテン・上がり系指標は現在使用しません。</div><div class="source-strip"><span class="source-chip '+(busy?'busy':(hasRich||es.status==='complete'?'good':'neutral'))+'">'+esc(txt)+'</span>'+src.map(function(z){return'<span class="source-chip good">'+esc(z)+'</span>'}).join('')+'</div>'+(es.error?'<div class="muted">'+esc(es.error)+'</div>':'')}
function raceSourceStrip(r){var src=r.dataSources||[],es=r.enrichmentSearch||{},chips=[];for(var i=0;i<src.length;i++)chips.push('<span class="source-chip good">'+esc(src[i])+'</span>');if(!chips.length)chips.push('<span class="source-chip neutral">自動取得待ち</span>');if(es.status==='running')chips.unshift('<span class="source-chip busy">情報取得中</span>');return'<div class="source-strip">'+chips.join('')+'</div>'}
function horseByNo(r,no){var hs=r.horses||[],i;for(i=0;i<hs.length;i++)if(n(hs[i].horseNumber)===n(no))return hs[i];return null}
function resultStatus(r){var s=String(r&&r.result&&r.result.status||"");if(s==="速報"||s==="確定")return s;if(r&&r.raceStatus==="速報")return"速報";if(r&&r.raceStatus==="確定")return"確定";return""}
function isFinal(r){return resultStatus(r)==="確定"}
function isFlash(r){return resultStatus(r)==="速報"}
function hasAnyResultData(r){return ((r&&r.result||{}).finishers||[]).some(function(x){return n(x&&x.finish)>0})}
function hasResultData(r){var fs=((r&&r.result||{}).finishers||[]).filter(function(x){var pos=n(x&&x.finish,0);return pos>=1&&pos<=3});return fs.length>=3&&fs.some(function(x){return n(x.finish,0)===1})}
function mins(t){var m=String(t||"").match(/^(\d{1,2}):(\d{2})/);return m?n(m[1])*60+n(m[2]):9999}
function nowMins(){var d=new Date(Date.now()+9*3600000);return d.getUTCHours()*60+d.getUTCMinutes()}
function timeHtml(r){var a=String(r.startTime||"—"),o=String(r.scheduledStartTime||a),c=!!r.startTimeChanged||(a!==o&&a!=="—"&&o!=="—");return c?'<span class="time-old">'+esc(o)+'</span><span class="time-changed">'+esc(a)+' 修正</span>':esc(a)}
function header(title,back,sub){return '<header class="header"><div class="header-row">'+(back?'<button data-action="back">‹</button>':'')+'<div class="header-title"><h1>'+esc(title)+'</h1>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div><span class="build-badge" aria-label="ARVEXQ">ARVEXQ</span><button data-action="reload">↻</button></div></header>'}
function recencyWeights(len){var a=[],i;for(i=0;i<len;i++)a.push(Math.pow(.82,i));return a}
function weightedRate(vals,weights,def){var s=0,w=0,i;for(i=0;i<vals.length;i++){if(vals[i]==null)continue;var q=weights&&weights[i]!=null?weights[i]:1;s+=n(vals[i])*q;w+=q}return w?s/w:(def==null?.5:def)}
function raceField(rr){return Math.max(4,n(rr&&rr.fieldSize,12))}
function firstCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[0],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
function lastCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[p.length-1],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
// Consistent pre-race window: deduplicate first, then take the newest five
// starts. A sixth (older) race cannot substitute for a missing first corner.
function historicalWindow(h,r){
  function normDate(v){
    var t=String(v||'').replace(/\//g,'-').slice(0,10);
    return /^\d{8}$/.test(t)?t.slice(0,4)+'-'+t.slice(4,6)+'-'+t.slice(6,8):t
  }
  var target=normDate(r&&r.date),seen={},out=[];
  if(!/^\d{4}-\d\d-\d\d$/.test(target))return[];
  [].concat(h&&h.recentRaces||[],h&&h.allPastRuns||[]).forEach(function(rr){
    if(!rr||typeof rr!=='object')return;
    var d=normDate(rr.date||rr.raceDate),
        no=n(rr.raceNumber,n(rr.raceNo,0)),
        key=[d,String(rr.track||''),n(rr.distance,0),no].join('|');
    if(!/^\d{4}-\d\d-\d\d$/.test(d)||d>=target)return;
    if(!seen[key]){
      seen[key]=Object.assign({},rr,{date:d});out.push(seen[key]);return
    }
    var old=seen[key],a=Array.isArray(rr.cornerPositions)?rr.cornerPositions:[],
        b=Array.isArray(old.cornerPositions)?old.cornerPositions.slice():[];
    // Prefer the earlier source's observed places; fill absent positions from
    // another feed without discarding a verified first corner.
    a.forEach(function(v,j){if(n(b[j],0)<=0&&n(v,0)>0)b[j]=v});
    if(!old.earlyTiming&&rr.earlyTiming&&typeof rr.earlyTiming==='object')old.earlyTiming=rr.earlyTiming;
    if(b.length)old.cornerPositions=b;
    if(!n(old.finish)&&n(rr.finish))old.finish=rr.finish
  });
  out.sort(function(a,b){return b.date.localeCompare(a.date)||
    n(b.raceNumber,n(b.raceNo,0))-n(a.raceNumber,n(a.raceNo,0))});
  return out.slice(0,5)
}
function validFirstCorner(rr){
  var p=n(rr&&rr.cornerPositions&&rr.cornerPositions[0],0),field=n(rr&&rr.fieldSize,0);
  return Number.isInteger(p)&&p>=1&&(!field||p<=field)
}
function styleRates(h,r){
  var rs=historicalWindow(h,r),w=recencyWeights(rs.length),a=[0,0,0,0],
      den=0,early3=0,moved3=0,ten=0,samples=0;
  rs.forEach(function(rr,i){
    if(!validFirstCorner(rr))return;
    var first=n(rr.cornerPositions[0]),fs=raceField(rr),
        norm=(first-1)/Math.max(1,fs-1),delta=Math.abs(n(rr.distance)-n(r.distance)),
        rel=1,last=(rr.cornerPositions||[]).slice(1);
    if(delta<=100)rel*=1.22;
    else if(delta<=300)rel*=1.08;
    else if(delta>=700)rel*=.74;
    if(rr.track===r.track)rel*=1.10;
    if(rr.condition&&r.condition&&sameCondition(rr.condition,r.condition))rel*=1.05;
    var weight=w[i]*rel;den+=weight;samples++;
    if(first===1)a[0]+=weight;
    else if(first<=3||norm<=.22)a[1]+=weight;
    else if(norm<=.62)a[2]+=weight;
    else a[3]+=weight;
    if(first<=3)early3+=weight;
    if(first>3&&last.some(function(v){return n(v)>0&&n(v)<=3}))moved3+=weight;
    ten+=weight*clamp(1-(first-1)/Math.max(3,fs-1),0,1)
  });
  if(!den)return{front:0,stalk:0,mid:0,close:0,early3:0,moved3:0,
    ten:.5,samples:0,availableRuns:rs.length,unknown:true,source:'recent5'};
  return{front:a[0]/den,stalk:a[1]/den,mid:a[2]/den,close:a[3]/den,
    early3:early3/den,moved3:moved3/den,ten:ten/den,samples:samples,
    availableRuns:rs.length,unknown:false,source:'recent5'}
}
function horseEarlyTimingProfile(h,r){
  // This is a pre-race, five-run evidence adapter. Race-wide leader laps and
  // unreferenced estimates must never become individual measured values.
  var runs=historicalWindow(h,r),samples=[],weights=recencyWeights(runs.length),i;
  for(i=0;i<runs.length;i++){
    var raw=runs[i]&&runs[i].earlyTiming||{},kind=String(raw.sourceKind||''),
        source=String(raw.sourceRef||'').trim(),a=Number(raw.first200mSeconds),
        g=Number(raw.gateReactionSeconds),acc=Number(raw.acceleration0to100Mps2),
        has200=raw.first200mSeconds!=null&&isFinite(a)&&a>=7&&a<=25,
        hasGate=raw.gateReactionSeconds!=null&&isFinite(g)&&g>=.05&&g<=3,
        hasAcc=raw.acceleration0to100Mps2!=null&&isFinite(acc)&&acc>=.1&&acc<=10;
    if((kind!=='individual_sensor'&&kind!=='video_estimate')||!source||(!has200&&!hasGate&&!hasAcc))continue;
    // Visual estimates remain estimates even if derived from a frame index.
    samples.push({kind:kind,source:source,date:String(runs[i].date||''),weight:(weights[i]||1)*(kind==='individual_sensor'?1:.55),
      first200mSeconds:has200?a:null,gateReactionSeconds:hasGate?g:null,acceleration0to100Mps2:hasAcc?acc:null});
  }
  function weighted(key,transform){
    var sum=0,w=0; samples.forEach(function(z){if(z[key]==null)return;sum+=z.weight*transform(z[key]);w+=z.weight});return{score:w?clamp(sum/w,0,1):null,weight:w}
  }
  // Capped qualitative normalization, NOT a calibrated speed probability.
  var first=weighted('first200mSeconds',function(v){return(16.2-v)/5.2}),
      gate=weighted('gateReactionSeconds',function(v){return(1-v)/.85}),
      accel=weighted('acceleration0to100Mps2',function(v){return v/5.5}),
      scores=[],ws=[];
  if(first.score!=null){scores.push(first.score);ws.push(.72)}
  if(gate.score!=null){scores.push(gate.score);ws.push(.18)}
  if(accel.score!=null){scores.push(accel.score);ws.push(.10)}
  var sum=ws.reduce(function(a,b){return a+b},0),value=sum?scores.reduce(function(a,v,i){return a+v*ws[i]},0)/sum:null,
      reliability=Math.min(1,samples.reduce(function(a,z){return a+z.weight},0)/2),
      timingWeight=value==null?0:clamp(.14+.23*reliability,0,.37),
      gateWeight=gate.score==null?0:clamp(.12+.23*reliability,0,.35);
  return{samples:samples,sourceKind:samples.some(function(x){return x.kind==='individual_sensor'})?'individual_sensor':(samples.length?'video_estimate':'none'),
    first200Score:first.score,gateScore:gate.score,accelerationScore:accel.score,
    timingScore:value,timingWeight:timingWeight,gateWeight:gateWeight,
    measuredSamples:samples.filter(function(x){return x.kind==='individual_sensor'}).length,
    videoSamples:samples.filter(function(x){return x.kind==='video_estimate'}).length}
}
function tenScore(h,r){
  // First-corner position proxy: not a measured individual opening furlong.
  var x=styleRates(h,r);return x.samples?clamp(x.ten,0,1):.5
}
function firstThreeType(h,r){var rr=historicalWindow(h,r)[0],p=rr&&rr.cornerPositions||[],j;if(!p.length)return"不明";if(n(p[0])>0&&n(p[0])<=3)return"最初から前";for(j=1;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3)return"途中から上昇";return"前走は中後方"}
function fadeRate(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),e=0,f=0,i,p,first,last,fin,fs,ww,sev;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];first=n(p[0]);if(!first||first>4)continue;ww=w[i];fs=raceField(rs[i]);last=n(p[p.length-1]);fin=n(rs[i].finish);if(!last&&!fin)continue;e+=ww;sev=0;if(last)sev=Math.max(sev,clamp((last-first)/Math.max(3,fs-1)*2.2,0,1));if(fin)sev=Math.max(sev,clamp((fin-first)/Math.max(3,fs-1)*1.8,0,1));if((last&&last>=first+2)||(fin&&fin>=first+3))sev=Math.max(sev,.55);f+=ww*sev}return e?clamp(f/e,0,1):.25}
function moveRate(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),e=0,g=0,i,p,a,b,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(p.length<2)continue;a=n(p[0]);b=n(p[p.length-1]);if(!a||!b)continue;ww=w[i];e+=ww;if(b<=a-2)g+=ww}return e?g/e:.2}
function holdRate(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),e=0,g=0,i,p,a,b,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);b=n(p[p.length-1]);if(!a||a>4)continue;ww=w[i];e+=ww;if((b&&b<=4)||(n(rs[i].finish)>0&&n(rs[i].finish)<=4))g+=ww}return e?g/e:.5}
function yieldFlex(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),e=0,g=0,i,p,a,fin,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);if(!a||a===1||a>5)continue;ww=w[i];e+=ww;if(fin>0&&fin<=4)g+=ww}return e?g/e:.45}

function breakReliability(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),v=[],ws=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);v.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1));ws.push(w[i])}return weightedRate(v,ws,.5)}
function lateGainScore(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),v=[],ws=[],i,p,a,b,fin,fs,g;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!p.length)continue;a=n(p[p.length-1]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||!fin)continue;g=(a-fin)/Math.max(3,fs-1);v.push(clamp(.5+g*1.8,0,1));ws.push(w[i])}return weightedRate(v,ws,.5)}
function positionConsistency(h,r){var rs=historicalWindow(h,r),vals=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);vals.push((n(p[0])-1)/Math.max(3,fs-1))}if(vals.length<2)return.5;var m=mean(vals),vv=0;for(i=0;i<vals.length;i++)vv+=(vals[i]-m)*(vals[i]-m);vv/=vals.length;return clamp(1-Math.sqrt(vv)*2.1,0,1)}
function positionTrend(h,r){var rs=historicalWindow(h,r),vals=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);vals.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1))}if(vals.length<3)return 0;var cut=Math.min(2,vals.length-1),recent=mean(vals.slice(0,cut)),older=mean(vals.slice(cut));return clamp(recent-older,-.45,.45)}
// Prior-race 4C-to-finish outcomes, independent of initial running-style classification.
function finishingEvidence(h,r){
 var rs=historicalWindow(h,r),w=recencyWeights(rs.length),
     holdW=0,held=0,closeW=0,converted=0,hs=0,cs=0,hw=0,cw=0;
 rs.forEach(function(rr,i){
   var ps=rr.cornerPositions||[],fs=raceField(rr),first=n(ps[0],0),
       last=n(ps[ps.length-1],0),fin=n(rr.finish,n(rr.finishPosition,0));
   if(ps.length<2||!Number.isInteger(last)||last<1||last>fs||
      !Number.isInteger(fin)||fin<1||fin>fs)return;
   if(first>0&&first<=4){
     holdW+=w[i];hs++;
     if(last<=4&&fin<=4){held+=w[i];hw++}
   }
   if(last>=4){
     closeW+=w[i];cs++;
     if(fin<=3&&fin<last){converted+=w[i];cw++}
   }
 });
 return {hold:holdW?held/holdW:.5,closing:closeW?converted/closeW:.5,
   holdSamples:hs,closingSamples:cs,holdWins:hw,closingWins:cw,window:rs.length}
}
function earlyCollapseSeverity(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),vals=[],ws=[],i,p,a,fin,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||a>4||!fin)continue;vals.push(clamp((fin-a)/Math.max(3,fs-1),0,1));ws.push(w[i])}return weightedRate(vals,ws,.18)}
// v244: same-day live track bias.  Use ONLY races already run at the same venue/date.
// It is intentionally market-independent and shrunk hard toward neutral when sample size is small.
function raceLiveBias(r,rows){
  rows=rows||[];
  var date=String(r&&r.date||state.date||''),circuit=String(r&&r.circuit||state.circuit||''),track=String(r&&r.track||state.track||''),raceNo=n(r&&r.raceNumber,99),
      completed=0,frameW=0,innerW=0,outerW=0,styleW=0,frontW=0,lateW=0,source=[];
  (state.races||[]).forEach(function(z){
    if(!z||String(z.date||date)!==date||String(z.circuit||'')!==circuit||String(z.track||'')!==track)return;
    if(n(z.raceNumber,99)>=raceNo)return;
    var d=resultDetailForTrend(z),fs=((d&&d.result||{}).finishers||[]).filter(function(x){return n(x&&x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});
    if(!fs.length)return;
    completed++;
    var gap=Math.max(1,raceNo-n(z.raceNumber,0)),rw=Math.pow(.86,Math.max(0,gap-1)),field=Math.max(1,n(d.fieldSize,(d.horses||[]).length||fs.length));
    source.push(n(z.raceNumber));
    fs.slice(0,3).forEach(function(f){
      var h,fr=n(f.frameNumber,0);if(!fr&&(d.horses||[]).length){h=(d.horses||[]).find(function(q){return n(q.horseNumber)===n(f.horseNumber)});fr=n(h&&h.frameNumber,0)}
      if(fr){var maxFrame=Math.max(2,Math.min(8,Math.ceil(field/2))),inside=clamp(1-(fr-1)/Math.max(1,maxFrame-1),0,1);frameW+=rw;innerW+=rw*inside;outerW+=rw*(1-inside)}
      var cp=(f.cornerPositions||[]).filter(function(v){return n(v)>0});
      if(cp.length){var pos=n(cp[0]),frontCut=Math.max(2,Math.ceil(field*.22)),lateCut=Math.max(frontCut+1,Math.ceil(field*.55));styleW+=rw;if(pos<=frontCut)frontW+=rw;else if(pos>=lateCut)lateW+=rw}
    })
  });
  var frameRaw=frameW?innerW/frameW:.5,frontRaw=styleW?frontW/styleW:.5,lateRaw=styleW?lateW/styleW:.25,
      evidence=clamp((completed/4)*.58+(Math.min(frameW,9)/9)*.22+(Math.min(styleW,9)/9)*.20,0,1),
      frameBias=.5+(frameRaw-.5)*evidence,frontBias=.5+(frontRaw-.5)*evidence,lateBias=.5+(lateRaw-.25)*evidence;
  var maxFrame=8;
  (r&&r.horses||[]).forEach(function(h){maxFrame=Math.max(maxFrame,n(h.frameNumber,0))});
  var byNo={};rows.forEach(function(x){
    var h=x.horse||{},fr=n(h.frameNumber,0),inside=fr?clamp(1-(fr-1)/Math.max(1,maxFrame-1),0,1):clamp(1-(n(h.horseNumber,1)-1)/Math.max(1,rows.length-1),0,1),
        rt=styleRates(h,r),early=clamp(rt.front*.52+rt.stalk*.28+rt.early3*.20,0,1),late=clamp(rt.mid*.30+rt.close*.48+rt.moved3*.22,0,1),
        drawFit=clamp(.5+(inside-.5)*(frameBias-.5)*4.0,0,1),
        styleSignal=frontBias-.5-(lateBias-.5)*.72,
        styleFit=clamp(.5+(early-late)*styleSignal*2.8,0,1);
    byNo[n(h.horseNumber)]={drawFit:drawFit,styleFit:styleFit,inside:inside,early:early,late:late}
  });
  return {completed:completed,evidence:evidence,frameBias:frameBias,frontBias:frontBias,lateBias:lateBias,byNo:byNo,sourceRaces:source}
}
// v313: same-day mark correction.  Only races that have already finished at the
// same venue/date are allowed to influence later marks.  One result is never enough:
// activation starts at two completed races and is strongly shrunk until 4-5 races.
function sameDayTrendSignatureV313(r,rows){
  // Observational results are not an approved trigger for recalculating marks.
  return 'morning-fixed-official-condition-only-v346'
}
function stylePoint(rt){return rt.front+2*rt.stalk+3*rt.mid+4*rt.close}
function styleName(pt){if(pt<1.65)return"逃げ";if(pt<2.35)return"先行";if(pt<3.15)return"差し";return"追込"}
function earlyOcc(r){var hs=r.horses||[],nums=[],early=[],moved=[],i,rr,p,j,hit;for(i=0;i<hs.length;i++){rr=(hs[i].recentRaces||[])[0];if(!rr)continue;p=rr.cornerPositions||[];hit=false;for(j=0;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3){hit=true;break}if(hit){nums.push(n(hs[i].horseNumber));if(n(p[0])<=3)early.push(n(hs[i].horseNumber));else moved.push(n(hs[i].horseNumber))}}return{nums:nums,early:early,moved:moved,rate:hs.length?nums.length/hs.length:0}}
// Use only prior races for early-position evidence. A takeover at 3C/4C is
// never treated as a fast start. Neither odds nor post-race target data enter.
function paceHistoryRuns(h,r){
  return historicalWindow(h,r).filter(validFirstCorner)
}
function minetaPastProfile(h,r){
  var rs=paceHistoryRuns(h,r),last=rs[0]||null,
      lp=(last&&last.cornerPositions||[]).map(function(v){return n(v,0)}).filter(function(v){return v>0}),
      field=last?raceField(last):12,first=lp.length?lp[0]:0,prevEarly=first>0&&first<=3,prevLeader=first===1,
      prevRear=first>=Math.max(6,Math.ceil(field*.66)),w=recencyWeights(rs.length),
      moveW=0,moveDen=0,leadW=0,leadDen=0,earlyW=0,rearW=0,rearDen=0,i,rr,p,j,best,ww,fs,midLead;
  for(i=0;i<rs.length;i++){
    rr=rs[i]||{};p=(rr.cornerPositions||[]).map(function(v){return n(v,0)}).filter(function(v){return v>0});
    if(!p.length)continue;
    fs=raceField(rr);ww=(w[i]||1)*(String(rr.track||'')===String(r&&r.track||'')?1.10:1)*
      (Math.abs(n(rr.distance,0)-n(r&&r.distance,0))<=200?1.12:1);
    best=99;for(j=1;j<p.length;j++)if(p[j]<best)best=p[j];
    moveDen+=ww;if(p[0]>3&&best<=Math.max(3,p[0]-2))moveW+=ww;
    leadDen+=ww;if(p[0]===1)leadW+=ww;if(p[0]<=3)earlyW+=ww;
    midLead=p[0]>1&&p.slice(1).some(function(v){return v===1});if(midLead)moveW+=ww*.25;
    rearDen+=ww;if(p[0]>=Math.max(6,Math.ceil(fs*.66)))rearW+=ww
  }
  var norm=first?((first-1)/Math.max(1,field-1)):1,bucket='不明';
  if(lp.length){if(prevEarly)bucket='先行';else if(norm<=.38)bucket='準先行';else if(norm<=.68)bucket='準後方';else bucket='後方'}
  // Recompute true midrace-takeover share separately from 3C move rate.
  var midLeadW=0;for(i=0;i<rs.length;i++){
    rr=rs[i];p=rr.cornerPositions||[];
    if(n(p[0],0)>1&&p.slice(1).some(function(v){return n(v,0)===1})){
      ww=(w[i]||1)*(String(rr.track||'')===String(r&&r.track||'')?1.10:1)*
        (Math.abs(n(rr.distance,0)-n(r&&r.distance,0))<=200?1.12:1);
      midLeadW+=ww
    }
  }
  return{samples:rs.length,firstCornerSamples:rs.length,prevEarly:prevEarly,prevLeader:prevLeader,
    prevRear:prevRear,firstPos:first,lastPositions:lp,bucket:bucket,
    leadRate:leadDen?leadW/leadDen:0,earlyRate:leadDen?earlyW/leadDen:0,
    moveHistory:moveDen?moveW/moveDen:0,midRaceLead:leadDen?midLeadW/leadDen:0,
    rearHistory:rearDen?rearW/rearDen:0}
}
function minetaRaceContext(rows,r){
  rows=rows||[];var active=rows.filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)}),field=Math.max(1,active.length),raw=0,adjusted=0,rear=0,leadPool=[],
      av=active.map(function(x){return n(x.ability,.5)}).sort(function(a,b){return a-b}),abilityMed=av.length?av[Math.floor(av.length/2)]:.5;
  active.forEach(function(z){
    var p=z.minetaPast||minetaPastProfile(z.horse,r);z.minetaPast=p;
    var early=!!p.prevEarly||(p.firstCornerSamples>=2&&n(p.earlyRate)>=.48),
        forwardEvidence=!!p.prevLeader||p.bucket==='準先行'||p.midRaceLead>=.20||p.moveHistory>=.35||
          (n(z.ten,.5)>=.58&&n(z.breakSkill,.5)>=.52)||
          (n(z.ability,.5)>=abilityMed&&p.rearHistory<.45&&n(z.positionTrend,.5)>=.50),
        adjustedEarly=early||(!!z.lengthen&&p.samples>0&&forwardEvidence&&p.rearHistory<.70);
    z.minetaEarlyIntent=adjustedEarly;z.minetaRawEarly=early;z.minetaLengthenForward=!!(adjustedEarly&&!early);
    if(early)raw++;if(adjustedEarly)adjusted++;if(p.prevRear)rear++
  });
  leadPool=active.filter(function(z){var q=z.minetaPast||{};return (q.prevLeader&&n(q.earlyRate)>=.25)||(q.firstCornerSamples>=2&&n(q.leadRate)>=.22)||z.rawFront>=.18||z.goProbBase>=.50||z.lengthen}).sort(function(a,b){
    var ap=a.minetaPast||{},bp=b.minetaPast||{};
    if(n(bp.leadRate)!==n(ap.leadRate))return n(bp.leadRate)-n(ap.leadRate);
    if(n(bp.earlyRate)!==n(ap.earlyRate))return n(bp.earlyRate)-n(ap.earlyRate);
    if(!!b.lengthen!==!!a.lengthen)return b.lengthen?1:-1;
    if(n(b.rawFront)!==n(a.rawFront))return n(b.rawFront)-n(a.rawFront);
    if(n(b.ten)!==n(a.ten))return n(b.ten)-n(a.ten);
    if(n(b.breakSkill)!==n(a.breakSkill))return n(b.breakSkill)-n(a.breakSkill);
    if(n(b.needLead)!==n(a.needLead))return n(b.needLead)-n(a.needLead);
    if(n(b.ability)!==n(a.ability))return n(b.ability)-n(a.ability);
    return n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  leadPool.slice(0,3).forEach(function(z,k){z.minetaLeadRank=k+1});
  var rawOcc=raw/field,adjustedOcc=adjusted/field,rearOcc=rear/field,band=rawOcc<=.25?'前少なめ':(rawOcc>=.45?'前多め':'中間');
  return{field:field,rawFrontCount:raw,adjustedFrontCount:adjusted,rearCount:rear,rawOcc:rawOcc,adjustedOcc:adjustedOcc,rearOcc:rearOcc,band:band,
    firstTurn:firstTurnDistance(r),leadNos:leadPool.slice(0,3).map(function(z){return n(z.horse.horseNumber)})}
}
function minetaAssignRoles(rows,r,ctx,pressure){
  rows=rows||[];ctx=ctx||minetaRaceContext(rows,r);pressure=pressure||pressureInfo(rows);
  var byNo={},abilityVals=rows.map(function(z){return n(z.ability,.5)}).sort(function(a,b){return a-b}),abilityMed=abilityVals.length?abilityVals[Math.floor(abilityVals.length/2)]:.5;
  rows.forEach(function(z){byNo[n(z.horse.horseNumber)]=z});
  rows.forEach(function(x){
    var no=n(x.horse.horseNumber),p=x.minetaPast||minetaPastProfile(x.horse,r),q=pressure[no]||{},
        left=byNo[no-1],left2=byNo[no-2],right=byNo[no+1],right2=byNo[no+2],role='不明',notes=[];
    if(!p.firstPos){x.expected='不明';x.minetaRole='不明';x.minetaNotes=['初角通過順位不足'];return}
    if((p.firstCornerSamples>=2&&p.leadRate>=.26)||
       (p.prevLeader&&n(x.rawFront,x.front)>=.22))role='逃げ候補';
    else if(p.prevEarly||p.bucket==='先行')role='先行';
    else if(p.bucket==='準先行')role='好位';
    else if(p.bucket==='準後方')role='中団';
    else role='後方';

    if(p.midRaceLead>=.20||p.moveHistory>=.35){if(role==='後方')role='中団';else if(role==='中団'&&n(x.ability)>=abilityMed)role='好位';notes.push(p.midRaceLead>=.20?'道中先頭歴':'道中進出歴')}
    if(x.lengthen&&x.minetaLengthenForward){if(role==='後方'&&(n(x.move)>=.28||n(x.ability)>=abilityMed))role='中団';else if(role==='中団'&&ctx.rawOcc<=.33)role='好位';notes.push('距離延長＋前進根拠あり')}
    if(x.shorten&&ctx.rawOcc>=.45){if(role==='好位'&&!p.prevEarly)role='中団';if(role==='中団'&&n(x.rawClose,x.close)>=.35)role='後方';notes.push('前多め＋距離短縮で脚ため')}
    if(ctx.rawOcc<=.25&&ctx.rearOcc>=.45){if(role==='中団'&&(n(x.ability)>=abilityMed||n(x.move)>=.30))role='好位';else if(role==='後方'&&n(x.move)>=.45)role='中団';notes.push('後方馬多く相対的に前')}

    x.minetaEscapeOutside=!!(left&&n(left.minetaLeadRank,0)>0&&n(left.minetaLeadRank)<=2&&!x.minetaEarlyIntent);
    x.minetaStrongLeaderOutside=!!(left&&n(left.minetaLeadRank,0)===1&&n(left.ability,.5)>=abilityMed&&!x.minetaEarlyIntent);
    x.minetaEscapeSandwich=!!(left&&right&&left.minetaEarlyIntent&&right.minetaEarlyIntent&&!x.minetaEarlyIntent);
    x.minetaSameStyleCrowd=!!((left&&left.minetaPast&&left.minetaPast.bucket===p.bucket)||(right&&right.minetaPast&&right.minetaPast.bucket===p.bucket));
    x.minetaDifferentStyleNeighbor=!!(
      (left&&left2&&left.minetaPast&&left2.minetaPast&&left.minetaPast.bucket===left2.minetaPast.bucket&&left.minetaPast.bucket!==p.bucket)||
      (right&&right2&&right.minetaPast&&right2.minetaPast&&right.minetaPast.bucket===right2.minetaPast.bucket&&right.minetaPast.bucket!==p.bucket)
    );
    if(x.minetaEscapeSandwich)notes.push('逃げ挟み');
    if(x.minetaStrongLeaderOutside)notes.push('強い先行馬の外');
    else if(x.minetaEscapeOutside)notes.push('逃げ馬の外');
    if(x.minetaSameStyleCrowd)notes.push('同脚質並び');
    if(x.minetaDifferentStyleNeighbor)notes.push('同脚質の塊の隣');
    if(p.prevEarly)notes.push('前走3番手以内');
    if(ctx.rawOcc>=.45&&x.minetaEarlyIntent&&x.outer)notes.push('前多め＋外で先行負荷');
    if(ctx.firstTurn<300&&x.minetaEarlyIntent&&x.inner)notes.push('初角近く内で先行しやすい');

    if(n(x.minetaLeadRank,0)===1&&role!=='不明')role='逃げ候補';
    else if(n(x.minetaLeadRank,0)>1&&role==='逃げ候補')role='先行';

    x.expected=role;x.minetaRole=role;x.minetaNotes=notes.slice(0,5);
    if(role==='逃げ候補')x.goProb=Math.max(n(x.goProb),.64);
    else if(role==='先行')x.goProb=Math.max(n(x.goProb),.53);
    else if(role==='好位')x.goProb=clamp(n(x.goProb),.38,.56);
    else if(role==='中団')x.goProb=Math.min(n(x.goProb),.44);
    else if(role==='後方')x.goProb=Math.min(n(x.goProb),.34);
    if(x.minetaEscapeOutside){x.flexibility=clamp(n(x.flexibility,.5)+.05,0,1);x.trafficTol=clamp(n(x.trafficTol,.5)+.05,0,1)}
    if(x.minetaStrongLeaderOutside){x.latePower=clamp(n(x.latePower,.5)+.035,0,1);x.move=clamp(n(x.move,.2)+.035,0,1)}
    if(x.minetaEscapeSandwich){x.trafficTol=clamp(n(x.trafficTol,.5)+.08,0,1);x.latePower=clamp(n(x.latePower,.5)+.04,0,1)}
    if(x.minetaDifferentStyleNeighbor){x.flexibility=clamp(n(x.flexibility,.5)+.035,0,1);x.trafficTol=clamp(n(x.trafficTol,.5)+.035,0,1)}
    if(ctx.firstTurn<300&&x.minetaEarlyIntent&&x.inner){x.goProb=clamp(n(x.goProb,.5)+.04,0,1);x.frontStay=clamp(n(x.frontStay,.5)+.025,0,1)}
    if(x.minetaSameStyleCrowd&&!x.minetaEscapeOutside&&!x.minetaEscapeSandwich&&!x.minetaDifferentStyleNeighbor)x.frontCost=clamp(n(x.frontCost,0)+.025,0,.30)
  });
  return ctx
}
function minetaStructureText(ctx){
  if(!ctx)return'';
  var bits=['先行占有 '+Math.round(ctx.rawOcc*100)+'%','距離補正後 '+Math.round(ctx.adjustedOcc*100)+'%','後方占有 '+Math.round(ctx.rearOcc*100)+'%'];
  if(ctx.band==='前少なめ')bits.push('前残りだけでなく強い先行馬を目標にする外の馬も重視');
  else if(ctx.band==='前多め')bits.push('競り合い消耗・内外・同脚質並び・差し巻き返しを重視');
  else bits.push('隊列・並び・逃げ挟み・同脚質の塊の隣を重視');
  return bits.join('｜')
}
function recentDistance(h){var rr=(h.recentRaces||[])[0];return rr?n(rr.distance):0}
function recentFirst(h){var rr=(h.recentRaces||[])[0],p=rr&&rr.cornerPositions||[];return n(p[0],99)}
function targetSeason(r){return season(r.date)}
function sameCondition(a,b){a=String(a||"");b=String(b||"");return a&&b&&a!=="不明"&&b!=="不明"&&a===b}
function contextualRuns(h,r){var rs=(h.allPastRuns||h.recentRaces||[]),tw=targetSeason(r),out={track:[],distance:[],condition:[],weather:[],season:[],surface:[],level:[]},i,rr,delta;for(i=0;i<rs.length;i++){rr=rs[i];delta=Math.abs(n(rr.distance)-n(r.distance));if(rr.track===r.track)out.track.push(rr);if(delta<=100||(n(r.distance)>=1800&&delta<=200))out.distance.push(rr);if(sameCondition(rr.condition,r.condition))out.condition.push(rr);if(String(rr.weather||"")===String(r.weather||"")&&r.weather&&r.weather!=="不明")out.weather.push(rr);if(season(rr.date)===tw)out.season.push(rr);if(n(r.racePrize1)>0&&n(rr.racePrize1)>=n(r.racePrize1)*.8)out.level.push(rr)}return out}
function runFinishQuality(rr){var f=n(rr.finish,0),fs=raceField(rr);if(!f)return.45;return clamp(1-(f-1)/Math.max(3,fs-1),0,1)}
function runTimeIndex(rr,targetDist){var t=n(rr.timeSeconds),d=n(rr.distance);if(!t||!d)return null;var speed=d/t,distPenalty=1-Math.min(.28,Math.abs(d-targetDist)/Math.max(600,targetDist)*.55),cond=String(rr.condition||"");var surfaceAdj=1;if(cond.indexOf("重")>=0||cond.indexOf("不")>=0)surfaceAdj=.985;else if(cond.indexOf("稍")>=0)surfaceAdj=.993;return speed*distPenalty/surfaceAdj}
function recentFinishScore(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),v=[],i;for(i=0;i<rs.length;i++)v.push(runFinishQuality(rs[i]));return weightedRate(v,w,.45)}
function speedRaw(h,dist){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),vals=[],ws=[],i,x;for(i=0;i<rs.length;i++){x=runTimeIndex(rs[i],dist);if(x!=null){vals.push(x);ws.push(w[i])}}if(!vals.length)return 0;var best=Math.max.apply(null,vals),avg=weightedRate(vals,ws,0);return best*.55+avg*.45}
function normalize(vals,x){var v=vals.filter(function(z){return isFinite(z)&&z>0});if(!v.length||!isFinite(x)||x<=0)return.5;var lo=Math.min.apply(null,v),hi=Math.max.apply(null,v);return hi===lo?.5:clamp((x-lo)/(hi-lo),0,1)}
function listQuality(list,targetDist){if(!list||!list.length)return.5;var w=recencyWeights(list.length),v=[],i,q,t;for(i=0;i<list.length;i++){q=runFinishQuality(list[i]);t=runTimeIndex(list[i],targetDist);v.push(q*.72+(t?clamp(t/18,0,1)*.28:.14))}return weightedRate(v,w,.5)}
function roleProfileScore(p){p=p||{};var starts=n(p.starts);if(!starts)return.5;var sample=clamp(starts/40,0,1);var q=n(p.overall,.5)*.30+n(p.track,.5)*.28+n(p.distance,.5)*.24+n(p.condition,.5)*.18;return .5*(1-sample)+q*sample}
function genericRoleScore(stats){stats=stats||{};var st=n(stats.starts);if(!st)return.5;var pr=(n(stats.wins)+n(stats.seconds)+n(stats.thirds))/st;var sample=clamp(st/50,0,1);return .5*(1-sample)+clamp(pr/.45,0,1)*sample}
function courseTraits(r){var cp=courseProfile(r),d=n(r.distance,1200),short=d<=1400,veryShort=d<=1200,compact=(cp.shape==="compact"||cp.shape==="pocket"||cp.shape==="egg"||cp.shape==="spiral"),wide=(cp.shape==="long"||cp.shape==="wide"),straight=clamp(cp.straight/520,0,1),turnLoad=compact?.78:(cp.shape==="boxy"?.62:(wide?.34:.48)),frontBias=clamp(.44+(veryShort?.14:(short?.08:0))+turnLoad*.12-straight*.12,0,1),outerLoad=clamp((short?.20:.07)+turnLoad*.12-straight*.05,0,.38),moveRoom=clamp(.35+straight*.38+(wide?.10:0)-turnLoad*.10,0,1);return{frontBias:frontBias,outerLoad:outerLoad,moveRoom:moveRoom,turnLoad:turnLoad,straight:straight}}
function ageSexScore(h,r){var age=n(h.age),sex=String(h.sex||"");var x=.5;if(age>0){if(r.circuit==="中央"){if(age>=3&&age<=5)x=.58;else if(age===6)x=.51;else if(age>=7)x=.44}else{if(age>=3&&age<=7)x=.54;else if(age>=8)x=.49}}if(sex.indexOf("牝")>=0)x+=.005;return clamp(x,0,1)}
function saneCarriedWeightValue(v,bodyWeight){
  if(v==null||v==='')return 0;
  var raw=String(v).replace(/[^0-9.+-]/g,''),x=parseFloat(raw);
  if(!isFinite(x)||x<=0)return 0;
  // Never infer a 3-digit value as 斤量. A wrong 461kg→46.1kg conversion is
  // much worse than showing “—”; upstream parsers must provide kg correctly.
  if(x>=35&&x<=80)return Math.round(x*10)/10;
  return 0
}
function carriedWeightText(h){var v=saneCarriedWeightValue(h&&h.carriedWeight,currentBodyWeight(h));return v?(String(v).replace(/\.0$/,'')+'kg'):'—'}
function weightScore(h){var rs=(h.recentRaces||[]).slice(0,3),vals=[],i;for(i=0;i<rs.length;i++){var w=saneCarriedWeightValue(rs[i].carriedWeight,rs[i].bodyWeight);if(w)vals.push(w)}var cur=saneCarriedWeightValue(h&&h.carriedWeight,currentBodyWeight(h));if(!vals.length||!cur)return.5;var avg=mean(vals),diff=cur-avg;return clamp(.55-diff*.035,.28,.72)}
function currentBodyWeight(h){
  if(!h)return 0;var vals=[h.bodyWeight,h.horseWeight,h.currentBodyWeight];
  for(var i=0;i<vals.length;i++){
    var m=String(vals[i]==null?'':vals[i]).match(/(?:^|\D)(\d{3})(?:\D|$)/),w=m?n(m[1],0):n(vals[i],0);
    if(w>=250&&w<=800)return Math.round(w)
  }
  return 0
}
function currentBodyWeightChange(h){if(!h)return null;var v=h.bodyWeightChange;if(v==null||v==='')v=h.weightChange;if(v==null||v==='')v=h.weightDiff;if(v==null||v==='')return null;var x=n(v,999);return Math.abs(x)<=99?x:null}
function bodyWeightConditionScore(h){
  var bw=currentBodyWeight(h);if(!bw)return .5;
  var ch=currentBodyWeightChange(h),base=.55;
  if(ch!=null){var a=Math.abs(ch);base=a<=6?.60:(a<=12?.55:(a<=20?.48:.42))}
  var rs=(h.allPastRuns||h.recentRaces||[]).slice(0,5),past=[];
  for(var i=0;i<rs.length;i++){var w=n(rs[i]&&rs[i].bodyWeight,0);if(w>250)past.push(w)}
  if(past.length){var avg=mean(past),pct=Math.abs(bw-avg)/Math.max(300,avg),hist=clamp(.62-pct*2.4,.38,.62);base=base*.58+hist*.42}
  return clamp(base,.38,.64)
}
function conditionFit(h,r){var pc=h&&h.precomputedMetrics&&h.precomputedMetrics.fit;if(pc&&pc.counts)return pc;var c=contextualRuns(h,r);return{track:listQuality(c.track,n(r.distance)),distance:listQuality(c.distance,n(r.distance)),condition:listQuality(c.condition,n(r.distance)),weather:listQuality(c.weather,n(r.distance)),season:listQuality(c.season,n(r.distance)),level:listQuality(c.level,n(r.distance)),counts:{track:c.track.length,distance:c.distance.length,condition:c.condition.length,weather:c.weather.length,season:c.season.length,level:c.level.length}}}
function confidenceBlend(score,count){var q=clamp(n(count)/3,0,1);return .5*(1-q)+score*q}
function buildRows(r){var hs=r.horses||[],tmp=[],speeds=[],prizes=[],i,h,rt,pt,sr,fit,ct=courseTraits(r),cp=courseProfile(r),field=Math.max(1,hs.length);for(i=0;i<hs.length;i++){h=hs[i];rt=styleRates(h,r);pt=rt.samples?stylePoint(rt):9;sr=speedRaw(h,n(r.distance));fit=conditionFit(h,r);var earlyTiming=horseEarlyTimingProfile(h,r),proxyTen=tenScore(h,r),proxyBreak=breakReliability(h,r),actualTen=earlyTiming.timingScore==null?proxyTen:clamp(proxyTen*(1-earlyTiming.timingWeight)+earlyTiming.timingScore*earlyTiming.timingWeight,0,1),actualBreak=earlyTiming.gateScore==null?proxyBreak:clamp(proxyBreak*(1-earlyTiming.gateWeight)+earlyTiming.gateScore*earlyTiming.gateWeight,0,1),cf=rt.samples?rt.front:.08,cs=rt.samples?rt.stalk:.28,cm=rt.samples?rt.mid:.40,cc=rt.samples?rt.close:.24,ce=rt.samples?rt.early3:.24,cmo=rt.samples?rt.moved3:.08;tmp.push({horse:h,front:cf,stalk:cs,mid:cm,close:cc,rawFront:rt.front,rawStalk:rt.stalk,rawMid:rt.mid,rawClose:rt.close,early3:ce,moved3:cmo,styleSamples:rt.samples,styleUnknown:!rt.samples,earlyTimingProfile:earlyTiming,ten:actualTen,fade:fadeRate(h,r),move:moveRate(h,r),hold:holdRate(h,r),yieldFlex:yieldFlex(h,r),breakRel:actualBreak,lateGain:lateGainScore(h,r),posCons:positionConsistency(h,r),collapse:earlyCollapseSeverity(h,r),finishEvidence:finishingEvidence(h,r),score:pt,pastStyle:rt.samples?styleName(pt):"履歴なし",expected:rt.samples?styleName(pt):"不明",speedRaw:sr,fit:fit});speeds.push(sr);prizes.push(n(h.prizeMoneyAtRace))}
for(i=0;i<tmp.length;i++){var x=tmp[i],hh=x.horse,rf=recentFirst(hh),rd=recentDistance(hh),distChange=rd?rd-n(r.distance):0,shorten=distChange>=150?1:0,lengthen=distChange<=-150?1:0,lengthenScale=rd?clamp((n(r.distance)-rd)/600,0,1):0,no=n(hh.horseNumber),draw=(no-1)/Math.max(1,field-1),outer=draw>.70?1:0,edge=no===field?1:0,inner=draw<.28?1:0,recentEarly=(rf<99?clamp((8-rf)/7,0,1):.5),posTrend=positionTrend(hh,r),jp=hh.jockeyProfile||{},jockeyFront=n(jp.early3Rate,0),leadHabit=n(jp.leaderRate,0),needLead=clamp(x.front*.78+Math.max(0,x.front-x.stalk)*.48+leadHabit*.10,0,1),flexibility=clamp(x.yieldFlex*.58+x.stalk*.25+x.mid*.12+(1-needLead)*.05,0,1),shortenBoost=shorten*(x.front*.12+x.stalk*.08+x.ten*.07),shortenPenalty=shorten*Math.max(0,.52-x.ten)*.18,lengthenBoost=lengthen*(x.stalk*.07+x.mid*.11+x.close*.05+(1-x.ten)*.055)+lengthenScale*.045,firstTurnRush=clamp(1-firstTurnDistance(r)/650,0,1),outerStress=outer*firstTurnRush*ct.turnLoad*(edge?.45:1),drawAdj=inner*ct.turnLoad*.055+edge*(1-ct.outerLoad)*.055-outerStress*.095,jf=hh.jockeyProfile?roleProfileScore(hh.jockeyProfile):genericRoleScore(hh.jockeyStats),tf=hh.trainerProfile?roleProfileScore(hh.trainerProfile):genericRoleScore(hh.trainerStats),trackFit=confidenceBlend(x.fit.track,x.fit.counts.track),distFit=confidenceBlend(x.fit.distance,x.fit.counts.distance),condFit=confidenceBlend(x.fit.condition,x.fit.counts.condition),weatherFit=confidenceBlend(x.fit.weather,x.fit.counts.weather),seasonFit=confidenceBlend(x.fit.season,x.fit.counts.season),levelFit=confidenceBlend(x.fit.level,x.fit.counts.level),speed=normalize(speeds,x.speedRaw),prize=normalize(prizes,n(hh.prizeMoneyAtRace)),baseAbility=recentFinishScore(hh)*.20+speed*.18+distFit*.11+trackFit*.08+condFit*.07+levelFit*.10+prize*.06+jf*.07+tf*.035+seasonFit*.02+weatherFit*.015+weightScore(hh)*.025+bodyWeightConditionScore(hh)*.040+ageSexScore(hh,r)*.025+x.lateGain*.025,dataN=Math.min(8,(hh.recentRaces||[]).length),coverage=clamp(dataN/5,0,1)*.60+clamp((x.fit.counts.distance+x.fit.counts.track)/4,0,1)*.22+clamp(n(jp.starts)/30,0,1)*.18,frontIntent=clamp(x.front*.36+x.stalk*.17+x.ten*.18+x.early3*.10+jockeyFront*.07+leadHabit*.05+needLead*.07+posTrend*.10,0,1.25),goBase=clamp(frontIntent+shortenBoost+lengthenBoost+drawAdj-shortenPenalty,0,1.25);x.forward=frontIntent;x.goProbBase=clamp(goBase*.72+x.breakRel*.14+x.ten*.14,0,1);x.goProb=x.goProbBase;x.needLead=needLead;x.flexibility=flexibility;x.positionTrend=posTrend;x.ability=clamp(baseAbility*.90+x.posCons*.035+(1-x.collapse)*.035+x.lateGain*.03,0,1);x.speedScore=speed;x.prizeScore=prize;x.jockeyScore=jf;x.trainerScore=tf;x.trackFit=trackFit;x.distFit=distFit;x.condFit=condFit;x.weatherFit=weatherFit;x.seasonFit=seasonFit;x.levelFit=levelFit;x.weightSuit=weightScore(hh);x.bodyWeightSuit=bodyWeightConditionScore(hh);x.bodyWeightKnown=!!currentBodyWeight(hh);x.ageSexSuit=ageSexScore(hh,r);x.coverage=coverage;x.draw=draw;x.outer=outer;x.edge=edge;x.inner=inner;x.outerStress=outerStress;x.shorten=shorten;x.lengthen=lengthen;x.lengthenScale=lengthenScale;x.leadVacancyBoost=0;x.distanceChange=distChange;x.course=ct;x.jockeyFront=jockeyFront;x.stamina=clamp((1-x.fade)*.35+x.hold*.26+distFit*.15+x.posCons*.10+x.ability*.09+(rd>n(r.distance)?.05:0),0,1);x.holdFront=clamp(x.hold*.33+(1-x.fade)*.30+x.stamina*.15+x.ability*.12+distFit*.06+ct.frontBias*.04,0,1);x.latePower=clamp(x.lateGain*.32+x.move*.13+x.close*.10+x.mid*.05+x.ability*.20+(1-x.fade)*.08+(.5+(x.finishEvidence.closing-.5)*Math.min(1,x.finishEvidence.closingSamples/3))*.12,0,1);x.turnSkill=clamp(trackFit*.22+x.move*.18+x.flexibility*.18+x.posCons*.16+(1-ct.turnLoad)*.06+x.ability*.20,0,1);x.breakSkill=clamp(x.breakRel*.32+x.ten*.30+x.goProbBase*.20+recentEarly*.10+jockeyFront*.08,0,1);x.trafficTol=clamp(x.flexibility*.34+x.move*.24+x.posCons*.18+x.turnSkill*.18+x.lateGain*.06,0,1)}
for(i=0;i<tmp.length;i++){var lx=tmp[i],le=lx.horse&&lx.horse.integratedEvaluation||{},lc=le.components||{},rawLap=(lc.lapScore!=null?lc.lapScore:(lx.horse&&lx.horse.lapScore));lx.lapScore=clamp(n(rawLap,.5),0,1);lx.sectionalSamples=n(lx.horse&&lx.horse.officialSectionalSamples,0)}
var minetaCtx=minetaRaceContext(tmp,r),clearFrontCount=tmp.filter(function(z){return z.minetaEarlyIntent||n(z.goProbBase)>=.53}).length;
if(clearFrontCount<=1){
  for(i=0;i<tmp.length;i++){
    var lv=tmp[i],reposition=clamp(n(lv.lengthenScale)*.52+n(lv.breakRel)*.15+n(lv.ten)*.09+n(lv.positionTrend)*.08+n(lv.jockeyFront)*.08+(1-n(lv.needLead))*.08,0,1),drawChance=lv.edge?.055:(lv.inner?.035:.045),vacancyBoost=clamp(reposition*(clearFrontCount===0?.16:.10)+n(lv.lengthenScale)*.045+drawChance*(1-n(lv.outerStress)),0,.18);
    lv.leadVacancyBoost=vacancyBoost;lv.goProbBase=clamp(lv.goProbBase+vacancyBoost,0,1);lv.goProb=lv.goProbBase
  }
}
var p0=pressureInfo(tmp);minetaAssignRoles(tmp,r,minetaCtx,p0);p0=pressureInfo(tmp);
for(i=0;i<tmp.length;i++){
  var y=tmp[i],q=p0[n(y.horse.horseNumber)]||{},pressurePenalty=(q.conflict||0)*(.055+.055*y.needLead)+(q.sandwich||0)*.075*(1-y.flexibility)+(q.lineMiddle||0)*.045*(.4+.6*y.needLead)+y.outerStress*.055-(q.lineEndRelief||0)*.025;
  y.leftPressure=q.left||0;y.rightPressure=q.right||0;y.sandwichRisk=q.sandwich||0;y.escapeSideRisk=q.escapeSide||0;y.frontLineRole=q.lineRole||'単独';y.frontLineMiddle=q.lineMiddle||0;y.frontLineEnd=q.lineEnd||0;y.lineEndRelief=q.lineEndRelief||0;
  y.frontCost=clamp(Math.max(n(y.frontCost,0),pressurePenalty),0,.30);
  if(y.expected==='逃げ候補')y.goProb=Math.max(y.goProb,.64);else if(y.expected==='先行')y.goProb=Math.max(y.goProb,.53);
  y.frontStay=clamp(y.goProb*.24+y.holdFront*.25+(1-y.fade)*.12+y.ability*.12+y.course.frontBias*.07+(.5+(y.finishEvidence.hold-.5)*Math.min(1,y.finishEvidence.holdSamples/3))*.15-y.frontCost*.27+(q.lineEndRelief||0)*.035+(minetaCtx.rawOcc<=.25&&y.minetaEarlyIntent?.045:0)+(y.minetaEscapeOutside?.025:0)-(minetaCtx.rawOcc>=.45&&y.outer&&y.minetaEarlyIntent?.035:0),0,1);
  y.comeFromBehind=clamp(y.latePower*.34+y.move*.13+y.ability*.16+y.course.moveRoom*.09+(1-y.goProb)*.07+(.5+(y.finishEvidence.closing-.5)*Math.min(1,y.finishEvidence.closingSamples/3))*.16+(minetaCtx.rawOcc>=.45?.035:0)+(y.shorten&&minetaCtx.rawOcc>=.45?.035:0)+(y.minetaEscapeSandwich?.035:0),0,1)
}
tmp.minetaContext=minetaCtx;return tmp}
function rowByNo(rows,no){var i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===n(no))return rows[i];return null}
function pressureInfo(rows){var sorted=rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),p={},attacks=[],hot=[],segFor=[],segments=[],i,x,l,r,lp,rp,base,current=null;function attack(z){if(!z)return 0;base=z.goProbBase!=null?z.goProbBase:z.goProb;return clamp(base*(.46+.34*z.needLead+.20*z.ten),0,1.2)}for(i=0;i<sorted.length;i++){attacks[i]=attack(sorted[i]);hot[i]=attacks[i]>.50&&n(sorted[i].goProbBase,sorted[i].goProb)>=.44}for(i=0;i<sorted.length;i++){if(hot[i]){if(!current||i===0||!hot[i-1]||n(sorted[i].horse.horseNumber)-n(sorted[i-1].horse.horseNumber)!==1){current={idx:[]};segments.push(current)}current.idx.push(i);segFor[i]=current}else current=null}for(i=0;i<sorted.length;i++){x=sorted[i];l=i?sorted[i-1]:null;r=i<sorted.length-1?sorted[i+1]:null;lp=l&&n(x.horse.horseNumber)-n(l.horse.horseNumber)===1?attacks[i-1]:0;rp=r&&n(r.horse.horseNumber)-n(x.horse.horseNumber)===1?attacks[i+1]:0;var leftHot=lp>.50,rightHot=rp>.50,sandwich=leftHot&&rightHot?1:0,escapeSide=(leftHot||rightHot)&&!sandwich?1:0,adj=(leftHot?1:0)+(rightHot?1:0),near2=0;if(i>1&&n(x.horse.horseNumber)-n(sorted[i-2].horse.horseNumber)===2)near2+=attacks[i-2]*.14;if(i<sorted.length-2&&n(sorted[i+2].horse.horseNumber)-n(x.horse.horseNumber)===2)near2+=attacks[i+2]*.14;var seg=segFor[i]||null,clusterLen=seg?seg.idx.length:0,clusterPos=seg?seg.idx.indexOf(i):-1,lineMiddle=clusterLen>=3&&clusterPos>0&&clusterPos<clusterLen-1?1:0,lineEnd=clusterLen>=2&&(clusterPos===0||clusterPos===clusterLen-1)?1:0,innerEnd=lineEnd&&clusterPos===0?1:0,outerEnd=lineEnd&&clusterPos===clusterLen-1?1:0,lineEndRelief=lineEnd?(.05+.08*x.flexibility):0;if(outerEnd&&!rightHot)lineEndRelief+=.04;if(innerEnd&&!leftHot)lineEndRelief+=.025;var conflict=(lp+rp)*(.43+.38*x.needLead+.19*x.ten)*(1-.42*x.flexibility)+near2+lineMiddle*(.10+.10*x.needLead)+(clusterLen>=4?.04:0);conflict=Math.max(0,conflict-lineEndRelief*.42);var freeOuter=x.edge?(.055+.075*x.flexibility):0,lineRole=lineMiddle?'先行列中央':(outerEnd?'先行列外端':(innerEnd?'先行列最内':(lineEnd?'先行列端':'単独/飛び')));p[n(x.horse.horseNumber)]={adj:adj,sandwich:sandwich,escapeSide:escapeSide,conflict:clamp(conflict,0,1.7),freeOuter:freeOuter,left:lp,right:rp,leftHot:leftHot,rightHot:rightHot,selfAttack:attacks[i],clusterLen:clusterLen,lineMiddle:lineMiddle,lineEnd:lineEnd,innerEnd:innerEnd,outerEnd:outerEnd,lineEndRelief:lineEndRelief,lineRole:lineRole}}return p}
function frontArrangement(rows,pressure){pressure=pressure||pressureInfo(rows);var field=Math.max(1,rows.length),front=rows.filter(function(x){return x.minetaEarlyIntent||x.expected==='逃げ候補'||x.expected==='先行'||x.goProb>=.50}).sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),segments=[],cur=[],i,x,no,prev=0;for(i=0;i<front.length;i++){x=front[i];no=n(x.horse.horseNumber);if(!cur.length||no===prev+1)cur.push(x);else{segments.push(cur);cur=[x]}prev=no}if(cur.length)segments.push(cur);var adjacentPairs=0,longest=0;for(i=0;i<segments.length;i++){longest=Math.max(longest,segments[i].length);adjacentPairs+=Math.max(0,segments[i].length-1)}var pattern=!front.length?'前候補なし':(front.length===1?'単独':(adjacentPairs===0?'飛び飛び':(longest>=3?'連続':'一部連続'))),innerCut=Math.ceil(field*.35),outerCut=Math.floor(field*.65)+1,innerCount=front.filter(function(z){return n(z.horse.horseNumber)<=innerCut}).length,outerCount=front.filter(function(z){return n(z.horse.horseNumber)>=outerCut}).length,innerShare=front.length?innerCount/front.length:0,outerShare=front.length?outerCount/front.length:0,concentrationText=innerShare>=.60?'内枠に集中':(outerShare>=.60?'外枠に集中':'内外に分散'),scored=rows.slice();for(i=0;i<scored.length;i++){x=scored[i];var q=pressure[n(x.horse.horseNumber)]||{};x.canYield=clamp(x.flexibility*.62+x.stalk*.20+(1-x.needLead)*.18,0,1)>=.55;x.leaderScore=clamp(x.goProb*.38+x.ten*.20+x.needLead*.17+x.breakSkill*.13+x.jockeyFront*.05+x.front*.05+(q.lineEndRelief||0)*.05-(q.conflict||0)*.04,0,1.3);x.secondScore=clamp(x.goProb*.34+x.stalk*.22+x.flexibility*.16+x.holdFront*.12+x.ability*.08+(q.lineEndRelief||0)*.05-(q.conflict||0)*.04,0,1.3);x.positionScore=clamp(x.goProb*.23+x.stalk*.24+x.mid*.13+x.flexibility*.13+x.ability*.12+x.turnSkill*.09+(1-x.frontCost)*.06,0,1.2)}var leadOrder=scored.filter(function(z){return z.minetaEarlyIntent||z.goProb>=.48}).sort(function(a,b){var ar=n(a.minetaLeadRank,99),br=n(b.minetaLeadRank,99);if(ar!==br)return ar-br;return b.leaderScore-a.leaderScore||n(a.horse.horseNumber)-n(b.horse.horseNumber)}),leadMax=leadOrder.length?leadOrder[0].leaderScore:0,leadCandidates=leadOrder.filter(function(z,idx){return idx<3&&((n(z.minetaLeadRank,0)>0)||(z.leaderScore>=leadMax-.085&&z.goProb>=.53))}),leadTop=leadCandidates[0]||leadOrder[0]||null,secondCandidates=scored.filter(function(z){return !leadTop||n(z.horse.horseNumber)!==n(leadTop.horse.horseNumber)}).filter(function(z){return z.goProb>=.42||z.stalk>=.28}).sort(function(a,b){return b.secondScore-a.secondScore}).slice(0,3),positionCandidates=scored.filter(function(z){return z.goProb>=.34||z.stalk>=.30||z.mid>=.34}).sort(function(a,b){return b.positionScore-a.positionScore}).slice(0,4),escapeSide=leadCandidates.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.escapeSide}),sandwich=leadCandidates.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.sandwich}),middleFront=front.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.lineMiddle}),highFade=front.filter(function(z){return z.fade>=.50}),hardLead=leadCandidates.filter(function(z){return z.needLead>=.58&&z.canYield===false});return{front:front,segments:segments,pattern:pattern,longest:longest,adjacentPairs:adjacentPairs,innerShare:innerShare,outerShare:outerShare,concentrationText:concentrationText,leadCandidates:leadCandidates,secondCandidates:secondCandidates,positionCandidates:positionCandidates,escapeSide:escapeSide,sandwich:sandwich,middleFront:middleFront,highFade:highFade,hardLeadCount:hardLead.length}}
function tacticalContext(r,rows){var pressure=pressureInfo(rows),arr=frontArrangement(rows,pressure),collapseWatch=arr.highFade.length>=2,i,x,q;for(i=0;i<rows.length;i++){x=rows[i];q=pressure[n(x.horse.horseNumber)]||{};x.frontLineRole=q.lineRole||'単独/飛び';x.collapseBeneficiary=collapseWatch&&x.goProb<.58?clamp(x.comeFromBehind*.42+x.latePower*.22+x.move*.15+x.trafficTol*.12+x.ability*.09,0,1):0}arr.collapseWatch=collapseWatch;arr.collapseRecheck=collapseWatch?rows.filter(function(z){return z.goProb<.58&&(z.mid+z.close)>=.45}).sort(function(a,b){return b.collapseBeneficiary-a.collapseBeneficiary||b.comeFromBehind-a.comeFromBehind}).slice(0,2):[];return{pressure:pressure,arrangement:arr}}
function scenarioModel(r,rows,pressure,arr){pressure=pressure||pressureInfo(rows);arr=arr||frontArrangement(rows,pressure);var front=rows.slice().sort(function(a,b){return b.goProb-a.goProb}),active=arr.front,top=active.slice().sort(function(a,b){return b.goProb-a.goProb}).slice(0,Math.min(5,active.length)),fade=top.length?mean(top.map(function(x){return x.fade})):0,hold=top.length?mean(top.map(function(x){return x.holdFront})):0,conf=top.length?mean(top.map(function(x){return (pressure[n(x.horse.horseNumber)]||{}).conflict||0})):0,sand=top.length?mean(top.map(function(x){return (pressure[n(x.horse.horseNumber)]||{}).sandwich||0})):0,flex=top.length?mean(top.map(function(x){return x.flexibility})):0,ct=rows.length?rows[0].course:courseTraits(r),cp=courseProfile(r),firstTurnRush=clamp(1-firstTurnDistance(r)/650,0,1),lead=arr.leadCandidates||[],leadGap=lead.length>1?Math.max(0,lead[0].leaderScore-lead[1].leaderScore):.20,clear=lead.length?clamp(leadGap*2.0+lead[0].holdFront*.10+(lead[0].lineEndRelief||0)*.08,0,.42):.12,cluster=clamp((arr.longest-1)/3,0,1),outerLoad=arr.outerShare*firstTurnRush*ct.turnLoad,frontVolume=clamp(active.length/Math.max(1,rows.length),0,1),stableLead=lead.length?clamp(lead[0].holdFront*.45+(1-lead[0].fade)*.30+lead[0].ten*.15+(lead[0].canYield?.10:0),0,1):0,hardMulti=Math.max(0,(arr.hardLeadCount||0)-1),spreadRelief=arr.pattern==='飛び飛び'?.08:(arr.pattern==='一部連続'?.035:0),A=.28+ct.frontBias*.24+clear*.20+hold*.12+(1-fade)*.075+(1-clamp(conf,0,1))*.05+flex*.03+stableLead*.045+spreadRelief*.035,C=.16+(1-ct.frontBias)*.09+ct.moveRoom*.09+fade*.17+clamp(conf,0,1)*.13+sand*.09+cluster*.06+outerLoad*.055+hardMulti*.055,B=.34+flex*.075+(1-Math.abs(A-C))*.035+spreadRelief*.03;if(arr.highFade.length>=2)C+=.045+Math.min(.055,(arr.highFade.length-2)*.018);if(frontVolume>.52)C+=cluster>.20?Math.min(.045,(frontVolume-.52)*.16):Math.min(.015,(frontVolume-.52)*.08);if(lead.length>1&&hardMulti===0)B+=.025;if(lead.length===1&&stableLead>.62)A+=.035;if(arr.pattern==='飛び飛び'&&flex>.52)C-=.025;A=clamp(A,.15,.68);B=clamp(B,.20,.52);C=clamp(C,.12,.60);var sum=A+B+C;A/=sum;B/=sum;C/=sum;return[{code:"A",title:"前残り",prob:A},{code:"B",title:"平均",prob:B},{code:"C",title:"前崩れ・差し届く",prob:C}]}
function startOrder(rows){var p=pressureInfo(rows);return rows.slice().sort(function(a,b){function s(x){var q=p[n(x.horse.horseNumber)]||{};return x.goProb+x.needLead*.12+(q.freeOuter||0)-q.conflict*.035}return s(b)-s(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function scenarioSuit(x,code,pressure){var q=pressure[n(x.horse.horseNumber)]||{},earlyCost=(q.conflict||0)*x.goProb*(.34+.42*x.needLead)*(1-.34*x.flexibility)+x.outerStress*.06+(q.lineMiddle||0)*x.goProb*.045-(q.lineEndRelief||0)*.025,frontStay=x.goProb*.27+x.holdFront*.31+(1-x.fade)*.12+x.ability*.18+x.stamina*.07+x.course.frontBias*.05-earlyCost*.16+(q.lineEndRelief||0)*.025,balanced=x.ability*.34+x.holdFront*.14+x.latePower*.13+x.move*.10+x.stamina*.10+x.goProb*.08+x.flexibility*.06+(1-x.fade)*.05+(q.lineEndRelief||0)*.015,close=x.ability*.26+x.latePower*.27+x.move*.17+x.mid*.08+x.close*.09+x.course.moveRoom*.07+x.trafficTol*.06+x.collapseBeneficiary*.10-x.goProb*.015;if(code==="A")return clamp(frontStay,0,1.25);if(code==="C")return clamp(close,0,1.25);return clamp(balanced,0,1.25)}
function suitability(rows,sc,pressure){var out={};pressure=pressure||pressureInfo(rows);var i,x,win,place,show,j,q,scenarioScores=[],frontFadePenalty,baseWin,basePlace,baseShow;for(i=0;i<rows.length;i++){x=rows[i];win=place=show=0;scenarioScores=[];frontFadePenalty=x.goProb>=.50?Math.max(0,x.fade-.38)*x.goProb:0;for(j=0;j<sc.length;j++){q=scenarioSuit(x,sc[j].code,pressure);scenarioScores.push({code:sc[j].code,score:q});baseWin=q*.72+x.ability*.20+x.hold*.08-frontFadePenalty*.18;basePlace=q*.57+x.ability*.20+(1-x.fade)*.13+x.flexibility*.06+x.hold*.04-frontFadePenalty*.065;baseShow=q*.46+x.ability*.20+(1-x.fade)*.14+x.move*.09+x.flexibility*.06+x.hold*.05-frontFadePenalty*.030;if(x.goProb>=.52&&x.fade<=.25){baseWin+=.025;basePlace+=.018;baseShow+=.012}if(sc[j].code==='C'&&x.collapseBeneficiary>.60){basePlace+=.035;baseShow+=.025}win+=sc[j].prob*baseWin;place+=sc[j].prob*basePlace;show+=sc[j].prob*baseShow}win=clamp(win,0,1.25);place=clamp(place,0,1.25);show=clamp(show,0,1.25);var overall=win*.54+place*.29+show*.17;out[n(x.horse.horseNumber)]={win:win,place:place,show:show,overall:overall,rankScore:win*.62+place*.24+show*.14,scenario:scenarioScores}}return out}
function cornerScores(r,rows,sc,suit){var pressure=pressureInfo(rows),top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0].code,out=[],i,x,z,q,s,earlyCost;for(i=0;i<rows.length;i++){x=rows[i];z=suit[n(x.horse.horseNumber)]||{overall:.5};q=pressure[n(x.horse.horseNumber)]||{};earlyCost=q.conflict*x.goProb*(.4+.4*x.needLead);s=x.goProb*.25+x.hold*.20+x.ability*.21+x.move*.11+(1-x.fade)*.11+z.overall*.12-earlyCost*.10;if(top==="A")s+=x.goProb*.11+x.hold*.07;if(top==="C")s+=x.move*.12+x.mid*.06+x.close*.08-x.goProb*.02;out.push({row:x,s:s})}return out.sort(function(a,b){return b.s-a.s}).map(function(z){return z.row})}
function seedHash(v){var s=String(v||"race"),h=2166136261,i;for(i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function prng(seed){var a=seed>>>0;return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function jitter(rng){return(rng()+rng()+rng()+rng()+rng()+rng()-3)/3}
function chooseScenario(sc,rng){var u=rng(),c=0,i;for(i=0;i<sc.length;i++){c+=sc[i].prob;if(u<=c)return sc[i].code}return sc.length?sc[sc.length-1].code:"B"}
function packStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,visualRankGap,scoreGap,lane,cp=courseProfile(r);for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);visualRankGap=(stage<2?.0048:(stage<5?.0065:.0085))*i;scoreGap=diff*(stage<2?.030:(stage<5?.043:.060));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&visualRankGap<.02)lane+=((i%3)-1);out.push({no:no,gap:clamp(visualRankGap+scoreGap,0,.42),lane:clamp(lane,-3,3)})}return out}
function stageMap(pack){var o={},i;for(i=0;i<pack.length;i++)o[pack[i].no]=pack[i];return o}
function stageByNo(pack,no){for(var i=0;i<pack.length;i++)if(n(pack[i].no)===n(no))return pack[i];return null}
function simulateOne(r,rows,sc,suit,seed){var rng=prng(seed),code=chooseScenario(sc,rng),pressure=pressureInfo(rows),cp=courseProfile(r),ct=courseTraits(r),dist=n(r.distance,1200),distanceLoad=clamp((dist-1000)/1800,0,1),firstTurnRush=clamp(1-firstTurnDistance(r)/650,0,1),paceHeat=0,i,x,no,q,noise;var S0={},S1={},S2={},S3={},S4={},S5={},S6={},S7={},L0={},L1={},L2={},L3={},L4={},L5={},L6={},L7={},energy={};
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);S0[no]=x.breakSkill*.50+x.goProb*.30+x.needLead*.08+x.jockeyFront*.05+(q.freeOuter||0)-q.conflict*.035+noise*.07;L0[no]=clamp(Math.round((x.draw-.5)*5),-3,3);energy[no]=1;if(x.goProb>.50)paceHeat+=x.goProb*(.45+.55*x.needLead)}
paceHeat=clamp((paceHeat-1.10)/Math.max(.8,rows.length*.18),0,1.55);
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var rushCost=(q.conflict||0)*(.08+.11*x.needLead)+paceHeat*x.goProb*.045+firstTurnRush*x.outer*.045;energy[no]-=rushCost;S1[no]=S0[no]*.56+x.goProb*.20+x.breakSkill*.10+x.flexibility*.05-x.collapse*.035-rushCost*.22+noise*.065;L1[no]=clamp(L0[no]+(x.edge&&x.goProb>.55?-1:0)+(q.sandwich&&x.flexibility<.45?1:0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var turnCost=Math.abs(L1[no])*.012*ct.turnLoad+x.outer*firstTurnRush*.025+(q.sandwich||0)*(.035-.020*x.trafficTol);energy[no]-=turnCost;S2[no]=S1[no]*.48+x.hold*.16+x.turnSkill*.12+x.ability*.12+x.flexibility*.06-turnCost*.32+noise*.06;L2[no]=clamp(L1[no]+(x.inner&&x.goProb<.35?0:Math.round((x.flexibility-.5)*-1)),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var draft=(x.stalk*.045+x.mid*.025)*(1-x.needLead),leaderDrain=paceHeat*x.goProb*(.045+.055*x.needLead)*(1+.45*distanceLoad);energy[no]-=leaderDrain;S3[no]=S2[no]*.43+x.ability*.18+x.hold*.13+x.stamina*.10+draft+x.move*.05+noise*.065;L3[no]=clamp(L2[no]+(x.move>.45&&x.goProb<.45?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var moveKick=x.move*(.08+.07*ct.moveRoom)+x.latePower*.055,wideCost=Math.max(0,Math.abs(L3[no])-1)*.018*ct.turnLoad;energy[no]-=wideCost;S4[no]=S3[no]*.42+x.ability*.17+x.stamina*.12+x.turnSkill*.09+moveKick-wideCost*.30+noise*.07;L4[no]=clamp(L3[no]+(x.move>.50?Math.round((rng()-.42)*2):0),-3,3)}
var pack4=packStage(r,rows,S4,L4,4),map4=stageMap(pack4);
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var pos4=map4[no]||{gap:.2,lane:0},blocked=0;if(pos4.gap>.025&&Math.abs(pos4.lane)<=1&&x.trafficTol<.55&&rng()>.48)blocked=(.02+.06*(1-x.trafficTol));var scFit=scenarioSuit(x,code,pressure),fatigue=(1-energy[no])*.16+x.collapse*.07+paceHeat*x.goProb*.035*distanceLoad;S5[no]=S4[no]*.37+scFit*.16+x.ability*.15+x.stamina*.11+x.turnSkill*.07+x.latePower*.07-blocked-fatigue+noise*.075;L5[no]=clamp(L4[no]+(blocked>0?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var straightBoost=x.latePower*(.10+.12*ct.straight)+x.move*.055*ct.moveRoom,frontKick=(code==="A"?x.goProb*.055+x.hold*.035:0),closeKick=(code==="C"?x.close*.07+x.move*.055:0),fatigue2=(1-energy[no])*.12+x.fade*.08;S6[no]=S5[no]*.34+x.ability*.20+x.stamina*.12+straightBoost+frontKick+closeKick-fatigue2+noise*.085;L6[no]=clamp(L5[no]+(x.latePower>.58&&Math.abs(L5[no])<3?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var suitx=suit[no]||{overall:.5},uncert=(1-x.coverage)*.070*jitter(rng);S7[no]=S6[no]*.34+suitx.overall*.24+x.ability*.18+x.latePower*.10+x.stamina*.08+(1-x.fade)*.05-q.conflict*.015+noise*.09+uncert;L7[no]=L6[no]}
var packs=[packStage(r,rows,S0,L0,0),packStage(r,rows,S1,L1,1),packStage(r,rows,S2,L2,2),packStage(r,rows,S3,L3,3),packStage(r,rows,S4,L4,4),packStage(r,rows,S5,L5,5),packStage(r,rows,S6,L6,6),packStage(r,rows,S7,L7,7)],maps=packs.map(stageMap),finish=packs[7];return{scenario:code,checkpoints:packs,maps:maps,start:packs[1],corner:packs[5],finish:finish,startMap:maps[1],cornerMap:maps[5],finishMap:maps[7],podium:finish.slice(0,3).map(function(z){return z.no}),paceHeat:paceHeat}}
function generateSimulations(r,rows,sc,suit,count){var runs=[],stats={},scenarioCount={A:0,B:0,C:0},combo={},i,j,no,run,key;for(i=0;i<rows.length;i++){no=n(rows[i].horse.horseNumber);stats[no]={horse:rows[i].horse,win:0,second:0,third:0,top3:0,startRank:0,cornerRank:0,finishRank:0}}var base=seedHash([r.id,r.date,r.track,r.raceNumber,r.distance,(r.horses||[]).length].join("|"));for(i=0;i<count;i++){run=simulateOne(r,rows,sc,suit,(base+Math.imul(i+1,2654435761))>>>0);runs.push(run);scenarioCount[run.scenario]=(scenarioCount[run.scenario]||0)+1;key=run.podium.join("-");combo[key]=(combo[key]||0)+1;for(j=0;j<run.start.length;j++)stats[run.start[j].no].startRank+=j+1;for(j=0;j<run.corner.length;j++)stats[run.corner[j].no].cornerRank+=j+1;for(j=0;j<run.finish.length;j++)stats[run.finish[j].no].finishRank+=j+1;if(run.podium[0]){stats[run.podium[0]].win++;stats[run.podium[0]].top3++}if(run.podium[1]){stats[run.podium[1]].second++;stats[run.podium[1]].top3++}if(run.podium[2]){stats[run.podium[2]].third++;stats[run.podium[2]].top3++}}var summary=Object.keys(stats).map(function(k){var z=stats[k];z.no=n(k);z.winRate=z.win/count;z.secondRate=z.second/count;z.thirdRate=z.third/count;z.top3Rate=z.top3/count;z.avgStart=z.startRank/count;z.avgCorner=z.cornerRank/count;z.avgFinish=z.finishRank/count;z.markScore=z.winRate*.53+z.secondRate*.24+z.thirdRate*.13+z.top3Rate*.10;return z}).sort(function(a,b){return b.markScore-a.markScore||a.avgFinish-b.avgFinish});var first=summary[0]||null,rest=summary.slice(1),second=rest.slice().sort(function(a,b){return b.secondRate-a.secondRate||b.top3Rate-a.top3Rate})[0]||summary[1]||null,thirdPool=summary.filter(function(z){return(!first||z.no!==first.no)&&(!second||z.no!==second.no)}),third=thirdPool.slice().sort(function(a,b){return b.thirdRate-a.thirdRate||b.top3Rate-a.top3Rate})[0]||summary[2]||null,podium=[first,second,third].filter(Boolean),exact=0,setHit=0,target=podium.map(function(z){return z.no}),targetKey=target.join("-");exact=combo[targetKey]||0;for(i=0;i<runs.length;i++){var a=runs[i].podium.slice().sort(function(a,b){return a-b}),b=target.slice().sort(function(a,b){return a-b});if(a.length===b.length&&a.join("-")===b.join("-"))setHit++}return{count:count,runs:runs,summary:summary,podium:podium,exactRate:exact/count,setRate:setHit/count,scenarioCount:scenarioCount}}
function avgOrder(rows,sim,key){var prop=key==="start"?"avgStart":(key==="corner"?"avgCorner":"avgFinish"),sm={};for(var i=0;i<sim.summary.length;i++)sm[sim.summary[i].no]=sim.summary[i][prop];return rows.slice().sort(function(a,b){return sm[n(a.horse.horseNumber)]-sm[n(b.horse.horseNumber)]})}
function packScenarioStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,rankGap,scoreGap,lane;for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);rankGap=(stage<=1?.010:(stage<=3?.013:.016))*i;scoreGap=diff*(stage<=1?.06:(stage<=3?.08:.10));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&i%3===0)lane+=1;if(i>0&&i%4===0)lane-=1;out.push({no:no,gap:clamp(rankGap+scoreGap,0,.34),lane:clamp(lane,-3,3),score:scoreMap[no]})}return out}
function rowsFromPack(rows,pack){var map={};for(var i=0;i<rows.length;i++)map[n(rows[i].horse.horseNumber)]=rows[i];return pack.map(function(z){return map[n(z.no)]}).filter(Boolean)}
function eventOrderPack(rows,order,laneMap,stage){
  var field=Math.max(1,order.length),out=[];
  for(var i=0;i<order.length;i++){
    var x=order[i],no=n(x.horse.horseNumber),lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4),
        pos=field<=1?1:1-i/(field-1),gap=clamp((stage<=1?.012:(stage<=3?.016:.020))*i,0,.34);
    out.push({no:no,gap:gap,lane:clamp(lane,-3,3),score:pos})
  }
  return out
}
function scenarioPlan(r,rows,sc,suit,pressure,arr){
  var scenario=sc.slice().sort(function(a,b){return b.prob-a.prob})[0]||{code:'B',title:'平均',prob:1},code=scenario.code;
  pressure=pressure||pressureInfo(rows);arr=arr||frontArrangement(rows,pressure);
  var p=pressure,lanes={},i,x,no,q,ct=courseTraits(r),
      firstRush=clamp(1-firstTurnDistance(r)/650,0,1),
      longDistance=clamp((n(r.distance,1400)-1400)/1200,0,1),
      frontRunners=(arr.front||[]).length,hardLeaders=Math.max(0,n(arr.hardLeadCount,0)-1),
      paceHeat=clamp(Math.max(0,frontRunners-1)*.060+hardLeaders*.095+
        (arr.middleFront||[]).length*.035+firstRush*Math.max(0,frontRunners-2)*.028,0,.65);
  function exposure(z){
    var qq=p[n(z.horse.horseNumber)]||{};
    return clamp(paceHeat*(.18+n(z.goProb,.5)*.28+n(z.needLead,.3)*.18+
      n(qq.conflict,0)*.22+n(z.frontCost,0)*.55)*(1+longDistance*.35),0,.52)
  }
  // Pre-race pace and ability only: neither odds nor results enter here.
  function finishStrength(z){
    var early=exposure(z),fade=n(z.fade,.25),late=n(z.latePower,.5);
    return n(z.ability,.5)*.27+n(z.stamina,.5)*.18+late*.21+
      n(z.comeFromBehind,.5)*.12+n(z.holdFront,.5)*.12+
      n(z.lateGain,.5)*.05+n(z.trafficTol,.5)*.05-
      early*.42-fade*(.055+early*.20)+
      (code==='A'?n(z.frontStay,.5)*.07:0)+
      (code==='C'?late*.05:0)
  }
  rows.forEach(function(z){lanes[n(z.horse.horseNumber)]=clamp(Math.round((z.draw-.5)*5),-3,3)});

  function lex(list,keys){
    return list.slice().sort(function(a,b){
      for(var k=0;k<keys.length;k++){
        var fn=keys[k],av=n(fn(a),0),bv=n(fn(b),0);
        if(bv!==av)return bv-av
      }
      return n(a.horse.horseNumber)-n(b.horse.horseNumber)
    })
  }
  function uniq(groups){
    var seen={},out=[];
    groups.forEach(function(g){(g||[]).forEach(function(z){var k=n(z.horse.horseNumber);if(!seen[k]){seen[k]=1;out.push(z)}})});
    rows.forEach(function(z){var k=n(z.horse.horseNumber);if(!seen[k]){seen[k]=1;out.push(z)}});
    return out
  }
  function idx(order,row){return order.indexOf(row)}
  function move(order,row,delta){
    var i=idx(order,row);if(i<0||!delta)return;
    var ni=clamp(i+delta,0,order.length-1);
    if(ni===i)return;
    order.splice(i,1);order.splice(ni,0,row)
  }
  function moveTo(order,row,target){
    var i=idx(order,row);if(i<0)return;
    target=clamp(target,0,order.length-1);
    if(i===target)return;
    order.splice(i,1);order.splice(target,0,row)
  }
  function topRank(order,row){var i=idx(order,row);return i<0?999:i+1}
  function isFront(z){return z.goProb>=.50||z.expected==='逃げ候補'||z.expected==='先行'}
  function isStalk(z){return z.expected==='好位'||z.stalk>=.30}
  function isCloser(z){return z.expected==='後方'||z.close>=.38||z.comeFromBehind>=.58}

  // START: distinguish "who contests the lead" from "where they settle after losing it".
  // A horse strong enough to be named in the lead battle cannot jump straight to midfield
  // unless a concrete retreat / pressure event occurs.
  var leaderPool=(arr.leadCandidates||[]).length?(arr.leadCandidates||[]):rows.filter(function(z){return z.goProb>=.50});
  // Real first-corner lead and break/ten evidence decide the front battle.
  leaderPool=leaderPool.slice().sort(function(a,b){
    function score(z){
      var past=z.minetaPast||{},sample=clamp(n(z.styleSamples,0)/3,0,1);
      return n(z.goProb,.5)*.25+n(z.breakSkill,.5)*.21+n(z.ten,.5)*.18+
        n(z.needLead,.5)*.12+n(z.jockeyFront,0)*.04+
        (n(past.leadRate)*.12+n(past.earlyRate)*.045+(past.prevLeader?.04:0))*sample+
        n(z.holdFront,.5)*.06+n(z.minetaLeadRank,0)*-.002
    }
    return score(b)-score(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  var leader=leaderPool[0]||lex(rows,[function(z){return z.goProb},function(z){return z.breakSkill}])[0]||null,
      leadBattlers=leaderPool.filter(function(z){return z!==leader}),
      front=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&isFront(z)}),[function(z){return z.goProb},function(z){return z.ten},function(z){return z.needLead}]),
      stalk=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&!isFront(z)&&isStalk(z)}),[function(z){return z.stalk},function(z){return z.posCons},function(z){return z.breakSkill}]),
      middle=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&!isFront(z)&&!isStalk(z)&&!isCloser(z)}),[function(z){return z.mid},function(z){return z.posCons}]),
      rear=lex(rows.filter(function(z){return z!==leader&&leadBattlers.indexOf(z)<0&&!isFront(z)&&!isStalk(z)&&isCloser(z)}),[function(z){return z.close},function(z){return z.latePower}]),
      orders=[];
  // At the instant of the break, all genuine lead battlers stay in the front cluster.
  orders[0]=uniq([[leader],leadBattlers,front,stalk,middle,rear]);

  // FIRST TURN: predict the settling order after the lead battle.
  // This is where a horse such as 7 can go from "challenged for the lead" to 2nd/3rd,
  // rather than incorrectly being thrown into midfield.
  orders[1]=orders[0].slice();
  if(leader){
    var settlePool=uniq([leadBattlers,(arr.secondCandidates||[]),front,stalk]).filter(function(z){return z&&z!==leader}).slice(0,Math.min(6,rows.length-1));
    function settleScore(z){
      var qq=p[n(z.horse.horseNumber)]||{},wasLead=leadBattlers.indexOf(z)>=0?1:0,
          yieldPenalty=wasLead*n(z.needLead)*(1-n(z.canYield,.5))*.16;
      return n(z.secondScore,.5)*.38+n(z.stalk,.3)*.15+n(z.flexibility,.5)*.12+n(z.breakSkill,.5)*.09+
        n(z.ten,.5)*.08+n(z.ability,.5)*.08+n(z.posCons,.5)*.06+wasLead*.08+
        (z.minetaEscapeOutside?.035:0)-(n(z.outerStress)*.06+n(qq.conflict)*.06+yieldPenalty)
    }
    settlePool.sort(function(a,b){return settleScore(b)-settleScore(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
    var settleTop=settlePool.slice(0,Math.min(4,settlePool.length)),
        rest=orders[1].filter(function(z){return z!==leader&&settleTop.indexOf(z)<0});
    orders[1]=[leader].concat(settleTop,rest)
  }
  orders[1].slice(0,Math.min(6,orders[1].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    var explicitRetreat=(z.fade>=.58&&z.frontCost>=.14)||(z.outerStress>=.68&&z.goProb>=.46)||
      (q.lineMiddle&&z.needLead>=.66&&z.flexibility<.40)||(q.sandwich&&z.flexibility<.38);
    if(explicitRetreat)move(orders[1],z,1);
    if(z.minetaEscapeOutside&&z.expected!=='逃げ候補'&&q.conflict<.55)move(orders[1],z,-1);
    if(z.minetaDifferentStyleNeighbor&&q.conflict<.55)move(orders[1],z,-1)
  });
  if(leader&&topRank(orders[1],leader)>1)moveTo(orders[1],leader,0);

  // BACKSTRETCH: mostly preserve established positions. Only obvious over-racing /
  // early-pressure horses concede a place; flexible stalkers can tuck in.
  orders[2]=orders[1].slice();
  orders[2].slice(0,Math.min(6,orders[2].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    if(z.fade>=.58&&z.frontCost>=.14&&z.needLead>=.50)move(orders[2],z,1);
    else if(z.canYield&&z.needLead>=.45&&topRank(orders[2],z)<=3&&q.conflict>=.55)move(orders[2],z,1)
  });

  // 3C: movers begin advancing. They gain only a small number of positions per
  // phase; this is a transition, not a wholesale re-ranking.
  orders[3]=orders[2].slice();
  var movers3=lex(rows.filter(function(z){return z.move>=.55&&z.latePower>=.50&&topRank(orders[3],z)>3}),[
    function(z){return z.move*.40+n(z.turnSkill,.5)*.22+z.latePower*.23+n(z.ability,.5)*.15},
    function(z){return z.comeFromBehind}
  ]);
  movers3.slice(0,code==='C'?3:2).forEach(function(z){
    var gain=(code==='C'&&paceHeat>=.22&&n(z.turnSkill,.5)>=.56)?2:1;
    move(orders[3],z,-gain)
  });
  orders[3].slice(0,Math.min(5,orders[3].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    if(z.fade>=.62&&z.frontCost>=.15&&(q.sandwich||q.conflict>=.60))move(orders[3],z,1)
  });

  // 4C: commit moves, but maintain continuity. A closer cannot teleport from last
  // to first in one step, and a leader does not collapse without fatigue evidence.
  orders[4]=orders[3].slice();
  var movers4=lex(rows.filter(function(z){return z.move>=.58&&z.latePower>=.56&&topRank(orders[4],z)>2}),[
    function(z){return z.move*.38+z.latePower*.30+n(z.turnSkill,.5)*.17+n(z.ability,.5)*.15},
    function(z){return z.comeFromBehind}
  ]);
  movers4.slice(0,code==='C'?3:2).forEach(function(z){
    var gain=(code==='C'&&paceHeat>=.20&&ct.moveRoom>=.45)?2:1;
    move(orders[4],z,-gain)
  });
  orders[4].slice(0,Math.min(5,orders[4].length)).forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    var severe=z.fade>=.68&&z.frontCost>=.18&&(q.sandwich||q.conflict>=.65);
    if(severe)move(orders[4],z,1)
  });

  // STRAIGHT: resolve hold / fade / pass events. Position changes require a reason.
  orders[5]=orders[4].slice();
  var frontAt4=orders[4].slice(0,Math.min(4,orders[4].length));
  frontAt4.forEach(function(z){
    q=p[n(z.horse.horseNumber)]||{};
    var stress=exposure(z),
        severeFade=z.fade>=.67&&(stress>=.19||z.frontCost>=.18||q.conflict>=.70||q.sandwich),
        moderateFade=z.fade>=.56&&(stress>=.13||z.frontCost>=.12||q.conflict>=.52),
        strongHold=z.frontStay>=.66&&z.holdFront>=.56&&z.fade<.52&&stress<.24;
    if(severeFade)move(orders[5],z,code==='C'?3:2);
    else if(moderateFade)move(orders[5],z,1);
    else if(strongHold&&topRank(orders[5],z)>topRank(orders[4],z))moveTo(orders[5],z,topRank(orders[4],z)-1)
  });

  var closers=lex(rows.filter(function(z){return isCloser(z)&&z.latePower>=.56&&z.comeFromBehind>=.56}),[
    function(z){return z.comeFromBehind},function(z){return z.latePower},function(z){return z.move}
  ]);
  // Runners have finite overtaking capacity: each pass needs superiority to
  // the horse directly ahead. No fixed -5 rank leap or magic lead restoration.
  var straightRoom=clamp(ct.straight*.68+ct.moveRoom*.32,0,1);
  closers.slice(0,code==='C'?3:2).sort(function(a,b){return finishStrength(b)-finishStrength(a)}).forEach(function(z){
    var cap=1+(straightRoom>=.58?1:0)+(n(z.latePower,0)>=.69&&straightRoom>=.55?1:0);
    if(code==='A')cap=Math.max(1,cap-1);
    if(code==='C'&&paceHeat>=.26&&straightRoom>=.58)cap+=1;
    for(var pass=0;pass<cap;pass++){
      var at=orders[5].indexOf(z);if(at<=0)break;
      var rival=orders[5][at-1];
      var gap=topRank(orders[4],z)-topRank(orders[4],rival);
      var required=.018+Math.max(0,gap-2)*.010+(code==='A'?.020:0);
      if(finishStrength(z)<finishStrength(rival)+required)break;
      move(orders[5],z,-1)
    }
  });
  if(leader){
    q=p[n(leader.horse.horseNumber)]||{};
    var leaderCollapse=leader.fade>=.66&&(exposure(leader)>=.19||leader.frontCost>=.18||q.conflict>=.68||q.sandwich),
        leaderHold=leader.frontStay>=.64&&leader.holdFront>=.54&&leader.fade<.55&&exposure(leader)<.24,
        challenger=orders[5].slice(0,Math.max(1,topRank(orders[5],leader)-1)).some(function(z){
          return finishStrength(z)>finishStrength(leader)+.025
        });
    if(leaderHold&&!leaderCollapse&&!challenger){
      var cap=(code==='C'&&leader.frontStay<.72)?2:1;
      if(topRank(orders[5],leader)>cap)moveTo(orders[5],leader,cap-1)
    }
  }

  // Build display stages from actual state order. score is only a normalized
  // screen-position rank for downstream compatibility; it is NOT the pace model.
  var labels=['スタート','1コーナー','向正面','3コーナー','4コーナー','直線'],
      keys=['start','first','back','turn3','turn4','straight'],packs=[],stages=[],markScore={};
  for(i=0;i<6;i++){
    packs[i]=eventOrderPack(rows,orders[i],lanes,i);
    stages.push({key:keys[i],label:labels[i],pack:packs[i],model:'event-transition-v2'})
  }
  orders[5].forEach(function(z,idx){markScore[n(z.horse.horseNumber)]=orders[5].length<=1?1:1-idx/(orders[5].length-1)});
  return{scenario:scenario,stages:stages,start:orders[0],corner:orders[4],straight:orders[5],markScore:markScore,model:'event-transition-v2'}
}
function gradeClass(g){return g==='S'?'grade-s':(g==='A'?'grade-a':(g==='B'?'grade-b':'grade-c'))}
function predictionProfile(r){
  var mode=raceMode(r);
  if(mode==='障害')return{code:'JUMP',label:'障害専用モデル',version:'ARVEXQ-JUMP-v3'};
  if(mode==='新馬')return{code:'DEBUT',label:'新馬専用モデル',version:'ARVEXQ-DEBUT-v3'};
  if(r.circuit==='地方')return{code:'NAR',label:'地方専用モデル',version:'ARVEXQ-NAR-v3'};
  return{code:'JRA',label:'中央専用モデル',version:'ARVEXQ-JRA-v3'}
}
function gradeRowsRelative(rows){
  if(!rows.length)return;
  var lo=Math.min.apply(null,rows.map(function(z){return z.overallRaw})),
      hi=Math.max.apply(null,rows.map(function(z){return z.overallRaw}));
  rows.forEach(function(z){
    var rel=hi===lo?.5:(z.overallRaw-lo)/(hi-lo), exact=clamp(z.overallRaw*.80+(.44+.56*rel)*.20,0,1)*100;
    z.overallScoreExact=Math.round(exact*10)/10;
    z.overallScore=Math.round(exact)
  });
  // v155: rank by the unrounded model value first. The UI and marks reuse this rank,
  // so horses tied at e.g. 76 points can no longer show the S horse in 3rd place.
  rows.sort(function(a,b){return n(b.overallRaw)-n(a.overallRaw)||n(b.overallScore)-n(a.overallScore)||n(b.ability)-n(a.ability)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
  var m=rows.length;
  rows.forEach(function(z,rank){
    var pct=(rank+1)/m,score=z.overallScore;
    z.overallRank=rank+1;
    if((score>=83)||(pct<=.12&&score>=72))z.overallGrade='S';
    else if((score>=73)||(pct<=.35&&score>=65))z.overallGrade='A';
    else if((score>=60)||(pct<=.70))z.overallGrade='B';
    else z.overallGrade='C';
    if(!z.overallReasons.length)z.overallReasons.push('総合バランス型')
  })
}
function baseGradeReasons(x,su,fitScore){
  x.overallReasons=[];
  if(x.ability>=.62)x.overallReasons.push('能力評価高め');
  if(n(su.overall)>=.62)x.overallReasons.push('展開適性高め');
  if(x.frontStay>=.64)x.overallReasons.push('前残り力');
  if(x.comeFromBehind>=.64)x.overallReasons.push('差し込み力');
  if(x.fade<=.25)x.overallReasons.push('下がり率低め');
  if(fitScore>=.58)x.overallReasons.push('今回条件に実績');
  if(x.bodyWeightKnown&&x.bodyWeightSuit>=.58)x.overallReasons.push('馬体重変動は安定圏');
  if(x.bodyWeightKnown&&x.bodyWeightSuit<=.45)x.overallReasons.push('馬体重変動注意');
  if(x.frontCost>=.12)x.overallReasons.push('隣接圧力注意');
  if(x.fade>=.50)x.overallReasons.push('下がり率注意');
  if(x.coverage<.45)x.overallReasons.push('データ補完中・複数ソース確認');
  if((x.horse.recentRaces||[]).length<2||x.styleSamples<2)x.overallReasons.push('限定データ評価')
}
function recentPeakScore(h,r){
  var runs=(h&&h.recentRaces)||[],best=.34,i,z,finish,field,sameTrack,sameDist,score;
  for(i=0;i<Math.min(5,runs.length);i++){
    z=runs[i]||{};finish=n(z.finish||z.finishPosition,99);field=Math.max(6,n(z.fieldSize,12));
    sameTrack=String(z.track||'')===String(r.track||'')?1:0;
    sameDist=Math.abs(n(z.distance)-n(r.distance))<=150?1:0;
    score=.28;
    if(finish<99)score+=clamp((field-finish)/Math.max(1,field-1),0,1)*.42;
    if(finish<=3)score+=.10;
    score+=sameTrack*.10+sameDist*.08;
    if(score>best)best=score
  }
  return clamp(best,0,1)
}
function edgeSoftmax(values,temp){
  if(!values||!values.length)return[];
  temp=Math.max(.035,n(temp,.09));
  var mx=Math.max.apply(null,values),ex=[],sum=0,i,v;
  for(i=0;i<values.length;i++){v=Math.exp((values[i]-mx)/temp);ex.push(v);sum+=v}
  if(!sum)return values.map(function(){return 1/values.length});
  return ex.map(function(z){return z/sum})
}
function conservativeProbabilityGuard(values,evidence,role){
  values=(values||[]).slice();if(!values.length)return[];
  var sum=values.reduce(function(a,b){return a+Math.max(0,n(b))},0)||1,field=values.length,uniform=1/field,
      ev=(evidence&&evidence.length)?mean(evidence.map(function(z){return clamp(n(z,.5),0,1)})):.5,
      extra=field>10?Math.min(.035,(field-10)*.004):0,
      cap=role==='p1'?.18:.22,
      shrink=Math.min(cap,.045+(1-ev)*.125+extra),out=[];
  values.forEach(function(v){var q=Math.max(0,n(v))/sum;out.push(uniform+(q-uniform)*(1-shrink))});
  var z=out.reduce(function(a,b){return a+b},0)||1;return out.map(function(v){return v/z})
}
function tripRecoveryProfile(x,r){
  var runs=(x.horse&&x.horse.recentRaces)||[],rr=runs[0]||{},field=Math.max(6,n(rr.fieldSize,12)),finish=n(rr.finish||rr.finishPosition,0),corners=rr.cornerPositions||[],first=corners.length?n(corners[0],0):0,last=corners.length?n(corners[corners.length-1],0):0,score=.50,reasons=[],gain=0;
  if(finish>0&&last>0){
    gain=(last-finish)/Math.max(5,field-1);
    score+=clamp(gain,-.22,.34)*.55;
    if(gain>=.12)reasons.push('前走4角から着順を上げた')
  }
  if(finish>Math.ceil(field*.55)&&n(x.lateGain)>=.60){score+=.07;reasons.push('着順以上の末脚')}
  if(first>0&&first<=3&&finish>Math.ceil(field*.60)&&n(x.flexibility)>=.52){score+=.035;reasons.push('前走先行失速から形替わり余地')}
  if(n(x.posCons)>=.64)score+=.025;
  return{score:clamp(score,.28,.78),reasons:reasons.slice(0,2)}
}
function recentTop3Rate(h){
  var runs=(h&&h.recentRaces)||[],m=Math.min(5,runs.length),i,hit=0,used=0,fin;
  for(i=0;i<m;i++){fin=n(runs[i]&&runs[i].finish||runs[i]&&runs[i].finishPosition,0);if(fin>0){used++;if(fin<=3)hit++}}
  return used?hit/used:.25
}
function sameConditionFrontMemory(x,r){
  var runs=(x.horse&&((x.horse.allPastRuns&&x.horse.allPastRuns.length)?x.horse.allPastRuns:x.horse.recentRaces))||[],i,rr,corners,first,field,front=0,frontCount=0,matchCount=0,movedOnly=0,hold=0;
  for(i=0;i<Math.min(5,runs.length);i++){
    rr=runs[i]||{};
    if(String(rr.track||'')!==String(r.track||''))continue;
    if(Math.abs(n(rr.distance)-n(r.distance))>150)continue;
    if(rr.surface&&r.surface&&String(rr.surface)!==String(r.surface))continue;
    matchCount++;corners=rr.cornerPositions||[];first=corners.length?n(corners[0],0):0;field=Math.max(6,n(rr.fieldSize,12));
    if(first>0&&first<=3){frontCount++;front=Math.max(front,clamp(1-(first-1)/Math.max(2,field-1),0,1));if(n(rr.finish||rr.finishPosition,99)<=3)hold=Math.max(hold,.85)}
    else if(corners.some&&corners.some(function(v){return n(v)>0&&n(v)<=3}))movedOnly++;
  }
  return{score:frontCount?clamp(.58+front*.32+Math.min(2,frontCount)*.05,0,1):0,frontCount:frontCount,matchCount:matchCount,movedOnly:movedOnly,hold:hold}
}
function sparseResetProfile(x,r,q){
  q=q||{};
  var mem=sameConditionFrontMemory(x,r),vacancy=clamp(n(x.leadVacancyBoost)/.18,0,1),conflict=clamp(n(q.conflict),0,1),free=clamp(1-conflict,0,1),
      runs=(x.horse&&x.horse.recentRaces)||[],rr=runs[0]||{},corners=rr.cornerPositions||[],first=corners.length?n(corners[0],0):0,field=Math.max(6,n(rr.fieldSize,12)),finish=n(rr.finish||rr.finishPosition,0),
      lastFrontFade=first>0&&first<=3&&finish>Math.ceil(field*.55),frontMemoryVacancy=0,fadeRecovery=0,reasons=[];
  // Validated rule: historical same-course/similar-distance early speed only matters when the current lead is actually vacant.
  if(mem.score>=.58&&vacancy>=.28&&conflict<=.50){frontMemoryVacancy=clamp(mem.score*vacancy*free,0,1);if(frontMemoryVacancy>=.16)reasons.push('同場同距離の前付け記憶×今回ハナ余地')}
  // Validated rule: a horse that went forward and faded last time is not blindly upgraded; pressure must ease today.
  if(lastFrontFade&&vacancy>=.22&&conflict<=.45){fadeRecovery=clamp(vacancy*free,0,1);if(fadeRecovery>=.16)reasons.push('前走先行失速×今回は競り圧低下')}
  var score=clamp(frontMemoryVacancy*.62+fadeRecovery*.38,0,1);
  return{score:score,frontMemoryVacancy:frontMemoryVacancy,fadeRecovery:fadeRecovery,frontMemory:mem.score,frontMemoryCount:mem.frontCount,lastFrontFade:lastFrontFade,reasons:reasons.slice(0,2)}
}
function raceTargetProfile(r,p){
  var rows=(p&&p.rows)||[],holes=rows.filter(function(x){return n(x.winRank)>=4&&n(x.bombScore)>=58&&n(x.edgeScore)>=56&&(n(x.p2Rank)<=5||n(x.p3Rank)<=6||n(x.p1Probability)>=1/Math.max(1,rows.length)*.52)}).sort(function(a,b){return n(b.bombScore)-n(a.bombScore)||n(b.roleUpside)-n(a.roleUpside)||n(b.edgeScore)-n(a.edgeScore)}),
      h1=holes[0]?n(holes[0].bombScore):0,h2=holes[1]?n(holes[1].bombScore):0,
      vol=n(r&&r.volatility&&r.volatility.score,0),volNorm=clamp(vol/18,0,1),
      sc=(p&&p.scenarios)||[],uncertainty=0,cov=n(p&&p.coverage,0);
  if(sc.length){var probs=sc.map(function(z){return n(z.prob)}).sort(function(a,b){return b-a});uncertainty=clamp(1-((probs[0]||0)-(probs[1]||0)),0,1)}
  var resetMax=rows.length?Math.max.apply(null,rows.map(function(z){return n(z.sparseReset)})):0,roleMax=rows.length?Math.max.apply(null,rows.map(function(z){return n(z.roleUpside)/100})):0,
      score=Math.round(clamp((h1/100)*.43+(h2/100)*.11+volNorm*.10+uncertainty*.07+cov*.10+resetMax*.12+roleMax*.07,0,1)*100),grade='C',label='本線寄り';
  if(score>=78){grade='S';label='RESET/ROLE穴を頭まで検討'}
  else if(score>=68){grade='A';label='ROLE穴を2・3着以上へ'}
  else if(score>=57){grade='B';label='相手穴を拾う'}
  return{score:score,grade:grade,label:label,holes:holes.slice(0,3)}
}
function raceSelectionProfile(r,p){return strictSelectedRaceProfile(r,p)}
function dataReadinessProfile(r,p){
  var hs=((r&&r.horses)||[]).filter(function(h){return !isScratchHorse(h)}),field=hs.length||1,
      card=hs.filter(function(h){return String(h.name||'').trim()&&String(h.jockey||'').trim()}).length/field,
      hist=mean(hs.map(function(h){if(h.debutNoHistory)return 1;return Math.min(5,((h.recentRaces||h.allPastRuns||[]).length))/5})),
      actual=hs.filter(function(h){return n(h.winOdds)>1&&!h.oddsForecast&&!/予想|forecast/i.test(String(h.oddsSource||''))}).length/field,
      body=hs.filter(function(h){var w=n(h.bodyWeight);return w>=250&&w<=800}).length/field,
      env=((r&&r.weather&&String(r.weather)!=='不明')?.5:0)+((r&&r.condition&&String(r.condition)!=='不明')?.5:0),
      analysis=clamp(n(p&&p.coverage,0),0,1),server=(r&&r.dataCoreHealth)||{},serverAnalysis=n(server.analysis&&server.analysis.completeness,0)/100,
      // v302: readiness must not flip just because the clock entered a T-120 window.
      // Body weight improves the model when published; unpublished weight is neutral.
      bodyReady=body>0?body:1;
  if(serverAnalysis>0)analysis=Math.max(analysis,serverAnalysis);
  var prediction=clamp(card*.18+hist*.28+env*.15+analysis*.28+bodyReady*.11,0,1),
      market=clamp(prediction*.72+actual*.28,0,1),missing=[];
  if(card<.90)missing.push('出馬表');if(hist<.70)missing.push('近走');if(env<.50)missing.push('馬場');if(analysis<.45)missing.push('診断');if(actual<.65)missing.push('実オッズ');
  return{prediction:prediction,market:market,card:card,history:hist,actualOdds:actual,bodyWeight:body,environment:env,analysis:analysis,missing:missing}
}
function arvexqFactorValues(z,r){
  // Mirrors Python: actual pre-race five-run evidence only; no old composite.
  var h=z&&z.horse||{},cutoff=String(r&&r.date||''),
      pool=[].concat(h.recentRaces||[],h.allPastRuns||[]),seen={},runs=[];
  pool.sort(function(a,b){return String(b&&b.date||b&&b.raceDate||'').localeCompare(String(a&&a.date||a&&a.raceDate||''))});
  pool.forEach(function(q){
    if(!q||!cutoff)return;
    var date=String(q.date||q.raceDate||'').slice(0,10),field=Number(q.fieldSize),
        finish=Number(q.finish||q.finishPosition||q.rank),
        key=String(q.raceId||'')+'|'+date+'|'+String(q.track||'')+'|'+String(q.raceNumber||'');
    if(!date||date>=cutoff||seen[key]||!(field>=2&&finish>=1&&finish<=field))return;
    seen[key]=1;
    if(runs.length<5)runs.push({source:q,quality:(field-finish)/(field-1),field:field});
  });
  var quality=runs.map(function(x){return x.quality}),tr=null,pure=null,sec=null;
  if(quality.length){
    var total=0,weight=0;
    quality.forEach(function(v,i){var w=5-i;total+=w*v;weight+=w});
    tr=total/weight;
    var ranked=quality.slice().sort(function(a,b){return a-b});
    var mid=ranked.length%2?ranked[(ranked.length-1)/2]:
      (ranked[ranked.length/2-1]+ranked[ranked.length/2])/2;
    pure=(ranked[ranked.length-1]+mid)/2;
  }
  var closes=[];
  runs.forEach(function(x){
    var q=x.source,field=x.field,rank=Number(q.last3fRank||q.last600Rank),
        percentile=q.last3fPercentile==null?null:Number(q.last3fPercentile);
    if(rank>=1&&rank<=field)closes.push((field-rank)/(field-1));
    else if(percentile!==null&&isFinite(percentile)&&percentile>=0&&percentile<=1)closes.push(percentile);
  });
  if(closes.length)sec=closes.reduce(function(a,b){return a+b},0)/closes.length;
  return {trueRun:tr,pure:pure,sectional:sec,
    coverage:(tr!==null?1:0)+(pure!==null?1:0)+(sec!==null?1:0),
    score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)};
}
function arvexqRacePolicy(r){
  return {id:'arvexq-true-run-pure-sectional-v2',
    value:{cov:.52,ready:.64,oddsCoverage:.85,ev:1.25,edge:66,evidence:.52,kelly:.030,score:80}};
}
function strictSelectedRaceProfile(r,p){
  var rows=((p&&p.rows)||[]).filter(function(z){return z&&z.horse&&!isScratchHorse(z.horse)}),
      ready=dataReadinessProfile(r,p),ordered=rows.slice().sort(function(a,b){return n(b.threeFactorScore)-n(a.threeFactorScore)}),
      top=ordered[0]||{},next=ordered[1]||{},score=Math.round(n(top.threeFactorScore,0)*100),
      margin=n(top.threeFactorScore,0)-n(next.threeFactorScore,0),coverage=n(top.threeFactorCoverage,0);
  var failed=[];
  if(rows.length<5)failed.push('頭数不足');
  if(coverage<3)failed.push('3要素根拠不足');
  var measured=rows.filter(function(z){return n(z.threeFactorCoverage)>=2}).length;
  if(measured<Math.ceil(rows.length*.70))failed.push('近走実測根拠不足');
  if(top.predMark!=='◎')failed.push('◎不一致');
  var selected=!failed.length;
  return {selected:selected,score:score,top:n(top.p1Probability,0),margin:margin,
    coverage:coverage/3,readiness:ready,failed:failed,
    reason:selected?'発走前の3指標が有効（券種別的中率は独立審査）':'見送り: '+failed.join('・'),
    model:'arvexq-true-run-pure-sectional-v2'};
}
// Optional ☆ eligibility changes neither the ranking nor the 45/35/20 score.
function eligibleOptionalStar(z,fourthScore){
  var f=z&&z.threeFactorValues||{},vals=[f.trueRun,f.pure,f.sectional];
  if(!z||n(z.threeFactorCoverage,0)!==3||
    vals.some(function(v){return v==null||!isFinite(Number(v))}))return false;
  var score=n(z.threeFactorScore,0),strong=vals.filter(function(v){return Number(v)>=.68}).length;
  return score>=.68&&n(fourthScore,0)-score<=.075&&strong>=2&&
    (n(f.trueRun,0)>=.70||n(f.sectional,0)>=.70);
}
function assignPredictionMarks(rows,r){
  if(!rows.length)return;
  var field=rows.length,ordered,topScore,total=0,weights=[],i,j,k;
  rows.forEach(function(z){var f=arvexqFactorValues(z,r);
    z.threeFactorScore=f.score;z.threeFactorCoverage=f.coverage;
    z.threeFactorValues={trueRun:f.trueRun,pure:f.pure,sectional:f.sectional};
    z.researchFactors={ability:f.pure,form:f.trueRun,pace:f.sectional,suitability:null,classLevel:null,connections:null,pedigree:null};
    z.researchModel='arvexq-true-run-pure-sectional-v2';
    z.researchConsensusScore=f.score;
    z.overallScoreExact=f.score*100;z.overallScore=f.score*100;z.overallRaw=f.score;
    z.hasFrozenEvaluation=f.coverage>0;
    z.modelScore=f.score*100;
    z.overallGrade=f.coverage===3&&f.score>=.80?'A':(f.coverage>=2&&f.score>=.65?'B':'C');
    z.predMark='';z.predRank=999;z.attentionReason='';
    var ev=z.horse&&z.horse.integratedEvaluation;
    if(ev){ev.score=z.overallScore;ev.grade=z.overallGrade;ev.modelVersion='arvexq-true-run-pure-sectional-v2';}
    if(z.evaluation){z.evaluation.score=z.overallScore;z.evaluation.grade=z.overallGrade;
      z.evaluation.modelScore=z.overallScore;z.evaluation.predictionModel='arvexq-true-run-pure-sectional-v2';
      z.evaluation.mode='TRUE RUN45%＋PURE35%＋SECTIONAL20%';}
  });
  if(rows.every(function(z){return z.threeFactorCoverage===0})){
    rows.forEach(function(z){z.predMark='';z.predRank=999;z.hasFrozenEvaluation=false});
    r.honmeiDecisionFrontend={version:'arvexq-true-run-pure-sectional-v2',
      eligible:false,horseNumber:0,role:'none',confidenceGrade:'',
      reason:'three-factor-evidence-missing'};
    return;
  }
  ordered=rows.slice().sort(function(a,b){return n(b.threeFactorScore)-n(a.threeFactorScore)||
    n(b.threeFactorCoverage)-n(a.threeFactorCoverage)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
  topScore=n(ordered[0].threeFactorScore,.5);
  rows.forEach(function(z){var w=Math.exp((n(z.threeFactorScore,.5)-topScore)/.15);weights.push(w);total+=w});
  // One source of truth for all three finishing roles: Plackett-Luce marginals.
  var p1=weights.map(function(w){return w/Math.max(1e-12,total)}),
      p2=weights.map(function(){return 0}),p3=weights.map(function(){return 0});
  for(i=0;i<field;i++){
    var rem=total-weights[i];
    if(rem<=1e-12)continue;
    for(j=0;j<field;j++)if(i!==j){
      var second=p1[i]*weights[j]/rem,rest=rem-weights[j];
      p2[j]+=second;
      if(rest>1e-12)for(k=0;k<field;k++)if(k!==i&&k!==j)p3[k]+=second*weights[k]/rest;
    }
  }
  var top=ordered[0],runner=ordered[1],gap=n(top.threeFactorScore)-n(runner&&runner.threeFactorScore);
  var grade=top.threeFactorCoverage===3&&n(top.threeFactorScore)>=.80&&gap>=.04?'A':
            (top.threeFactorCoverage>=2&&n(top.threeFactorScore)>=.65?'B':'C');
  rows.forEach(function(z,idx){
    z.p1Probability=p1[idx];z.p2Probability=p2[idx];z.p3Probability=p3[idx];
    z.winProbability=p1[idx];z.pureWinProbability=p1[idx];z.evWinProbability=p1[idx];
    z.winnerDecisionProbability=p1[idx];z.winnerConsensusProbability=p1[idx];
    z.winEvidenceProbability=p1[idx];z.axisProbability=(p1[idx]+p2[idx]+p3[idx])/3;
    z.podiumRecallScore=clamp(p1[idx]+p2[idx]+p3[idx],0,1);
    z.p2RecallScore=p2[idx];z.p3RecallScore=p3[idx];
    z.pairwiseWinRate=(field>1?rows.reduce(function(sum,x){return sum+(z.threeFactorScore>x.threeFactorScore?1:(z.threeFactorScore===x.threeFactorScore?.5:0))},0)/field:.5);
    z.winnerDecisionStable=top.threeFactorCoverage===3&&gap>=.04;
    z.axisConfidence=top.threeFactorCoverage/3*clamp(.5+gap*3,0,1);
    z.marketProbability=n(z.marketProbability,0);z.edgeRatio=z.marketProbability>0?p1[idx]/z.marketProbability:0;
    z.edgeScore=z.marketProbability>0?Math.round(clamp(50+Math.log(Math.max(1e-9,z.edgeRatio))/Math.LN2*12,0,100)):50;
    z.bombScore=Math.round(clamp(z.podiumRecallScore*100,0,100));
    z.honmeiRole='';z.honmeiGrade='';z.podiumAxisEligible=false;
    z.winEvidenceRank=0;z.winnerConsensusRank=0;z.winnerDecisionRank=0;
  });
  var winOrder=rows.slice().sort(function(a,b){return n(b.p1Probability)-n(a.p1Probability)});
  var secondOrder=rows.slice().sort(function(a,b){return n(b.p2Probability)-n(a.p2Probability)});
  var thirdOrder=rows.slice().sort(function(a,b){return n(b.p3Probability)-n(a.p3Probability)});
  winOrder.forEach(function(z,idx){z.winRank=idx+1;z.p1Rank=idx+1;z.winnerDecisionRank=idx+1;
    z.winnerConsensusRank=idx+1;z.winEvidenceRank=idx+1;z.pairwiseRank=idx+1;});
  secondOrder.forEach(function(z,idx){z.p2Rank=idx+1;z.p2RecallRank=idx+1});
  thirdOrder.forEach(function(z,idx){z.p3Rank=idx+1;z.p3RecallRank=idx+1});
  var labels=['◎','○','▲','△'],fourthScore=n(ordered[Math.min(3,ordered.length-1)].threeFactorScore,0);
  var starCandidate=ordered.slice(4).find(function(z){return eligibleOptionalStar(z,fourthScore)})||null;
  ordered.forEach(function(z,idx){z.predRank=idx+1;
    z.predMark=idx<labels.length?labels[idx]:(z===starCandidate?'☆':'');
    z.honmeiRole=idx===0?'win':'';
    z.honmeiGrade=idx===0?grade:'';
    z.podiumAxisEligible=idx===0&&grade==='A';
    z.singleWinSuitable=idx===0&&grade==='A';z.singleWinStrength=n(z.threeFactorScore);
    z.singleWinReason=idx===0?'同一3要素で1着・3着内の軸を判定':'';
    z.attentionReason=idx===0?'TRUE RUN 45%＋PURE 35%＋SECTIONAL 20%｜信頼度'+grade:
      (idx<labels.length?'総合 '+Math.round(z.threeFactorScore*100)+'/100':
       (z===starCandidate?'TRUE RUN・PURE・SECTIONALの複数独立根拠により選出':''));
    var e=z.horse&&z.horse.integratedEvaluation;
    if(e){e.mark=z.predMark;e.honmeiRole=z.honmeiRole;e.honmeiGrade=z.honmeiGrade;
      e.honmeiEligible=z.podiumAxisEligible;}
  });
  // 注 and ☆+ are retired for new predictions. ☆ is optional, not rank five.
  r.honmeiDecisionFrontend={version:'arvexq-true-run-pure-sectional-v2',eligible:grade==='A',
    horseNumber:n(top.horse.horseNumber),role:'win',confidenceGrade:grade,
    axisScore:n(top.threeFactorScore),axisGap:gap,
    reason:grade==='A'?'strong-unified-honmei':'relative-honmei-not-fixed'};
  r.predictionModelVersion='arvexq-true-run-pure-sectional-v2';
}

// v343 — standalone win-only call, independent of ◎ and of market odds.
function assignSingleWinCandidate(rows,r){
  return (rows||[]).find(function(z){return z.predMark==='◎'&&z.honmeiGrade==='A'})||null;
}

function raceMode(r){r=r||{};if(['平地','新馬','障害'].indexOf(r.analysisMode)>=0)return r.analysisMode;var title=String(r.title||'');if(r.surface==='障害'||/障害|J[･・.]?G[ⅠⅡⅢ123]|\bJS\b|ジャンプ/i.test(title))return '障害';return /新馬|メイクデビュー/.test(title)?'新馬':'平地'}
function saveRaceAnalysis(r,p){return}
function isScratchHorse(h){var s=String(h&&h.status||'');return !!(h&&(h.scratched===true||h.withdrawn===true||/欠場|出走取消|取消|競走除外|除外/.test(s)))}
function analysisRace(r){
  var active=(r.horses||[]).filter(function(h){return !isScratchHorse(h)}).map(function(h){
    var runs=h.allPastRuns||h.recentRaces||[];
    if(raceMode(r)==='障害')runs=runs.filter(function(z){return /障害|ジャンプ|J[・･.]?G|\bJS\b/i.test((z.surface||'')+(z.title||''))});
    return Object.assign({},h,{recentRaces:runs,allPastRuns:runs})
  });
  return Object.assign({},r,{horses:active,fieldSize:active.length||n(r.fieldSize)})
}
function integratedGrades(r,rows){
  rows.forEach(function(x){
    var score=n(x.overallScore,50),coverage=n(x.threeFactorCoverage,0)/3;
    x.modelScore=score;
    x.evidenceScore=null;
    x.evaluation={
      score:score,
      grade:x.overallGrade||'C',
      modelScore:score,
      evidenceScore:null,
      predictionModel:'arvexq-true-run-pure-sectional-v2',
      confidence:coverage>=.72?'高':(coverage>=.45?'中':'低'),
      tier:coverage>=1?'3指標実測評価':(coverage>=2/3?'2指標実測評価':'実測データ不足'),
      mode:'近走内容45%・基礎能力35%・区間性能20%',
      winProbability:n(x.winProbability),
      p1Probability:n(x.p1Probability),
      p2Probability:n(x.p2Probability),
      p3Probability:n(x.p3Probability),
      p1Rank:n(x.p1Rank),
      p2Rank:n(x.p2Rank),
      p3Rank:n(x.p3Rank),
      sparseReset:n(x.sparseReset),
      marketProbability:n(x.marketProbability),
      edgeScore:n(x.edgeScore),
      bombScore:n(x.bombScore),
      paceScore:n(x.paceScore),
      tripScore:n(x.tripScore),
      shiftScore:n(x.shiftScore)
    }
  })
}

// v345: immutable *displayed* marks, independent of live odds, body weight
// refresh and the mutable winner model.  The server pre-race archive is preferred
// after the off.  A local device freeze is recorded BEFORE the scheduled start.
function raceMarkClock(r){
  var date=String(r&&r.date||''),post=mins(r&&r.startTime),current=today(),
      status=String(r&&r.raceStatus||''),
      resultPublished=isFinal(r)||isFlash(r)||hasAnyResultData(r)||
        /^(?:発走済|発走中|発走$|進行中|確定|速報|終了)/.test(status);
  return {valid:!!date&&post<9999,
    started:resultPublished||!!date&&(date<current||(date===current&&post<9999&&nowMins()>=post)),
    remaining:date===current?post-nowMins():9999};
}
// Retired v345 device-only frozen marks are not loaded or written by this UI.
// Server-side pre-off receipts remain available for historical audit.
// Server archive is trusted only with evidence of a genuine pre-off capture.
function serverFrozenPrediction(r){
  if(!r||!r.id)return null;
  var q=r.preRacePrediction||{},clock=raceMarkClock(r);
  if(!q.frozen||!clock.valid||String(q.raceId||'')!==String(r.id)||
     String(q.raceDate||'')!==String(r.date)||!Array.isArray(q.horses)||q.horses.length<2)return null;
  var post=Date.parse(String(r.date)+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      captured=n(q.capturedAtEpoch,0)*1000;
  if(!isFinite(post)||!captured||captured>=post)return null;
  var seen={};
  for(var i=0;i<q.horses.length;i++){var v=q.horses[i]||{},no=n(v.horseNumber,0);
    if(!no||seen[no]||['','◎','○','▲','☆+','☆','△','注'].indexOf(String(v.mark||''))<0)return null;
    seen[no]=1;
  }
  return q;
}
function validMorningMarkSnapshot(r){
  var snap=r&&r.morningMarkSnapshot;
  // D1 can lose its prediction row while the original static morning receipt
  // survives. A verified dated receipt is the only alternative evidence.
  if((!snap||!Array.isArray(snap.horses))&&r){
    var evidence=r.morningTicketEvidence,
        source=(typeof window!=='undefined'&&window.ARVEXQMorningEvidence)||null;
    if(source&&source.verify(r,evidence)){
      snap={version:'arvexq-morning-marks-v1',
        raceId:String(r.id),raceDate:String(r.date),
        fixedAt:evidence.fixedAt,source:'static-original-ticket-evidence',
        horses:evidence.marks};
    }
  }
  if(!r||!snap||snap.version!=='arvexq-morning-marks-v1'||
      String(snap.raceId||'')!==String(r.id)||String(snap.raceDate||'')!==String(r.date)||
      !Array.isArray(snap.horses)||snap.horses.length<3)return null;
  var post=Date.parse(String(r.date||'')+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      fixed=Date.parse(String(snap.fixedAt||''));
  return isFinite(post)&&isFinite(fixed)&&fixed<post?snap:null
}
function latestOfficialMarkRevision(r){
  var initial=validMorningMarkSnapshot(r);
  if(!initial)return null;
  var post=Date.parse(String(r.date||'')+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      latest=null;
  (r.officialMarkRevisions||[]).forEach(function(z){
    if(!z||z.version!=='arvexq-official-mark-revision-v1'||
        String(z.raceId||'')!==String(r.id)||String(z.raceDate||'')!==String(r.date)||
        !Array.isArray(z.horses)||z.horses.length<3)return;
    var at=Date.parse(String(z.revisedAt||'')),
        announced=Date.parse(String((z.officialCourseCondition||{}).publishedAt||'')),
        url=String((z.officialCourseCondition||{}).sourceUrl||'');
    if(!isFinite(at)||!isFinite(announced)||at>=post||announced>at||!/^https:\/\//.test(url))return;
    if(!latest||Date.parse(String(latest.revisedAt||''))<at)latest=z
  });
  return latest
}
function latestUserApprovedModelMarkRevision(r){
  var initial=validMorningMarkSnapshot(r);
  if(!initial||String(r.date)!=='2026-10-09')return null;
  var post=Date.parse(String(r.date||'')+'T'+String(r.startTime||r.scheduledStartTime||'').slice(0,5)+':00+09:00'),
      approval=Date.parse('2026-10-09T20:10:00+09:00'),fixed=Date.parse(String(initial.fixedAt||'')),
      expected={};
  (initial.horses||[]).forEach(function(h){expected[n(h.horseNumber,0)]=true});
  var count=Object.keys(expected).length,latest=null;
  (r.modelMarkRevisions||[]).forEach(function(z){
    if(!z||z.version!=='arvexq-user-model-mark-revision-v1'||
       z.approvalId!=='user-approved-past-five-from-2026-10-09-20-10-jst'||
       z.modelVersion!=='arvexq-axis-reliability-v2-past-context'||
       String(z.raceId||'')!==String(r.id)||String(z.raceDate||'')!==String(r.date)||
       !Array.isArray(z.horses)||z.horses.length!==count)return;
    var at=Date.parse(String(z.revisedAt||'')),seen={},valid=true;
    if(!isFinite(at)||at<approval||at<=fixed||at>=post)return;
    z.horses.forEach(function(h){
      var no=n(h&&h.horseNumber,0),mark=String(h&&h.mark||'');
      if(!no||!expected[no]||seen[no]||['','◎','○','▲','☆+','☆','△','注'].indexOf(mark)<0)valid=false;
      seen[no]=true
    });
    if(!valid)return;
    if(!latest||Date.parse(String(latest.revisedAt||''))<at)latest=z
  });
  return latest
}
function latestAuthorizedMarkRevision(r){
  var official=latestOfficialMarkRevision(r),model=latestUserApprovedModelMarkRevision(r);
  if(!official)return model;
  if(!model)return official;
  return Date.parse(String(model.revisedAt||''))>Date.parse(String(official.revisedAt||''))?model:official
}
function authorizedPreOffMarks(r){
  return latestAuthorizedMarkRevision(r)||validMorningMarkSnapshot(r)||serverFrozenPrediction(r)||
    (typeof window!=='undefined'&&window.ARVEXQSavedSnapshot&&window.ARVEXQSavedSnapshot.marks(r))
}
function immutableArchivedPrediction(r){
  // Does not invoke ability, pace, winner or bet calculation after the off.
  var lock=authorizedPreOffMarks(r),
      saved=lock?lock.horses:[],byNo={},order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};
  saved.forEach(function(q){byNo[n(q.horseNumber||q.no,0)]=q});
  var rows=(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).map(function(h){
    var snap=byNo[n(h.horseNumber)]||{},ev=snap.lockedEvaluation||{},
        mark=isScratchHorse(h)?'':String(snap.mark||''),
        history=(h.recentRaces||h.allPastRuns||[]).slice(0,5),finishEvidence={holdWins:0,holdSamples:0,closingWins:0,closingSamples:0};
    history.forEach(function(run){
      var cp=run.cornerPositions||[],first=n(cp[0],0),last=n(cp[cp.length-1],0),
          finish=n(run.finish,n(run.finishPosition,0));
      if(first>0&&first<=4&&last>0){finishEvidence.holdSamples++;
        if(last<=4&&finish>0&&finish<=4)finishEvidence.holdWins++}
      if(last>=4&&finish>0){finishEvidence.closingSamples++;
        if(finish<=3)finishEvidence.closingWins++}
    });
    var honmei=validatedHonmeiMetadata(snap);
    return{horse:h,predMark:mark,predRank:order[mark]||999,markFrozen:!!saved.length,
      honmeiRole:mark==='◎'?honmei.honmeiRole:'',
      honmeiGrade:mark==='◎'?honmei.honmeiGrade:'',
      podiumAxisEligible:mark==='◎'&&honmei.honmeiGrade==='A'&&snap.podiumAxisEligible===true,
      hasFrozenEvaluation:ev.score!=null,
      overallRaw:ev.score!=null?n(ev.score):null,overallGrade:String(ev.grade||'—'),
      overallScore:ev.score!=null?n(ev.score):null,overallScoreExact:ev.score!=null?n(ev.score):null,
      finishEvidence:finishEvidence,p1Probability:n(snap.p1Probability,0),
      p2Probability:n(snap.p2Probability,0),p3Probability:n(snap.p3Probability,0),
      winnerDecisionProbability:n(snap.decisionProbability,0),
      singleWinSuitable:!isScratchHorse(h)&&(!!(snap.singleWinSuitable||snap.single)||
        (lock&&n((r.preRaceBet||{}).singleWinHorseNumber)===n(h.horseNumber))),
      expected:'不明',pastStyle:'不明',styleSamples:0,coverage:0,rawFront:0,
      rawStalk:0,rawMid:0,rawClose:0,fade:0,frontStay:0,comeFromBehind:0,
      collapseBeneficiary:0,paceScore:0,posCons:0,latePower:0,
      axisConfidence:n(snap.axisConfidence,0),attentionReason:'発走前保存印'};
  });
  return{rows:rows,occ:0,scenarios:[],plans:{},plan:null,coverage:0,
    pressure:0,arrangement:{},profile:{},outcome:null,
    markFreeze:{source:lock&&lock.version==='arvexq-user-model-mark-revision-v1'?'user-model-revision':(lock&&lock.version==='arvexq-official-mark-revision-v1'?'official-course-revision':(validMorningMarkSnapshot(r)?'morning-fixed':(lock?'server-prerace':'missing-prerace'))),
      fixedAt:lock?String(lock.revisedAt||lock.fixedAt||lock.sealedAtJst||lock.capturedAtJst||''):'',
      reason:String((lock&&lock.reason)||'')},
    engineVersion:'arvexq-archived-prerace-readonly-v346'};
}
function applyFrozenMarks(r,p){
  if(!r||!p||!Array.isArray(p.rows))return p;
  var clock=raceMarkClock(r),server=authorizedPreOffMarks(r);
  // Current pre-off marks are always calculated from the freshest race input.
  // Retain the first pre-off server/local receipt for later accuracy audits
  // and any already-fixed bet, but never let the receipt overwrite live marks.
  // A verified pre-off receipt is the sole display authority on both sides
  // of the start. Never replace displayed marks with a different archive at off.
  if(!clock.started&&!server){
    p.rows.forEach(function(z){z.markFrozen=false;z.computedLiveMark=String(z.predMark||'')});
    p.markFreeze={source:'live-before-post',originalPreserved:false,
      reason:'発走前の暫定AI印（保存原本はまだありません）。発走後は未保存印を再生成しません。'};
    return p
  }
  if(server){
    var remote={};server.horses.forEach(function(q){remote[n(q.horseNumber)]=q});
    var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};
    p.rows.forEach(function(z){
      var q=remote[n(z.horse&&z.horse.horseNumber)]||{},scratched=isScratchHorse(z.horse);
      z.computedLiveMark=String(z.predMark||'');z.predMark=scratched?'':String(q.mark||'');
      z.predRank=order[z.predMark]||999;z.markFrozen=true;
      var lockedHonmei=validatedHonmeiMetadata(q);
      z.honmeiRole=z.predMark==='◎'?lockedHonmei.honmeiRole:'';
      z.honmeiGrade=z.predMark==='◎'?lockedHonmei.honmeiGrade:'';
      z.podiumAxisEligible=z.predMark==='◎'&&lockedHonmei.honmeiGrade==='A'&&q.podiumAxisEligible===true;
      z.singleWinSuitable=!scratched&&(!!q.singleWinSuitable||
        (n((r.preRaceBet||{}).singleWinHorseNumber,0)>0&&
         n((r.preRaceBet||{}).singleWinHorseNumber)===n(z.horse&&z.horse.horseNumber)));
      if(q.lockedEvaluation){
        z.overallScore=n(q.lockedEvaluation.score,z.overallScore);
        z.overallScoreExact=n(q.lockedEvaluation.score,z.overallScoreExact);
        z.overallGrade=String(q.lockedEvaluation.grade||z.overallGrade||'C');
      }
    });
    p.markFreeze={source:server.version==='arvexq-user-model-mark-revision-v1'?'user-model-revision':(server.version==='arvexq-official-mark-revision-v1'?'official-course-revision':(validMorningMarkSnapshot(r)?'morning-fixed':'server-prerace')),
      fixedAt:server.revisedAt||server.fixedAt||server.sealedAtJst||server.capturedAtJst||'',
      reason:String(server.reason||'')};
  }else if(clock.started){
    var frozen=Array.isArray(r.preRacePrediction&&r.preRacePrediction.horses)?
      r.preRacePrediction.horses:[];
    if(frozen.length){
      p.markFreeze={source:'server-prerace',fixedAt:String(r.preRacePrediction.fixedAt||'')};
    }else{
      // Never publish a newly calculated post-result mark as a pre-race forecast.
      p.rows.forEach(function(z){z.computedLiveMark=String(z.predMark||'');z.predMark='';z.predRank=999;z.singleWinSuitable=false});
      p.markFreeze={source:'missing-prerace'};
    }
  }else p.markFreeze={source:'provisional'};
  return p;
}
// Recompute marks only when the actual inputs to the single 45/35/20
// model change. Historical audit scores, win odds and old evaluation marks
// never enter this signature. Only the active pre-off race is recalculated.
function threeFactorMarkInputSignature(r){
  var modelRace=analysisRace(r);
  return JSON.stringify({
    engine:'arvexq-true-run-pure-sectional-v2',
    raceId:String(r&&r.id||''),date:String(r&&r.date||''),
    raceMode:raceMode(r),
    runners:(modelRace.horses||[]).map(function(h){
      var factor=arvexqFactorValues({horse:h},modelRace);
      return [n(h.horseNumber,0),String(h.name||''),factor.coverage,
        factor.trueRun,factor.pure,factor.sectional];
    }).sort(function(a,b){return a[0]-b[0]})
  });
}
function predict(r){
  var started=raceMarkClock(r).started,markSignature=null;
  if(!started){
    markSignature=threeFactorMarkInputSignature(r);
    if(r._prediction&&
        r._prediction.engineVersion==='arvexq-true-run-pure-sectional-v2'&&
        r._prediction.markInputSignature===markSignature)
      return applyFrozenMarks(r,r._prediction);
    // A stale or older-engine in-memory result is discarded by recomputing
    // below. Historical pre-off seals and ticket receipts are not edited.
  }else if(r._prediction&&r._prediction.engineVersion==='arvexq-archived-prerace-readonly-v346')
    return applyFrozenMarks(r,r._prediction);
  if(started){
    // A transition to post-time must discard any formerly live prediction;
    // the only marks permitted now come from the immutable pre-off receipt.
    var archive=immutableArchivedPrediction(r);
    Object.defineProperty(r,'_prediction',{value:archive,configurable:true,writable:true,enumerable:false});
    return archive;
  }
  var modelRace=analysisRace(r),profile=predictionProfile(modelRace),rows=buildRows(modelRace),occ=earlyOcc(modelRace),minetaContext=rows.minetaContext||minetaRaceContext(rows,modelRace),
      tactical=tacticalContext(modelRace,rows),pressure=tactical.pressure,arrangement=tactical.arrangement,
      sc=scenarioModel(r,rows,pressure,arrangement),suit=suitability(rows,sc,pressure),plans={},i;
  // Unified TRUE RUN/PURE/SECTIONAL authority for marks, rank and tickets.
  assignPredictionMarks(rows,modelRace);
  integratedGrades(r,rows);
  for(i=0;i<sc.length;i++){
    var code=sc[i].code,candidates=rows.slice().sort(function(a,b){return scenarioSuit(b,code,pressure)-scenarioSuit(a,code,pressure)});
    sc[i].horses=candidates.slice(0,3).map(function(x){return x.horse});
    plans[code]=scenarioPlan(r,rows,[sc[i]],suit,pressure,arrangement)
  }
  var top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0],
      plan=plans[top.code]||scenarioPlan(r,rows,sc,suit,pressure,arrangement),
      draft={rows:rows,occ:occ,scenarios:sc,plan:plan,plans:plans,suit:suit,pressure:pressure,arrangement:arrangement,profile:profile,minetaContext:minetaContext};
  // Finish visualization uses the final 45/35/20 probabilities.
  // Second pass: refresh the displayed outcome with the now-final P1/P2/P3 decision roles.
  var outcome=paceOutcomeModel(r,draft),cov=mean(rows.map(function(x){return x.coverage}));
  assignSingleWinCandidate(rows,modelRace);
  var result={rows:rows,occ:occ,scenarios:sc,plan:plan,plans:plans,suit:suit,coverage:cov,pressure:pressure,arrangement:arrangement,profile:profile,minetaContext:minetaContext,outcome:outcome,
    engineVersion:'arvexq-true-run-pure-sectional-v2',markEngineVersion:'arvexq-true-run-pure-sectional-v2',
    markInputSignature:markSignature,
    researchAudit:{expertAIConsensusV317:true,marketBlindFactorsV317:true,podiumRecallV312:true,sameDayFlowV313:true,sectional:true,probabilityRegularization:true,conservativeProbabilityGuardV260:true,predictionMarketIndependent:true,marketUsedForEdgeEvOnly:true,liveTrackBias:true,robustLiveTrackSpeedV300:true,historicalDrawBias:true,strongerP2P3Roles:true,conditionalPlaceRoles:true,markRolesV246:true,winnerSelectorV300Independent:true,immutablePreRaceAuditV300:true,dateBlockedWinnerLearningV300:true,raceTypeTicketV300:true,pairwiseDuelV300:true,fullOrderSequential:true,strictReadinessV300:true,actualOddsEvOnlyV300:true,oddsCoverageV247:true,diagnosisPaceOutcomeLinkedV318:true,marksLinkedToOutcomeV318:true,betsLinkedToOutcomeV318:true}};
  applyFrozenMarks(r,result);
  Object.defineProperty(r,"_prediction",{value:result,configurable:true,writable:true,enumerable:false});
  return result
}
function nextRace(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime});a.sort(function(x,y){var ax=mins(x.startTime),ay=mins(y.startTime),now=nowMins(),kx=ax>=now?ax:ax+1440,ky=ay>=now?ay:ay+1440;return kx-ky});return a.length?a[0]:null}
function liveRaces(){if(state.date!==today())return[];var now=nowMins(),a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime&&mins(r.startTime)>=now-25});a.sort(function(x,y){return mins(x.startTime)-mins(y.startTime)});return a.slice(0,4)}
function liveTag(r){var d=mins(r.startTime)-nowMins();if(d<0&&d>=-25)return'<span class="live-tag running">進行中</span>';if(d>=0&&d<=10)return'<span class="live-tag now">まもなく</span>';return'<span class="live-tag">次走</span>'}
function homeVenueMark(track){var t=String(track||"?");return '<span class="venue-mark">'+esc(t.slice(0,1))+'</span>'}
function horseBodyWeightText(h){var w=currentBodyWeight(h);if(!w)return'';var ch=currentBodyWeightChange(h),s=w+'kg';if(ch!=null)s+=ch>0?' (+'+ch+')':' ('+ch+')';return s}
function referenceBodyWeight(h){if(!h)return 0;var w=n(h.referenceBodyWeight,0);if(w>250&&w<800)return w;var rs=h.recentRaces||[];for(var i=0;i<rs.length;i++){w=n(rs[i]&&rs[i].bodyWeight,0);if(w>250&&w<800)return w}return 0}
function horseCheckKey(r){return 'arvexq-horse-check-v217:'+String(r&&r.id||'unknown')}
function horseCheckMap(r){try{var raw=localStorage.getItem(horseCheckKey(r));var obj=raw?JSON.parse(raw):{};return obj&&typeof obj==='object'?obj:{}}catch(e){return{}}}
function isHorseChecked(r,no){var m=horseCheckMap(r);return !!m[String(n(no,0))]}
function setHorseChecked(r,no,val){if(!r||!n(no,0))return;var m=horseCheckMap(r),k=String(n(no,0));if(val)m[k]=1;else delete m[k];try{localStorage.setItem(horseCheckKey(r),JSON.stringify(m))}catch(e){}}
function toggleHorseChecked(r,no){setHorseChecked(r,no,!isHorseChecked(r,no));render()}
function horseCheckGlyph(r,no){return isHorseChecked(r,no)?'☑️':'☐'}
function sortedHorseRows(rows){return(rows||[]).slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function openHorseModal(no){state.modalScroll=window.scrollY;if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}state.horseModalNo=n(no)||null;render();document.body.style.overflow='hidden'}
function closeHorseModal(){var y=state.modalScroll||0;state.horseModalNo=null;document.body.style.overflow='';render();window.scrollTo(0,y);if(state.race)scheduleHistoryPoll(state.race.id)}
function moveHorseModal(dir){if(!state.pred)return;var rows=sortedHorseRows(state.pred.rows),idx=rows.findIndex(function(x){return n(x.horse.horseNumber)===n(state.horseModalNo)});if(!rows.length)return;state.horseModalNo=n(rows[(idx+dir+rows.length)%rows.length].horse.horseNumber);render()}
function horseDisplayName(r,h){
  h=h||{};var no=n(h.horseNumber,0),pools=[r&&r.horses,r&&r.entries,r&&r.runners,r&&r.starters,r&&r.raceEntries,r&&r.aiEvaluation&&r.aiEvaluation.horses,r&&r.result&&r.result.finishers],i,j,z,nm;
  nm=String(h.name||h.horseName||'').trim();if(nm)return nm;
  for(i=0;i<pools.length;i++){var a=pools[i];if(!Array.isArray(a))continue;for(j=0;j<a.length;j++){z=a[j]||{};if(no&&n(z.horseNumber||z.number||z.no,0)!==no)continue;nm=String(z.name||z.horseName||z.hname||'').trim();if(nm)return nm}}
  return no?(no+'番 馬名取得中'):'馬名取得中';
}
// Research-only evidence is maintained in /research/research_view.js.
function researchHorsePanel(r,h){return window.ARVEXQResearchView&&window.ARVEXQResearchView.renderHorse?
  window.ARVEXQResearchView.renderHorse(r,h,esc):''}
function researchRecapPanel(r){return window.ARVEXQResearchView&&window.ARVEXQResearchView.renderRecap?
  window.ARVEXQResearchView.renderRecap(r,esc,isFinal(r)):''}

var CAREER_STATE_LABELS={'complete':'取得完了','complete-with-missing-fields':'取得完了・一部項目欠損','complete-no-starts':'既走なし（確認済）','partially-acquired':'一部取得','acquisition-unverified':'取得未確認','history-present-but-unusable':'履歴あり・分析不能','no-history':'履歴なし（取得未確認）','race-date-unverified':'レース日不明のため未確認'};
function careerCoverageLabel(h){var c=h&&h.careerCoverage;if(!c||!c.state)return'';return CAREER_STATE_LABELS[c.state]||'取得未確認'}
function careerCoverageLine(h){var c=h&&h.careerCoverage,label=careerCoverageLabel(h);if(!label)return'';var got=n(c.eligibleRuns,0),rep=c.reportedStarts;return '<div class="muted career-coverage" data-career-state="'+esc(c.state)+'" style="margin:2px 0 6px;font-size:11px">全キャリア：'+esc(label)+'（取得 '+esc(got)+'走'+(rep!=null?' / 総出走 '+esc(rep)+'走':'')+(n(c.unusableRecords,0)?' / 項目欠損 '+esc(c.unusableRecords)+'走':'')+'）</div>'}
function runnerDetailBody(r,p,x){
  var h=x.horse,displayName=horseDisplayName(r,h),recent=(h.recentRaces||h.allPastRuns||[]).slice(0,5),reasons=(x.overallReasons||[]).slice(0,4),bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明',
      rf=x.researchFactors||{},sp=styleDisplayPcts(x),out=(p&&p.outcome)||(raceMarkClock(r).started?null:paceOutcomeModel(r,p)),no=n(h.horseNumber),role=raceMarkClock(r).started?'発走前保存情報':'相手候補';
  // No model evidence must never be displayed as zero ability.
  var hasScoredEvidence=n(x.threeFactorCoverage,0)>0;
  function pct(v){if(!hasScoredEvidence||v==null||v===''||!Number.isFinite(Number(v)))return '未評価';return Math.round(clamp(Number(v),0,1)*100)}
  function scoreCell(label,v){return '<div class="horse-info-cell"><small>'+esc(label)+'</small><b>'+pct(v)+'</b></div>'}
  if(out){
    var f=(out.first||[]).some(function(z){return n(z.horse&&z.horse.horseNumber)===no}),
        s=(out.second||[]).some(function(z){return n(z.horse&&z.horse.horseNumber)===no}),
        t=(out.third||[]).some(function(z){return n(z.horse&&z.horse.horseNumber)===no});
    role=f?('1着候補・'+out.verdict):(s?'2着候補':(t?'3着候補':'相手候補'))
  }
  // Only scores supplied by the authoritative three-factor model are shown.
  // Historical composite fields must never be presented as current factors.
  var ability=rf.ability,form=rf.form,klass=rf.classLevel,
      suit=rf.suitability,pace=rf.pace;
  return '<div class="horse-detail">'
    +'<div class="runner-overall-box"><div class="runner-overall-head"><span class="label">AI総合評価</span><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'C')+'</strong><span class="runner-overall-mark" data-ai-mark="'+esc(x.predMark||'')+'">'+esc(x.predMark||'—')+'</span><span class="runner-overall-score">総合 '+esc(overallScoreText(x))+'</span></div>'+
    '<div class="overall-reasons"><i class="good">'+esc(role)+'</i>'+(reasons.length?reasons.map(function(z){var warn=String(z).indexOf('注意')>=0||String(z).indexOf('不足')>=0;return '<i class="'+(warn?'warn':'good')+'">'+esc(z)+'</i>'}).join(''):'')+'</div></div>'+
    '<div class="detail-heading">基本情報</div><div class="horse-info-grid"><div class="horse-info-cell"><small>馬番 / 枠</small><b>'+esc(h.horseNumber)+'番 / '+esc(h.frameNumber||frame(h))+'枠</b></div><div class="horse-info-cell"><small>性齢 / 斤量</small><b>'+esc(h.sex||'—')+esc(h.age||'—')+' / '+esc(carriedWeightText(h))+'</b></div><div class="horse-info-cell"><small>脚質</small><b>'+esc(styleTxt)+'</b></div><div class="horse-info-cell"><small>騎手</small><b>'+esc(h.jockey||'—')+'</b></div><div class="horse-info-cell"><small>調教師</small><b>'+esc(h.trainer||'—')+'</b></div><div class="horse-info-cell"><small>馬体重</small><b>'+(bodyTxt?esc(bodyTxt):'—')+'</b></div></div>'+
    '<div class="detail-heading">能力・実績・適性</div><div class="horse-info-grid">'+scoreCell('能力',ability)+scoreCell('近況・実績',form)+scoreCell('相手レベル',klass)+scoreCell('条件適性',suit)+scoreCell('展開適性',pace)+scoreCell('データ充足',n(x.threeFactorCoverage,0)/3)+'</div>'+
    '<div class="detail-heading">脚質・今回の勝ち筋</div>'+(x.minetaNotes&&x.minetaNotes.length?'<div class="muted" style="margin:-2px 0 8px;font-size:11px">今回位置：'+esc(x.expected||'不明')+'｜'+esc(x.minetaNotes.join('・'))+'</div>':'')+'<div class="horse-info-grid"><div class="horse-info-cell"><small>逃げ率</small><b>'+esc(sp[0]==null?'—':sp[0]+'%')+'</b></div><div class="horse-info-cell"><small>先行率</small><b>'+esc(sp[1]==null?'—':sp[1]+'%')+'</b></div><div class="horse-info-cell"><small>差し率</small><b>'+esc(sp[2]==null?'—':sp[2]+'%')+'</b></div><div class="horse-info-cell"><small>追込率</small><b>'+esc(sp[3]==null?'—':sp[3]+'%')+'</b></div><div class="horse-info-cell"><small>前残り力</small><b>'+pct(x.frontStay)+'</b></div><div class="horse-info-cell"><small>差し込み力</small><b>'+pct(x.comeFromBehind)+'</b></div></div>'+
    '<div class="muted">脚質＝近走5走の初角位置／前残り・差し込み＝推定スコア（的中確率ではありません）。初角4番手内→4角・ゴール4番手内 '+esc(x.finishEvidence.holdWins)+'/'+esc(x.finishEvidence.holdSamples)+'走、4角4番手以下→3着内 '+esc(x.finishEvidence.closingWins)+'/'+esc(x.finishEvidence.closingSamples)+'走を評価。</div><div class="recent-list-title">近走データ（直近5走）</div>'+careerCoverageLine(h)+(recent.length?recent.map(function(rr){var rid=rr.raceId||((r.circuit==='地方'&&rr.date&&rr.track&&n(rr.raceNumber))?('nar-'+rr.date+'-'+rr.track+'-'+String(n(rr.raceNumber)).padStart(2,'0')):'');return '<div class="recent"><div class="recent-head"><b>'+esc(rr.date||'—')+' '+esc(rr.track||'—')+' '+(n(rr.raceNumber)?esc(rr.raceNumber)+'R ':'')+esc(rr.distance||'—')+'m</b><strong>'+esc(rr.finish||rr.finishPosition||'—')+'着</strong></div><div>'+fmtTime(rr.timeSeconds)+'　'+esc(rr.condition||'不明')+' / '+esc(rr.weather||'不明')+'</div><div class="muted">'+(rr.title?esc(rr.title)+'　':'')+'通過 '+esc((rr.cornerPositions||[]).join('-')||'—')+'　頭数 '+esc(rr.fieldSize||'—')+(saneCarriedWeightValue(rr.carriedWeight,rr.bodyWeight)?'　斤量 '+esc(String(saneCarriedWeightValue(rr.carriedWeight,rr.bodyWeight)).replace(/\.0$/,''))+'kg':'')+(rr.jockey?'　騎手 '+esc(rr.jockey):'')+'</div>'+(rid?'<button type="button" class="recent-open" data-past-race="'+esc(rid)+'">この過去レースを見る</button>':'')+'</div>'}).join(''):'<div class="empty compact">過去データを確認できませんでした</div>')+researchHorsePanel(r,h)+'</div>'
}
function horseModal(r,p){var no=n(state.horseModalNo,0);if(!no)return'';var rows=sortedHorseRows(p.rows),idx=-1,i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===no){idx=i;break}if(idx<0)return'';var x=rows[idx],h=x.horse,displayName=horseDisplayName(r,h),bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明';return'<div class="horse-modal-layer"><div class="horse-modal-backdrop" data-horse-close="1"></div><section class="horse-modal" role="dialog" aria-modal="true"><div class="horse-modal-head"><button type="button" class="horse-modal-nav" data-horse-prev="1">‹</button><div class="horse-modal-title"><div class="horse-modal-title-top">'+badge(h)+'<div style="min-width:0"><div class="horse-modal-name">'+esc(displayName)+'</div>'+(bodyTxt?'<div class="runner-weight-inline">('+esc(bodyTxt)+')</div>':'')+'</div></div><div class="horse-modal-meta"><span>'+esc(h.sex||'—')+esc(h.age||'—')+'</span><span>'+esc(styleTxt)+'</span><span>'+esc(h.jockey||'騎手不明')+'</span><span>'+esc(carriedWeightText(h))+'</span></div><div class="horse-modal-sidechips"><span class="horse-modal-chip grade">総合評価 '+esc(x.overallGrade||'C')+'</span><span class="horse-modal-chip">総合点 '+esc(overallScoreText(x))+'</span><span class="horse-modal-chip mark" data-ai-mark="'+esc(x.predMark||'')+'">予想印 '+esc(x.predMark||'—')+'</span><button type="button" class="horse-modal-chip horse-check-chip '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+' チェック</button></div><div class="horse-modal-counter">'+(idx+1)+' / '+rows.length+' 頭</div></div><button type="button" class="horse-modal-nav" data-horse-next="1">›</button><button type="button" class="horse-modal-close" data-horse-close="1">×</button></div><div class="horse-modal-swipe">画面左半分タップ＝前の馬　／　右半分タップ＝次の馬</div><div id="horse-modal-panel" class="horse-modal-body">'+runnerDetailBody(r,p,x)+'</div></section></div>'}
function miniPacePreview(r){return '<div class="home-ai-preview-photo mini-flow-demo"><div class="mini-flow-axis"><span>← 後方</span><b>隊列イメージ</b><span>前方 →</span></div><div class="mini-flow-line"></div><i class="mini-flow-dot d1">1</i><i class="mini-flow-dot d2">4</i><i class="mini-flow-dot d3">7</i><i class="mini-flow-dot d4">10</i><div class="mini-flow-caption">写真背景なし・右が前</div></div>'}
function raceNumbers(r){var track=r?r.track:state.track,rs=state.races.filter(function(x){return x.track===track&&x.circuit===(r?r.circuit:state.circuit)}),out='';for(var i=1;i<=12;i++){var found=rs.find(function(x){return n(x.raceNumber)===i});out+='<button '+(found?'data-race="'+esc(found.id)+'"':'disabled')+' class="'+(r&&n(r.raceNumber)===i?'active':'')+'">'+i+'R</button>'}return '<nav class="race-numbers">'+out+'</nav>'}
function evaluationText(x){var e=x.evaluation||{},p=state.pred&&state.pred.profile||null;return (p?esc(p.label)+'　':'')+esc(e.mode||'基礎')+' / '+esc(e.tier||'基礎データ評価')+'　データ充足度 '+n(e.dataCompleteness)+'%　評価信頼度 '+esc(e.confidence||'低')+(e.tied?'　同点は馬番順':'')}
function oddsText(h){var ok=h&&h.winOdds!=null&&h.winOdds!==''&&n(h.winOdds)>0,pop=n(h&&h.popularity,0);return '単勝 '+(ok?esc((Math.round(n(h.winOdds)*10)/10).toFixed(1))+'倍':'--.-倍')+'　'+(pop>0?esc(pop)+'人気':'--人気')}
function oddsClass(h){var o=n(h&&h.winOdds,0);return o>0&&o<10?'odds-single':''}



var instantTrackDetails={},trackSnapshotJobs={};

function edgeRaceUrl(id){
  return 'https://kraiz-api.4b89h4fydd.workers.dev/api/race/'
    +encodeURIComponent(id)
    +'?view=display&t='+Date.now()
}

// v240 data-integrity merge. D1 /api/race returns the saved detail and a separate
// odds_current array. Older clients ignored the separate live rows and could also
// let a sparse incoming snapshot overwrite a richer cached one. Keep the richest
// horse/history/diagnosis data while allowing newer live fields to win.
function reflectUseful(v){
  if(v===false||v===0)return true;
  if(v==null||v==='')return false;
  if(Array.isArray(v))return v.length>0;
  if(typeof v==='object')return Object.keys(v).length>0;
  if(typeof v==='string'&&(v==='不明'||v==='—'))return false;
  return true
}
function edgeOddsRow(z){
  z=z||{};return {
    horseNumber:n(z.horseNumber!=null?z.horseNumber:z.horse_no,0),
    winOdds:z.winOdds!=null?z.winOdds:z.win_odds,
    popularity:z.popularity,
    bodyWeight:z.bodyWeight!=null?z.bodyWeight:z.body_weight,
    bodyWeightChange:z.bodyWeightChange!=null?z.bodyWeightChange:z.body_weight_change,
    status:z.status!=null?z.status:z.horse_status,
    scratched:z.scratched===true||z.withdrawn===true||/欠場|出走取消|取消|競走除外|除外/.test(String(z.status!=null?z.status:z.horse_status||'')),
    updatedAt:z.updatedAt!=null?z.updatedAt:z.updated_at
  }
}
function mergeHorseReflection(oldH,newH,liveH){
  oldH=oldH||{};newH=newH||{};liveH=liveH||{};
  var out=Object.assign({},oldH),richArrays=['recentRaces','allPastRuns'],k;
  Object.keys(newH).forEach(function(key){
    var v=newH[key];
    if(richArrays.indexOf(key)>=0){
      var a=Array.isArray(out[key])?out[key]:[],b=Array.isArray(v)?v:[];
      if(b.length>=a.length&&b.length)out[key]=b;
      return
    }
    if(key==='scratched'){
      if(v===true||out[key]!==true)out[key]=!!v;
      return
    }
    if(key==='status'&&isScratchHorse(out)&&!isScratchHorse(newH))return;
    if(reflectUseful(v))out[key]=v
  });
  ['winOdds','popularity','bodyWeight','bodyWeightChange','status','updatedAt'].forEach(function(key){
    if(liveH[key]!=null&&liveH[key]!==''){
      if(key==='status'&&isScratchHorse(out)&&!/欠場|出走取消|取消|競走除外|除外/.test(String(liveH[key])))return;
      out[key]=liveH[key]
    }
  });
  if(liveH.scratched===true){out.scratched=true;if(!isScratchHorse(out))out.status='出走取消'}
  if(liveH.horseNumber)out.horseNumber=liveH.horseNumber;
  return out
}
// Result updates can be sparse: newer racecard/poll payloads must not erase
// already verified finishers, payout rows, or a final status.
function mergePublishedResult(oldResult,newResult){
  var prev=oldResult&&typeof oldResult==='object'?oldResult:{},
      next=newResult&&typeof newResult==='object'?newResult:{};
  if(!reflectUseful(next))return prev;
  var out=Object.assign({},prev),
      priorFinal=String(prev.status||'')==='確定',newFinal=String(next.status||'')==='確定';
  Object.keys(next).forEach(function(k){
    if(k==='status'||k==='finishers'||k==='payouts')return;
    if(reflectUseful(next[k]))out[k]=next[k]
  });
  var oldFs=Array.isArray(prev.finishers)?prev.finishers:[],
      freshFs=Array.isArray(next.finishers)?next.finishers:[],
      oldRanked=oldFs.filter(function(x){return x&&n(x.finish)>0}).length,
      newRanked=freshFs.filter(function(x){return x&&n(x.finish)>0}).length;
  if(freshFs.length&&(newRanked>=oldRanked)&&(!priorFinal||newFinal)){
    var oldBy={};
    oldFs.forEach(function(x){if(x&&n(x.horseNumber)>0)oldBy[n(x.horseNumber)]=x});
    out.finishers=freshFs.map(function(x){
      var merged=Object.assign({},oldBy[n(x&&x.horseNumber)]||{});
      Object.keys(x||{}).forEach(function(k){if(reflectUseful(x[k]))merged[k]=x[k]});
      return merged
    });
  }
  if(Array.isArray(next.payouts)&&next.payouts.length){
    var oldPay=Array.isArray(prev.payouts)?prev.payouts:[];
    if(next.payouts.length>=oldPay.length)out.payouts=next.payouts
  }
  if(newFinal)out.status='確定';
  else if(!priorFinal&&reflectUseful(next.status))out.status=next.status;
  return out
}
function mergeRaceReflection(base,incoming,oddsRows,summary){
  base=base||{};incoming=incoming||{};summary=summary||{};
  var out=Object.assign({},base);
  Object.keys(incoming).forEach(function(key){
    var v=incoming[key];
    if(key==='horses'||key==='result')return;
    if(reflectUseful(v))out[key]=v
  });
  Object.keys(summary).forEach(function(key){
    var v=summary[key];
    if(key==='horses'||key==='result')return;
    if(reflectUseful(v))out[key]=v
  });
  var combinedResult=mergePublishedResult(base.result,incoming.result);
  if(reflectUseful(combinedResult))out.result=combinedResult;
  var oldBy={},newBy={},liveBy={},order=[];
  (base.horses||[]).forEach(function(h){var no=n(h&&h.horseNumber,0);if(no){oldBy[no]=h;order.push(no)}});
  (incoming.horses||[]).forEach(function(h){var no=n(h&&h.horseNumber,0);if(no){newBy[no]=h;if(order.indexOf(no)<0)order.push(no)}});
  (oddsRows||[]).forEach(function(z){var q=edgeOddsRow(z),no=n(q.horseNumber,0);if(no){liveBy[no]=q;if(order.indexOf(no)<0)order.push(no)}});
  if(order.length){
    order.sort(function(a,b){return a-b});
    out.horses=order.map(function(no){return mergeHorseReflection(oldBy[no],newBy[no],liveBy[no])})
  }else if(Array.isArray(incoming.horses)&&incoming.fieldSize!=null&&Number(incoming.fieldSize)===0){out.horses=[]}
  if((oddsRows||[]).length){
    out.oddsUpdatedAt=String((oddsRows||[]).reduce(function(mx,z){return Math.max(mx,n(z&&((z.updatedAt!=null)?z.updatedAt:z.updated_at),0))},0)||out.oddsUpdatedAt||'');
    out.liveFieldsMerged=true
  }
  if(typeof window!=='undefined'&&window.ARVEXQRaceIdentity)out=window.ARVEXQRaceIdentity.sanitize(out);
  return mergeResultHorseFields(out)
}
function raceDisplayCoreReady(d,row){
  if(!d)return false;
  var hs=(d.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}),fs=d.result&&d.result.finishers||[];
  if(!hs.length){
    return isFinal(d)&&fs.some(function(x){return x&&n(x.horseNumber)>0&&String(x.name||'').trim()})
  }
  var active=hs.filter(function(h){return !isScratchHorse(h)});
  if(!active.length)active=hs;
  var named=active.filter(function(h){return String(h.name||'').trim()}).length;
  // Rendering uses runner identity only. Secondary fields can continue syncing.
  // Display readiness is separate from evidence-based model ticket readiness.
  return named>=Math.min(active.length,Math.max(1,Math.ceil(active.length*.50)))
}

function edgeFetchJson(url,timeoutMs){
  timeoutMs=n(timeoutMs,6500);
  var controller=(typeof AbortController!=='undefined')?new AbortController():null,timer=null,opts={cache:'no-store'};
  if(controller){opts.signal=controller.signal;timer=setTimeout(function(){try{controller.abort()}catch(e){}},timeoutMs)}
  return fetch(url,opts).then(function(res){if(!res.ok)throw Error('http '+res.status);return res.json()}).finally(function(){if(timer)clearTimeout(timer)})
}
// Each section retains its own readiness; failed requests never enter the detail cache.
var raceDetailStates={},raceDetailTrace=[];
function detailState(id){
  var key=String(id);
  return raceDetailStates[key]||(raceDetailStates[key]={basic:'loading',entry:'loading',odds:'loading',diagnosis:'loading',history:'loading',pace:'loading',result:'loading',payouts:'loading',busy:false,error:'',attempts:0})
}
function traceRaceDetail(id,event,extra){
  var item=Object.assign({raceId:String(id),event:event,at:Date.now()},extra||{});
  raceDetailTrace.push(item);if(raceDetailTrace.length>60)raceDetailTrace.shift();
  if(event==='failed')console.warn('[ARVEXQ race detail]',item)
}
function normalizeDetailSummary(row,id){
  row=row||{};
  var out=Object.assign({},row),aliases={id:'race_id',date:'race_date',raceNumber:'race_no',startTime:'start_time',fieldSize:'field_size',raceStatus:'race_status'};
  Object.keys(aliases).forEach(function(k){if(out[k]==null&&row[aliases[k]]!=null)out[k]=row[aliases[k]]});
  if(!out.id)out.id=String(id);return out
}
function updateDetailSections(id,r,received){
  var st=detailState(id),hs=r&&r.horses||[],hasEntries=hs.some(function(h){return h&&n(h.horseNumber)>0&&String(h.name||'').trim()}),missing=st.error?'error':'loading';
  st.basic=r&&r.id?'loaded':missing;
  st.entry=hasEntries?'loaded':(received&&Array.isArray(r&&r.horses)&&r.fieldSize!=null&&Number(r.fieldSize)===0?'empty':missing);
  st.odds=hs.some(function(h){return n(h&&h.winOdds)>0})?'loaded':missing;
  st.history=hs.some(function(h){return h&&((h.recentRaces||[]).length||(h.allPastRuns||[]).length)})?'loaded':(hasEntries&&hs.every(function(h){return h.debutNoHistory})?'empty':missing);
  st.diagnosis=r&&r._prediction?'loaded':missing;st.pace=r&&r._prediction?'loaded':missing;
  st.result=hasAnyResultData(r||{})?'loaded':(r&&!isFinal(r)&&!isFlash(r)?'empty':missing);
  st.payouts=r&&r.result&&(r.result.payouts||[]).length?'loaded':missing;
  return st
}
function entryDataAvailable(r){return !!(r&&(r.horses||[]).some(function(h){return h&&n(h.horseNumber)>0&&String(h.name||'').trim()}))}
function raceHeadCountText(r){
  var count=Number(r.fieldSize),hs=r.horses||[],st=detailState(r.id);
  if(r.fieldSize!=null&&isFinite(count)&&count>0)return count+'頭';
  if(hs.length)return hs.length+'頭';
  return st.entry==='empty'?'0頭':'頭数取得中'
}
function raceDetailNotice(r){
  var st=detailState(r.id),staticNotice=r&&r._staticRacecardFallback?
    '<div class="diagnosis-refresh-note" role="status">保存済みの出走表を表示中です。取消・騎手変更・オッズの最新情報は未確認です。</div>':'';
  if(r&&r._resultIdentityError)staticNotice+='<div class="diagnosis-refresh-note">結果の馬番・馬名が出走表と一致しないため表示を保留しています。</div>';
  if(r&&r._rosterIdentityError)staticNotice+='<div class="diagnosis-refresh-note">APIの出走馬不一致を検出し、検証済みの出走表を表示しています。</div>';
  if(!st.error)return staticNotice;
  return staticNotice+'<div class="diagnosis-refresh-note" role="status">'+(entryDataAvailable(r)?'取得済みの出走表を表示しています。':'レース基本情報を表示しています。')+' 詳細の更新に失敗しました。 <button type="button" data-detail-retry="'+esc(r.id)+'">再試行</button></div>'
}
function pendingDetailPanel(r){
  var key=state.openPanel||'entry';if(key==='diagnosis')key='entry';var labels={entry:'出走表',pace:'展開予想',bets:'買い目',result:'結果・払戻'},st=detailState(r.id),status=st[key==='bets'?'diagnosis':key]||'loading';
  if(key==='result')return resultPanel(r);
  return '<section class="card" data-section-state="'+esc(status)+'"><h2>'+esc(labels[key]||'出走表')+'</h2><p role="status">'+(status==='empty'?'出走馬0頭を確認しました。':(status==='error'?'この項目を取得できませんでした。取得済みの情報は表示を継続します。':'この項目を取得中です。'))+'</p>'+(status==='error'?'<button type="button" data-detail-retry="'+esc(r.id)+'">再試行</button>':'')+'</section>'
}
function racecardOddsHtml(h){
  if(isScratchHorse(h))return '<span class="odd scratch-odds">取消</span><span class="pop scratch-note">出走取消</span>';
  var valid=h&&h.winOdds!=null&&h.winOdds!==''&&n(h.winOdds)>0,
      value=valid?n(h.winOdds):0,pop=n(h&&h.popularity,0),
      forecast=!!(h&&h.oddsForecast)||/予想|forecast/i.test(String(h&&h.oddsSource||''));
  return '<span class="odd '+(value>0&&value<10?'single':'')+'">'+esc(valid?(Math.round(value*10)/10).toFixed(1):'未取得')+'</span>'
    +'<span class="pop">'+(forecast?'予想 ':'')+(pop>0?esc(pop)+'人気':'未取得')+'</span>';
}
function racecardMarkDisplay(mark){
  var raw=String(mark||'—').trim(),pair=/^([◎○▲☆△注])([+＋])$/.exec(raw);
  if(pair){
    return '<span class="rc-mark-stack" aria-hidden="true"><span class="rc-mark-top">'+esc(pair[1])+'</span><span class="rc-mark-bottom">＋</span></span>';
  }
  return esc(raw);
}

function validatedHonmeiMetadata(source){
  var q=source||{},role=String(q.honmeiRole||q.role||''),
      grade=String(q.honmeiGrade||q.confidenceGrade||'');
  return{honmeiRole:role==='win'||role==='axis'?role:'',
    honmeiGrade:['A','B','C'].indexOf(grade)>=0?grade:''}
}
function honmeiBadgeText(x){return '';} // Retain locked A/B/C metadata without displaying the old role badges.
function honmeiA11yText(x){return x&&x.predMark==='◎'?'◎・勝ち切る能力と3着内の安定性を総合評価した本命（的中保証ではありません）':'';}
function racecardMarkLegend(r){
  var server=authorizedPreOffMarks(r),clock=raceMarkClock(r),
      status=server?'発走前保存印（発走前後で同一の原本）':
        (!clock.started?'発走前の暫定AI印（原本未保存）':'発走前印の保存なし');
  var original=clock.started?authorizedPreOffMarks(r):null,
      axisNote=original&&original.horses&&!original.horses.some(function(h){return h.mark==='◎'})?'軸なし｜相手上位馬を評価　':'';
  return '<div class="rc-mark-legend">'+esc(axisNote)+'<b>◎</b> 本命　<b>○</b> 1・2着向き　<b>▲</b> 2・3着向き　<b>△</b> 3着向き　<b>☆</b> 好走根拠が複数揃う場合だけ　<span class="rc-mark-freeze-note">'+esc(status)+'</span></div>';
}
function racecardEntryRow(r,h,x){
  var scratch=isScratchHorse(h),no=n(h.horseNumber),name=horseDisplayName(r,h),
      fr=clamp(n(h.frameNumber,no),1,8),curBw=currentBodyWeight(h),
      deltaValue=currentBodyWeightChange(h),pastBw=!curBw?referenceBodyWeight(h):0,
      weightMain=scratch?'—':(curBw?String(curBw):(pastBw?('前'+pastBw):'—')),
      weightDelta=(!scratch&&curBw&&deltaValue!=null)?('('+(deltaValue>0?'+':'')+deltaValue+')'):'',
      weightHint=curBw?'馬体重':(pastBw?'前走馬体重':'馬体重未計量'),
      disabled=scratch?' disabled aria-disabled="true"':'',
      openAttr=scratch?'':(' data-horse-open="'+esc(no)+'"'),
      detailLabel=' aria-label="'+esc(name)+'の詳細を開く"';
  return '<div class="racecard-row rc-racecard-v336 rc-racecard-v339'+(scratch?' scratched':'')+'" '+(scratch?'aria-disabled="true"':'')+'>'
    +'<div class="rc-v336-mark"><span class="rc-mark-box rc-ai-mark" data-ai-mark="'+esc(x&&x.predMark||'')+'" aria-label="'+esc(String(x&&x.predMark||'—').replace(/\+/g,'＋')+(x&&x.predMark==='◎'?'、'+honmeiA11yText(x):'')+(x&&x.singleWinSuitable&&!scratch?'、単勝向き':''))+'"><span class="rc-mark-main">'+racecardMarkDisplay(x&&x.predMark)+'</span>'+(x&&x.singleWinSuitable&&!scratch&&x.predMark!=='◎'?'<span class="rc-single-tip" title="単勝向き（1着狙い）" aria-hidden="true">単</span>':'')+'</span></div>'
    +'<button type="button" class="rc-v336-number"'+openAttr+detailLabel+disabled+'><span class="rc-number frame'+fr+'">'+esc(no)+'</span></button>'
    +'<div class="rc-v336-info"><button type="button" class="rc-horse-main"'+openAttr+detailLabel+disabled+'>'
      +'<span class="rc-horse-name">'+esc(name)+'</span>'
      +'<span class="rc-v336-meta"><span class="rc-sexage">'+esc(h.sex||'—')+esc(h.age||'—')+'</span>'
      +'<span class="carry">'+esc(carriedWeightText(h))+'</span><span class="jockey">'+esc(h.jockey||'—')+'</span></span>'
    +'</button></div>'
    +'<div class="rc-v339-weight'+(curBw?'':' pending')+'" aria-label="'+esc(weightHint)+'">'
      +'<b>'+esc(weightMain)+'</b><span class="rc-weight-delta">'+esc(weightDelta||'　')+'</span>'
    +'</div>'
    +'<div class="rc-v336-odds rc-odds" data-odds-no="'+esc(no)+'">'+racecardOddsHtml(h)+'</div>'
    +'</div>';
}
function morningSavedMarkRows(r){
  // A pre-off loading/partial racecard must not display archived marks as live AI output.
  // Verified receipts may be shown after the off only for historical review.
  var snap=raceMarkClock(r).started?authorizedPreOffMarks(r):null,byNo={};
  if(snap&&Array.isArray(snap.horses)){
    snap.horses.forEach(function(z){byNo[n(z&&z.horseNumber,0)]=z})
  }
  return (r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).map(function(h){
    var z=byNo[n(h.horseNumber)]||{};
    return {horse:h,predMark:isScratchHorse(h)?'':String(z.mark||''),
      predRank:999,singleWinSuitable:!!z.singleWinSuitable};
  })
}
function minimalRacecardPanel(r){
  var receiptRows=morningSavedMarkRows(r);
  return '<div id="section-entry" class="accordion-panel"><section class="card"><h2>出走表</h2>'+racecardMarkLegend(r)+'<div class="diagnosis-refresh-note busy" style="margin:7px 0">AI解析はバックグラウンドで再取得します。出走表は先に表示しています。</div><div class="racecard-table">'
    +(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){var z=receiptRows.find(function(x){return n(x.horse&&x.horse.horseNumber)===n(h.horseNumber)});return racecardEntryRow(r,h,z)}).join('')
    +'</div></section></div>';
}
function safeEntryPanel(r,p){
  try{return runnerStyleSection(r,p)}catch(error){
    traceRaceDetail(r.id,'section-failed',{section:'entry-decoration',message:String(error&&error.message||error)});
    return minimalRacecardPanel(r)
  }
}
var racePredictionTasks=new WeakMap();
function renderPredictionPending(r){
  var st=detailState(r.id),task=racePredictionTasks.get(r);
  if(!task&&!r._entryOnly){
    task={status:'loading'};racePredictionTasks.set(r,task);
    setTimeout(function(){
      try{predict(r);task.status='loaded';st.diagnosis='loaded';st.pace='loaded'}
      catch(error){task.status='error';st.diagnosis='error';st.pace='error';traceRaceDetail(r.id,'analysis-failed',{message:String(error&&error.message||error)})}
      if(state.race===r)render()
    },30)
  }
  if(!state.openPanel)state.openPanel='entry';
  if(state.subPage==='horse'){
    var hh=(r.horses||[]).find(function(z){return n(z.horseNumber)===n(state.detailHorseNo)})||{};
    return '<div class="smart-shell">'+raceSubpageTopBar(r,horseDisplayName(r,hh))+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">馬情報を取得中です。</div></section></main>'+cinematicFooter()+'</div>'
  }
  if(state.subPage==='bets')return frozenAiBetForRace(r)?betDetailPage(r,{rows:morningSavedMarkRows(r)}):'<div class="smart-shell">'+raceSubpageTopBar(r,'買い目')+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">発走前の買い目原本が未取得です。取得後に表示します（発走後の再計算はしません）。</div></section></main>'+cinematicFooter()+'</div>';
  if(state.subPage==='pace-stage')return paceStagePendingPage(r);
  var content=state.openPanel==='entry'?safeEntryPanel(r,{rows:morningSavedMarkRows(r)}):(state.openPanel==='result'?resultPanel(r):pendingDetailPanel(r));
  return '<div class="smart-shell">'+smartRaceTopBar(r)+'<main class="smart-main smart-race-page">'+smartRaceHead(r)+cinematicTabs(r)+raceDetailNotice(r)+'<div class="smart-race-content">'+content+'</div></main>'+cinematicFooter()+'</div>'
}
function renderPartialRace(r){
  if(!state.openPanel)state.openPanel='entry';
  if(state.subPage==='horse'){
    var h=(r.horses||[]).find(function(z){return n(z.horseNumber)===n(state.detailHorseNo)})||{};
    return '<div class="smart-shell">'+raceSubpageTopBar(r,horseDisplayName(r,h))+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">馬情報を取得中です。</div></section></main>'+cinematicFooter()+'</div>'
  }
  if(state.subPage==='bets')return frozenAiBetForRace(r)?betDetailPage(r,{rows:morningSavedMarkRows(r)}):'<div class="smart-shell">'+raceSubpageTopBar(r,'買い目')+'<main class="smart-main smart-race-page"><section class="card"><div class="empty">発走前の買い目原本が未取得です。取得後に表示します（発走後の再計算はしません）。</div></section></main>'+cinematicFooter()+'</div>';
  if(state.subPage==='pace-stage')return paceStagePendingPage(r);
  return '<div class="smart-shell">'+smartRaceTopBar(r)+'<main class="smart-main smart-race-page">'+smartRaceHead(r)+cinematicTabs(r)+raceDetailNotice(r)+'<div class="smart-race-content">'+pendingDetailPanel(r)+'</div></main>'+cinematicFooter()+'</div>'
}
// Display the factual dated roster immediately, independently of Cloudflare D1.
// This never supplies odds, AI marks, betting evidence, or post-off results.
function hydrateStaticRacecardFirst(id,seq,summary){
  var loader=window.ARVEXQStaticRacecard;
  if(!loader||typeof loader.available!=='function')return Promise.resolve(false);
  var date=String((summary||{}).date||state.date||'');
  if(!/^20\d{2}-\d{2}-\d{2}$/.test(date))return Promise.resolve(false);
  return loader.available(date,id,function(path){return edgeFetchJson(path,6500)}).then(function(card){
    if(seq!==state.detailSeq||!card||String(card.id)!==String(id)||
       !state.race||String(state.race.id)!==String(id))return false;
    // A complete API or verified full snapshot always takes precedence.
    if(entryDataAvailable(state.race)&&(state.race.horses||[]).length>=card.horses.length)return false;
    state.race=applySummaryEnvironment(mergeRaceReflection(state.race,card,null,null));
    state.race._entryOnly=true;state.race._staticRacecardFallback=true;
    instantTrackDetails[String(id)]=state.race;saveDetailCache(id,state.race);
    updateDetailSections(id,state.race,true);
    traceRaceDetail(id,'racecard-static-first',{date:date,horses:card.horses.length});
    render();
    return true;
  }).catch(function(error){
    traceRaceDetail(id,'racecard-static-first-failed',{message:String(error&&error.message||error)});
    return false;
  });
}
function fetchRacecardOnly(id){
  var url='https://kraiz-api.4b89h4fydd.workers.dev/api/racecard/'+encodeURIComponent(id)+'?t='+Date.now();
  traceRaceDetail(id,'racecard-request',{url:url});
  return edgeFetchJson(url,6500).then(function(body){
    var d=body&&body.detail;
    if(!body||!body.ok||!d||String(d.id)!==String(id))throw Error('racecard unavailable or id mismatch');
    if(!entryDataAvailable(d)&&!(body.entry_state==='empty'&&Number(d.fieldSize)===0))throw Error('racecard incomplete');
    d=Object.assign({},d,{_entryOnly:true});return d
  }).catch(function(error){
    traceRaceDetail(id,'racecard-failed',{url:url,message:String(error&&error.message||error)});
    var loader=window.ARVEXQStaticRacecard;
    if(!loader||typeof loader.available!=='function')return null;
    var summary=(state.races||[]).find(function(r){return String(r&&r.id||'')===String(id)})||state.race||{},
        date=String(summary.date||state.date||'');
    return loader.available(date,id,function(path){return edgeFetchJson(path,6500)}).then(function(card){
      if(card)traceRaceDetail(id,'racecard-static-backup',{date:date,horses:(card.horses||[]).length});
      return card
    }).catch(function(){return null})
  })
}
function fetchSelectedRaceOdds(id,seq,force){
  return window.ARVEXQLiveOdds.fetch(id,edgeFetchJson,force).then(function(body){
    if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return false;
    var changed=mergeOddsPayload(body);
    updateDetailSections(id,state.race,false);
    if(changed){saveDetailCache(id,state.race);render()}
    else render();
    return changed
  }).catch(function(error){
    traceRaceDetail(id,'odds-failed',{message:String(error&&error.message||error)});
    if(seq===state.detailSeq&&state.race&&String(state.race.id)===String(id)){
      if(!raceHasOdds(state.race))detailState(id).odds='error';
      var status=document.getElementById('odds-status');
      if(status)status.textContent='更新失敗｜'+window.ARVEXQLiveOdds.status(state.race)
    }
    return false
  })
}
function fetchEdgeRace(id,forceNetwork,retryLimit){
  if(!id)return Promise.resolve(null);
  var key=String(id),cached=instantTrackDetails[key]||loadDetailCache(id,true),row=(state.races||[]).find(function(x){return String(x&&x.id||'')===key})||null;
  if(!forceNetwork&&cached&&cached.date&&String(cached.date)<today()&&entryDataAvailable(cached))return Promise.resolve(cached);
  var st=detailState(id),maxAttempts=retryLimit||2;
  st.error='';st.busy=true;st.attempts=0;
  updateDetailSections(id,cached||row,false);
  function attempt(index){
    var url=edgeRaceUrl(id);st.attempts=index+1;
    traceRaceDetail(id,'request',{attempt:index+1,url:url,date:(row||cached||{}).date||state.date,venue:(row||cached||{}).track,raceNo:(row||cached||{}).raceNumber});
    return edgeFetchJson(url,9000).then(function(body){
      if(!body||body.ok===false)throw Error('race detail response unavailable');
      var d=body.detail||null;
      if(d&&d.result&&d.result.finishers!=null&&!Array.isArray(d.result.finishers)){
        traceRaceDetail(id,'section-failed',{section:'result',message:'invalid finishers payload'});
        d=Object.assign({},d);delete d.result
      }
      if(d&&d.id&&String(d.id)!==key)throw Error('race detail id mismatch: '+d.id);
      if(body.race_id&&String(body.race_id)!==key)throw Error('response race id mismatch: '+body.race_id);
      var summary=normalizeDetailSummary(body.summary||row,id);
      if(String(summary.id)!==key)throw Error('summary race id mismatch: '+summary.id);
      var merged=mergeRaceReflection(cached,d,Array.isArray(body.odds)?body.odds:[],summary);
      // Basic fields returned by /api/day must survive sparse detail responses.
      merged=mergeRaceReflection(normalizeDetailSummary(row,id),merged,null,null);
      if(!d&&!entryDataAvailable(merged))throw Error('racecard unavailable');
      if(!entryDataAvailable(merged)&&!(d&&Array.isArray(d.horses)&&Number(d.fieldSize)===0&&d.fieldSize!=null))throw Error('racecard incomplete');
      if(d&&!d._entryOnly){merged._entryOnly=false;delete merged._staticRacecardFallback}
      if(body.analysis_ready)merged.preparedMeta=Object.assign({},merged.preparedMeta||{},{diagnosisReady:true});
      st.error='';updateDetailSections(id,merged,true);
      traceRaceDetail(id,'loaded',{attempt:index+1,horses:(merged.horses||[]).length,sections:Object.assign({},st)});
      instantTrackDetails[key]=merged;saveDetailCache(id,merged);return merged
    }).catch(function(error){
      traceRaceDetail(id,'failed',{attempt:index+1,url:url,message:String(error&&error.message||error)});
      var message=String(error&&error.message||error);
      if(index+1<maxAttempts&&!/http (?:404|400)/i.test(message))return new Promise(function(resolve){setTimeout(resolve,(index+1)*1000)}).then(function(){return attempt(index+1)});
      st.error=message;updateDetailSections(id,cached||row,false);
      // Immutable pre-race archives remain for audits, not live roster recovery.
      return entryDataAvailable(cached)?cached:null
    })
  }
  return attempt(0).finally(function(){st.busy=false})
}

function warmTrackSnapshots(track,high){
  track=track||state.track;
  if(!track)return Promise.resolve(0);

  var key=[state.date,state.circuit,track].join('|');
  if(trackSnapshotJobs[key])return trackSnapshotJobs[key];

  var targets=(state.races||[])
    .filter(function(r){
      return r&&r.id
        &&String(r.track||'')===String(track)
        &&String(r.circuit||'')===String(state.circuit||'')
    })
    .sort(function(a,b){
      return n(a.raceNumber)-n(b.raceNumber)
    });

  // Cloudflare is fast enough to warm a venue directly.
  // Do not wake Render just to prepare cards.
  var cursor=0,count=0,workers=[];
  var concurrency=Math.min(4,Math.max(1,targets.length));

  function worker(){
    if(cursor>=targets.length)return Promise.resolve();
    var row=targets[cursor++];
    var needLiveResult=state.date===today()&&mins(row.startTime)<=nowMins()-3&&!isFinal(row);
    return fetchEdgeRace(row.id,needLiveResult)
      .then(function(d){if(d)count++})
      .then(worker)
  }

  for(var i=0;i<concurrency;i++)workers.push(worker());

  trackSnapshotJobs[key]=Promise.all(workers)
    .then(function(){return count})
    .catch(function(){return count})
    .finally(function(){delete trackSnapshotJobs[key]});

  return trackSnapshotJobs[key]
}

function prewarmVisibleTrackSnapshots(rows){
  // Intentionally do not prefetch every venue on the home screen.
  // Only the venue the user opens is warmed.
  return
}


var trackPackBusy={};
function warmTrackLocal(track,attempt){return Promise.resolve(0)}

function prewarmSelectedTrack(track,raceNo){return}

function openFirstRace(){return}
function archivedCacheComplete(r){
  if(!r)return false;
  var hs=r.horses||[],withHist=hs.filter(function(h){return (h.recentRaces||[]).length>0}).length,
      historyOk=r.analysisMode==='新馬'||!hs.length||withHist>=Math.max(2,Math.ceil(hs.length*.5)),
      oddsOk=raceHasOdds(r),diagOk=diagnosisCurrent(r);
  return historyOk&&diagOk&&oddsOk
}
function oddsRefreshCadence(r){var start=mins(r&&r.startTime),now=nowMins();if(start>=9999)return 60000;var remain=start-now;if(remain<=0)return 0;return remain<=30?30000:60000}
function raceHasOdds(r){return !!(r&&(r.horses||[]).some(function(h){return n(h.winOdds)>0}))}
function raceOddsComplete(r){
  var hs=(r&&r.horses||[]).filter(function(h){return !isScratchHorse(h)&&n(h.horseNumber)>0}),got=hs.filter(function(h){return n(h.winOdds)>0}).length;
  return !!hs.length&&got===hs.length
}
function raceBodyWeightComplete(r){var hs=(r&&r.horses||[]).filter(function(h){return !isScratchHorse(h)&&n(h.horseNumber)>0}),got=hs.filter(function(h){return currentBodyWeight(h)>250}).length;return !!hs.length&&got===hs.length}
function markRelevantInputSignature(r){
  if(!r)return'';
  var horses=(r.horses||[]).map(function(h){
    var x=Object.assign({},h);
    ['winOdds','popularity','oddsForecast','oddsSource','oddsUpdatedAt','marketUpdatedAt'].forEach(function(k){delete x[k]});
    return x;
  });
  return JSON.stringify([r.date,r.startTime,r.distance,r.surface,r.weather,r.condition,
    r.fieldSize,r.markEngineVersion,r.preRacePrediction, horses]);
}
function refreshOddsOnly(force){
  if(!state.race||state.oddsBusy)return Promise.resolve(false);
  var id=String(state.race.id||''),seq=state.detailSeq;if(!id)return Promise.resolve(false);
  state.oddsBusy=true;
  var status=document.getElementById('odds-status');if(status)status.textContent=' 最新データ確認中…';
  return fetchSelectedRaceOdds(id,seq,force).finally(function(){
    state.oddsBusy=false;
    if(seq===state.detailSeq&&state.race&&String(state.race.id)===id)ensureAutoOdds(state.race)
  })
}
function ensureAutoOdds(r){
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  if(!r||r.date!==today()||isFinal(r)||!entryDataAvailable(r))return;
  var id=String(r.id),seq=state.detailSeq;
  state.oddsTimer=setTimeout(function(){
    if(seq===state.detailSeq&&state.race&&String(state.race.id)===id)refreshOddsOnly(false)
  },raceOddsComplete(r)?15000:8000)
}
function overallScoreText(x){if(x&&x.hasFrozenEvaluation===false)return '—';var v=x&&x.overallScoreExact!=null?Number(x.overallScoreExact):Number(x&&x.overallScore);return isFinite(v)?(Math.round(v*10)/10).toFixed(1):'—'}
function aiBetStoreKey(id){return 'arvexq:prebet:v300:'+String(id||'')}
function loadStoredAiBet(id){
  // Only the current device receipt key is eligible for live presentation.
  // Legacy v180-v218 receipts remain untouched in storage for external audit.
  try{
    var x=JSON.parse(localStorage.getItem(aiBetStoreKey(id))||'null');
    return x&&((x.items&&x.items.length)||x.decision==='見送り')?x:null;
  }catch(e){return null}
}
function saveStoredAiBet(r,plan){
  try{
    if(!r||!r.id||!plan||isFinal(r))return;
    var st=mins(r.startTime),raceDate=String(r.date||''),todayKey=today(),started=(raceDate===todayKey&&st<9999&&nowMins()>=st);
    if(raceMarkClock(r).started||started||st>=9999||raceDate!==todayKey||loadStoredAiBet(r.id))return;
    var rd=plan.dataReadiness||{},central=String(r.circuit||'')==='中央',
        minReady=central?.62:.58,ready=Number(rd.prediction),remain=st-nowMins(),lockWindow=30,
        gate=plan.betInputGate||{};
    if(remain>lockWindow||remain<0)return;
    if(!isFinite(ready)||ready<minReady||gate.ready!==true)return;
    if(n(rd.card,0)<.90||n(rd.history,0)<.55||n(rd.analysis,0)<.45)return;
    plan.raceId=String(r.id);plan.raceDate=raceDate;plan.fixedAt=new Date().toISOString();plan.fixedBeforePost=true;plan.fixedMinutesBeforePost=Math.max(0,Math.round(remain));
    plan.fixedInputReadiness={prediction:n(rd.prediction,0),card:n(rd.card,0),history:n(rd.history,0),actualOdds:n(rd.actualOdds,0),bodyWeight:n(rd.bodyWeight,0),environment:n(rd.environment,0),analysis:n(rd.analysis,0)};
    plan.lockPolicy='v355-prerace-model-evidence-30m';
    plan.inputWarningsAtFreeze=(gate.warnings||[]).slice();
    localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))
  }catch(e){}
}
function betComboText(kind,combos){
  combos=combos||[];
  function j(c,sep){return (c||[]).join(sep)}
  if(kind==='単勝')return combos.map(function(c){return j(c,'')}).join('・');
  if(kind==='馬単'||kind==='3連単')return combos.map(function(c){return j(c,' → ')}).join(' / ');
  return combos.map(function(c){return j(c,' - ')}).join(' / ')
}
function isFeaturedBetRace(r,p){
  var title=String(r&&r.title||''),sel=null;
  try{sel=strictSelectedRaceProfile(r,p)}catch(e){}
  return !!(r&&(isMainForecastRace(r)||raceIsGraded(r)||
    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||
    (sel&&sel.selected)||
    (window.ARVEXQMorningTicketLanes&&window.ARVEXQMorningTicketLanes.hasMorningPlace(r,morningPickOf(r)))))
}
function immutableStoredAiBetView(r,plan){
  // A post-lock cancellation or scratch is a display warning, not a license
  // to erase the historical pre-off ticket or silently revise its selections.
  if(!plan)return null;
  var status=String(r&&r.raceStatus||'')+' '+String(r&&r.result&&r.result.status||'');
  var scratched={};(r&&r.horses||[]).forEach(function(h){if(isScratchHorse(h))scratched[n(h.horseNumber)]=1});
  var affected=(plan.items||[]).some(function(z){return (z.combos||[]).some(function(c){return (c||[]).some(function(no){return !!scratched[n(no)]})})});
  if(/中止|取止|取り止め|不成立/.test(status))return Object.assign({},plan,{postLockNotice:'レース中止・取止め。発走前の買い目を記録として表示しています（投票可否・返還は公式情報で確認）。'});
  if(affected)return Object.assign({},plan,{postLockNotice:'固定後に取消・除外馬が発生。発走前の買い目は変更せず記録として表示します。'});
  return plan
}
function verifiedSavedAiBet(r,plan){
  if(!r||!r.id||!plan||!plan.fixedAt)return null;
  // Failed server captures carry a timestamp too. They are retry receipts,
  // never immutable original tickets and must not block a pre-off retry.
  if(plan.captureStatus==='failed'||plan.captureStatus==='engine-missing'||
     plan.decision==='未取得'||plan.decision==='エラー'||plan.decision==='データ不足'||
     (plan.betInputGate&&plan.betInputGate.ready===false))return null;
  if(plan.raceId&&String(plan.raceId)!==String(r.id))return null;
  if(plan.raceDate&&String(plan.raceDate)!==String(r.date))return null;
  var off=Date.parse(String(r.date||'')+'T'+String(r.scheduledStartTime||r.startTime||'').slice(0,5)+':00+09:00');
  var at=Date.parse(String(plan.fixedAt||''));
  if(!isFinite(off)||!isFinite(at)||at>=off)return null;
  return plan
}
function currentBetEnginePlan(plan){
  // Historical sealed tickets remain in audit storage, not in the live UI.
  // Never re-derive or relabel a legacy ticket after the off.
  return plan&&/^arvexq-true-run-pure-sectional-v[12]$/.test(
    String(plan.engineVersion||plan.betStrategy||''))?plan:null
}
function frozenAiBetForRace(r){
  if(!r||!r.id)return null;
  var server=currentBetEnginePlan(verifiedSavedAiBet(r,r.preRaceBet));
  if(server)return server;
  var mod=window.ARVEXQMorningEvidence,original=r.morningTicketEvidence;
  if(mod&&mod.verify(r,original)){
    var fixed=currentBetEnginePlan(verifiedSavedAiBet(r,mod.sealedPlan(r,original)));
    if(fixed)return fixed
  }
  return currentBetEnginePlan(verifiedSavedAiBet(r,loadStoredAiBet(r.id)))
}
// Outcome context is explanatory: it must not reorder or exclude ticket combos.
function attachBetOutcomeAudit(plan,r,p){
  if(!plan||!p||plan.fixedAt)return plan;
  var o=p.outcome||paceOutcomeModel(r,p);if(!o)return plan;
  function ids(xs){return (xs||[]).map(function(x){return n(x&&x.horse&&x.horse.horseNumber)}).filter(function(no){return no>0})}
  plan.outcomeLink={verdict:o.verdict,first:ids(o.first),second:ids(o.second),third:ids(o.third)};
  return plan
}
// Marks are explanatory annotations, not a competing ticket selector.
function captureExactaBetEvidence(ranked,rows){
  var axis=(rows||[]).find(function(z){return z&&z.horse&&z.predMark==='◎'})||null,
      axisNo=n(axis&&axis.horse&&axis.horse.horseNumber,0);
  if(!axisNo)return null;
  var arr=(ranked||[]).filter(function(z){return z&&z.combo&&n(z.combo[0])===axisNo})
    .map(function(z){return {second:n(z.combo[1]),joint:Math.max(0,n(z.score,0))}})
    .sort(function(a,b){return b.joint-a.joint||a.second-b.second});
  var total=arr.reduce(function(sum,z){return sum+z.joint},0);
  if(!total)return null;
  return {version:'exacta-conditional-v342',axis:axisNo,pairs:arr.map(function(z){
    return {second:z.second,joint:z.joint,p2GivenFirst:z.joint/total};
  })};
}
// Marks represent general 1st-to-3rd role, while an exacta requires
// the actual conditional 2nd-place model. Do not silently rewrite that model.
function alignBetPlanToMarks(plan,r,p){
  if(!plan||!p||!Array.isArray(plan.items)||plan.fixedAt)return plan;
  var marks={},axis=0,mismatches=[];
  (p.rows||[]).forEach(function(z){
    if(!z||!z.horse)return;
    var no=n(z.horse.horseNumber,0),mark=String(z.predMark||'').replace(/＋/g,'+');
    if(!no)return;
    marks[no]=mark;if(mark==='◎')axis=no;
  });
  (plan.items||[]).forEach(function(item){
    if(item.kind!=='馬単')return;
    (item.combos||[]).forEach(function(combo){
      var first=n(combo&&combo[0]),second=n(combo&&combo[1]),mark=marks[second]||'';
      if(first===axis&&(mark==='☆'||mark==='△'||mark==='注'))mismatches.push({first:first,second:second,mark:mark});
    });
  });
  plan.markAlignment={version:'v342-model-first-explain',axis:axis,mismatches:mismatches};
  return plan
}
// Every explanation is recorded with the candidate plan *before* it can be
// persisted. Historic locked plans never acquire explanations from live data.
function attachAiBetExplanation(plan,r,p){
  if(!plan||plan.fixedAt)return plan;
  var rows=(p&&p.rows||[]).filter(function(z){return z&&z.horse}),marks={};
  rows.forEach(function(z){
    var no=n(z.horse.horseNumber,0);
    if(no)marks[no]=String(z.predMark||'').replace(/＋/g,'+');
  });
  var evidence=plan.exactaEvidence||null,
      pairs=evidence&&Array.isArray(evidence.pairs)?evidence.pairs:[],
      pairByNo={},axis=n(evidence&&evidence.axis,0),lines=[];
  pairs.forEach(function(x){pairByNo[n(x.second)]=Math.max(0,n(x.p2GivenFirst,0))});
  function has(no){return Object.prototype.hasOwnProperty.call(pairByNo,no)}
  function pct(v){return (Math.max(0,Math.min(1,n(v,0)))*100).toFixed(1)+'%'}
  var betItems=(plan.items||[]).filter(function(z){return z&&z.kind==='馬単'&&(z.combos||[]).length});
  betItems.forEach(function(item){
    var actual=(item.combos||[]).filter(function(c){return c&&n(c[0])>0&&n(c[1])>0}).slice(0,4);
    actual.forEach(function(c){
      var first=n(c[0]),second=n(c[1]),mark=marks[second]||'無印';
      if(first===axis&&has(second)){
        lines.push('馬単 '+first+'→'+second+'（'+mark+'）：'+first+'を1着とした場合の、'+second+'の条件付き2着推定は'+pct(pairByNo[second])+'。');
      }else{
        lines.push('馬単 '+first+'→'+second+'（'+mark+'）：着順AIの選択候補。発走前の条件付き比較スコアが残っていないため、確率差は断定しません。');
      }
    });
    var used=actual.filter(function(c){return n(c[0])===axis}).map(function(c){return n(c[1])}),
        excluded=rows.filter(function(z){
          var no=n(z.horse.horseNumber),mark=marks[no];
          return no!==axis&&used.indexOf(no)<0&&(mark==='○'||mark==='☆+');
        }).sort(function(a,b){
          return (marks[n(a.horse.horseNumber)]==='○'?0:1)-(marks[n(b.horse.horseNumber)]==='○'?0:1);
        }),
        selectedLower=used.filter(function(no){return marks[no]==='☆'||marks[no]==='△'||marks[no]==='注'});
    if(!excluded.length||!selectedLower.length)return;
    var omitted=n(excluded[0].horse.horseNumber),om=marks[omitted],kept=selectedLower[0],km=marks[kept];
    if(has(kept)&&has(omitted)&&pairByNo[kept]>pairByNo[omitted]){
      lines.push('印と異なる理由：'+km+kept+'の条件付き2着推定 '+pct(pairByNo[kept])+' が、'+om+omitted+'の '+pct(pairByNo[omitted])+' を上回ります。☆＋は1着逆転を含めた総合評価のため、2着専用の順位とは一致しない場合があります。');
    }else if(has(kept)&&has(omitted)){
      lines.push('印との不整合を検出：'+om+omitted+'の条件付き2着推定 '+pct(pairByNo[omitted])+' が、採用した'+km+kept+'の '+pct(pairByNo[kept])+' 以上です。展開や買い目選択ゲートで候補が外れた可能性があり、根拠の再点検が必要です。');
    }else{
      lines.push('印との違い：'+om+omitted+'を外して'+km+kept+'を採用。両馬の着順比較スコアが保存されていないため、どちらの方が2着確率が高いか断定できません。');
    }
  });
  if(!betItems.length&&(plan.items||[]).length){
    var main=(plan.items||[])[0],kind=String(main.kind||'');
    if(['馬連','ワイド','3連複'].indexOf(kind)>=0)lines.push(kind+'を選択：今回の予測では着順の固定より、上位候補を順不同で組み合わせることを優先しました。');
    else if(kind==='3連単')lines.push('3連単を選択：1〜3着順序の集中度と券種選択条件を通過した組み合わせです。');
  }
  if(!lines.length&&plan.decision==='見送り')lines.push('券種選択の条件を満たさなかったため買い目を見送りました。');
  if(lines.length&&plan.outcomeLink&&plan.outcomeLink.verdict)lines.push('展開判定：'+String(plan.outcomeLink.verdict)+'。展開と着順の役割を併せて検討しています。');
  plan.betExplanation={version:'v342-conditional-second',axis:axis,lines:lines.slice(0,7),
    note:'表示％はAIモデル内の条件付き2着推定で、実際の的中率や馬券の回収率を保証しません。発走前に固定した買い目と根拠は変更しません。'};
  return plan
}
function aiBetExplanationHtml(plan){
  var d=plan&&plan.betExplanation||null;
  if(!d||!Array.isArray(d.lines)||!d.lines.length){
    if(plan&&plan.fixedAt)return '<section class="ai-bet-why"><b>買い目の根拠</b><p>この買い目は発走前に固定されています。当時の比較数値が保存されていないため、今の分析値による後付け説明はしません。</p></section>';
    return '';
  }
  return '<section class="ai-bet-why"><b>この買い目になった理由</b>'
    +d.lines.map(function(line){return '<p>'+esc(line)+'</p>'}).join('')
    +'<small>'+esc(d.note||'')+'</small></section>'
}
// Gate purchasable tickets separately from prediction display. A first-corner
// placing is a historical early-position proxy, NOT measured first-1F speed.
function paceEvidenceProfile(r,p){
  var entries=((p&&p.rows)||[]).filter(function(z){return z&&z.horse&&!isScratchHorse(z.horse)}),
      date=String((r&&r.date)||''),counts={},valid=0,leaderNos={},i;
  // Use the exact same five-race, de-duplicated pre-race source as the
  // development engine. A stored five-row history may have zero valid corners.
  entries.forEach(function(z){
    var no=n(z.horse.horseNumber,0),runs=paceHistoryRuns(z.horse,r);
    counts[no]={history:runs.length,earlyPositions:runs.length};
    if(runs.length>=2)valid++
  });
  ((p&&p.arrangement&&p.arrangement.leadCandidates)||[]).slice(0,2).forEach(function(z){
    var no=n(z&&z.horse&&z.horse.horseNumber,0);if(no)leaderNos[no]=1
  });
  var ranked=entries.slice().sort(function(a,b){
    return n(b.winnerDecisionProbability,n(b.winnerConsensusProbability,n(b.p1Probability)))-
      n(a.winnerDecisionProbability,n(a.winnerConsensusProbability,n(a.p1Probability)))
  });
  var top=ranked.slice(0,Math.min(3,ranked.length)),topMissing=top.filter(function(z){
    var q=counts[n(z.horse.horseNumber)]||{};
    return n(q.earlyPositions)<2||n(q.history)<3
  }).map(function(z){return n(z.horse.horseNumber)});
  var leaderMissing=Object.keys(leaderNos).filter(function(no){
    return n((counts[no]||{}).earlyPositions)<2
  }).map(Number);
  var coverage=entries.length?valid/entries.length:0,
      sufficient=entries.length>=4&&coverage>=.55&&!topMissing.length&&!leaderMissing.length;
  var reasons=[];
  if(coverage<.55)reasons.push('全頭の初角通過順位が不足');
  if(topMissing.length)reasons.push('上位馬'+topMissing.join('・')+'の先行根拠不足');
  if(leaderMissing.length)reasons.push('ハナ候補'+leaderMissing.join('・')+'の先行根拠不足');
  if(!date)reasons.push('対象日を確認できない');
  return{ready:sufficient,coverage:coverage,topMissing:topMissing,leaderMissing:leaderMissing,
    observedHorses:valid,totalHorses:entries.length,reason:reasons.join('／')||'過去走の初角通過順位を確認',
    source:'過去走初角順位による位置取り推定（実測テン1Fではない）'};
}
function buildAiBetPlan(r,p){
  var started=raceMarkClock(r).started,stored=frozenAiBetForRace(r);
  if(stored)return immutableStoredAiBetView(r,stored);
  if(isFinal(r)||started)return null;
  var rows=((p&&p.rows)||[]).filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)});
  if(rows.length<4)return null;
  var selected=strictSelectedRaceProfile(r,p),ready=dataReadinessProfile(r,p),
      ordered=rows.slice().sort(function(a,b){return n(b.threeFactorScore)-n(a.threeFactorScore)}),
      field=rows.length,score=n(ordered[0].threeFactorScore),gap=score-n(ordered[1].threeFactorScore),
      mark=ordered[0],measured=rows.filter(function(z){return n(z.threeFactorCoverage)>=2}).length,
      isReady=n(mark.threeFactorCoverage)>=3&&measured>=Math.ceil(field*.70),
      active=selected.selected&&isReady;
  function no(z){return n(z&&z.horse&&z.horse.horseNumber)}
  function item(level,kind,combos,reason){
    return {level:level,kind:kind,combos:combos,points:combos.length,
      combo:betComboText(kind,combos),reason:reason||'同じ45/35/20モデルから抽出'};
  }
  var items=[],tri=[],i,j,k,w=[],sum=0,top=n(ordered[0].threeFactorScore);
  rows.forEach(function(z){var v=Math.exp((n(z.threeFactorScore)-top)/.15);w.push(v);sum+=v});
  // Ordered trifecta outcomes use the very same three-factor strengths and
  // Plackett-Luce ranking as ◎○▲, never an independent ticket predictor.
  if(active){
    items.push(item('本線','馬連',[[no(ordered[0]),no(ordered[1])]],
      '◎と○の組合せ（3要素による1・2着候補）'));
    items.push(item('保険','ワイド',[[no(ordered[0]),no(ordered[2])]],
      '◎と▲の3着内組合せ'));
    if(gap>=.055){
      for(i=0;i<field;i++)for(j=0;j<field;j++)if(i!==j)
        for(k=0;k<field;k++)if(i!==k&&j!==k){
          var d1=sum-w[i],d2=d1-w[j];
          if(d1<=0||d2<=0)continue;
          tri.push({combo:[no(rows[i]),no(rows[j]),no(rows[k])],
            score:w[i]/sum*w[j]/d1*w[k]/d2});
        }
      tri=tri.filter(function(z){return z.combo[0]===no(mark)});
      tri.sort(function(a,b){return b.score-a.score});
      var maxPoints=6,combos=tri.slice(0,maxPoints).map(function(z){return z.combo});
      if(combos.length)items.push(item('3連単チャレンジ','3連単',combos,
        '◎1着固定。3要素の順序確率上位を最大6点'));
    }
  }
  var trifecta=items.some(function(z){return z.kind==='3連単'}),
      plan={raceId:String(r.id||''),raceDate:String(r.date||''),items:items,
        engineVersion:'arvexq-true-run-pure-sectional-v2',betStrategy:'arvexq-true-run-pure-sectional-v2',
        betQuality:Math.round(score*100),decision:active?'購入候補':'見送り',
        featuredRace:isFeaturedBetRace(r,p),selectionAudit:selected,
        honmei:{horseNumber:no(mark),role:'win',grade:mark.honmeiGrade},
        noAxis:!active,referenceOnly:!selected.selected,
        trifectaReviewed:true,trifectaDecision:trifecta?'採用':'見送り',
        trifectaReason:trifecta?'◎の差と発走前根拠が順序判断条件を通過':'順序信頼または◎の差が不足',
        insuranceDecision:active?'採用':'見送り',
        reason:active?'45%近走内容・35%基礎能力・20%区間性能による同一モデルの本線':
          selected.reason+'／データ充足の審査が必要',
        expectedValueReason:'各券種の的中率・期待値は検証で校正されていません。',
        referenceBudget:{points:items.reduce(function(v,x){return v+x.points},0)},
        dataReadiness:ready,betInputGate:{ready:isReady,missing:isReady?[]:['3要素または出走前データ不足']},
        betWarnings:!isReady?['直近5走・区間の実測根拠不足']:[],
        p1Model:'arvexq-true-run-pure-sectional-v2',
        p2Model:'plackett-luce-same-score',p3Model:'plackett-luce-same-score',
        roles:{p1:ordered.slice(0,4).map(function(x){return {no:no(x),p:n(x.p1Probability)}}),
          p2:rows.slice().sort(function(a,b){return n(b.p2Probability)-n(a.p2Probability)}).slice(0,5).map(function(x){return {no:no(x),p:n(x.p2Probability)}}),
          p3:rows.slice().sort(function(a,b){return n(b.p3Probability)-n(a.p3Probability)}).slice(0,6).map(function(x){return {no:no(x),p:n(x.p3Probability)}})}};
  saveStoredAiBet(r,plan);
  return plan;
}

function betItemHit(item,order){
  if(!item||!order||!order.length)return false;var t=order.slice(0,3).map(n);
  return (item.combos||[]).some(function(c){var a=(c||[]).map(n);if(item.kind==='単勝')return t[0]===a[0];if(item.kind==='馬単')return t[0]===a[0]&&t[1]===a[1];if(item.kind==='馬連')return a.length===2&&a.slice().sort().join('-')===t.slice(0,2).sort().join('-');if(item.kind==='ワイド')return a.length===2&&t.slice(0,3).indexOf(a[0])>=0&&t.slice(0,3).indexOf(a[1])>=0;if(item.kind==='3連複')return a.length===3&&a.slice().sort().join('-')===t.slice(0,3).sort().join('-');if(item.kind==='3連単')return a.length===3&&a[0]===t[0]&&a[1]===t[1]&&a[2]===t[2];return false})
}
function aiBetPlanHit(r,plan){if(!isFinal(r)||!plan)return null;var fs=((r.result||{}).finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)}),order=fs.map(function(x){return n(x.horseNumber)});if(order.length<2)return null;var levels={},kinds={},any=false,tri=false;(plan.items||[]).forEach(function(z){var h=betItemHit(z,order);levels[z.level]=!!levels[z.level]||h;kinds[z.kind]=!!kinds[z.kind]||h;if(z.kind==='3連単'||z.level==='3連単チャレンジ')tri=tri||h;else any=any||h});return {hit:any,tri:tri,levels:levels,kinds:kinds}}
function betTransferText(r,p){
  var plan=buildAiBetPlan(r,p);
  if(!plan)return '';
  var lines=['ARVEXQ 買い目',String(r.track||'')+' '+String(r.raceNumber||'')+'R '+String(r.title||''),'発走 '+String(r.startTime||'--:--')];
  (plan.items||[]).forEach(function(z){lines.push(String(z.level||'')+'｜'+String(z.kind||'')+'｜'+String(z.combo||'')+'｜'+String(z.points||0)+'点'+(z.confidence?'｜'+String(z.confidence):''))});
  if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');
  lines.push('※投票内容・金額は公式投票サイトで確認して確定してください。');
  return lines.join('\n')
}
function setBetCopyStatus(msg){var el=document.getElementById('bet-copy-status');if(el){el.textContent=msg;el.classList.add('show');setTimeout(function(){if(el)el.classList.remove('show')},1800)}}
function fallbackCopyText(text){var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();ta.setSelectionRange(0,ta.value.length);var ok=false;try{ok=document.execCommand('copy')}catch(e){}document.body.removeChild(ta);return ok}
function copyCurrentBet(){
  if(!state.race)return;var p=state.pred||predict(state.race),text=betTransferText(state.race,p);
  if(!text){setBetCopyStatus('買い目がまだありません');return}
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(function(){setBetCopyStatus('買い目をコピーしました')}).catch(function(){setBetCopyStatus(fallbackCopyText(text)?'買い目をコピーしました':'コピーできませんでした')})}
  else setBetCopyStatus(fallbackCopyText(text)?'買い目をコピーしました':'コピーできませんでした')
}
// Dedicated betting display: /betting/bet_view.js
function aiBetRecommendation(r,p){
 if(!window.ARVEXQBetView||typeof window.ARVEXQBetView.render!=='function')
  return '<div class="ai-bet-box"><b>買い目表示モジュール未取得</b><p>再読み込みしてください。保存済み予想は変更しません。</p></div>';
 return window.ARVEXQBetView.render(r,p,{buildAiBetPlan:buildAiBetPlan,esc:esc,n:n,
  isFinal:isFinal,raceMarkClock:raceMarkClock,aiBetExplanationHtml:aiBetExplanationHtml,betComboText:betComboText});
}

function aiMarksPanel(r,p){
  var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.predRank)-n(b.predRank)});
  return '<section id="section-aimarks" class="card"><h2>AI印予想</h2><p class="muted">◎は近走内容45%・基礎能力35%・区間性能20%の総合最高評価。○は1・2着、▲は2・3着、△は3着向き。☆は独立した好走根拠が複数揃った場合だけ選びます。発走後は保存済み予想のみ表示します。</p><div class="ai-mark-list">'+rows.map(function(x){var h=x.horse,mark=x.predMark||'—',bw=horseBodyWeightText(h)||(isFinal(r)?'結果確認中':'取得中'),bomb=n(x.bombScore),reason=(x.attentionReason||(x.upsetReasons||[]).slice(0,2).join('・')),wp=(n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.winProbability)))*100).toFixed(1),mp=(n(x.marketProbability)*100).toFixed(1);return '<button class="ai-mark-row" data-horse-open="'+esc(h.horseNumber)+'"><span class="ai-mark-symbol">'+esc(mark)+'</span>'+badge(h)+'<span class="ai-mark-name"><b>'+esc(h.name)+'</b>'+(x.predMark==='◎'?'<small>'+esc(honmeiBadgeText(x)==='未保存'?'◎：当時の役割・信頼度未保存':'◎'+honmeiBadgeText(x)+'｜'+(x.honmeiRole==='win'?'1着向き':'3着内の軸向き')+'｜信頼度'+x.honmeiGrade)+'</small>':'')+'<small>1着 '+esc(wp)+'%　P2 '+(n(x.p2Probability)*100).toFixed(1)+'%　P3 '+(n(x.p3Probability)*100).toFixed(1)+'%</small><small>市場 '+esc(mp)+'%　EDGE '+esc(x.edgeScore||50)+'</small><small>'+esc(x.overallGrade||'C')+' '+esc(overallScoreText(x))+'　馬体重 '+esc(bw)+'</small>'+(bomb>=55?'<small class="upset-line">BOMB '+esc(bomb)+'/100'+(reason?'　'+esc(reason):'')+'</small>':'')+'</span><span class="ai-mark-rank">勝率'+esc(x.winnerDecisionRank||x.winnerConsensusRank||x.winRank||'—')+'位</span></button>'}).join('')+'</div></section>'
}
function betPanel(r,p){return '<section id="section-bets" class="card bet-card-clean">'+aiBetRecommendation(r,p)+'</section>'}
function diagnosisPanel(r,p){
  var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.horse&&a.horse.horseNumber,999)-n(b.horse&&b.horse.horseNumber,999)});
  var details='<div class="diagnosis-merged-list">'+rows.map(function(x,i){
    var h=x.horse,e=x.evaluation||{},confidence=esc(e.confidence||'低'),rank=n(x.overallRank,i+1),bw=horseBodyWeightText(h),refbw=!bw?referenceBodyWeight(h):0,bwLabel=bw?bw:(refbw?('前走 '+refbw+'kg'):(isFinal(r)?'結果確認中':'計量待ち'));
    var reason=(x.overallReasons||[]).join(' / ')+(n(x.bombScore)>=65?' / BOMB '+n(x.bombScore)+' EDGE '+n(x.edgeScore)+' '+(x.upsetReasons||[]).slice(0,2).join('・'):'')+(x.predMark==='☆'&&x.attentionReason?' / ☆の根拠 '+x.attentionReason:'');
    return '<article class="horse-card diagnosis-merged-row">'
      +'<div class="diagnosis-merged-head">'
        +'<span class="diag-check-cell"><span class="rc-horse-check '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+'</span></span>'
        +'<button class="diagnosis-horse-main" data-horse-open="'+esc(h.horseNumber)+'">'+badge(h)+'<span class="diagnosis-horse-name"><b>'+esc(h.name)+'</b><small>総合'+rank+'位　馬体重 '+esc(bwLabel)+'</small></span></button>'
        +'<span class="diagnosis-eval"><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'C')+'</strong><b>'+esc(overallScoreText(x))+'</b><i class="diagnosis-ai-mark" data-ai-mark="'+esc(x.predMark||'')+'">'+esc(x.predMark||'—')+'</i></span>'
      +'</div>'
      +'<div class="diag-confidence">データ信頼度 <strong>'+confidence+'</strong>　勝率 '+(n(x.winProbability)*100).toFixed(1)+'% / 市場 '+(n(x.marketProbability)*100).toFixed(1)+'%</div>'
      +'<p class="diag-explain">'+esc(reason||'総合バランス型')+'</p>'
    +'</article>'
  }).join('')+'</div>';
  return '<section id="section-diagnosis" class="card"><h2>全頭診断</h2><p class="muted diagnosis-tap-note">馬名をタップすると、直近5走・適性・騎手/調教師・血統までまとめて確認できます。</p>'+details+'</section>'
}
function historyPanel(r){return '<section id="section-history" class="card"><h2>過去走（直近5走）</h2>'+(r.horses||[]).map(function(h){var runs=(h.allPastRuns||h.recentRaces||[]).slice(0,5),count=runs.length,status=h.debutNoHistory?'新馬・既走なし':(count>=5?'5/5走取得済':count+'/5走・履歴補完中'),career=careerCoverageLabel(h);if(career)status+='・全キャリア'+career;return '<article class="horse-card"><button data-horse-open="'+esc(h.horseNumber)+'">'+esc(h.horseNumber)+' '+esc(h.name)+'</button><small class="muted" style="margin-left:8px">'+esc(status)+'</small>'+ (runs.length?runs.map(function(z){return '<div class="recent">'+esc(z.date||'—')+' '+esc(z.track||'—')+' '+esc(z.title||'')+' '+esc(z.distance||'—')+'m　'+esc(z.finish||z.finishStatus||'—')+'着　通過 '+esc((z.cornerPositions||[]).join('-')||'—')+'</div>'}).join(''): '<p>'+(h.debutNoHistory?'新馬：既走データなし':'履歴補完中。取得できた実走だけを表示します。')+'</p>')+'</article>'}).join('')+'</section>'}
function pacePanel(r,p){return '<section id="section-pace" class="card pace-panel-direct">'+paceBoard(r,p)+'</section>'}
function openHorseDetailPage(no){
  no=n(no,0);if(!no||!state.race)return;
  state.detailHorseNo=no;
  state.subPageReturnPanel=state.openPanel||'entry';
  state.subPage='horse';
  state.horseModalNo=null;
  window.scrollTo(0,0);
  render()
}
function moveDetailHorse(dir){
  if(!state.pred)return;var rows=sortedHorseRows(state.pred.rows);if(!rows.length)return;
  var idx=rows.findIndex(function(z){return n(z.horse.horseNumber)===n(state.detailHorseNo)});if(idx<0)idx=0;
  state.detailHorseNo=n(rows[(idx+dir+rows.length)%rows.length].horse.horseNumber);state.subPage='horse';render()
}
function resultPanel(r){
  var final=isFinal(r),flash=isFlash(r),any=hasAnyResultData(r);
  return '<section id="section-result" class="card result-panel-compact"><h2>レース結果</h2>'+
    (any?renderResult(r)+(final?renderPayouts(r):'<section class="card result-wait-card"><div class="section-title">払い戻し <span class="muted">確定待ち</span></div><div class="muted">確定後に自動反映します。</div></section>')+renderActualFlow(r):
      '<div class="muted result-status-compact">'+(final?'結果は確定扱いですが着順詳細は未取得です。':(String(r.date||'')<today()||String(r.date||'')===today()&&mins(r.startTime)<=nowMins()?'公式結果の反映待ちです。自動再確認しています。':'発走前・結果未確定'))+'</div><button type="button" data-detail-retry="'+esc(r.id)+'">結果を再確認</button>') +
  researchRecapPanel(r)+'</section>'
}
function detailTabs(r,p){var key=state.openPanel;if(key==='diagnosis'){state.openPanel='entry';key='entry'}if(key==='entry')return '<div id="section-entry" class="accordion-panel">'+runnerStyleSection(r,p)+(window.ARVEXQDiagnosisView?window.ARVEXQDiagnosisView.render(r,p,{original:authorizedPreOffMarks,esc:esc,started:function(x){return raceMarkClock(x).started},scratch:isScratchHorse}):'')+'</div>';if(key==='pace')return '<div class="accordion-panel">'+pacePanel(r,p)+'</div>';if(key==='result')return '<div class="accordion-panel">'+resultPanel(r)+'</div>';return '<div class="accordion-idle">出走表・展開予想から見たい項目を押してください。</div>'}
function renderPicker(){var a=state.races.filter(function(r){return r.circuit===state.circuit});a.sort(function(x,y){return (x.track||'').localeCompare(y.track||'ja')||n(x.raceNumber)-n(y.raceNumber)});return'<div class="shell">'+header("全レース",true,state.date+'・'+state.circuit)+'<main class="main"><section class="card"><div class="picker-list">'+(a.length?a.map(function(r){return'<button class="picker-item '+(isFinal(r)?'final':'')+'" data-race="'+esc(r.id)+'"><span>'+esc(r.track)+' '+esc(r.raceNumber)+'R　'+esc(r.title||"")+'</span><span class="picker-side"><strong>'+(isFinal(r)?'確定':(isFlash(r)?'速報':timeHtml(r)))+'</strong></span></button>'}).join(""):'<div class="empty">レースデータなし</div>')+'</div></section></main></div>'}
var VENUE_PHOTOS={};
function cinematicContext(r){var circuit=r&&r.circuit||state.circuit,rows=state.races.filter(function(x){return x.circuit===circuit}),venues=[];(circuit==='中央'?['中山','阪神','札幌','中京'].concat(CENTRAL.filter(function(t){return ['中山','阪神','札幌','中京'].indexOf(t)<0})):LOCAL).forEach(function(track){var races=rows.filter(function(x){return x.track===track});if(races.length)venues.push({track:track,count:races.length})});if(r&&!venues.some(function(v){return v.track===r.track}))venues.push({track:r.track,count:1});var track=r&&r.track||state.track||(venues[0]&&venues[0].track)||'',races=rows.filter(function(x){return x.track===track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),featured=r||races.find(function(x){return n(x.raceNumber)===1})||races[0]||null;return{circuit:circuit,venues:venues,track:track,races:races,featured:featured}}
function cinematicHero(){return '<header class="cinema-hero"><img class="cinema-hero-image" src="/arvexq-racing-hero.webp" alt="" fetchpriority="high"><div class="cinema-tools"><time>'+esc(state.date.replace(/-/g,'.'))+'</time><button data-action="reload" aria-label="更新" title="更新">↻</button></div></header>'}
function cinematicControls(circuit){return '<div class="cinema-controls"><div class="cinema-circuit" aria-label="開催区分"><button data-circuit="中央" class="'+(circuit==='中央'?'active':'')+'">中央</button><button data-circuit="地方" class="'+(circuit==='地方'?'active':'')+'">地方</button></div>'+dateStrip()+'<label class="cinema-calendar" title="日付を選択"><span aria-hidden="true">▦</span><input id="date" type="date" value="'+esc(state.date)+'" aria-label="開催日"></label></div>'}
function dateStrip(){var center=new Date(state.date+'T12:00:00'),out='';for(var i=-7;i<=2;i++){var d=new Date(center);d.setDate(d.getDate()+i);var key=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'),label=(d.getMonth()+1)+'/'+d.getDate()+' ('+'日月火水木金土'[d.getDay()]+')';out+='<button data-date="'+key+'" class="'+(key===state.date?'active':'')+'" aria-pressed="'+(key===state.date)+'">'+label+'</button>'}return '<nav class="date-strip" aria-label="開催日">'+out+'</nav>'}
function cinematicVenues(ctx){return '<nav class="cinema-venues">'+ctx.venues.map(function(v){return '<button class="cinema-venue '+(ctx.track===v.track?'active':'')+'" data-track="'+esc(v.track)+'"><strong>'+esc(v.track)+'</strong><small>全'+v.count+'R</small></button>'}).join('')+'</nav>'}
function cinematicNumbers(ctx){return '<nav class="cinema-numbers" aria-label="レース番号">'+Array.from({length:12},function(_,i){var row=ctx.races.find(function(x){return n(x.raceNumber)===i+1});if(!row&&ctx.featured&&n(ctx.featured.raceNumber)===i+1)row=ctx.featured;return '<button '+(row?'data-race="'+esc(row.id)+'"':'disabled')+' class="'+(ctx.featured&&n(ctx.featured.raceNumber)===i+1?'active':'')+'">'+(i+1)+'R</button>'}).join('')+'</nav>'}
function cinematicGrade(r){var g=r.grade||r.gradeLabel||'',match=String(r.title||'').match(/(?:J[・･.]?)?G[ⅠⅡⅢ123]/i);if(!g&&match)g=match[0];return g?'<span class="cinema-grade">'+esc(g)+'</span>':''}
function cinematicTabs(r){
  function tab(label,key){var active=state.openPanel===key;return '<button type="button" data-panel="'+key+'" aria-expanded="'+active+'" class="race-nav-v230-btn '+(active?'active':'')+'"><span class="race-nav-v230-label">'+label+'</span><span class="race-nav-v230-caret">'+(active?'−':'＋')+'</span></button>'}
  // v230: isolated navigation classes only. Do not inherit any legacy cinema-tabs sizing.
  return '<div class="race-nav-v230">'
    +'<div class="race-nav-v230-row race-nav-v230-top">'+tab('出走表','entry')+tab('展開予想','pace')+tab('買い目','bets')+'</div>'
    +'</div>'
}
function cinematicFeature(r){if(!r)return '';var count=n(r.fieldSize,(r.horses||[]).length),surface=r.surface||'—',course=COURSE[r.track]||{},turn=r.turn||course.turn||'—';return '<section class="cinema-feature" aria-label="選択したレース"><div class="cinema-feature-photo" aria-hidden="true"></div><div class="cinema-feature-info"><div class="cinema-feature-heading"><h1>'+esc(r.track)+' '+esc(r.raceNumber)+'R</h1>'+cinematicGrade(r)+'</div><h2>'+esc(r.title||'レース詳細')+'</h2><div class="cinema-feature-meta">'+timeHtml(r)+' 発走　'+esc(surface)+' '+esc(r.distance||'—')+'m ('+esc(turn)+')　<span>'+esc(r.weather||'')+' '+esc(r.condition||'')+'</span></div><div class="cinema-metrics">'+[[r.distance?r.distance+'m':'—','距離'],[turn,'コース'],[surface,'馬場'],[r.raceClass||r.className||raceMode(r),'条件'],[count?count+'頭':'—','頭数']].map(function(x){return '<div><b>'+esc(x[0])+'</b><small>'+esc(x[1])+'</small></div>'}).join('')+'</div></div><button class="cinema-feature-open" data-race="'+esc(r.id)+'" aria-label="レース詳細を開く">›</button>'+cinematicTabs(r)+'</section>'}
function otherRaces(r){var ctx=cinematicContext(r),rows=ctx.races.filter(function(x){return !r||x.id!==r.id});return '<section class="cinema-others"><div class="cinema-section-heading"><h2>◷ '+(state.date===today()?'本日の他レース':'この日の他レース')+'</h2><button data-action="all-races">全レース一覧 ›</button></div><div class="cinema-other-list">'+(rows.length?rows.map(function(x){return '<button data-race="'+esc(x.id)+'" class="cinema-other-row '+(isFinal(x)?'final':'')+'"><span>'+esc(x.track)+'</span><b>'+esc(x.raceNumber)+'R</b><span class="other-title">'+esc(x.title||'')+'</span><time>'+timeHtml(x)+'</time><span class="other-distance">'+esc(x.surface||'')+' '+esc(x.distance||'—')+'m</span><span class="other-condition">'+esc(x.condition||'')+'</span><span class="other-status">'+(isFinal(x)?'結果確定':(isFlash(x)?'結果速報':'レース詳細'))+' ›</span></button>'}).join(''):'<div class="cinema-empty">他のレースはありません</div>')+'</div></section>'}
function cinematicFooter(){return '<footer class="cinema-footer">ARVEXQ　<small>PACE · POSITION · VALUE · BUILD '+esc(window.ARVEXQ_BUILD||'v327')+'</small></footer>'}
function smartTopBar(back,title,sub){
  // One dated subpage header for both sports. Retire the previous empty spacer.
  if(state.homePage&&!state.track&&!state.race){
    return '<header class="smart-topbar smart-topbar-clean smart-section-topbar arv-dated-subbar">'+
      '<button type="button" class="arv-sub-back" data-action="back" aria-label="戻る">‹</button>'+
      '<div class="smart-head-copy smart-head-copy-clean"><strong>'+esc(String(title||'').replace(/^本日の/,''))+'</strong></div>'+
      '<label class="arv-sub-date"><span>'+esc(state.date.replace(/-/g,'/'))+'</span>'+
      '<input type="date" id="date" value="'+esc(state.date)+'" aria-label="厳選・特別・AI成績の表示日を変更"></label>'+
      '<button type="button" class="arv-sub-close" data-home-close="1" aria-label="トップへ戻る">×</button>'+
      '</header>'
  }
  return '<header class="smart-topbar smart-topbar-clean smart-section-topbar">'+
    '<span class="smart-pull-space" aria-hidden="true"></span>'+ 
    '<div class="smart-head-copy smart-head-copy-clean"><strong>'+esc(title||'開催場')+'</strong><small>'+esc(sub||'')+'</small></div>'+ 
    (back?'<button class="smart-section-close" data-action="back" aria-label="トップへ戻る">×</button>':'<span class="smart-back-space"></span>')+
  '</header>'
}
function smartRaceTopBar(r){
  var rows=(state.races||[]).filter(function(x){return x&&r&&x.circuit===r.circuit&&x.track===r.track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),idx=-1;
  for(var i=0;i<rows.length;i++){if(String(rows[i].id)===String(r.id)){idx=i;break}}
  var prev=idx>0?rows[idx-1]:null,next=idx>=0&&idx<rows.length-1?rows[idx+1]:null;
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar">'+
    '<span class="smart-pull-space" aria-hidden="true"></span>'+ 
    (prev?'<button class="smart-race-step prev" data-race="'+esc(prev.id)+'" data-preserve-panel="1" aria-label="前のレース">&lt;</button>':'<button class="smart-race-step prev" disabled>&lt;</button>')+
    '<div class="smart-head-copy smart-head-copy-clean smart-race-head-copy"><strong>'+esc(r.track)+' '+esc(r.raceNumber)+'R</strong></div>'+ 
    (next?'<button class="smart-race-step next" data-race="'+esc(next.id)+'" data-preserve-panel="1" aria-label="次のレース">&gt;</button>':'<button class="smart-race-step next" disabled>&gt;</button>')+
    '<button class="smart-race-close" data-action="back" aria-label="開催場のレース一覧へ戻る">×</button>'+ 
  '</header>'
}
function smartPageControls(){return ''}
function smartVenueGroup(circuit,label){
  var rows=state.races.filter(function(x){return x.circuit===circuit}),
      tracks=[],seen={},waiting=!rows.length&&state.loading,
      countText=waiting?'準備中':rows.length+'レース';
  rows.forEach(function(r){
    var t=String(r.track||'');
    if(t&&!seen[t]){seen[t]=1;tracks.push(t)}
  });
  tracks.sort(function(a,b){return a.localeCompare(b,'ja')});
  var progress=state.bootstrapProgress||{},waitText='全レースデータを読み込み中';
  if(waiting&&n(progress.total)>0)waitText+='　'+n(progress.ready)+' / '+n(progress.total);
  return '<section class="smart-section smart-group-section">'+
    '<div class="smart-section-title smart-group-title"><div><b>'+esc(label)+'</b><small>開催場</small></div><span>'+esc(countText)+'</span></div>'+
    '<div class="smart-venue-grid">'+
      (tracks.length?tracks.map(function(track){
        var rs=rows.filter(function(x){return x.track===track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),
            first=rs[0],last=rs[rs.length-1];
        return '<button class="smart-venue-card smart-venue-card-one" data-track="'+esc(track)+'" data-circuit="'+esc(circuit)+'">'+
          '<span class="smart-venue-mark">'+esc(track.slice(0,1))+'</span>'+
          '<span class="smart-venue-name"><b>'+esc(track)+'</b></span>'+
          '<span class="smart-venue-count">'+rs.length+'レース</span>'+
          '<span class="smart-venue-times"><small>'+(first?timeHtml(first):'--:--')+'</small><i>–</i><small>'+(last?timeHtml(last):'--:--')+'</small></span>'+
          '<span class="smart-chevron">›</span>'+
        '</button>'
      }).join(''):(waiting?'<div class="smart-empty">'+esc(waitText)+'</div>':'<div class="smart-empty">本日の開催情報はまだありません</div>'))+
    '</div>'+
  '</section>'
}
function smartVenueCards(){
  var hasCentral=state.races.some(function(x){return x.circuit==='中央'}),
      hasLocal=state.races.some(function(x){return x.circuit==='地方'}),html='';
  if(hasCentral)html+=smartVenueGroup('中央','中央');
  if(hasLocal)html+=smartVenueGroup('地方','地方');
  if(!html)html='<div class="smart-empty">開催場データを準備中です</div>';
  return '<div class="smart-home-list-heading"><b>開催場の一覧</b></div><div class="smart-group-wrap">'+html+'</div>'
}

function aiStoredMarks(detail){
  // Only verifiable pre-off snapshots count. Live horse evaluation is not evidence.
  var server=authorizedPreOffMarks(detail),saved=[];
  if(server)saved=server.horses.map(function(x){return {no:n(x.horseNumber),mark:String(x.mark||''),p:n(x.decisionProbability,0),confidence:n(server.winnerConfidence,0)}});
  else if(local){
    var off=Date.parse(String(detail.date||'')+'T'+String(detail.scheduledStartTime||detail.startTime||'').slice(0,5)+':00+09:00'),at=Date.parse(String(local.fixedAt||''));
    if(isFinite(off)&&isFinite(at)&&at<off)saved=local.marks.map(function(x){return {no:n(x.no),mark:String(x.mark||''),p:0,confidence:0}});
  }
  return saved.filter(function(x){return x.no>0})
}
function aiDailyOne(detail){
  if(!detail||!isFinal(detail))return null;
  var fs=((detail.result||{}).finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)}).slice(0,3),
      nums=fs.map(function(x){return n(x.horseNumber)});
  if(fs.map(function(x){return n(x.finish)}).join(',')!=='1,2,3'||nums.some(function(v){return v<1})||new Set(nums).size!==3)return null;
  var marks=aiStoredMarks(detail);if(!marks.length)return null;
  var hon=marks.find(function(x){return x.mark==='◎'}),marked={};marks.forEach(function(x){if(['◎','○','▲','☆+','☆','△','注'].indexOf(x.mark)>=0)marked[x.no]=x.mark});
  var winner=nums[0],podium={},markedCount=nums.filter(function(no){return !!marked[no]}).length;
  nums.forEach(function(no){podium[no]=1});
  var honPlaceHit=!!(hon&&podium[hon.no]),winHit=!!(hon&&hon.no===winner),markHit=!!marked[winner],fullPodiumHit=markedCount===3,
      frozenBet=frozenAiBetForRace(detail),triItems=((frozenBet&&frozenBet.items)||[]).filter(function(x){return x.kind==='3連単'&&Array.isArray(x.combos)&&x.combos.length>0}),
      triEligible=triItems.length>0,triHit=triItems.some(function(x){return betItemHit(x,nums)}),
      ranked=marks.filter(function(x){return n(x.p,0)>0}).slice().sort(function(a,b){return n(b.p)-n(a.p)}),
      wr=ranked.findIndex(function(x){return x.no===winner})+1;
  return {raceId:String(detail.id||''),track:String(detail.track||''),raceNumber:n(detail.raceNumber),title:String(detail.title||''),circuit:String(detail.circuit||''),
    winHit:winHit,honPlaceHit:honPlaceHit,honEligible:!!hon,markHit:markHit,fullPodiumHit:fullPodiumHit,triEligible:triEligible,triHit:triHit,
    markedPodiumCount:markedCount,holePlace:marks.some(function(x){return ['☆','☆+','注'].indexOf(x.mark)>=0&&podium[x.no]}),
    top2:wr>0&&wr<=2,top3:wr>0&&wr<=3,candidateOrderMiss:!winHit&&markHit,candidateMiss:!markHit,
    highConf:!!(hon&&hon.confidence>=.70),highConfHit:!!(hon&&hon.confidence>=.70&&winHit),brier:0,logLoss:0,
    reason:winHit?'◎1着':(markHit?'印内の1着順位':'1着候補外'),
    winner:winner,winnerMark:String(marked[winner]||''),podiumNos:nums,marks:marks.filter(function(x){return !!x.mark}).map(function(x){return {no:x.no,mark:x.mark}}),
    hasMarks:true,resultReady:true,eligible:true,betSaved:!!frozenBet}
}
function resetDailyAiStats(date){dailyAiStats={date:date||'',loading:false,done:false,total:0,finalCount:0,winHits:0,honPlaceHits:0,triHits:0,triTotal:0,markHits:0,fullPodiumHits:0,centralPodiumHits:0,centralPodiumTotal:0,localPodiumHits:0,localPodiumTotal:0,markedPodiumSum:0,holePlaceHits:0,top2Hits:0,top3Hits:0,candidateOrderMisses:0,candidateMisses:0,highConfHits:0,highConfTotal:0,brierSum:0,logLossSum:0,reasons:{},rows:[],error:''}}
function scheduleDailyAiStats(){
  if(dailyAiStats.date!==state.date)resetDailyAiStats(state.date);
  if(dailyAiStats.loading)return;
  var targetDate=state.date,dayRaces=(state.races||[]).filter(function(r){return r&&r.id});
  var finals=dayRaces.filter(function(r){return isFinal(r)});
  if(!finals.length){dailyAiStats.done=false;dailyAiStats.total=0;dailyAiStats.finalCount=0;return}
  if(dailyAiStats.done&&dailyAiStats.finalCount===finals.length)return;
  var token=++dailyAiStatsJob,cursor=0,results=[];dailyAiStats.loading=true;dailyAiStats.done=false;dailyAiStats.error='';
  render();
  function worker(){
    if(token!==dailyAiStatsJob||cursor>=finals.length)return Promise.resolve();
    var row=finals[cursor++];
    return fetchEdgeRace(row.id,false).then(function(d){
      var z=aiDailyOne(d);
      if(z){
        z.hasMarks=true;z.resultReady=true;z.loadError=false;results.push(z)
      }else{
        var fs=(d&&d.result&&d.result.finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)}),marks=aiStoredMarks(d||{});
        results.push({raceId:String(row.id||''),track:String((d&&d.track)||row.track||''),raceNumber:n((d&&d.raceNumber)||row.raceNumber),title:String((d&&d.title)||row.title||''),circuit:String((d&&d.circuit)||row.circuit||''),winHit:false,markHit:false,fullPodiumHit:false,markedPodiumCount:0,holePlace:false,top2:false,top3:false,candidateOrderMiss:false,candidateMiss:!marks.length,highConf:false,highConfHit:false,brier:0,logLoss:0,reason:marks.length?'結果未取得':'発走前予想未保存',winner:n(fs[0]&&fs[0].horseNumber),winnerMark:'',podiumNos:fs.slice(0,3).map(function(x){return n(x.horseNumber)}).filter(function(x){return x>0}),marks:marks.filter(function(x){return !!String(x.mark||'')}).map(function(x){return{no:x.no,mark:x.mark}}),hasMarks:marks.length>0,resultReady:fs.some(function(x){return n(x.finish)===3}),eligible:false,triEligible:false,triHit:false,loadError:false})
      }
    }).catch(function(){
      results.push({raceId:String(row.id||''),track:String(row.track||''),raceNumber:n(row.raceNumber),title:String(row.title||''),circuit:String(row.circuit||''),marks:[],podiumNos:[],winHit:false,markHit:false,fullPodiumHit:false,markedPodiumCount:0,hasMarks:false,resultReady:false,eligible:false,triEligible:false,triHit:false,loadError:true})
    }).then(worker)
  }
  Promise.all([worker(),worker()]).then(function(){
    if(token!==dailyAiStatsJob||state.date!==targetDate)return;
    results.sort(function(a,b){var c=String(a.circuit||'').localeCompare(String(b.circuit||''),'ja');if(c)return c;var t=String(a.track||'').localeCompare(String(b.track||''),'ja');return t||n(a.raceNumber)-n(b.raceNumber)});
    dailyAiStats.loading=false;dailyAiStats.done=true;dailyAiStats.rows=results;dailyAiStats.total=results.filter(function(x){return x.eligible}).length;dailyAiStats.finalCount=finals.length;
    dailyAiStats.honPlaceHits=results.filter(function(x){return x.eligible&&x.honPlaceHit}).length;
    dailyAiStats.triTotal=results.filter(function(x){return x.eligible&&x.triEligible}).length;
    dailyAiStats.triHits=results.filter(function(x){return x.eligible&&x.triEligible&&x.triHit}).length;
    dailyAiStats.winHits=results.filter(function(x){return x.winHit}).length;
    dailyAiStats.markHits=results.filter(function(x){return x.markHit}).length;
    dailyAiStats.fullPodiumHits=results.filter(function(x){return x.fullPodiumHit}).length;
    dailyAiStats.markedPodiumSum=results.reduce(function(a,x){return a+n(x.markedPodiumCount)},0);
    dailyAiStats.centralPodiumTotal=results.filter(function(x){return x.circuit==='中央'}).length;dailyAiStats.centralPodiumHits=results.filter(function(x){return x.circuit==='中央'&&x.fullPodiumHit}).length;
    dailyAiStats.localPodiumTotal=results.filter(function(x){return x.circuit==='地方'}).length;dailyAiStats.localPodiumHits=results.filter(function(x){return x.circuit==='地方'&&x.fullPodiumHit}).length;
    dailyAiStats.holePlaceHits=results.filter(function(x){return x.holePlace}).length;
    dailyAiStats.top2Hits=results.filter(function(x){return x.top2}).length;
    dailyAiStats.top3Hits=results.filter(function(x){return x.top3}).length;
    dailyAiStats.candidateOrderMisses=results.filter(function(x){return x.candidateOrderMiss}).length;
    dailyAiStats.candidateMisses=results.filter(function(x){return x.candidateMiss}).length;
    dailyAiStats.highConfTotal=results.filter(function(x){return x.highConf}).length;
    dailyAiStats.highConfHits=results.filter(function(x){return x.highConfHit}).length;
    dailyAiStats.brierSum=results.reduce(function(a,x){return a+n(x.brier)},0);dailyAiStats.logLossSum=results.reduce(function(a,x){return a+n(x.logLoss)},0);
    dailyAiStats.reasons={};results.forEach(function(x){if(x.winHit)return;var k=x.reason||'その他';dailyAiStats.reasons[k]=(dailyAiStats.reasons[k]||0)+1});
    render()
  }).catch(function(){if(token!==dailyAiStatsJob)return;dailyAiStats.loading=false;dailyAiStats.done=true;dailyAiStats.error='集計できませんでした';render()})
}

function resetPreviousAiStats(date){previousAiStats={date:date||'',loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,markedPodiumSum:0,rows:[],error:''}}
function schedulePreviousAiStats(){
  var targetDate=previousDateKey(today());
  if(!targetDate)return;
  if(previousAiStats.date!==targetDate)resetPreviousAiStats(targetDate);
  if(previousAiStats.loading||previousAiStats.done)return;
  // Race opening/current-day preload always has priority over yesterday's audit.
  if(state.raceLoading||state.race||state.track||state.picker)return;
  if(state.date===today()&&!selectedRacePreload.fullLoaded){
    setTimeout(function(){if(!previousAiStats.done&&!previousAiStats.loading)schedulePreviousAiStats()},2500);
    return
  }
  var token=++previousAiStatsJob;previousAiStats.loading=true;previousAiStats.error='';render();
  edgeFetchJson('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+encodeURIComponent(targetDate)+'&details=0&t='+Date.now(),9000)
    .then(function(body){
      if(token!==previousAiStatsJob)return null;
      var rows=Array.isArray(body)?body:((body&&body.races)||[]);
      rows=rows.filter(function(r){return r&&r.id});
      previousAiStats.finalCount=rows.length;
      var cursor=0,results=rows.map(function(row){
        return {
          raceId:String(row.id||''),track:String(row.track||''),raceNumber:n(row.raceNumber),
          title:String(row.title||''),circuit:String(row.circuit||''),marks:[],podiumNos:[],
          winHit:false,markHit:false,fullPodiumHit:false,markedPodiumCount:0,
          hasMarks:false,resultReady:false,loadError:false
        }
      }),workers=[];
      function worker(){
        if(token!==previousAiStatsJob||cursor>=rows.length)return Promise.resolve();
        var idx=cursor++,row=rows[idx],id=String(row.id||'');
        return edgeFetchJson(edgeRaceUrl(id),9000)
          .then(function(body){
            var d=body&&body.detail?body.detail:null;
            if(!d){results[idx].loadError=true;return}
            if(!d.track)d.track=row.track;if(!d.raceNumber)d.raceNumber=row.raceNumber;if(!d.title)d.title=row.title;if(!d.circuit)d.circuit=row.circuit;
            var finishers=(d.result&&d.result.finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});
            results[idx].resultReady=finishers.length>0;
            results[idx].podiumNos=finishers.slice(0,3).map(function(x){return n(x.horseNumber)}).filter(function(x){return x>0});
            var marks=aiStoredMarks(d);
            results[idx].hasMarks=marks.length>0;
            results[idx].marks=marks.filter(function(x){return !!String(x.mark||'')}).map(function(x){return{no:x.no,mark:x.mark}});
            var z=aiDailyOne(d);
            if(z){
              z.hasMarks=true;z.resultReady=results[idx].resultReady;z.loadError=false;
              results[idx]=z
            }
          })
          .catch(function(){results[idx].loadError=true})
          .then(worker)
      }
      // Keep yesterday's audit strictly low priority: one request at a time.
      if(rows.length)workers.push(worker());
      return Promise.all(workers).then(function(){return results})
    })
    .then(function(results){
      if(token!==previousAiStatsJob||!results)return;
      results.sort(function(a,b){var c=String(a.circuit||'').localeCompare(String(b.circuit||''),'ja');if(c)return c;var t=String(a.track||'').localeCompare(String(b.track||''),'ja');return t||n(a.raceNumber)-n(b.raceNumber)});
      previousAiStats.loading=false;previousAiStats.done=true;previousAiStats.rows=results;previousAiStats.total=results.length;
      previousAiStats.winHits=results.filter(function(x){return x.winHit}).length;
      previousAiStats.markHits=results.filter(function(x){return x.markHit}).length;
      previousAiStats.fullPodiumHits=results.filter(function(x){return x.fullPodiumHit}).length;
      previousAiStats.markedPodiumSum=results.reduce(function(a,x){return a+n(x.markedPodiumCount)},0);
      render()
    })
    .catch(function(err){
      if(token!==previousAiStatsJob)return;
      previousAiStats.loading=false;previousAiStats.done=true;previousAiStats.error=String(err&&err.message||'前日AI成績を取得できませんでした');render()
    })
}
function smartPreviousAiStats(){
  var s=previousAiStats,date=s.date||previousDateKey(today()),p=String(date||'').split('-'),label=(n(p[1])&&n(p[2]))?(n(p[1])+'月'+n(p[2])+'日'):'前日';
  if(!s.done&&!s.loading){setTimeout(schedulePreviousAiStats,0);return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日のAI成績</b><small>全レース集計準備中</small></div></section>'}
  if(s.loading)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>前日の全レースを集計中…</small></div></section>';
  if(s.error)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>'+esc(s.error)+'</small></div></section>';
  if(!s.total)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>前日のレースデータなし</small></div></section>';
  function rate(hit){return Math.round(hit/s.total*100)}
  function markText(row){var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};var txt=(row.marks||[]).slice().sort(function(a,b){return n(order[a.mark],99)-n(order[b.mark],99)||n(a.no)-n(b.no)}).map(function(x){return x.mark+x.no}).join(' ');return txt||'印なし'}
  var rows=(s.rows||[]).map(function(x){
    var result=(x.podiumNos||[]).slice(0,3).join('-')||'—',cls=x.fullPodiumHit?'hit':(x.markHit?'partial':'miss'),judge;
    if(x.loadError)judge='詳細取得失敗';
    else if(!x.resultReady)judge='結果未取得';
    else if(!x.hasMarks)judge='印なし';
    else judge=x.fullPodiumHit?'3頭完全':(x.markHit?'1着印内':'1着印外');
    return '<div class="smart-ai-race-row '+cls+'"><span class="smart-ai-race-name"><b>'+esc(x.track)+' '+esc(x.raceNumber)+'R</b><small>'+esc(x.title||'')+'</small></span><span class="smart-ai-race-marks">'+esc(markText(x))+'</span><span class="smart-ai-race-result">結果 '+esc(result)+'</span><strong>'+esc(judge)+'</strong></div>'
  }).join('');
  return '<section class="smart-ai-daily smart-ai-previous"><div class="smart-ai-daily-head"><b>前日 '+esc(label)+' のAI成績</b><small>前日の全'+s.total+'レース</small></div><div class="smart-ai-daily-grid">'+
    '<div><small>AI印内1着</small><strong>'+rate(s.markHits)+'%</strong><em>'+s.markHits+'/'+s.total+'</em></div>'+
    '<div><small>◎1着</small><strong>'+rate(s.winHits)+'%</strong><em>'+s.winHits+'/'+s.total+'</em></div>'+
    '<div><small>印内3頭完全</small><strong>'+rate(s.fullPodiumHits)+'%</strong><em>'+s.fullPodiumHits+'/'+s.total+'</em></div>'+
  '</div><div class="smart-ai-race-list">'+rows+'</div><p>※分母は前日の全レース。事前AI印が無いレースも除外せず「印なし」として表示します。</p></section>'
}
function aiStatsDayTitle(){
  if(state.date===today())return '本日のAI成績';
  var p=String(state.date||'').split('-'),m=n(p[1]),d=n(p[2]);
  return (m&&d)?(m+'月'+d+'日のAI成績'):'当日のAI成績'
}

var selectedRacePreload={date:'',busy:{},done:{},timer:null,fullLoaded:false,fullLoading:false,loadedCount:0,expectedCount:0,lastError:''},fastTopRefresh=null,selectedSectionsOpen={selected:false},selectedCircuitSectionsOpen={selected:{'中央':false,'地方':false}};
function selectedRaceLoadStatus(){
  var expected=n(selectedRacePreload.expectedCount,0)||(state.races||[]).filter(function(r){return r&&r.id}).length,loaded=n(selectedRacePreload.loadedCount,0);
  return{expected:expected,loaded:loaded,complete:!!selectedRacePreload.fullLoaded,loading:!!selectedRacePreload.fullLoading,error:selectedRacePreload.lastError||''}
}
function raceIsGraded(r){
  if(!r)return false;
  if(r.isGraded===true||r.graded===true||r.isGradeRace===true||r.gradeRace===true)return true;
  var t=String(r.title||''),meta=[r.grade,r.gradeLabel,r.raceGrade,r.gradeCode,r.raceClass,r.className,r.category].map(function(v){return String(v||'')}).join(' '),s=t+' '+meta,grade='(?:[ⅠⅡⅢ]|I{1,3}|[123])';
  if(new RegExp('(?:Jpn\\s*)?G\\s*'+grade+'|(?:Jpn\\s*)'+grade+'|(?:^|[\\s（(\\[])(?:S|H|M|SP)\\s*'+grade+'(?:$|[\\s）)\\]])|重賞|賞\\s*[（(]重賞[）)]','i').test(s))return true;
  return /(?:ダービー|優駿|グランプリ)(?:$|[（(])/i.test(t)
}
function mandatoryTrifectaRace(r){
  var title=String(r&&r.title||'');
  return !!(r&&(raceIsGraded(r)||(String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))))
}
// Only the independent strategy decides whether the reviewed 3連単 is adopted.
function markMandatoryTrifectaReview(plan,r){
  if(plan&&mandatoryTrifectaRace(r))plan.mandatoryTrifectaReviewed=plan.trifectaReviewed===true;
  return plan
}
function explicitSelectedRace(r){return !!(r&&(r.arvexqSelected||r.selectedRace||r.isSelected||r.recommendedRace||r.aiSelected))}
function mainRaceForTrack(rows){
  rows=(rows||[]).filter(function(r){return r&&r.id}).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;
  var explicit=rows.find(function(r){var role=String(r.raceRole||r.role||r.raceType||'').toLowerCase();return r.isMain===true||r.mainRace===true||role==='main'||role==='mainrace'||/メイン/.test(String(r.title||''))});if(explicit)return explicit;
  var featured=rows.find(function(r){return r.featured===true});if(featured)return featured;
  var r11=rows.find(function(r){return n(r.raceNumber)===11});if(r11)return r11;
  return rows[rows.length-1]
}
function isMainForecastRace(r){
  if(!r||!r.id)return false;
  var circuit=String(r.circuit||''),track=String(r.track||''),rows=(state.races||[]).filter(function(z){
    if(!z||!z.id||String(z.track||'')!==track)return false;
    return !circuit||!z.circuit||String(z.circuit||'')===circuit
  }),main=mainRaceForTrack(rows);
  return !!(main&&String(main.id)===String(r.id))
}
function kochiFinalRace(rows){rows=(rows||[]).filter(function(r){return r.track==='高知'}).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;return rows.find(function(r){return /ファイナル/i.test(String(r.title||''))})||rows[rows.length-1]}
function raceChronologicalCompare(a,b){
  var ra=(a&&a.race)||a||{},rb=(b&&b.race)||b||{},ta=mins(ra.startTime),tb=mins(rb.startTime);
  if(ta!==tb)return ta-tb;
  var tc=String(ra.track||'').localeCompare(String(rb.track||''),'ja');if(tc)return tc;
  return n(ra.raceNumber)-n(rb.raceNumber)
}
// Strict selection is performed in strictSelectedRaceProfile; there is no top-1 cap.
function eliteSelectedRaceCut(rows){
 if(!window.ARVEXQMorningSelection||!window.ARVEXQMorningSelection.allStrictQualifiers)
   throw Error('morning selection module missing; refuse an incomplete morning freeze');
 return window.ARVEXQMorningSelection.allStrictQualifiers(rows,{n:n,chronological:raceChronologicalCompare});
}
function computeMorningRaceCandidates(circuit){
 if(!window.ARVEXQSelectedRacePipeline)throw Error('morning selector module missing');
 return window.ARVEXQSelectedRacePipeline.select(
  (state.races||[]).filter(function(r){return r&&r.id&&(!circuit||String(r.circuit||'')===String(circuit))}),
  {getDetail:function(r){return instantTrackDetails[String(r.id)]||loadDetailCache(r.id)},
   isFinal:isFinal,isScratch:isScratchHorse,predict:predict,
   evaluateQuality:strictSelectedRaceProfile,makeTicket:buildAiBetPlan,
   lanes:window.ARVEXQMorningTicketLanes,evidence:window.ARVEXQMorningEvidence,
   cut:eliteSelectedRaceCut,warn:function(){console.warn.apply(console,arguments)}})
}
function morningPickOf(r){
  if(!r)return null;
  var v=r.volatility&&r.volatility.morningPicks,
      e=r.environmentMeta&&r.environmentMeta.morningPicks,
      m=v&&v.version==='v1'&&v.fixedAt?v:(e&&e.version==='v1'&&e.fixedAt?e:null);
  if(m)return m;
  if(r.morningPickVersion==='v1'&&r.morningPickFixedAt)return {
    version:'v1',fixedAt:String(r.morningPickFixedAt),
    selected:r.morningSelected===true,selectedScore:n(r.morningSelectedScore,0),
    special:r.morningSpecial===true,scope:n(r.morningPickScope,0),assessed:r.morningAssessed!==false,
    selectionModelVersion:String(r.morningSelectionModelVersion||''),
     primaryType:String(r.morningPrimaryType||''),types:Array.isArray(r.morningSelectedTypes)?r.morningSelectedTypes.slice():[],
     selectionReason:String(r.morningSelectionReason||''),
     ticketKinds:Array.isArray(r.morningTicketKinds)?r.morningTicketKinds.slice():[],
     ticketEvidence:r.morningTicketEvidence||null
  };
  return null
}
function morningPickReady(){
  return (state.races||[]).some(function(r){return !!morningPickOf(r)})
}
function morningPublicStatus(r){
  var m=morningPickOf(r),mod=window.ARVEXQMorningTicketLanes,
      receipt=window.ARVEXQMorningEvidence;
  var status=mod&&mod.selectionDisplayStatus?mod.selectionDisplayStatus(m,r):'unavailable';
  if(status!=='actionable')return status;
  // A frozen ticket kind without actual horse-number combinations is
  // an unverified historic selection, not a purchasable recommendation.
  if(!receipt||typeof receipt.verify!=='function'||
     !receipt.verify(r,m&&m.ticketEvidence)||!m.ticketEvidence||
     (m.ticketKinds||[]).slice().sort().join('|')!==
       (m.ticketEvidence.ticketKinds||[]).slice().sort().join('|'))
    return 'ticket-original-missing';
  return 'actionable'
}
function selectedRaceCandidates(circuit){
  // Published free selections require a frozen ticket-backed type.
  return (state.races||[]).filter(function(r){
    var m=morningPickOf(r);
    return !!(r&&r.id&&m&&morningPublicStatus(r)==='actionable'&&String(m.selectionModelVersion||'')==='arvexq-empirical-ticket-hit-v1'&&
      String(m.primaryType||'')==='的中重視型'&&Array.isArray(m.types)&&m.types.includes('的中重視型')&&
      (!circuit||String(r.circuit||'')===String(circuit)))
  }).map(function(r){
    var m=morningPickOf(r);
    return {race:r,tags:['厳選'],selection:{
      selected:true,score:n(m&&m.selectedScore,0),
      reason:String(m&&m.selectionReason||'朝の事前選定固定'),
       primaryType:String(m&&m.primaryType||''),types:Array.isArray(m&&m.types)?m.types.slice():[],
       fixedAt:String(m&&m.fixedAt||''),
       ticketKinds:Array.isArray(m&&m.ticketKinds)?m.ticketKinds.slice():[],
       noAxis:!!(m&&m.ticketEvidence&&m.ticketEvidence.axisStatus==='no-axis')
    }}
  }).sort(raceChronologicalCompare)
}
function expectedValueRaceProfile(r,p){
  var rows=(p&&p.rows||[]).slice(),field=rows.length,cov=n(p&&p.coverage,0),uniform=1/Math.max(1,field),ready=dataReadinessProfile(r,p),strict=strictSelectedRaceProfile(r,p),method=arvexqRacePolicy(r),vg=method.value;
  if(!strict.selected)return{selected:false,score:0,reason:'厳選品質ゲート未通過',readiness:ready,selection:strict,model:method.id};
  if(field<5||cov<vg.cov||ready.prediction<vg.ready)return{selected:false,score:0,reason:'予想データ不足',readiness:ready,selection:strict,model:method.id};
  var actual=rows.filter(function(x){var h=x.horse||{};return n(h.winOdds)>1&&!h.oddsForecast&&!/予想|forecast/i.test(String(h.oddsSource||''))}),need=Math.max(4,Math.ceil(field*vg.oddsCoverage));
  if(actual.length<need)return{selected:false,score:0,reason:'実オッズ待ち',mode:'actual',readiness:ready,selection:strict,model:method.id};
  var candidates=rows.map(function(x){
    var h=x.horse||{},odds=n(h.winOdds,0),forecast=!!h.oddsForecast||/予想|forecast/i.test(String(h.oddsSource||'')),pwin=n(x.evWinProbability,n(x.winnerDecisionProbability,n(x.p1Probability,0))),ev=odds>1?pwin*odds:0,
        kelly=(odds>1&&ev>1)?(ev-1)/(odds-1):0,edge=n(x.edgeScore,0),evidence=n(x.edgeEvidence,0),rank=n(x.winnerDecisionRank,n(x.winnerConsensusRank,n(x.winRank,999)));
    return{x:x,odds:odds,pwin:pwin,ev:ev,kelly:kelly,edge:edge,evidence:evidence,rank:rank,forecast:forecast}
  }).filter(function(z){return !z.forecast&&z.odds>1&&z.ev>=vg.ev&&z.edge>=vg.edge&&z.evidence>=vg.evidence&&z.kelly>=vg.kelly&&z.pwin>=Math.max(.055,uniform*.72)&&z.rank<=2}).sort(function(a,b){return b.ev-a.ev||b.kelly-a.kelly||b.edge-a.edge||b.pwin-a.pwin});
  if(!candidates.length)return{selected:false,score:0,reason:'実オッズ期待値基準未達',mode:'actual',readiness:ready,selection:strict,model:method.id};
  var best=candidates[0],evEdge=best.ev-1,score=Math.round(clamp(clamp(evEdge/.65,0,1)*.40+clamp((best.edge-60)/32,0,1)*.21+best.evidence*.15+ready.market*.12+clamp(best.kelly/.10,0,1)*.08+clamp(best.pwin/Math.max(uniform*2,.12),0,1)*.04,0,1)*100),selected=score>=vg.score;
  return{selected:selected,score:score,horse:best.x.horse,horseNo:n(best.x.horse&&best.x.horse.horseNumber),horseName:String(best.x.horse&&best.x.horse.name||''),odds:best.odds,pwin:best.pwin,ev:best.ev,kelly:best.kelly,riskFraction:Math.min(.02,best.kelly*.20),edge:best.edge,evidence:best.evidence,coverage:cov,mode:'actual',readiness:ready,selection:strict,reason:selected?'買い目品質ゲート通過':'買い目品質スコア不足',model:method.id+'-actual-odds'}
}
function fixedPickLoadStatus(circuit){
  var rows=(state.races||[]).filter(function(r){return r&&r.id&&String(r.circuit||'')===String(circuit)}),loaded=0;
  rows.forEach(function(r){var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id);if(d&&raceDisplayCoreReady(d,r||d))loaded++});
  return{expected:rows.length,loaded:loaded,complete:rows.length?loaded>=rows.length:selectedRaceLoadStatus().complete,partial:loaded>0}
}
function fixedPickEmpty(kind,circuit){
  if(!morningPickReady())return '<div class="fixed-pick-empty"><b>朝の選定未確定</b><small>全レースを朝に一度だけ判定。発走後に選定を追加しません。</small></div>';
  var st=fixedPickLoadStatus(circuit),label='厳選判定';
  // Missing late detail data must not change the already published morning list.
  var incomplete=(state.races||[]).filter(function(r){return r&&String(r.circuit||'')===String(circuit)&&morningPickOf(r)&&morningPickOf(r).assessed===false}).length;
  return '<div class="fixed-pick-empty"><b>該当なし</b><small>'+(incomplete?('基準を満たす確定候補なし｜情報不足 '+incomplete+'レース（朝の未判定を後付けしません）'):(label+'基準を通過したレースなし'))+'</small></div>'
}
function fixedSelectedBox(circuit,picks){
  var body=picks.length?picks.map(function(z){var r=z.race,t=z.selection||{};return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small><small>'+esc(t.reason||'朝に選定・固定')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+esc(t.primaryType||'厳選')+(t.noAxis?'｜軸なし・相手上位評価':'')+'｜'+esc(t.score||'—')+'点</em></button>'}).join(''):fixedPickEmpty('selected',circuit),open=!!(selectedCircuitSectionsOpen.selected&&selectedCircuitSectionsOpen.selected[circuit]);
  return '<details class="fixed-pick-box fixed-pick-circuit" data-selected-circuit="selected" data-pick-circuit="'+esc(circuit)+'" '+(open?'open':'')+'><summary class="fixed-pick-box-head"><b>'+esc(circuit)+'</b><span class="fixed-pick-summary-right"><em>'+picks.length+'レース</em><i>⌄</i></span></summary><div class="fixed-pick-box-body">'+body+'</div></details>'
}
function selectedRaceBetPreview(r){
  var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id),st=mins(r.startTime),started=r.date===today()&&st<9999&&nowMins()>=st,
      source=mergeRaceReflection(r,d,null,null),plan=frozenAiBetForRace(source),p=null;
  if(plan)plan=immutableStoredAiBetView(source,plan);
  if(d&&!plan&&!isFinal(d)&&!started){try{p=predict(d);plan=buildAiBetPlan(d,p)}catch(e){}}
  if(!plan)return '<div class="selected-bet-pending">発走前の馬番入り買い目原本が未保存・未取得です。結果から作り直しません。</div>';
  if(plan.decision==='見送り')return '<div class="selected-bet-pending">ARVEXQ買い目　見送り（'+esc(plan.betQuality||0)+'/100）</div>';
  var lines=(plan.items||[]).map(function(z){return '<span class="selected-bet-chip '+(z.level==='3連単チャレンジ'?'tri':'')+'"><b>'+esc(z.level)+'</b> '+esc(z.kind)+' '+esc(z.combo)+'</span>'}).join('');if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines+='<span class="selected-bet-chip tri"><b>3連単</b> 検討済み・見送り</span>';
  var result='';if(d&&isFinal(d)){var hit=aiBetPlanHit(d,plan),lv=hit&&hit.levels||{},hits=[];['本線','保険'].forEach(function(k){if(lv[k])hits.push(k+'HIT')});result='<div class="selected-result '+(hit&&hit.hit?'hit':'miss')+'">結果　'+(hits.length?hits.join(' / '):'通常買い目不的中')+(hit&&hit.tri?'　<strong>3連単HIT</strong>':'')+'</div>'}
  return '<div class="selected-bets">'+lines+'</div>'+result
}
function smartSelectedRaces(forceOpen){
  var central=selectedRaceCandidates('中央'),local=selectedRaceCandidates('地方'),open=forceOpen?true:!!selectedSectionsOpen.selected,total=central.length+local.length;
  return '<details class="smart-fixed-picks" data-selected-section="selected" '+(open?'open':'')+'><summary class="smart-fixed-picks-head"><span><b>厳選レース</b><small>朝固定・券種別／点数別の実測的中率80%以上（検証不足は厳選対象外）</small></span><span class="smart-fixed-summary-right"><em>'+total+'レース</em><i>⌄</i></span></summary><div class="smart-fixed-pick-grid">'+fixedSelectedBox('中央',central)+fixedSelectedBox('地方',local)+'</div></details>'
}
function computeMorningSpecialRaceCandidates(){
 if(!window.ARVEXQSpecialSelection)throw Error('special selection module missing');
 return window.ARVEXQSpecialSelection.select(state.races||[]);
}
function specialForecastRaceCandidates(){
  // Selection membership is frozen once; live results and names do not add races.
  return (state.races||[]).filter(function(r){
    var m=morningPickOf(r);
    return !!(r&&r.id&&m&&m.special===true)
  }).slice().sort(raceChronologicalCompare)
}
function specialForecastRaceTag(r){
  var title=String(r&&r.title||'');
  if(raceIsGraded(r))return '重賞';
  if(String(r&&r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r&&r.raceNumber)===12))return '高知ファイナル';
  if(isMainForecastRace(r))return 'メイン';
  return '特別'
}
function prebuildSpecialForecastPlans(){
  var picks=specialForecastRaceCandidates();
  picks.forEach(function(r){
    var id=String(r&&r.id||''),detail=id?(instantTrackDetails[id]||loadDetailCache(id)):null;
    if(!detail||isFinal(detail))return;
    var st=mins(detail.startTime||r.startTime),started=(detail.date||r.date)===today()&&st<9999&&nowMins()>=st;
    if(started)return;
    try{var p=predict(detail);buildAiBetPlan(detail,p)}catch(e){}
  })
}
function smartSpecialForecastRaces(forceOpen){
  if(typeof state.specialForecastOpen!=='boolean'){
    try{state.specialForecastOpen=localStorage.getItem('arvexq-special-forecast-open')!=='0'}catch(e){state.specialForecastOpen=true}
  }
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=specialForecastRaceTag(r);
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日のメイン・重賞・高知ファイナルなし</small></div>';
  return '<details class="smart-fixed-picks smart-special-picks" data-special-fold="1"'+((forceOpen||state.specialForecastOpen)?' open':'')+'><summary class="smart-fixed-picks-head"><span><b>特別予想</b><small>メイン・重賞・高知ファイナル｜朝固定</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em><i class="special-fold-icon" aria-hidden="true">›</i></span></summary><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></details>'
}

function smartDailyAiStats(){
  var dayRaces=(state.races||[]).filter(function(r){return r&&r.id});
  var allFinished=dayRaces.length>0&&dayRaces.every(function(r){return isFinal(r)});
  if(!allFinished)return '';
  var s=dailyAiStats,title=aiStatsDayTitle();if(s.date!==state.date)resetDailyAiStats(state.date),s=dailyAiStats;
  if(s.loading&&!s.total)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>全レース終了・集計中…</small></div></section>';
  if(!s.done)return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>集計準備中</small></div></section>';
  if(!s.total){
    var msg=s.finalCount?'当時の事前AI印が保存されているレースなし':'まだ集計対象の確定レースなし';
    return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>'+msg+'</small></div><p>※結果を見てから予想を作り直したレースは成績に含めません。</p></section>'
  }
  function rate(hit){return Math.round(hit/s.total*100)}
  var miss=Math.max(0,s.total-s.winHits),reasonRows=Object.keys(s.reasons||{}).map(function(k){return[k,n(s.reasons[k])]}).sort(function(a,b){return b[1]-a[1]}).slice(0,3),reasonText=reasonRows.length?reasonRows.map(function(z){return z[0]+' '+z[1]}).join(' / '):'なし',hc=s.highConfTotal?(Math.round(s.highConfHits/s.highConfTotal*100)+'% '+s.highConfHits+'/'+s.highConfTotal):'対象なし',avgB=s.total?(s.brierSum/s.total).toFixed(3):'—',avgPod=s.total?(s.markedPodiumSum/s.total).toFixed(2):'—',centralPod=s.centralPodiumTotal?(Math.round(s.centralPodiumHits/s.centralPodiumTotal*100)+'% '+s.centralPodiumHits+'/'+s.centralPodiumTotal):'対象なし',localPod=s.localPodiumTotal?(Math.round(s.localPodiumHits/s.localPodiumTotal*100)+'% '+s.localPodiumHits+'/'+s.localPodiumTotal):'対象なし';
  return '<section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(title)+'</b><small>'+s.total+'レース集計 / 目標 3頭完全包含83%</small></div><div class="smart-ai-daily-grid">'+
    '<div><small>印内3頭完全</small><strong>'+rate(s.fullPodiumHits)+'%</strong><em>'+s.fullPodiumHits+'/'+s.total+'</em></div>'+ 
    '<div><small>◎1着</small><strong>'+rate(s.winHits)+'%</strong><em>'+s.winHits+'/'+s.total+'</em></div>'+ 
    '<div><small>AI印内1着</small><strong>'+rate(s.markHits)+'%</strong><em>'+s.markHits+'/'+s.total+'</em></div>'+ 
  '</div><div class="smart-ai-review"><b>候補抽出KPI</b><span>中央 3頭完全 '+centralPod+'　地方 '+localPod+'</span><span>平均 '+avgPod+'/3頭を印内　☆・注3着内 '+rate(s.holePlaceHits)+'%</span><span>◎外れ '+miss+'　順位ミス '+s.candidateOrderMisses+' / 候補外 '+s.candidateMisses+'</span><span>高信頼◎ '+hc+'　Brier '+avgB+'</span><small>主なズレ　'+esc(reasonText)+'</small></div><p>※当日補正を含む発走前固定の印だけで集計。目標は12Rなら10R前後で1〜3着を全頭印内に含めること。発走後の再計算は混ぜません。</p></section>'
}

function smartRaceDayHeading(){
  var parts=String(state.date||'').split('-'),m=n(parts[1]),d=n(parts[2]),isToday=state.date===today(),
      hasCentral=state.races.some(function(x){return x.circuit==='中央'}),
      hasLocal=state.races.some(function(x){return x.circuit==='地方'});
  var title=isToday?'本日のレース':(m&&d?m+'月'+d+'日のレース':'開催レース');
  var sub=isToday?(hasCentral&&hasLocal?'今日の中央・地方開催':(hasCentral?'今日の中央開催':(hasLocal?'今日の地方開催':'今日の開催'))):((state.date||'').replace(/-/g,'.')+' の開催');
  return '<section class="smart-race-day-heading"><div><b>'+esc(title)+'</b><small>'+esc(sub)+'</small></div></section>'
}
function smartLiveVenueRace(rows,now){
  var active=(rows||[]).filter(function(r){return !isFinal(r)&&r.startTime});
  if(!active.length)return null;
  var running=active.filter(function(r){var d=mins(r.startTime)-now;return d<0&&d>=-25})
    .sort(function(a,b){return mins(b.startTime)-mins(a.startTime)});
  if(running.length)return running[0];
  var future=active.filter(function(r){return mins(r.startTime)>=now})
    .sort(function(a,b){return mins(a.startTime)-mins(b.startTime)});
  return future.length?future[0]:null
}
function smartLiveCircuitGroup(circuit,label,now){
  var source=state.races.filter(function(r){return r.circuit===circuit}),tracks=[],seen={};
  source.forEach(function(r){var t=String(r.track||'');if(t&&!seen[t]){seen[t]=1;tracks.push(t)}});
  tracks.sort(function(a,b){return a.localeCompare(b,'ja')});
  var rows=tracks.map(function(track){return smartLiveVenueRace(source.filter(function(r){return r.track===track}),now)}).filter(Boolean);
  if(!rows.length)return'';
  return '<div class="smart-live-circuit"><div class="smart-live-circuit-head"><b>'+esc(label)+'</b><small>'+rows.length+'会場</small></div><div class="smart-live-strip">'+
    rows.map(function(r){
      var d=mins(r.startTime)-now,status=d<0?'進行中':(d<=10?'まもなく':d+'分後'),cls=d<0?'running':(d<=10?'soon':'upcoming');
      return '<button type="button" class="smart-live-card '+cls+'" data-race="'+esc(r.id)+'">'+
        '<small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small>'+ 
        '<b>'+esc(r.title||((r.track||'')+' '+n(r.raceNumber)+'R'))+'</b>'+ 
        '<strong>'+esc(r.startTime||'--:--')+'</strong>'+ 
        '<span class="smart-live-status">'+esc(status)+'</span>'+ 
        '<em>'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m</em>'+ 
      '</button>'
    }).join('')+
  '</div></div>'
}
function smartLiveRaceSection(){
  if(state.date!==today())return'';
  var now=nowMins(),central=smartLiveCircuitGroup('中央','中央',now),local=smartLiveCircuitGroup('地方','地方',now),body=central+local;
  return '<section class="smart-live-section"><div class="smart-live-heading"><b>リアルタイム</b><small>各会場から1レース</small></div>'+
    (body||'<div class="smart-live-empty">現在の対象レースはありません</div>')+
  '</section>'
}
var ARVEXQ_LOCAL_LIVE_SLUG={"帯広":"obihiro","門別":"monbetsu","盛岡":"morioka","水沢":"mizusawa","浦和":"urawa","船橋":"funabashi","大井":"ooi","川崎":"kawasaki","金沢":"kanazawa","笠松":"kasamatsu","名古屋":"nagoya","園田":"sonoda","姫路":"himeji","高知":"kouchi","佐賀":"saga"};
var ARVEXQ_JRA_YOUTUBE_CHANNEL='UCj6AKkCWS6FJqf0o5wP45eQ';
function liveVenueExternal(circuit,track){
  if(String(circuit||'')==='中央')return 'https://www.youtube.com/@jraofficial/live';
  var slug=ARVEXQ_LOCAL_LIVE_SLUG[String(track||'')]||'';
  return slug?'https://simple.keiba-lv-st.jp/?track='+encodeURIComponent(slug):'https://simple.keiba-lv-st.jp/'
}
function liveVenueOptions(){
  var rows=[],seen={};
  (state.races||[]).forEach(function(r){var c=String(r.circuit||''),t=String(r.track||'');if(!t)return;var k=c+'|'+t;if(seen[k])return;seen[k]=1;rows.push({circuit:c,track:t})});
  rows.sort(function(a,b){if(a.circuit!==b.circuit)return a.circuit==='中央'?-1:1;return a.track.localeCompare(b.track,'ja')});
  return rows
}
function smartLiveLauncher(){
  return '<section class="smart-live-launcher"><button type="button" data-action="live-open" class="smart-live-launch-button"><span class="smart-live-launch-badge">● LIVE</span><span class="smart-live-launch-copy"><b>ライブ中継</b><small>中央 / 地方から公式LIVEへ</small></span><strong>▶</strong></button></section>'
}
function liveCenterModal(){
  if(!liveCenterOpen)return '';
  var rows=liveVenueOptions();
  var locals=rows.filter(function(v){return String(v.circuit||'')==='地方'});
  var jra=liveVenueExternal('中央','');
  var localBody=locals.length?locals.map(function(v){
    return '<a class="live-direct-venue" href="'+esc(liveVenueExternal('地方',v.track))+'" target="_blank" rel="noopener noreferrer"><small>地方</small><b>'+esc(v.track)+'</b><strong>›</strong></a>'
  }).join(''):'<div class="live-center-empty">本日の地方開催場はありません</div>';
  return '<div class="live-center-overlay" data-live-key="direct" role="dialog" aria-modal="true" aria-label="ライブ中継">'+
    '<div class="live-center-sheet live-direct-sheet">'+
      '<header class="live-center-head"><div><b>LIVE</b><small>公式ライブへ移動</small></div><button type="button" data-action="live-close" aria-label="閉じる">×</button></header>'+
      '<div class="live-direct-menu">'+
        '<a class="live-direct-box central" href="'+esc(jra)+'" target="_blank" rel="noopener noreferrer"><span><small>中央競馬</small><b>中央</b></span><em>JRA公式LIVEへ</em><strong>›</strong></a>'+
        '<details class="live-direct-local"><summary class="live-direct-box local"><span><small>地方競馬</small><b>地方</b></span><em>開催場を選ぶ</em><strong>＋</strong></summary><div class="live-direct-venues">'+localBody+'</div></details>'+
      '</div>'+
    '</div></div>'
}
function syncLiveCenterOverlay(){
  var existing=document.querySelector('body > .live-center-overlay');
  if(!liveCenterOpen){if(existing)existing.remove();return}
  var key='direct';
  if(existing&&existing.getAttribute('data-live-key')===key)return; // keep the LIVE menu state alive
  if(existing)existing.remove();
  var box=document.createElement('div');box.innerHTML=liveCenterModal();
  var node=box.firstElementChild;if(node)document.body.appendChild(node)
}
function shouldShowTodayReturn(){
  var d=state.race&&state.race.date?String(state.race.date):String(state.date||'');
  return !!d&&d!==today()
}
function smartTodayReturn(){
  if(!shouldShowTodayReturn())return '';
  return '<button type="button" class="smart-today-return" data-action="today-return" aria-label="今日のレースへ戻る"><span>↩</span><b>今日へ</b></button>'
}
function returnToToday(){
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  if(state.environmentTimer){clearTimeout(state.environmentTimer);state.environmentTimer=null}
  if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
  state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.date=today();state.openPanel=null;state.race=null;state.track=null;state.picker=false;state.horseModalNo=null;state.detailHorseNo=null;state.subPage=null;state.subPageReturnPanel=null;state.subPage=null;state.subPageReturnPanel=null;state.scenarioCode=null;state.paceStage=0;
  window.scrollTo(0,0);load()
}
function smartHomeHero(){
  var shared=window.ARVEXQUnifiedHome;
  if(shared)return shared.hero();
  return '<div class="arv-unified-hero"><img src="/arvexq-racing-hero.webp" alt="ARVEXQ"></div>';
}
// Unused legacy home hub removed; unified horse home is authoritative.
function aiStatsMarkText(row){
  var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};
  return (row.marks||[]).slice().sort(function(a,b){return n(order[a.mark],99)-n(order[b.mark],99)||n(a.no)-n(b.no)}).map(function(x){return x.mark+x.no}).join(' ')||'印なし'
}
function aiStatsCell(label,rows,key,filter){
  var eligible=rows.filter(function(x){return x.eligible&&(!filter||filter(x))}),hits=eligible.filter(function(x){return !!x[key]}).length;
  return '<div><small>'+esc(label)+'</small><strong>'+(eligible.length?Math.round(hits/eligible.length*100)+'%':'—')+'</strong><em>'+hits+'/'+eligible.length+'</em></div>'
}
function aiStatsMetrics(rows){
  return '<div class="smart-ai-daily-grid arv-ai-metrics">'
    +aiStatsCell('◎3着以内',rows,'honPlaceHit',function(x){return x.honEligible})
    +aiStatsCell('◎1着',rows,'winHit',function(x){return x.honEligible})
    +aiStatsCell('印内1着',rows,'markHit')
    +aiStatsCell('印内3頭完全包含',rows,'fullPodiumHit')
    +aiStatsCell('3連単的中',rows,'triHit',function(x){return x.triEligible})
    +'</div>'
}
function aiStatsRaceRow(x){
  var result=(x.podiumNos||[]).slice(0,3).join('-')||'—',
      cls=!x.eligible?'pending':(x.fullPodiumHit?'hit':(x.markHit?'partial':'miss')),
      judge=x.loadError?'再取得待ち':(!x.resultReady?'結果未取得':(!x.hasMarks?'発走前予想未保存':(x.fullPodiumHit?'3頭完全包含':(x.markHit?'1着印内':'1着印外'))));
  var detail=x.eligible?'<small>◎3着内 '+(x.honEligible?(x.honPlaceHit?'○':'×'):'対象外')+' ／ ◎1着 '+(x.honEligible?(x.winHit?'○':'×'):'対象外')+' ／ 印内1着 '+(x.markHit?'○':'×')+' ／ 印内3頭 '+(x.fullPodiumHit?'○':'×')+' ／ 3連単 '+(x.triEligible?(x.triHit?'的中':'不的中'):'未保存・対象外')+'</small>':'<small>集計対象外（不的中には算入しません）</small>';
  return '<div class="smart-ai-race-row '+cls+'"><span class="smart-ai-race-name"><b>'+esc(x.raceNumber)+'R</b><small>'+esc(x.title||'')+'</small></span><span class="smart-ai-race-marks">'+esc(aiStatsMarkText(x))+'</span><span class="smart-ai-race-result">結果 '+esc(result)+'</span><strong>'+esc(judge)+'</strong>'+detail+'</div>'
}
function smartDailyAiStatsPage(){
  var s=dailyAiStats;if(s.date!==state.date)resetDailyAiStats(state.date),s=dailyAiStats;
  if(!s.done&&!s.loading)setTimeout(scheduleDailyAiStats,0);
  if(state.aiStatsTrack){
    var rows=(s.rows||[]).filter(function(x){return String(x.track||'')===String(state.aiStatsTrack||'')});
    return '<div class="smart-shell">'+smartTopBar(true,state.aiStatsTrack+' AI成績','発走前の保存予想のみ')+'<main class="smart-main smart-home-subpage"><section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>'+esc(state.aiStatsTrack)+'</b><small>集計対象 '+rows.filter(function(x){return x.eligible}).length+' / '+rows.length+'レース</small></div>'+aiStatsMetrics(rows)+'<div class="smart-ai-race-list">'+(rows.length?rows.map(aiStatsRaceRow).join(''):'<div class="smart-empty">確定レースを集計中です</div>')+'</div></section></main>'+cinematicFooter()+'</div>'
  }
  if(s.loading&&!s.rows.length)return '<div class="smart-shell">'+smartTopBar(true,'本日のAI成績','保存済み予想を照合')+'<main class="smart-main smart-home-subpage"><div class="smart-loading"><span class="smart-loading-dot"></span><b>AI成績を集計中</b></div></main>'+cinematicFooter()+'</div>';
  var groups={},keys=[];
  (s.rows||[]).forEach(function(x){var k=String(x.circuit||'')+'|'+String(x.track||'');if(!groups[k]){groups[k]={circuit:x.circuit||'',track:x.track||'',rows:[]};keys.push(k)}groups[k].rows.push(x)});
  keys.sort(function(a,b){var x=groups[a],y=groups[b],c=String(x.circuit).localeCompare(String(y.circuit),'ja');return c||String(x.track).localeCompare(String(y.track),'ja')});
  var venues=keys.map(function(k){var g=groups[k],eligible=g.rows.filter(function(x){return x.eligible}),hits=eligible.filter(function(x){return x.honPlaceHit}).length;return '<button type="button" class="arv-ai-venue-card" data-ai-stats-track="'+esc(g.track)+'"><span><small>'+esc(g.circuit)+'</small><b>'+esc(g.track)+'</b></span><em>◎3着内 '+hits+'/'+eligible.length+'（対象 '+eligible.length+'R）</em><strong>›</strong></button>'}).join('');
  return '<div class="smart-shell">'+smartTopBar(true,'本日のAI成績','発走前固定の予想だけ')+'<main class="smart-main smart-home-subpage"><section class="smart-ai-daily"><div class="smart-ai-daily-head"><b>全レースAI成績</b><small>集計対象 '+s.total+' / 確定 '+s.finalCount+'レース</small></div>'+aiStatsMetrics(s.rows||[])+'<p class="muted">結果未取得・発走前予想未保存は分母から除外。3連単は発走前に3連単買い目を保存したレースだけが対象です。</p></section><section class="arv-ai-venues"><div class="smart-section-title"><div><b>開催場ごとのAI成績</b><small>開催場を押すと各レースへ</small></div></div>'+(venues||'<div class="smart-empty">確定レースを集計中です</div>')+'</section></main>'+cinematicFooter()+'</div>'
}
// Shared by the horse-only home and the selected/special subpages.
function homePickCounts(kind){
  if(kind==='selected')return {
    central:selectedRaceCandidates('中央').length,
    local:selectedRaceCandidates('地方').length
  };
  var rows=specialForecastRaceCandidates();
  return {
    central:rows.filter(function(r){return String(r.circuit||'')==='中央'}).length,
    local:rows.filter(function(r){return String(r.circuit||'')==='地方'}).length
  }
}
function homeCircuitChooser(title,kind){
  var rows=(state.races||[]),counts=homePickCounts(kind),buttons='',loading=!rows.length,
      pending=!morningPickReady();
  ['中央','地方'].forEach(function(circuit){
    var count=circuit==='中央'?counts.central:counts.local,
        status=loading?'取得中':(pending?'朝の判定待ち':'朝の確定選定');
    buttons+='<button type="button" class="arv-pick-circuit-btn" data-pick-circuit="'+circuit+'" aria-label="'+esc(circuit+' '+count+'件の'+title)+'"><span><small>'+esc(title)+'</small><b>'+esc(circuit)+'</b><em class="arv-pick-count">'+count+'件</em>'+(status?'<small class="arv-pick-count-pending">'+status+'</small>':'')+'</span><strong>›</strong></button>'
  });
  return '<section class="arv-pick-circuit-page"><div class="smart-section-title"><div><b>'+esc(title)+'</b><small>中央・地方ごとの該当件数</small></div></div><div class="arv-pick-circuit-grid">'+buttons+'</div>'+
    '</section>'
}
function selectedCircuitPage(circuit){
  var picks=selectedRaceCandidates(circuit),body=picks.length?picks.map(function(z){var r=z.race,t=z.selection||{};return '<button type="button" class="fixed-pick-row arv-direct-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small><small>'+esc(t.reason||'朝の固定判定')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+esc(t.primaryType||'厳選')+(t.noAxis?'｜軸なし・相手上位評価':'')+'｜'+esc((t.types||[]).filter(function(x){return x!==t.primaryType}).join('・')||t.score||'—')+'</em></button>'}).join(''):fixedPickEmpty('selected',circuit);

  return '<section class="smart-fixed-picks arv-direct-picks"><div class="smart-fixed-picks-head"><span><b>'+esc(circuit)+' 厳選レース</b><small>発走前の印・馬番入り買い目を保存確認</small></span><em>'+picks.length+'レース</em></div><div class="fixed-pick-box-body">'+body+'</div></section>'
}
function specialCircuitPage(circuit){
  var picks=specialForecastRaceCandidates().filter(function(r){return String(r.circuit||'')===String(circuit)}),body=picks.length?picks.map(function(r){return '<button type="button" class="fixed-pick-row arv-direct-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+esc(specialForecastRaceTag(r))+'</em></button>'}).join(''):(morningPickReady()?'<div class="fixed-pick-empty"><b>該当なし</b><small>'+esc(circuit)+'の重賞・高知ファイナルなし</small></div>':'<div class="fixed-pick-empty"><b>朝の特別予想未確定</b><small>朝の全開催確定後に一度だけ対象を固定します</small></div>');
  return '<section class="smart-fixed-picks arv-direct-picks"><div class="smart-fixed-picks-head"><span><b>'+esc(circuit)+' 特別予想</b><small>メイン・重賞・高知ファイナル｜朝固定</small></span><em>'+picks.length+'レース</em></div><div class="fixed-pick-box-body">'+body+'</div></section>'
}
function renderHomeSectionPage(){
  var page=state.homePage||'';
  if(page==='ai-stats')return smartDailyAiStatsPage();
  if(page==='selected')return '<div class="smart-shell">'+smartTopBar(true,state.pickCircuit?(state.pickCircuit+' 厳選レース'):'厳選レース',state.pickCircuit?'本日の厳選':'中央 / 地方')+'<main class="smart-main smart-home-subpage">'+(state.pickCircuit?selectedCircuitPage(state.pickCircuit):homeCircuitChooser('厳選レース','selected'))+'</main>'+cinematicFooter()+'</div>';
  if(page==='special')return '<div class="smart-shell">'+smartTopBar(true,state.pickCircuit?(state.pickCircuit+' 特別予想'):'特別予想',state.pickCircuit?'重賞・高知ファイナル':'中央 / 地方')+'<main class="smart-main smart-home-subpage">'+(state.pickCircuit?specialCircuitPage(state.pickCircuit):homeCircuitChooser('特別予想','special'))+'</main>'+cinematicFooter()+'</div>';
  state.homePage=null;state.pickCircuit=null;return renderHome()
}
function renderHome(){
  return '<div class="smart-shell smart-home">'+smartHomeHero()+'<main class="smart-main smart-home-main">'+(window.ARVEXQUnifiedHome?'<div class="arv-unified-body">'+window.ARVEXQUnifiedHome.dateBar(state.date)+window.ARVEXQUnifiedHome.buttons('horse'):'')+
    (window.ARVEXQHorsePortal?window.ARVEXQHorsePortal.home(state.races||[],{date:state.date,today:today(),nowMinutes:nowMins(),selected:homePickCounts('selected'),special:homePickCounts('special')}):
      '<section class="arv-all-panel"><header class="arv-all-title"><h2>各会場の全レース</h2></header><p class="arv-all-empty">出走データを読み込み中です。</p></section>')+
    (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
    (window.ARVEXQUnifiedHome?'</div>':'')+
    '</main>'+cinematicFooter()+'</div>'
}
function volatilityBadge(r){
  var v=r&&r.volatility||{},ready=v.ready===true&&n(v.score)>0,label=ready?String(v.label||'標'):'…',
      cls=ready?(' vol-'+(label==='硬'?'hard':label==='標'?'standard':label==='荒'?'rough':'wild')):' vol-pending',
      title=ready?('荒れ度 '+n(v.score)+'/18'+((v.reasons||[]).length?'・'+(v.reasons||[]).join(' / '):'')):'荒れ度を内部計算中';
  return '<span class="race-vol-badge'+cls+'" title="'+esc(title)+'"><small>荒れ度</small><b>'+esc(label)+'</b></span>'
}

function persistRaceSummaryCache(){
  try{
    var hasCentral=state.races.some(function(x){return x.circuit==='中央'}),
        hasLocal=state.races.some(function(x){return x.circuit==='地方'});
    if(hasCentral&&hasLocal)saveRaceCache(state.date,'__ALL__',state.races);
    else saveRaceCache(state.date,state.circuit,state.races)
  }catch(e){}
}
function mergeCachedVolatilityForTrack(track){
  var changed=false;
  state.races.forEach(function(r){
    if(r.circuit!==state.circuit||r.track!==track||!r.id)return;
    var d=loadDetailCache(r.id),v=d&&d.volatility;
    if(v&&v.version==='arvexq-volatility-v1'){
      if(JSON.stringify(r.volatility||null)!==JSON.stringify(v)){r.volatility=v;changed=true}
    }
  });
  if(changed)persistRaceSummaryCache();
  return changed
}
function mergeVolatilityPack(rows){
  var changed=false,map={};
  (rows||[]).forEach(function(x){if(x&&x.id)map[String(x.id)]=x.volatility||null});
  state.races.forEach(function(r){
    var v=map[String(r.id)];
    if(v&&JSON.stringify(r.volatility||null)!==JSON.stringify(v)){r.volatility=v;changed=true}
  });
  if(changed)persistRaceSummaryCache();
  return changed
}



function validEnvironmentValue(v){return !!(v&&v!=='不明'&&v!=='—')}
function applySummaryEnvironment(detail){
  if(!detail||!detail.id)return detail;
  var row=state.races.find(function(x){return String(x.id)===String(detail.id)});
  if(!row)return detail;
  ['track','date','raceNumber','title','distance','startTime','scheduledStartTime','fieldSize','surface','circuit'].forEach(function(k){
    if(!reflectUseful(detail[k])&&reflectUseful(row[k]))detail[k]=row[k]
  });
  var changed=false;
  ['weather','condition'].forEach(function(k){
    if(validEnvironmentValue(row[k])&&detail[k]!==row[k]){detail[k]=row[k];changed=true}
  });
  if(row.environmentMeta)detail.environmentMeta=row.environmentMeta;
  if(changed){
    try{delete detail._prediction}catch(e){}
    state.pred=null
  }
  return detail
}
function mergeEnvironmentPack(rows){
  var map={},changed=false;
  (rows||[]).forEach(function(x){if(x&&x.id)map[String(x.id)]=x});
  state.races.forEach(function(r){
    var z=map[String(r.id)];if(!z)return;
    ['weather','condition'].forEach(function(k){
      if(validEnvironmentValue(z[k])&&r[k]!==z[k]){r[k]=z[k];changed=true}
    });
    if(z.environmentMeta)r.environmentMeta=z.environmentMeta
  });
  if(state.race){
    var z=map[String(state.race.id)];
    if(z){
      var raceChanged=false;
      ['weather','condition'].forEach(function(k){
        if(validEnvironmentValue(z[k])&&state.race[k]!==z[k]){state.race[k]=z[k];raceChanged=true;changed=true}
      });
      if(z.environmentMeta)state.race.environmentMeta=z.environmentMeta;
      if(raceChanged){
        try{delete state.race._prediction}catch(e){}
        state.pred=null;state.analysisSaved={};saveDetailCache(state.race.id,state.race)
      }
    }
  }
  if(changed)persistRaceSummaryCache();
  return changed
}
function refreshEnvironmentLocal(track,attempt){
  track=track||state.track;
  if(!track||state.environmentBusy)return;
  state.environmentBusy=true;
  fetch(
    'https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='
    +encodeURIComponent(state.date)
    +'&details=0&t='+Date.now(),
    {cache:'no-store'}
  )
    .then(function(res){
      if(!res.ok)throw Error('edge-environment '+res.status);
      return res.json()
    })
    .then(function(body){
      var rows=(body&&body.races)||[];
      rows=rows.filter(function(x){
        return String(x.track||'')===String(track)
          &&String(x.circuit||'')===String(state.circuit||'')
      });
      if(mergeEnvironmentPack(rows))render()
    })
    .catch(function(){})
    .finally(function(){state.environmentBusy=false})
}


function mergeTrackPack(rows){
  var changed=false;
  (rows||[]).forEach(function(d){
    if(!d||!d.id)return;
    var id=String(d.id),old=instantTrackDetails[id]||loadDetailCache(id)||null,
        r=state.races.find(function(x){return String(x.id)===id}),merged=mergeRaceReflection(old,d,null,r||null);
    instantTrackDetails[id]=merged;saveDetailCache(id,merged);
    if(r&&merged.volatility){
      var before=JSON.stringify(r.volatility||null),after=JSON.stringify(merged.volatility);
      if(before!==after){r.volatility=merged.volatility;changed=true}
    }
  });
  return changed
}


function venueRows(){return state.races.filter(function(x){return x.circuit===state.circuit&&x.track===state.track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)})}
function venueHeaderInfo(){
  var rows=venueRows(),isTodayView=state.date===today(),now=nowMins(),futureRows=[],nextId='',status='1R〜12R';
  if(isTodayView){
    futureRows=rows.filter(function(x){return !isFinal(x)&&x.startTime&&mins(x.startTime)>=now}).sort(function(a,b){return mins(a.startTime)-mins(b.startTime)});
    if(futureRows.length){nextId=String(futureRows[0].id||'');status='次のレース '+n(futureRows[0].raceNumber)+'R '+String(futureRows[0].startTime||'')}
    else if(rows.length&&rows.every(function(x){return isFinal(x)}))status='本日のレース終了'
  }
  return {rows:rows,isTodayView:isTodayView,now:now,nextId:nextId,status:status}
}
var venueTrendTimer=null,venueTrendBusy=false,venueTrendLastFetch=0;
function resultDetailForTrend(r){
  var id=String(r&&r.id||''),d=(id&&instantTrackDetails[id])||loadDetailCache(id)||null;
  if(d&&d.result&&(d.result.finishers||[]).length)return d;
  return r||{}
}
function trendResultReady(r){var d=resultDetailForTrend(r);return !!(d&&d.result&&(d.result.finishers||[]).some(function(x){return n(x&&x.finish)>0}))}
function mergeVenueTrendDetail(d){
  if(!d||!d.id)return false;
  var id=String(d.id),changed=false,r=state.races.find(function(x){return String(x&&x.id||'')===id});
  instantTrackDetails[id]=d;saveDetailCache(id,d);
  if(r){
    if(d.result&&hasAnyResultData(d)){
      var before=JSON.stringify(r.result||null),after=JSON.stringify(d.result||null);
      if(before!==after){r.result=d.result;changed=true}
      if(d.result.status&&r.raceStatus!==d.result.status){r.raceStatus=d.result.status;changed=true}
    }
    ['weather','condition','oddsUpdatedAt','environmentMeta'].forEach(function(k){if(d[k]!=null&&d[k]!==''&&d[k]!=='不明'&&r[k]!==d[k]){r[k]=d[k];changed=true}})
  }
  return changed
}
function refreshVenueTrendData(){
  if(venueTrendBusy||!state.track||state.race||state.picker)return Promise.resolve(false);
  var viewKey=[state.date,state.circuit,state.track].join('|'),date=state.date,track=state.track,circuit=state.circuit;
  venueTrendBusy=true;venueTrendLastFetch=Date.now();
  return fetch('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+encodeURIComponent(date)+'&details=0&t='+Date.now(),{cache:'no-store'})
    .then(function(res){if(!res.ok)throw Error('venue-day '+res.status);return res.json()})
    .then(function(body){
      var rows=(body&&body.races)||[],changed=false;
      rows.forEach(function(z){
        if(String(z.track||'')!==String(track)||String(z.circuit||'')!==String(circuit))return;
        var r=state.races.find(function(x){return String(x&&x.id||'')===String(z.id||'')});if(!r)return;
        ['raceStatus','startTime','scheduledStartTime','weather','condition','title','surface','distance'].forEach(function(k){if(z[k]!=null&&z[k]!==''&&r[k]!==z[k]){r[k]=z[k];changed=true}})
      });
      return changed
    }).catch(function(){return false})
    .then(function(summaryChanged){
      if([state.date,state.circuit,state.track].join('|')!==viewKey)return summaryChanged;
      var now=nowMins(),todayView=date===today(),targets=venueRows().filter(function(r){
        if(!r||!r.id)return false;
        var started=!todayView||(r.startTime&&mins(r.startTime)<=now-1);
        return started&&(!trendResultReady(r)||isFlash(r)||!isFinal(r))
      }),cursor=0,changed=!!summaryChanged,workers=[];
      function worker(){
        if(cursor>=targets.length)return Promise.resolve();
        var row=targets[cursor++];
        return fetchEdgeRace(row.id,true).then(function(d){if(d&&mergeVenueTrendDetail(d))changed=true}).catch(function(){}).then(worker)
      }
      for(var i=0;i<Math.min(4,targets.length);i++)workers.push(worker());
      return Promise.all(workers).then(function(){return changed})
    }).then(function(changed){
      if(changed&&[state.date,state.circuit,state.track].join('|')===viewKey)render();
      return changed
    }).finally(function(){
      venueTrendBusy=false;
      if(state.track&&!state.race&&!state.picker&&state.date===today())scheduleVenueTrendRefresh(12000)
    })
}
function scheduleVenueTrendRefresh(delay){
  if(venueTrendTimer){clearTimeout(venueTrendTimer);venueTrendTimer=null}
  if(!state.track||state.race||state.picker)return;
  var minWait=Math.max(0,10000-(Date.now()-venueTrendLastFetch)),wait=Math.max(n(delay,350),minWait);
  venueTrendTimer=setTimeout(function(){venueTrendTimer=null;refreshVenueTrendData()},wait)
}
function venueTodayTrend(){
  var rows=venueRows(),completed=0,frameCount={},frameSamples=0,inner=0,outer=0,front=0,mid=0,close=0,styleSamples=0;
  rows.forEach(function(r){
    var d=resultDetailForTrend(r),fs=((d.result||{}).finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});
    if(!fs.length)return;completed++;
    var field=Math.max(1,n(d.fieldSize,(d.horses||[]).length||fs.length));
    fs.slice(0,3).forEach(function(f){
      var fr=n(f.frameNumber,0),h;
      if(!fr&&(d.horses||[]).length){h=(d.horses||[]).find(function(z){return n(z.horseNumber)===n(f.horseNumber)});fr=n(h&&h.frameNumber,0)}
      if(fr){frameCount[fr]=(frameCount[fr]||0)+1;frameSamples++;if(fr<=4)inner++;else outer++}
      var cp=(f.cornerPositions||[]).filter(function(v){return n(v)>0});
      if(cp.length){var pos=n(cp[0]),frontCut=Math.max(2,Math.ceil(field*.22)),midCut=Math.max(4,Math.ceil(field*.45));if(pos<=frontCut)front++;else if(pos<=midCut)mid++;else close++;styleSamples++}
    })
  });
  var bias='集計中';
  if(frameSamples>=3){var share=inner/frameSamples;bias=share>=.62?'内有利':(share<=.38?'外有利':'フラット')}
  var style='集計中';
  if(styleSamples>=3){var fp=front/styleSamples,cp=close/styleSamples;style=fp>=.55?'逃げ・先行':(cp>=.45?'差し・追込':'フラット')}
  var frames=Object.keys(frameCount).sort(function(a,b){return frameCount[b]-frameCount[a]||n(a)-n(b)}).slice(0,2),good=frames.length?frames.join('・')+'枠':'集計中';
  return {completed:completed,bias:bias,style:style,frames:good}
}
function venueTrendCard(){
  var t=venueTodayTrend(),caption=t.completed?String(t.completed)+'R集計・自動更新':'結果待ち・自動更新';
  return '<section class="smart-venue-trend"><div class="smart-venue-trend-head"><b>本日の傾向</b><small>'+esc(caption)+'</small></div><div class="smart-venue-trend-grid">'+
    '<div><small>トラックバイアス</small><strong>'+esc(t.bias)+'</strong></div>'+ 
    '<div><small>脚質</small><strong>'+esc(t.style)+'</strong></div>'+ 
    '<div><small>好走枠</small><strong>'+esc(t.frames)+'</strong></div>'+ 
  '</div></section>'
}
function venueRaceRows(){
  var info=venueHeaderInfo(),rows=info.rows,isTodayView=info.isTodayView,now=info.now,nextId=info.nextId;
  return venueTrendCard()+
    '<section class="smart-section smart-race-section">'+
    '<div class="smart-race-list">'+
      Array.from({length:12},function(_,idx){
        var no=idx+1,r=rows.find(function(x){return n(x.raceNumber)===no});
        if(!r)return '<div class="smart-race-row disabled"><strong>'+no+'R</strong><span class="smart-race-time">--:--</span><span class="smart-race-title">レース情報待ち</span><span></span></div>';
        var fin=isFinal(r),flash=isFlash(r),isNext=isTodayView&&!fin&&!flash&&String(r.id||'')===nextId,
            started=isTodayView&&!fin&&!flash&&r.startTime&&mins(r.startTime)<now,
            delta=isNext?Math.max(0,mins(r.startTime)-now):9999,
            cls=fin?'final':(flash?'result-flash':(isNext?'next-race'+(delta<=10?' soon':''):(started?'result-awaiting':''))),
            stateTag=fin?'<span class="race-state-pill final">確定</span>':
                     (flash?'<span class="race-state-pill flash">速報</span>':
                     (isNext?'<span class="race-state-pill next">'+(delta<=10?'次のレース・まもなく':'次のレース')+'</span>':
                     (started?'<span class="race-state-pill awaiting">結果待ち</span>':'')));
        return '<button class="smart-race-row '+cls+'" data-race="'+esc(r.id)+'">'+
          '<strong>'+no+'R</strong>'+ 
          '<span class="smart-race-time">'+(fin?'確定':(flash?'速報':timeHtml(r)))+'</span>'+ 
          '<span class="smart-race-title">'+stateTag+'<b>'+esc(r.title||no+'R')+'</b><small>'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc((r.weather&&r.weather!=='不明')?r.weather:'天候待ち')+' / '+esc((r.condition&&r.condition!=='不明')?r.condition:'馬場待ち')+'</small></span>'+ 
          '<span class="smart-chevron">›</span>'+ 
        '</button>'
      }).join('')+
    '</div>'+ 
  '</section>'
}
function venueTopBar(hi){
  return '<header class="smart-venue-topbar">'+
    '<span class="smart-pull-space" aria-hidden="true"></span>'+ 
    '<div class="smart-venue-topcopy"><strong>'+esc((state.track||'開催場')+' 全レース')+'</strong><small>'+esc((hi&&hi.status)||'')+'</small></div>'+ 
    '<button class="smart-venue-close" data-action="back" aria-label="トップへ戻る">×</button>'+ 
  '</header>'
}
function renderVenue(){
  var hi=venueHeaderInfo();
  return '<div class="smart-shell smart-venue-page">'+
    venueTopBar(hi)+
    '<main class="smart-main">'+
      (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
      venueRaceRows()+
    '</main>'+ 
    cinematicFooter()+
  '</div>'
}
function smartInlineResult(r){
  var final=isFinal(r),flash=isFlash(r),any=hasAnyResultData(r),ready=hasResultData(r),f=((r.result||{}).finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)}).slice(0,3),nums=ready&&f.length?f.map(function(x){return n(x.horseNumber)}).join(' - '):'';
  return '<button type="button" class="smart-inline-result '+(final?'final':(flash?'flash':''))+'" data-panel="result"><span>レース結果</span><strong>'+(final?(ready?'確定':'着順未取得'):(flash?(any?'速報':'速報待ち'):(String(r.date||'')<today()?'結果未取得':'未確定')))+'</strong></button>'
}
function officialRaceLinks(r){
  var central=String((r&&r.circuit)||state.circuit||'')==='中央';
  return central?{
    live:'https://www.jra.go.jp/tvradio/racelive/',
    vote:'https://www.ipat.jra.go.jp/sp/',
    liveLabel:'JRA LIVE',voteLabel:'JRA 投票'
  }:{
    live:'https://www.keiba.go.jp/live/index.html',
    vote:'https://www.spat4.jp/keiba/pc',
    liveLabel:'地方 LIVE',voteLabel:'SPAT4 投票'
  }
}
function officialRaceActions(r){
  return ''
}
function smartRaceHead(r){
  var count=raceHeadCountText(r),clock=raceMarkClock(r),revision=latestOfficialMarkRevision(r),baseline=validMorningMarkSnapshot(r),
      markState=!clock.started?'印：最新の取得データで再評価（発走前）':(revision?'発走前の公式馬場変更で印修正：'+String(revision.reason||''):baseline?'発走前に保存された印':'');
  
  return '<section class="smart-race-head smart-race-head-compact smart-race-head-v222">'+
    '<div class="smart-race-title-stack smart-race-full-title"><h1>'+esc(r.title||'レース詳細')+'</h1>'+(markState?'<small class="arv-mark-fix-status">'+esc(markState)+'</small>':'')+'</div>'+
    '<div class="smart-race-head-layout">'+
      '<div class="smart-race-left-stack">'+
        '<div class="smart-race-head-left"><span class="smart-circuit-chip">'+esc(r.circuit||state.circuit)+'</span><div class="smart-race-title-stack"><div class="smart-race-meta">'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc(r.weather||'')+' '+esc(r.condition||'')+'　'+count+'</div></div>'+cinematicGrade(r)+'</div>'+
        officialRaceActions(r)+
      '</div>'+ 
      '<div class="smart-race-result-side"><time>'+timeHtml(r)+' 発走</time>'+smartInlineResult(r)+'</div>'+ 
    '</div>'+ 
  '</section>'
}
function renderRaceLoading(){
  var row=state.races.find(function(x){return String(x.id)===String(state.raceLoading)});
  return '<div class="smart-shell">'+
    (row?smartRaceTopBar(row):smartTopBar(true,state.track||'レース','レース詳細'))+
    '<main class="smart-main smart-race-page">'+
      (row?smartRaceHead(row):'')+
      '<div class="smart-loading"><span class="smart-loading-dot"></span><b>'+(state.error?'取得済み情報を維持して再取得中':'レース情報を読み込み中')+'</b><small>'+(state.error?'通信が不安定でも画面は閉じません。取得できた情報から表示を続けます。':'選択したレースだけ取得しています。開催場一覧は先に表示します。')+'</small>'+(state.error&&row?'<button type="button" class="smart-refresh" data-race="'+esc(row.id)+'">再取得</button>':'')+'</div>'+
    '</main>'+cinematicFooter()+
  '</div>'
}
function mergeResultHorseFields(r){
  if(typeof window!=='undefined'&&window.ARVEXQRaceIdentity)r=window.ARVEXQRaceIdentity.sanitize(r);
  if(!r)return r;
  var fs=r.result&&r.result.finishers||[],by={};
  fs.forEach(function(f){var no=n(f&&f.horseNumber,0);if(no)by[no]=f});
  (r.horses||[]).forEach(function(h){var f=by[n(h.horseNumber,0)];if(!f)return;['bodyWeight','bodyWeightChange','popularity','winOdds'].forEach(function(k){if((h[k]==null||h[k]==='')&&f[k]!=null&&f[k]!=='')h[k]=f[k]})});
  return r
}
function raceSubpageTopBar(r,title){
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar smart-race-subpage-topbar">'
    +'<button type="button" class="smart-race-step prev" data-action="close-race-subpage" aria-label="レースへ戻る">&lt;</button>'
    +'<div class="smart-head-copy smart-head-copy-clean smart-race-head-copy"><strong>'+esc(title||'詳細')+'</strong><small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small></div>'
    +'<button type="button" class="smart-race-close" data-action="close-race-subpage" aria-label="閉じる">×</button>'
    +'</header>'
}
function horseDetailPage(r,p){
  var rows=sortedHorseRows(p.rows||[]),no=n(state.detailHorseNo,0),idx=rows.findIndex(function(z){return n(z.horse&&z.horse.horseNumber)===no});
  if(idx<0&&rows.length){idx=0;state.detailHorseNo=n(rows[0].horse.horseNumber)}
  var x=idx>=0?rows[idx]:null,h=x&&x.horse||null,title=h?horseDisplayName(r,h):'馬詳細';
  return '<div class="smart-shell horse-detail-page-shell">'
    +'<header class="smart-topbar smart-topbar-clean smart-race-topbar horse-detail-topbar">'
      +'<button type="button" class="horse-detail-step" data-detail-prev="1" aria-label="前の馬">‹</button>'
      +'<div class="horse-detail-top-title"><strong>'+(h?esc(h.horseNumber)+'　'+esc(title):'馬詳細')+'</strong><small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small></div>'
      +'<button type="button" class="horse-detail-step" data-detail-next="1" aria-label="次の馬">›</button>'
      +'<button type="button" class="smart-race-close horse-detail-close" data-action="close-race-subpage" aria-label="出走表へ戻る">×</button>'
    +'</header>'
    +'<main class="smart-main smart-race-page horse-detail-page"><section class="card">'
    +(x?runnerDetailBody(r,p,x):'<div class="empty">馬情報を取得中です。</div>')
    +'</section></main>'+cinematicFooter()+'</div>'
}
function betDetailPage(r,p){
  return '<div class="smart-shell bet-detail-page-shell">'+raceSubpageTopBar(r,'買い目')
    +'<main class="smart-main smart-race-page"><section class="card bet-card-clean">'+aiBetRecommendation(r,p)+'</section></main>'
    +cinematicFooter()+'</div>'
}
function renderRace(){
  var r=applySummaryEnvironment(mergeResultHorseFields(state.race)),p=null,predictionError=null;
  state.race=r;
  try{
    p=predict(r);
    state.pred=p
  }catch(e){
    predictionError=e;
    state.pred=null;
    p={
      rows:(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).map(function(h){return{
        horse:h,predMark:'',predRank:999,overallRaw:0,overallGrade:'C',winProbability:0,marketProbability:0,
        p1Probability:0,p2Probability:0,p3Probability:0,winnerDecisionProbability:0,winnerConsensusProbability:0,
        expected:'不明',pastStyle:'不明',styleSamples:0,rawFront:0,rawStalk:0,rawMid:0,rawClose:0,fade:0,
        frontStay:0,comeFromBehind:0,collapseBeneficiary:0,paceScore:0,posCons:0,latePower:0,coverage:0
      }}),
      scenarios:[],plans:{},plan:null,arrangement:{},coverage:0
    };
    // The racecard is a primary view and must never depend on AI completion.
    state.openPanel='entry'
  }
  if(!state.openPanel)state.openPanel='entry';
  var top=(p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)})[0];
  if(!state.scenarioCode||!p.plans||!p.plans[state.scenarioCode])state.scenarioCode=top?top.code:null;
  if(state.subPage==='horse')return horseDetailPage(r,p);
  if(state.subPage==='bets')return betDetailPage(r,p);
  if(state.subPage==='pace-stage')return paceStagePage(r,p);
  var content='';
  try{
    content=detailTabs(r,p)
  }catch(e){
    predictionError=predictionError||e;
    state.openPanel='entry';
    content=minimalRacecardPanel(r)
  }
  if(predictionError&&content.indexOf('AI解析はバックグラウンド')<0){
    content='<div class="diagnosis-refresh-note busy" style="margin:7px 0">AI解析の一部を再取得中です。出走表の表示は継続します。</div>'+content
  }
  return '<div class="smart-shell">'+
    smartRaceTopBar(r)+
    '<main class="smart-main smart-race-page">'+
      smartRaceHead(r)+
      cinematicTabs(r)+
      '<div class="smart-race-content">'+content+'</div>'+ 
    '</main>'+ 
    cinematicFooter()+
  '</div>'
}

function resultFinish(r,no){var f=r&&r.result&&r.result.finishers||[];for(var i=0;i<f.length;i++)if(n(f[i].horseNumber)===n(no))return n(f[i].finish);return 0}
function actualCornerLeaders(r,idx){var f=r&&r.result&&r.result.finishers||[],best=999,out=[],i,p,v;for(i=0;i<f.length;i++){p=f[i].cornerPositions||[];v=n(p[idx],0);if(v&&v<best){best=v;out=[f[i]]}else if(v&&v===best)out.push(f[i])}return out}
function actualCornerCount(r){var f=r&&r.result&&r.result.finishers||[],m=0,i;for(i=0;i<f.length;i++)m=Math.max(m,(f[i].cornerPositions||[]).length);return m}
function actualCornerLabel(i,count){if(count===1)return"4角";if(count===2)return i===0?"3角":"4角";if(count===3)return["2角","3角","4角"][i];if(count===4)return["1角","2角","3角","4角"][i];return(i+1)+"角"}
function actualOrderAt(r,idx){var f=(r.result&&r.result.finishers||[]).slice(),a=[];for(var i=0;i<f.length;i++){var p=f[i].cornerPositions||[],v=n(p[idx],0);if(v)a.push({x:f[i],pos:v})}a.sort(function(u,v){return u.pos-v.pos||n(u.x.finish)-n(v.x.finish)});return a}
function renderResultLink(r){var final=isFinal(r),flash=isFlash(r),any=hasAnyResultData(r),label=final?'確定':(flash?'速報':'未確定');return '<details class="card result-disclosure"><summary style="cursor:pointer;padding:8px 0;font-weight:700">レース結果　'+label+' ＞</summary>'+(any?renderResult(r)+(final?renderPayouts(r):'')+renderActualFlow(r):'<p class="muted">'+(flash?'速報取得中です。':'結果はまだ出ていません。')+'</p>')+'</details>'}
function renderPayouts(r){var result=r.result||{},rows=result.payouts||[],types=['単勝','複勝','枠連','馬連','ワイド','馬単','3連複','3連単'],head=state.payoutBusy?'<span class="muted">　取得中…</span>':(rows.length?'':('<span class="muted">　'+esc(result.payoutError||'取得待ち')+'</span>'));return '<section class="card"><div class="section-title">払い戻し'+head+'</div>'+types.map(function(t){var a=rows.filter(function(x){return x.type===t});return '<div style="padding:8px 0;border-bottom:1px solid #e4e7ec"><b>'+t+'</b>　'+(a.length?a.map(function(x){return esc(x.combination)+'　'+(x.amount==null?esc(x.note||'未取得'):fmtMoney(x.amount)+'円')}).join('<br>'):'<span class="muted">'+(state.payoutBusy?'取得中…':'—')+'</span>')+'</div>'}).join('')+'</section>'}
function resultRowHtml(r,x){var h=horseByNo(r,x.horseNumber)||x;return'<div class="result-row"><span>'+esc(x.finishLabel||(x.finish?x.finish+'着':'—'))+'</span>'+badge(h)+'<span class="result-name">'+esc(x.name||h.name||"")+'</span><span>'+fmtTime(x.timeSeconds)+'</span></div>'}
function renderResult(r){if(!hasAnyResultData(r))return"";var final=isFinal(r),label=final?"確定":"速報",badgeCls=final?"final-badge":"flash-badge",results=(r.result.finishers||[]).slice();(r.horses||[]).forEach(function(h){if(!results.some(function(z){return n(z.horseNumber)===n(h.horseNumber)}))results.push({horseNumber:h.horseNumber,name:h.name,finishLabel:h.status||"結果待ち"})});var f=results.sort(function(a,b){return (n(a.finish)||999)-(n(b.finish)||999)}),top=f.slice(0,5),rest=f.slice(5);return'<section class="card result-card"><div class="section-title">レース結果 <span class="'+badgeCls+'">'+(final&&!hasResultData(r)?'一部取得':label)+'</span></div>'+(final?'':'<div class="muted" style="margin-bottom:7px">速報値です。確定まで自動更新します。</div>')+'<div class="muted" style="margin-bottom:7px">馬場 '+esc(r.condition||'不明')+' / 天候 '+esc(r.weather||'不明')+'</div>'+top.map(function(x){return resultRowHtml(r,x)}).join("")+(rest.length?'<details class="result-more"><summary>6着以下を見る　'+rest.length+'頭</summary><div class="result-more-list">'+rest.map(function(x){return resultRowHtml(r,x)}).join("")+'</div></details>':'')+'</section>'}
function gradeRank(g){return g==='S'?0:(g==='A'?1:(g==='B'?2:(g==='C'?3:9)))}

function actualNumberArrowList(r,items){return (items||[]).map(function(it){var x=it&&it.x?it.x:it,h=horseByNo(r,x.horseNumber)||x;return badge(h)}).join('<i>→</i>')}
function renderActualFlow(r){if(!hasAnyResultData(r))return"";var count=actualCornerCount(r),html='<section class="card actual-flow"><div class="section-title">実際の展開順序</div>';if(!count)html+='<div class="muted">コーナー通過順データなし</div>';for(var j=0;j<count;j++){var a=actualOrderAt(r,j);html+='<div class="actual-stage"><b>'+actualCornerLabel(j,count)+'</b><div class="actual-order actual-order-compact">'+actualNumberArrowList(r,a)+'</div></div>'}var f=(r.result.finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)});html+='<div class="actual-stage"><b>ゴール</b><div class="actual-order actual-order-compact">'+actualNumberArrowList(r,f)+'</div></div></section>';return html}
function roleDetail(label,stats,profile){stats=stats||{};profile=profile||{};var st=n(stats.starts)||n(profile.starts),w=n(stats.wins),s=n(stats.seconds),t=n(stats.thirds);if(!st)return'<div class="role-box"><b>'+esc(label)+'</b><div>過去データ未取得 / 該当履歴なし</div></div>';var wr=Math.round(w/st*100),rr=Math.round((w+s)/st*100),pr=Math.round((w+s+t)/st*100),bits=['出走 '+st,'1着 '+w,'2着 '+s,'3着 '+t,'勝率 '+wr+'%','連対 '+rr+'%','複勝 '+pr+'%'];if(n(profile.starts)>0){bits.push('競馬場 '+Math.round(n(profile.track)*100)+'%');bits.push('距離 '+Math.round(n(profile.distance)*100)+'%');if(profile.condition!=null)bits.push('馬場 '+Math.round(n(profile.condition)*100)+'%');if(n(profile.early3Rate,0))bits.push('序盤3番手内 '+Math.round(n(profile.early3Rate)*100)+'%');if(n(profile.leaderRate,0))bits.push('逃げ '+Math.round(n(profile.leaderRate)*100)+'%')}return'<div class="role-box"><b>'+esc(label)+'</b><div>'+bits.join(' / ')+'</div></div>'}
function styleDisplayPcts(x){if(!x||!n(x.styleSamples))return[null,null,null,null];var raw=[n(x.rawFront,x.front),n(x.rawStalk,x.stalk),n(x.rawMid,x.mid),n(x.rawClose,x.close)],vals=[],sum=0,i,maxi=0;for(i=0;i<4;i++){vals[i]=Math.max(0,Math.round(raw[i]*100));sum+=vals[i];if(raw[i]>raw[maxi])maxi=i}vals[maxi]+=100-sum;return vals}
function styleCell(label,val,active,cls){var unk=val==null||!isFinite(Number(val));return '<div class="style-rate '+cls+(active?' dominant':'')+(unk?' unknown':'')+'"><div class="style-rate-head"><span>'+label+'</span><b>'+(unk?'—':val+'%')+'</b></div><div class="style-bar"><i style="width:'+(unk?0:Math.max(2,val))+'%"></i></div></div>'}
function positionBucket(x){if(x.expected==="逃げ候補")return"逃げ候補";if(x.expected==="先行")return"先行";if(x.expected==="好位")return"好位";if(x.expected==="後方")return"後方";if(x.expected==="不明")return"不明";return"中団"}
function stylePositionMap(r,p){var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),labels=['逃げ候補','先行','好位','中団','後方','不明'],field=Math.max(1,(r.horses||[]).length),html='<div class="style-position-map"><div class="style-map-axis"><span>内枠</span><b>脚質マップ＋枠順</b><span>外枠</span></div>';for(var j=0;j<labels.length;j++){var lab=labels[j];html+='<div class="style-lane"><div class="style-lane-label">'+lab+'</div><div class="style-lane-track">';for(var i=0;i<rows.length;i++){var x=rows[i],h=x.horse;if(positionBucket(x)!==lab)continue;var left=field<=1?50:6+(n(h.horseNumber)-1)/Math.max(1,field-1)*88,shift=x.pastStyle!==x.expected&&!(x.pastStyle==='先行'&&x.expected==='好位');html+='<span class="style-map-horse'+(shift?' shifted':'')+'" style="left:'+left+'%" title="'+esc(h.name)+'｜過去 '+esc(x.pastStyle)+' → 今回 '+esc(x.expected)+'｜'+esc(x.frontLineRole||'')+'">'+badge(h)+'</span>'}html+='</div></div>'}html+='<div class="style-map-note"><b>水色縁</b>＝過去脚質から今回条件で位置想定が動いた馬。馬番順で内→外を維持。</div>';html+='<div class="style-map-rate-list">'+rows.map(function(x){var h=x.horse,ps=styleDisplayPcts(x),fade=x.styleSamples?Math.round(x.fade*100):null;function cell(l,v,cls){return'<span class="style-map-rate-cell '+(cls||'')+'">'+l+'<strong class="'+(cls==='fade'&&v!=null&&v>=55?'high':'')+'">'+(v==null?'—':v+'%')+'</strong></span>'}return'<div class="style-map-rate-row"><span class="style-map-rate-horse">'+badge(h)+'<b>'+esc(h.name||'')+'</b></span>'+cell('逃',ps[0])+cell('先',ps[1])+cell('差',ps[2])+cell('追',ps[3])+cell('下',fade,'fade')+'</div>'}).join('')+'</div>';var arr=p.arrangement||{};html+='<div class="style-map-summary"><b>先行列：</b>'+esc(arr.pattern||'—')+'　<b>配置：</b>'+esc(arr.concentrationText||'—')+'　<b>初角まで：</b>'+Math.round(firstTurnDistance(r))+'m'+((r.firstTurnDistance||r.startToFirstTurn||r.firstCornerDistance||r.firstCornerMeters)?'':'（コース推定）')+'</div></div>';return html}
function runnerStyleSection(r,p){
  var diagnosisReady=diagnosisCurrent(r),
      cadenceText=window.ARVEXQLiveOdds.status(r);
  // Only current three-factor marks are displayed; no V313 correction badge.
  return '<section class="card"><h2>出走表</h2>'+racecardMarkLegend(r)+'<button data-action="odds-update">オッズ・馬体重更新</button><span id="odds-status" role="status"> '+cadenceText+'</span>'
    +(!diagnosisReady?'<div class="diagnosis-refresh-note busy" style="margin:7px 0">'+(r._entryOnly?'出走表を先に表示しています。履歴・能力評価を取得中です。':'取得済みデータでAI評価を先に計算中。更新後は馬名タップの詳細と展開予想へ反映します。')+'</div>':'')
    +'<div class="racecard-table">'
    +(r.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0}).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){
      var x=(p.rows||[]).find(function(z){return z&&z.horse&&n(z.horse.horseNumber)===n(h.horseNumber)});
      return racecardEntryRow(r,h,x);
    }).join('')
    +'</div></section>';
}
function rowName(x){return x&&x.horse?(x.horse.horseNumber+' '+x.horse.name):'—'}
function paceStageRows(p,key){
  var plan=activeScenarioPlan(p)||p.plan||{},st=((plan.stages||[]).find(function(s){return String(s&&s.key||'')===key}))||{},by={};
  (p.rows||[]).forEach(function(x){by[n(x.horse&&x.horse.horseNumber)]=x});
  return (st.pack||[]).map(function(z){return by[n(z.no)]}).filter(Boolean)
}
function paceNos(list){return(list||[]).map(function(x){return n(x&&x.horse&&x.horse.horseNumber)}).filter(Boolean)}
function paceNosText(list){var a=paceNos(list);return a.length?a.join('・'):'—'}
function paceStageNarrative(p,key){
  var rows=p.rows||[],arr=p.arrangement||{},order=paceStageRows(p,key),plan=activeScenarioPlan(p)||p.plan||{},out=p.outcome||null,
      byNo={},i;rows.forEach(function(x){byNo[n(x.horse&&x.horse.horseNumber)]=x});
  if(!order.length)return '展開データを準備中です。';
  var leader=order[0],second=order[1]||null,third=order[2]||null,fourth=order[3]||null,tail=order[order.length-1]||null,
      leadNo=n(leader&&leader.horse&&leader.horse.horseNumber),secondNo=n(second&&second.horse&&second.horse.horseNumber),
      front2=[third,fourth].filter(Boolean),midStart=Math.min(4,Math.max(2,order.length-3)),midEnd=Math.max(midStart,order.length-1),
      middle=order.slice(midStart,midEnd),leadCandidates=(arr.leadCandidates||[]).filter(Boolean).slice(0,3),
      text=[],prevKey=key==='turn3'?'back':(key==='turn4'?'turn3':(key==='straight'?'turn4':'')),prev=prevKey?paceStageRows(p,prevKey):[],
      prevRank={},rank={},gainers=[],droppers=[];
  prev.forEach(function(x,j){prevRank[n(x.horse.horseNumber)]=j+1});
  order.forEach(function(x,j){rank[n(x.horse.horseNumber)]=j+1});
  rows.forEach(function(x){var no=n(x.horse.horseNumber),a=n(prevRank[no],0),b=n(rank[no],0);if(a&&b&&a-b>=2)gainers.push(x);if(a&&b&&b-a>=2)droppers.push(x)});

  if(key==='start'){
    var contenders=leadCandidates.length>=2?leadCandidates:order.slice(0,Math.min(2,order.length)),
        settled=paceStageRows(p,'first'),settledLeader=settled[0]||leader,
        secondLine=settled.slice(1,Math.min(3,settled.length)),
        nextLine=settled.slice(3,Math.min(5,settled.length)),
        midSettled=settled.slice(5,Math.max(5,settled.length-1)),
        tailSettled=settled[settled.length-1]||tail;
    if(contenders.length>=2)text.push(paceNosText(contenders)+'がハナ争い');
    text.push(n(settledLeader&&settledLeader.horse&&settledLeader.horse.horseNumber)+'がハナ');
    // Expose the data behind the claim; first-corner occupancy is NOT measured
    // gate reaction or first-1F time. Show sample sizes to avoid false certainty.
    contenders.slice(0,Math.min(3,contenders.length)).forEach(function(z){
      var ph=z.minetaPast||minetaPastProfile(z.horse,state.race||{}),cnt=n(ph.firstCornerSamples,0);
      if(cnt)text.push(n(z.horse.horseNumber)+'の近走初角先頭 '+Math.round(n(ph.leadRate)*100)+'%（'+cnt+'走）');
      var timing=z.earlyTimingProfile||{},observed=(timing.samples||[]).filter(function(e){return e.first200mSeconds!=null||e.gateReactionSeconds!=null});
      if(observed.length){
        var one=observed[0],kind=one.kind==='individual_sensor'?'個別センサー':'映像推定';
        text.push(n(z.horse.horseNumber)+'の'+kind+'（'+one.date+'）：'+(one.first200mSeconds!=null?'個別テン1F '+one.first200mSeconds.toFixed(2)+'秒':'テン1F未取得')+(one.gateReactionSeconds!=null?'、ゲート反応 '+one.gateReactionSeconds.toFixed(2)+'秒':'')+'。取得元 '+one.source)
      }
    });
    if(secondLine.length)text.push('2番手集団 '+paceNosText(secondLine));
    if(nextLine.length)text.push('その後ろ '+paceNosText(nextLine));
    if(midSettled.length>=2)text.push('中団 '+paceNosText(midSettled));
    else if(midSettled.length===1)text.push('中団 '+paceNosText(midSettled));
    if(tailSettled&&settled.length>5)text.push('しんがり '+n(tailSettled.horse.horseNumber));
    return text.join(' → ')
  }

  if(key==='turn3'){
    text.push(leadNo+'が先頭');
    if(secondNo)text.push(secondNo+'が2番手で追走');
    if(gainers.length)text.push(paceNosText(gainers.slice(0,3))+'が中団から進出');
    else text.push('前の隊列は大きく変わらず');
    var hold=order.filter(function(x){return n(x.horse.horseNumber)!==leadNo&&x.move<.52&&x.comeFromBehind>=.52}).slice(-2);
    if(hold.length)text.push(paceNosText(hold)+'はまだ脚をためる');
    if(tail)text.push(n(tail.horse.horseNumber)+'は後方待機');
    return text.join(' → ')
  }

  if(key==='turn4'){
    text.push(leadNo+'が先頭で直線へ');
    if(secondNo)text.push(secondNo+'が直後');
    if(gainers.length)text.push(paceNosText(gainers.slice(0,3))+'が進出して前との差を詰める');
    var attack=order.filter(function(x){return n(x.horse.horseNumber)!==leadNo&&(x.comeFromBehind>=.56||x.latePower>=.58)}).slice(0,3);
    if(attack.length)text.push(paceNosText(attack)+'は差し・追い込み態勢');
    if(droppers.length)text.push(paceNosText(droppers.slice(0,2))+'は手応え注意');
    if(tail)text.push('最後方'+n(tail.horse.horseNumber)+'も直線勝負');
    return text.join(' → ')
  }

  if(key==='straight'){
    out=out||paceOutcomeModel(state.race||{},p);
    var winner=out&&out.winner?out.winner:leader,winnerNo=n(winner&&winner.horse&&winner.horse.horseNumber),
        verdict=String(out&&out.verdict||''),chasers=order.slice(1,Math.min(4,order.length)),
        closers=rows.filter(function(x){return x!==winner&&(x.comeFromBehind>=.56||x.latePower>=.58)}).sort(function(a,b){return n(rank[n(a.horse.horseNumber)],99)-n(rank[n(b.horse.horseNumber)],99)}).slice(0,3);
    if(winnerNo===leadNo&&/逃げ切り/.test(verdict))text.push(leadNo+'がハナのまま逃げ切り態勢');
    else if(winnerNo!==leadNo)text.push(leadNo+'が粘るが、'+winnerNo+'が'+(verdict||'抜け出し')+'本線');
    else text.push(winnerNo+'が先頭で押し切り態勢');
    if(chasers.length)text.push(paceNosText(chasers)+'が後ろから追う');
    var stalkAttack=chasers.filter(function(x){return x.expected==='先行'||x.expected==='好位'||x.stalk>=.28}).slice(0,3);
    if(stalkAttack.length)text.push(paceNosText(stalkAttack)+'は脚をためて差しを狙う');
    if(closers.length)text.push(paceNosText(closers)+'が追い込みを仕掛ける');
    if(tail&&closers.indexOf(tail)>=0)text.push('しんがり'+n(tail.horse.horseNumber)+'も大外から追い込み');
    return text.join(' → ')
  }
  return ''
}
function paceStructureSection(r,p){
  var ctx=p&&p.minetaContext;if(!ctx)return'';
  var lead=(ctx.leadNos||[]).join('・')||'—',label=ctx.band==='前少なめ'?'前が少ない構成':(ctx.band==='前多め'?'先行争いが濃い構成':'中間の構成');
  return '<section class="ai-stage-event" style="margin:10px 0;padding:11px 13px;border:1px solid rgba(120,170,255,.22);border-radius:12px;background:rgba(8,18,36,.45)">'
    +'<div style="font-size:15px;font-weight:900;color:#8de9ff">'+esc(label)+'</div>'
    +'<div style="margin-top:7px;font-size:14px;line-height:1.75">先行占有 '+Math.round(ctx.rawOcc*100)+'%　/　距離補正後 '+Math.round(ctx.adjustedOcc*100)+'%　/　後方占有 '+Math.round(ctx.rearOcc*100)+'%　/　ハナ候補 '+esc(lead)+'</div>'
    +'<div class="muted" style="margin-top:6px;font-size:13px;line-height:1.65">'+esc(minetaStructureText(ctx))+'</div></section>'
}
function paceNarrativeCards(r,p){
  var stages=[
    ['start','スタート'],
    ['turn3','3コーナー'],
    ['turn4','4コーナー'],
    ['straight','ラスト']
  ];
  return '<div class="pace-text-timeline">'+stages.map(function(z){
    return '<section class="ai-stage-event" style="margin:10px 0;padding:13px 14px;border:1px solid rgba(120,170,255,.24);border-radius:12px;background:rgba(8,18,36,.50)">'
      +'<div style="font-size:16px;font-weight:900;color:#8de9ff;margin-bottom:8px">'+z[1]+'</div>'
      +'<div style="font-size:17px;line-height:1.75;font-weight:700">'+esc(paceStageNarrative(p,z[0]))+'</div>'
      +'</section>'
  }).join('')+'</div>'
}

var PACE_STAGE_PAGES=[
  {key:'start',visualKey:'first',label:'スタート',detail:'スタート直後'},
  {key:'turn3',visualKey:'turn3',label:'3C',detail:'3コーナー'},
  {key:'turn4',visualKey:'turn4',label:'4C',detail:'4コーナー'},
  {key:'straight',visualKey:'straight',label:'ラスト',detail:'直線・決着'}
];
function paceStageConfig(idx){
  idx=clamp(n(idx,0),0,PACE_STAGE_PAGES.length-1);
  return Object.assign({index:idx},PACE_STAGE_PAGES[idx])
}
function paceStageMenu(r,p){
  return '<div class="pace-stage-menu pace-stage-entry" role="navigation" aria-label="4局面展開">'
    +'<button type="button" class="pace-stage-entry-btn" data-pace-open="0">'
      +'<span class="pace-stage-entry-copy"><b>4局面展開</b><small>スタート → 3C → 4C → ラスト</small></span>'
      +'<span class="pace-stage-entry-sub">隊列図＋説明を見る</span><i>›</i>'
    +'</button></div>'
}
function openPaceStagePage(idx){
  state.paceStage=clamp(n(idx,0),0,PACE_STAGE_PAGES.length-1);
  state.subPageReturnPanel='pace';
  state.openPanel='pace';
  state.subPage='pace-stage';
  window.scrollTo(0,0);
  render()
}
function paceStageTopBar(r,cfg){
  var prev=cfg.index>0?'<button type="button" class="pace-stage-step prev" data-pace-open="'+(cfg.index-1)+'" aria-label="前の局面">‹</button>':'<span class="pace-stage-step ghost" aria-hidden="true"></span>',
      next=cfg.index<PACE_STAGE_PAGES.length-1?'<button type="button" class="pace-stage-step next" data-pace-open="'+(cfg.index+1)+'" aria-label="次の局面">›</button>':'<span class="pace-stage-step ghost" aria-hidden="true"></span>';
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar pace-stage-topbar">'
    +prev
    +'<div class="pace-stage-top-title"><strong>'+esc(cfg.label)+'</strong><small>'+esc(r.track)+' '+esc(r.raceNumber)+'R</small></div>'
    +next
    +'<button type="button" class="smart-race-close pace-stage-close" data-action="close-race-subpage" aria-label="4局面一覧へ戻る">×</button>'
    +'</header>'
}
function paceStageJumpNav(active){
  return '<nav class="pace-stage-jump" aria-label="展開局面を直接選択">'
    +PACE_STAGE_PAGES.map(function(z,idx){return '<button type="button" data-pace-open="'+idx+'" class="'+(idx===active?'active':'')+'">'+esc(z.label)+'</button>'}).join('')
    +'</nav>'
}
function paceStagePack(p,key){
  var plan=activeScenarioPlan(p)||p.plan||{},st=((plan.stages||[]).find(function(z){return String(z&&z.key||'')===key}))||{};
  return (st.pack||[]).slice()
}
function paceFormationDiagram(r,p,cfg){
  var pack=paceStagePack(p,cfg.visualKey),byNo={};
  (r.horses||[]).forEach(function(h){byNo[n(h.horseNumber)]=h});
  if(!pack.length)return '<div class="empty pace-stage-empty">隊列図を準備中です。</div>';
  var height=Math.max(330,112+Math.max(0,pack.length-1)*27),span=Math.max(1,pack.length-1);
  return '<section class="pace-formation-card">'
    +'<div class="pace-formation-head"><b>隊列図</b><span>'+(cfg.key==='start'?'ハナ争い後の収まり想定':'上が前方・下が後方')+'</span></div>'
    +'<button type="button" class="pace-formation-next" data-pace-next="'+((cfg.index+1)%PACE_STAGE_PAGES.length)+'" aria-label="隊列図をタップして次の局面へ：'+esc(PACE_STAGE_PAGES[(cfg.index+1)%PACE_STAGE_PAGES.length].label)+'">'
    +'<div class="pace-lane-axis"><span>内</span><b>想定進路</b><span>外</span></div>'
    +'<div class="pace-formation-track" style="height:'+height+'px">'
      +'<div class="pace-front-arrow">前方 ↑</div>'
      +'<div class="pace-center-line" aria-hidden="true"></div>'
      +pack.map(function(z,idx){
        var no=n(z.no),h=byNo[no]||{},fr=clamp(n(h.frameNumber,no),1,8),lane=clamp(n(z.lane,0),-3,3),
            left=50+lane*9,top=52+(height-100)*(idx/span),rankLabel=idx===0?'ハナ':(idx===1?'2番手':String(idx+1));
        return '<div class="pace-horse-node" style="left:'+left+'%;top:'+Math.round(top)+'px" aria-label="'+esc(rankLabel+' '+no+'番 '+(h.name||''))+'">'
          +'<span class="pace-rank-label">'+esc(rankLabel)+'</span><i class="pace-horse-dot frame'+fr+'">'+esc(no)+'</i></div>'
      }).join('')
      +'<div class="pace-rear-label">後方</div>'
    +'</div><div class="pace-formation-tap-hint">図をタップ：次の局面 '+esc(PACE_STAGE_PAGES[(cfg.index+1)%PACE_STAGE_PAGES.length].label)+' ›</div></button>'
    +(cfg.key==='start'?'<div class="pace-diagram-note">ハナ争いは説明文、図は争いが収まった直後の隊列を表示。</div>':'')
    +'</section>'
}
function paceStageEvidence(p,cfg){
  return '<section class="pace-stage-explain"><h2>'+esc(cfg.detail)+'</h2>'
    +'<p class="pace-stage-narrative">'+esc(paceStageNarrative(p,cfg.key))+'</p>'
    +(cfg.key==='start'?'<p class="muted">先行の基本根拠は過去5走の初角位置。取得元付きの個別テン1F・ゲート反応・初動加速データがある場合のみ弱い補正に使用します。個別センサーは提供測定値、映像解析は推定値、公式レースラップは先頭馬の区間時計です。データが無い馬は実測値を表示しません。</p>':'')
    +'</section>'
}
function paceStagePage(r,p){
  var cfg=paceStageConfig(state.paceStage);
  return '<div class="smart-shell pace-stage-shell">'+paceStageTopBar(r,cfg)
    +'<main class="smart-main smart-race-page pace-stage-page">'+paceStageJumpNav(cfg.index)
      +paceStageEvidence(p,cfg)+paceFormationDiagram(r,p,cfg)
    +'</main>'+cinematicFooter()+'</div>'
}
function paceStagePendingPage(r){
  var cfg=paceStageConfig(state.paceStage);
  return '<div class="smart-shell pace-stage-shell">'+paceStageTopBar(r,cfg)
    +'<main class="smart-main smart-race-page pace-stage-page">'+paceStageJumpNav(cfg.index)
    +'<section class="card"><div class="empty">展開データを計算中です。</div></section></main>'+cinematicFooter()+'</div>'
}
function activeScenarioPlan(p){return p&&p.plan?p.plan:null}
function visiblePaceStages(plan){var wanted={start:1,turn3:1,turn4:1,straight:1};return ((plan&&plan.stages)||[]).filter(function(s){return !!wanted[String(s&&s.key||'')]})}
function scenarioProbabilitySection(p){return''}
function paceOutcomeModel(r,p){
  var rows=(p&&p.rows||[]).slice(),plan=activeScenarioPlan(p)||p.plan||{},stages=visiblePaceStages(plan),
      straight=stages.find(function(s){return s&&s.key==='straight'})||stages[stages.length-1]||{},pack=straight.pack||[],byNo={},i;
  rows.forEach(function(x){byNo[n(x.horse&&x.horse.horseNumber)]=x});
  if(!rows.length)return null;
  var order=pack.map(function(z){return byNo[n(z.no)]}).filter(Boolean);
  rows.forEach(function(x){if(order.indexOf(x)<0)order.push(x)});
  var day={active:false,flowLabel:'中立',byNo:{},policy:'past-results-do-not-revise-pace-or-marks'},sc=plan.scenario||{},arr=p.arrangement||{},
      leader=((plan.start||[])[0])||(arr.leadCandidates||[])[0]||null,field=Math.max(1,order.length),rankByNo={};
  order.forEach(function(x,idx){rankByNo[n(x.horse.horseNumber)]=idx+1});
  rows.forEach(function(x){
    var no=n(x.horse.horseNumber),rank=n(rankByNo[no],field),pos=field<=1?1:1-(rank-1)/(field-1),dc=(day.byNo||{})[no]||{},
        win=n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,.5))),
        p2=n(x.p2RecallScore,n(x.p2Probability,.5)),p3=n(x.p3RecallScore,n(x.p3Probability,.5));
    x._paceOutcomeFirst=clamp(pos*.58+win*.22+n(x.ability,.5)*.10+n(x.frontStay,.5)*.05+n(x.comeFromBehind,.5)*.05+n(dc.winBoost,0)*2,0,1);
    x._paceOutcomeSecond=clamp(pos*.42+p2*.33+n(x.posCons,.5)*.10+n(x.latePower,.5)*.08+n(x.frontStay,.5)*.07+n(dc.p2Boost,0)*2,0,1);
    x._paceOutcomeThird=clamp(pos*.34+p3*.36+n(x.latePower,.5)*.12+n(x.move,.2)*.08+n(x.posCons,.5)*.10+n(dc.p3Boost,0)*2,0,1);
    x.paceOutcomeFirst=x._paceOutcomeFirst;x.paceOutcomeSecond=x._paceOutcomeSecond;x.paceOutcomeThird=x._paceOutcomeThird
  });
  var top=order[0]||null,firstGroup=top?[top]:[],secondGroup=order.slice(1,Math.min(4,order.length)),thirdGroup=order.slice(2,Math.min(6,order.length)),
      leaderNo=n(leader&&leader.horse&&leader.horse.horseNumber),winnerNo=n(top&&top.horse&&top.horse.horseNumber),leaderRow=byNo[leaderNo]||leader||null,
      winnerStyle=String(top&&(top.expected||top.pastStyle)||''),verdict='好位抜け出し',ctx=p.minetaContext||null;
  if(top){
    if(winnerNo===leaderNo&&n(top.frontStay)>=Math.max(.52,n(top.comeFromBehind)-.03))verdict='逃げ切り';
    else if(winnerStyle.indexOf('後方')>=0||winnerStyle.indexOf('追')>=0)verdict='追い込み';
    else if(winnerStyle.indexOf('中団')>=0||winnerStyle.indexOf('差')>=0||n(top.comeFromBehind)>=n(top.frontStay)+.05)verdict='差し切り';
    else if(winnerStyle.indexOf('先行')>=0||winnerStyle.indexOf('好位')>=0)verdict='先行押し切り'
  }
  var leadRank=leaderRow?order.indexOf(leaderRow)+1:0,reason=[];
  reason.push('ハナ想定 '+(leaderRow?rowName(leaderRow):'不明'));
  if(ctx)reason.push(minetaStructureText(ctx));
  if(day.active)reason.push('当日バイアス '+day.flowLabel);
  if(winnerNo===leaderNo)reason.push('局面遷移で先頭を維持');
  else if(leaderRow)reason.push('逃げ馬はラスト'+leadRank+'番手、'+(top?rowName(top):'不明')+'が前へ');
  return{verdict:verdict,leader:leaderRow,winner:top,first:firstGroup,second:secondGroup,third:thirdGroup,margin:0,day:day,scenario:sc,reason:reason.join('｜'),order:order}
}
function paceOutcomeNums(list){return(list||[]).map(function(x){return n(x.horse&&x.horse.horseNumber)}).filter(Boolean).join('・')||'—'}
function paceOutcomeSection(r,p){
  var o=paceOutcomeModel(r,p);if(!o)return'';
  var winner=o.winner?rowName(o.winner):'—',lead=o.leader?rowName(o.leader):'—';
  return '<div class="ai-stage-event" style="margin:10px 0 12px;padding:12px;border:1px solid rgba(120,170,255,.32);border-radius:12px;background:rgba(8,18,36,.68)">'
    +'<div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><b style="font-size:15px">展開結論：'+esc(o.verdict)+'</b><span class="muted">'+esc(o.day&&o.day.active?o.day.flowLabel:'バイアス中立')+'</span></div>'
    +'<div style="margin-top:7px;font-size:13px;line-height:1.6">逃げ想定 <b>'+esc(lead)+'</b>　→　勝ち切り本線 <b>'+esc(winner)+'</b></div>'
    +'<div style="margin-top:8px;font-size:16px;font-weight:800;letter-spacing:.02em">'+esc(paceOutcomeNums(o.first))+' → '+esc(paceOutcomeNums(o.second))+' → '+esc(paceOutcomeNums(o.third))+'</div>'
    +'<div class="muted" style="margin-top:7px;line-height:1.55">'+esc(o.reason)+'</div>'
    
    +'</div>'
}
function paceBoard(r,p){
  return '<section class="card ai-flow-card pace-stage-menu-card">'
    +'<div class="ai-flow-head"><span class="ai-flow-bars"><i></i><i></i><i></i></span><div class="ai-flow-copy"><div class="ai-flow-title">AI展開予想</div><div class="ai-flow-sub">展開結論を確認し、4局面から直接開けます。</div></div></div>'
    +paceOutcomeSection(r,p)
    +paceStageMenu(r,p)
    +'</section>'
}
function historySearchSection(r){var hs=r.historySearch||{},cv=hs.coverage||{},months=n(hs.monthsDone),max=n(hs.maxMonths,60),progress=max?clamp(months/max*100,4,96):8,counts=cv.counts||{},isCentral=r.circuit==='中央',horseHtml=(r.horses||[]).map(function(h){var c=n(counts[h.name]);return'<span>'+badge(h)+esc(h.name||'')+' <b>'+Math.min(5,c)+'/5</b></span>'}).join(''),src=isCentral?'中央データを過去へさかのぼり':'NAR公式履歴を過去へさかのぼり';return'<section class="card history-search-card"><div class="history-search-head"><span class="history-spinner"></span><div><div class="history-search-title">直近5走を取得中</div><div class="history-search-sub">全頭について'+src+'、直近最大5走を確認します。キャリア5走未満の馬は存在する全走を取得した時点で確定し、固定値では埋めません。取得した過去レースは詳細画面から開けます。</div></div></div><div class="history-progress"><i style="width:'+progress+'%"></i></div><div class="history-stats"><span>検索 '+months+' / '+max+'か月</span><span>'+(isCentral?'履歴確定 ':'5走取得 ')+n(isCentral?(cv.horsesResolved||cv.horsesWith5Plus):cv.horsesWith5Plus)+' / '+n(cv.totalHorses,(r.horses||[]).length)+'頭</span><span>履歴あり '+n(cv.horsesWithHistory)+'頭</span><span>取得 '+n(cv.totalRuns)+'走</span></div><div class="history-horses">'+horseHtml+'</div></section>'}
function scheduleHistoryPoll(id){return}
function prefetchNextHistory(){return}

function waitForRaceReady(id,seq,attempt){
  attempt=n(attempt,0);
  if(seq!==state.detailSeq)return;
  setTimeout(function(){
    if(seq!==state.detailSeq)return;
    fetchEdgeRace(id).then(function(body){
      if(seq!==state.detailSeq)return;
      if(body){
        state.raceLoading=null;
        state.race=applySummaryEnvironment(body);
        render();
        return
      }
      if(attempt<4){
        waitForRaceReady(id,seq,attempt+1);
        return
      }
      state.raceLoading=null;
      state.error='Cloudflare同期待ちです。少し後でもう一度更新してください。';
      render()
    })
  },500+attempt*350)
}

var raceBiasTimer=null,raceBiasBusy=false;
function scheduleRaceBiasRefresh(delay){
  if(raceBiasTimer){clearTimeout(raceBiasTimer);raceBiasTimer=null}
  var r=state.race;if(!r||String(r.date||'')!==today())return;
  raceBiasTimer=setTimeout(function(){raceBiasTimer=null;refreshRaceBiasData()},Math.max(500,n(delay,1200)))
}
function refreshRaceBiasData(){
  var r=state.race;if(raceBiasBusy||!r||String(r.date||'')!==today())return Promise.resolve(false);
  var id=String(r.id||''),raceNo=n(r.raceNumber,99),now=nowMins(),targets=(state.races||[]).filter(function(z){
    if(!z||String(z.date||'')!==String(r.date||'')||String(z.circuit||'')!==String(r.circuit||'')||String(z.track||'')!==String(r.track||''))return false;
    if(n(z.raceNumber,99)>=raceNo)return false;
    if(mins(z.startTime)>now-2)return false;
    return !trendResultReady(z)
  }).sort(function(a,b){return n(b.raceNumber)-n(a.raceNumber)}).slice(0,6),before=sameDayTrendSignatureV313(r,(state.pred&&state.pred.rows)||buildRows(analysisRace(r)));
  if(!targets.length){scheduleRaceBiasRefresh(12000);return Promise.resolve(false)}
  raceBiasBusy=true;var cursor=0,changed=false,workers=[];
  function worker(){
    if(cursor>=targets.length)return Promise.resolve();var z=targets[cursor++];
    return fetchEdgeRace(z.id,true).then(function(d){if(d){if(mergeVenueTrendDetail(d))changed=true}}).catch(function(){}).then(worker)
  }
  for(var i=0;i<Math.min(3,targets.length);i++)workers.push(worker());
  return Promise.all(workers).then(function(){
    if(!state.race||String(state.race.id)!==id)return false;
    var after=sameDayTrendSignatureV313(state.race,(state.pred&&state.pred.rows)||buildRows(analysisRace(state.race)));
    if(changed||before!==after){try{delete state.race._prediction}catch(e){}state.pred=null;render();return true}
    return false
  }).finally(function(){raceBiasBusy=false;if(state.race&&String(state.race.id)===id)scheduleRaceBiasRefresh(12000)})
}
// Results are fetched independently of prediction/diagnosis readiness.
// A re-render (for example from odds updates) must not postpone the polling timer.
var resultPollBusy=false,resultPollActiveId='';
function scheduleResultRefresh(){
  var r=state.race;
  if(!r||!r.id||!r.startTime||!/^\d{4}-\d{2}-\d{2}$/.test(String(r.date||''))||
      String(r.date||'')>today()||
      (Date.parse(today()+'T00:00:00+09:00')-Date.parse(String(r.date||'')+'T00:00:00+09:00'))>7*86400000||
      (isFinal(r)&&hasResultData(r)&&((r.result||{}).payouts||[]).length>0)){
    if(state.resultTimer){clearTimeout(state.resultTimer);state.resultTimer=null}
    return;
  }
  var id=String(r.id);
  if(state.resultTimer&&resultPollActiveId===id)return;
  if(state.resultTimer){clearTimeout(state.resultTimer);state.resultTimer=null}
  if(resultPollBusy)return;
  resultPollActiveId=id;
  var delta=mins(r.startTime)-nowMins();
  var wait=delta>3?Math.min(300000,Math.max(30000,(delta-2)*60000)):20000;
  state.resultTimer=setTimeout(function(){
    state.resultTimer=null;
    var seq=state.detailSeq;
    if(!state.race||String(state.race.id)!==id)return;
    resultPollBusy=true;
    fetchEdgeRace(id,true,1).then(function(body){
      if(!body||seq!==state.detailSeq||!state.race||String(state.race.id)!==id)return;
      state.race=applySummaryEnvironment(mergeRaceReflection(state.race,body,null,null));
      instantTrackDetails[id]=state.race;saveDetailCache(id,state.race);
      updateDetailSections(id,state.race,true);
      // Keep the opened tab, historical predictions and tickets unchanged.
      render()
    }).catch(function(error){
      traceRaceDetail(id,'result-poll-failed',{message:String(error&&error.message||error)});
      if(state.race&&String(state.race.id)===id)detailState(id).result='error';
    }).finally(function(){
      resultPollBusy=false;
      scheduleResultRefresh()
    })
  },wait)
}

function refreshPayoutsOnly(attempt){
  var r=state.race;
  if(!r||!r.id||state.payoutBusy)return;
  state.payoutBusy=true;
  fetchEdgeRace(r.id,true)
    .then(function(body){
      if(!body||!state.race||String(state.race.id)!==String(r.id))return;
      state.race=applySummaryEnvironment(mergeRaceReflection(state.race,body,null,null));
      saveDetailCache(r.id,state.race)
    })
    .catch(function(error){traceRaceDetail(r.id,'payout-refresh-failed',{message:String(error&&error.message||error)})})
    .finally(function(){state.payoutBusy=false;if(state.race&&String(state.race.id)===String(r.id))render()})
}



function idleTask(fn,delay){
  delay=n(delay,1200);
  if(window.requestIdleCallback){
    setTimeout(function(){requestIdleCallback(function(){try{fn()}catch(e){}},{timeout:1800})},delay)
  }else setTimeout(function(){try{fn()}catch(e){}},delay)
}

function diagnosisCurrent(r){
  var pm=r&&r.preparedMeta||{};
  return pm.diagnosisReady===true&&pm.diagnosisVersion==='arvexq-edge-2026.10-v53-consensus-rebuild'
}
function openRace(id,keepStack,skipHistory,preservePanel){
  if(!id)return;
  if(previousAiStats.loading){
    ++previousAiStatsJob;
    previousAiStats.loading=false;
    previousAiStats.done=false;
  }
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  state.oddsBusy=false;
  if(state.environmentTimer){clearTimeout(state.environmentTimer);state.environmentTimer=null}
  // v235: when moving with the race < / > controls, keep the currently selected panel.
  // Normal venue/top selections still open the racecard first.
  var preservedPanel=preservePanel?(state.openPanel||'entry'):null;
  state.openPanel=preservedPanel||'entry';
  var seq=++state.detailSeq;
  if(!keepStack){state.raceStack=[];state.raceReturnPicker=state.picker}
  state.horseModalNo=null;state.detailHorseNo=null;state.subPage=null;state.subPageReturnPanel=null;
  if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
  state.error=null;
  state.pred=null;
  state.picker=false;
  state.scenarioCode=null;
  state.paceStage=0;

  var row=(state.races||[]).find(function(x){return String(x&&x.id||'')===String(id)}),cached=instantTrackDetails[String(id)]||loadDetailCache(id,true);
  var initial=mergeRaceReflection(normalizeDetailSummary(row,id),cached,null,null);
  initial=normalizeDetailSummary(initial,id);
  var st=detailState(id);st.error='';updateDetailSections(id,initial,false);
  state.raceLoading=null;
  state.race=applySummaryEnvironment(initial);
  render();
  // Start the verified local roster without waiting for the slower D1/full-history path.
  hydrateStaticRacecardFirst(id,seq,initial);
  if(entryDataAvailable(initial))fetchSelectedRaceOdds(id,seq);
  // One authoritative detail request. The dated immutable factual card is
  // painted immediately above; retired parallel racecard/snapshot fetches no
  // longer race to replace a healthy D1 detail.
  fetchEdgeRace(id,true,2).then(function(body){
    if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return;
    if(body){
      state.race=applySummaryEnvironment(mergeRaceReflection(state.race,body,null,null));
      instantTrackDetails[String(id)]=state.race;saveDetailCache(id,state.race);
    }
    if(entryDataAvailable(state.race)){
      updateDetailSections(id,state.race,true);render();
      if(!entryDataAvailable(initial))fetchSelectedRaceOdds(id,seq);
      return;
    }
    // Only when D1 and the vetted dated archive could not supply any runners,
    // ask the narrow racecard endpoint once. It is not a second live source.
    return fetchRacecardOnly(id).then(function(card){
      if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return;
      if(card&&entryDataAvailable(card)){
        state.race=applySummaryEnvironment(mergeRaceReflection(state.race,card,null,row));
        instantTrackDetails[String(id)]=state.race;saveDetailCache(id,state.race);
        st.error='';
        traceRaceDetail(id,'racecard-last-resort',{horses:(card.horses||[]).length});
        fetchSelectedRaceOdds(id,seq);
      }
      updateDetailSections(id,state.race,!!card);render();
    });
  }).catch(function(error){
    if(seq!==state.detailSeq)return;
    st.error=String(error&&error.message||error);
    updateDetailSections(id,state.race,false);render()
  })
}

function openPastRace(id){if(!id)return;if(state.race)state.raceStack.push(state.race);openRace(id,true,true)}
function installPullRefresh(){
  // The shared sport module owns the touch listeners and indicator.
  window.ARVEXQPullRefresh.mount({refresh:reloadCurrent});
}
function reloadCurrent(){
  if(state.race&&state.race.id){
    openRace(state.race.id,true,true,true);return
  }
  if(state.raceLoading){openRace(state.raceLoading,true,true,true);return}

  try{localStorage.removeItem(cacheKey(state.date,state.circuit))}catch(e){}
  state.races=[];
  load(true)
}
function mergeOddsPayload(body){
  if(!state.race||!body)return false;
  var changed=false,predictionInputChanged=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h,old;
  for(i=0;i<rows.length;i++){
    z=rows[i]||{};
    if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z
  }
  for(i=0;i<hs.length;i++){
    h=hs[i];z=map[n(h.horseNumber)];
    if(!z)continue;
    var wasScratch=isScratchHorse(h);
    // An odds-only refresh must carry the withdrawal state even when its
    // updated horse has no odds and no body weight.
    var liveScratch=z.scratched===true||z.withdrawn===true||
      /欠場|出走取消|取消|競走除外|除外/.test(String(z.status||z.horse_status||''));
    if(liveScratch&&!wasScratch){
      h.scratched=true;
      h.status=String(z.status||z.horse_status||'出走取消');
      h.winOdds=null;h.popularity=null;
      changed=true;predictionInputChanged=true
    }
    if(wasScratch||liveScratch)continue;
    if(z.winOdds!=null&&String(z.winOdds)!==''){
      if(String(h.winOdds||'')!==String(z.winOdds))changed=true;
      h.winOdds=z.winOdds
    }
    if(z.popularity!=null&&String(z.popularity)!==''){
      if(String(h.popularity||'')!==String(z.popularity))changed=true;
      h.popularity=z.popularity
    }
    if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){
      old=String(h.bodyWeight||'');
      if(old!==String(z.bodyWeight)){changed=true;predictionInputChanged=true}
      h.bodyWeight=z.bodyWeight
    }
    if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){
      old=String(h.bodyWeightChange||'');
      if(old!==String(z.bodyWeightChange)){changed=true;predictionInputChanged=true}
      h.bodyWeightChange=z.bodyWeightChange
    }
    if(z.status!=null&&String(z.status)!==''){
      if(String(h.status||'')!==String(z.status)){changed=true;predictionInputChanged=true}
      h.status=z.status
    }
    if(z.oddsSource)h.oddsSource=z.oddsSource;
    if(z.oddsForecast===false)h.oddsForecast=false
  }
  if(body.oddsSource)state.race.oddsSource=body.oddsSource;
  if(body.sourcePublishedAt)state.race.sourcePublishedAt=body.sourcePublishedAt;
  if(body.popularitySource)state.race.popularitySource=body.popularitySource;
  if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;
  if(predictionInputChanged){
    try{delete state.race._prediction}catch(e){}
    state.pred=null;state.analysisSaved={}
  }
  return changed
}
function refreshRaceAfterCollect(id,attempt){reloadCurrent()}
function collectRaceInfo(no){reloadCurrent()}
function stopTimer(){if(state.timer){clearTimeout(state.timer);state.timer=null}if(state.anim){cancelAnimationFrame(state.anim);state.anim=null}state.simRunning=false}
function drawPaceStage(idx){state.paceStage=clamp(n(idx,0),0,3)}
function render(){
  var savedY=window.scrollY;
  syncLocation();stopTimer();
  try{
    var view=state.raceLoading?renderRaceLoading():(state.race?renderRace():(state.picker?renderPicker():(state.track?renderVenue():(state.homePage?renderHomeSectionPage():renderHome()))));
    app.innerHTML=view+smartTodayReturn();
    arvexqBootPainted=true;
    syncLiveCenterOverlay();
    bind();
    if(entryDataAvailable(state.race)&&state.race._prediction){initPaceBoard();ensureAutoOdds(state.race);scheduleRaceBiasRefresh(700)}
    else if(state.track&&!state.picker){scheduleVenueTrendRefresh(350)}
    // The result and payout lane must work even when AI diagnosis is unavailable.
    if(state.race) scheduleResultRefresh();
    if(entryDataAvailable(state.race))ensureAutoOdds(state.race)
    window.scrollTo(0,savedY)
  }catch(e){
    try{console.error('ARVEXQ render recovery',e)}catch(_e){}
    try{
      if(app){
        var old=app.querySelector('#arvexq-runtime-recovery');if(old)old.remove();
        var note=document.createElement('div');note.id='arvexq-runtime-recovery';note.className='diagnosis-refresh-note busy';
        note.setAttribute('role','status');note.style.margin='8px 12px';
        note.textContent='一部データを再取得中です。表示できている情報はそのまま維持します。';
        app.insertBefore(note,app.firstChild);
        try{bind()}catch(_bindError){}
        setTimeout(function(){try{if(note&&note.parentNode)note.parentNode.removeChild(note)}catch(_removeError){}},2200)
      }
    }catch(_uiError){}
  }
}
function canGoBack(){return !!(state.subPage||state.horseModalNo||state.raceLoading||state.race||state.picker||state.track||state.homePage||state.aiStatsTrack)}
function goBack(){
    if(!canGoBack())return;
    if(state.subPage){
        // A stale subPage flag must not consume the race-level × click. Only
        // a visibly rendered child screen gets its own close navigation.
        var nestedVisible=!!document.querySelector('[data-action="close-race-subpage"]');
        state.subPage=null;state.openPanel=state.subPageReturnPanel||'entry';state.subPageReturnPanel=null;
        if(nestedVisible){window.scrollTo(0,0);render();return}
    }
    if(state.horseModalNo){
        if(document.querySelector('.horse-modal-layer')){closeHorseModal();return}
        state.horseModalNo=null
    }
    ++state.detailSeq;
    if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
    if(state.collectTimer){clearTimeout(state.collectTimer);state.collectTimer=null}
    state.collectingHorse=null;state.error=null;state.pred=null;state.scenarioCode=null;state.paceStage=0;

    if(state.raceLoading||state.race){
        if(state.raceStack.length){
            // A past-race detail returns to the race detail that opened it.
            state.raceLoading=null;
            state.race=state.raceStack.pop();
            state.picker=false;
            if(state.race&&state.race.track)state.track=state.race.track
        }else if(state.raceReturnHomePage){
            state.raceLoading=null;state.race=null;state.picker=false;state.track=null;
            state.homePage=state.raceReturnHomePage;state.pickCircuit=state.raceReturnPickCircuit||null;
            state.raceReturnHomePage=null;state.raceReturnPickCircuit=null
        }else{
            // A normal race detail returns to this venue's full race list.
            var keepTrack=state.track||(state.race&&state.race.track)||"";
            state.raceLoading=null;
            state.race=null;
            state.picker=false;
            state.track=keepTrack||null
        }
    }else if(state.picker){
        state.picker=false;
        state.track=null
    }else if(state.track){
        state.track=null;
        state.picker=false
    }else if(state.aiStatsTrack){
        state.aiStatsTrack=null
    }else if(state.pickCircuit){
        state.pickCircuit=null
    }else if(state.homePage){
        state.homePage=null;
        state.pickCircuit=null;
        state.aiStatsTrack=null
    }

    // Do not use browser history for the × button; keep app hierarchy deterministic.
    routeKey=null;
    render();
    window.scrollTo(0,0)
}
var navigationRestoring=false,routeKey=null;
function locationState(){return {tab:state.detailTab||'出走表',date:state.date,circuit:state.circuit,track:state.track,picker:state.picker,home:state.homePage||'',pick_circuit:state.pickCircuit||'',ai_track:state.aiStatsTrack||'',race_id:String(state.raceLoading||(state.race&&state.race.id)||''),horse:null,stack:state.raceStack.map(function(r){return r.id}),returnPicker:state.raceReturnPicker}}
function syncLocation(){if(navigationRestoring||!window.history)return;var view=locationState(),key=JSON.stringify(view);if(key===routeKey)return;var u=new URL(window.location.href);u.pathname=view.race_id?'/race':(view.track?'/venue':(view.home?'/section':'/'));['date','circuit','track','race_id','horse','tab','home','pick_circuit','ai_track'].forEach(function(k){if(view[k])u.searchParams.set(k,view[k]);else u.searchParams.delete(k)});if(view.picker)u.searchParams.set('picker','1');else u.searchParams.delete('picker');u.searchParams.delete('pwa');var prior=window.history.state||{},depth=n(prior.keibaDepth);if(routeKey===null)window.history.replaceState({keibaDepth:depth,view:view},'',u);else window.history.pushState({keibaDepth:depth+1,view:view},'',u);routeKey=key}
function normalizeInitialAppLaunch(){
  try{
    var standalone=!!((window.matchMedia&&window.matchMedia('(display-mode: standalone)').matches)||window.navigator.standalone===true);
    if(!standalone)return;
    var u=new URL(window.location.href),t=today(),d=u.searchParams.get('date');
    // A fresh ARVEXQ app launch always starts from today's home. Historical
    // navigation inside the running app is still preserved and has the 今日へ button.
    if(d&&d!==t){
      u.searchParams.set('date',t);
      ['race_id','track','picker','horse','tab','home','pick_circuit','ai_track'].forEach(function(k){u.searchParams.delete(k)});
      window.history.replaceState({},'',u.pathname+(u.searchParams.toString()?'?'+u.searchParams.toString():'')+u.hash);
    }
  }catch(e){}
}
function restoreLocation(){var u=new URL(window.location.href),saved=(window.history.state||{}).view||{},id=u.searchParams.get('race_id');navigationRestoring=true;++state.detailSeq;state.raceLoading=null;state.race=null;state.horseModalNo=n(u.searchParams.get('horse'))||null;state.detailTab=u.searchParams.get('tab')||'出走表';state.date=u.searchParams.get('date')||today();state.circuit=u.searchParams.get('circuit')||'中央';state.track=u.searchParams.get('track')||null;state.picker=u.searchParams.get('picker')==='1';state.homePage=u.searchParams.get('home')||null;state.pickCircuit=u.searchParams.get('pick_circuit')||null;state.aiStatsTrack=u.searchParams.get('ai_track')||null;state.raceReturnPicker=!!saved.returnPicker;state.raceStack=(saved.stack||[]).map(loadDetailCache).filter(Boolean);if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}var horse=state.horseModalNo;if(id){var cached=loadDetailCache(id);if(cached){state.race=cached;render()}else{openRace(id,true,true);state.horseModalNo=horse}}else render();navigationRestoring=false;routeKey=null;syncLocation()}
function installNavigation(){window.addEventListener('popstate',restoreLocation)}
function installEdgeBack(){
    var gesture=null,suppressClickUntil=0;
    document.addEventListener('touchstart',function(e){
        gesture=null;if(e.touches.length!==1||!canGoBack())return;
        var t=e.touches[0];if(t.clientX>28)return;
        if(e.target.closest&&e.target.closest('input,textarea,select,[contenteditable="true"]'))return;
        gesture={id:t.identifier,x:t.clientX,y:t.clientY,time:Date.now(),locked:false};
    },{passive:true});
    document.addEventListener('touchmove',function(e){
        if(!gesture)return;if(e.touches.length!==1){gesture=null;return}
        var t=e.touches[0],dx=t.clientX-gesture.x,dy=Math.abs(t.clientY-gesture.y);
        if(t.identifier!==gesture.id||dx < -8||(!gesture.locked&&dy>12&&dy>=Math.abs(dx))){gesture=null;return}
        if(dx>12&&dx>dy*1.5)gesture.locked=true;
        if(gesture.locked&&e.cancelable)e.preventDefault();
    },{passive:false});
    document.addEventListener('touchend',function(e){
        var g=gesture;gesture=null;if(!g||e.touches.length)return;
        var t=e.changedTouches[0];if(!t||t.identifier!==g.id)return;
        var dx=t.clientX-g.x,dy=Math.abs(t.clientY-g.y);
        if(dx>=80&&dx>dy*1.5&&Date.now()-g.time<1200){
            if(e.cancelable)e.preventDefault();suppressClickUntil=Date.now()+450;goBack();
        }
    },{passive:false});
    document.addEventListener('touchcancel',function(){gesture=null},{passive:true});
    document.addEventListener('click',function(e){if(Date.now()<suppressClickUntil){e.preventDefault();e.stopImmediatePropagation()}},true);
}

function refreshDiagnosisNow(id){
  if(!id||!state.race)return;
  state.diagnosisBusy=false;
  state.analysisSaved={};
  try{delete state.race._prediction}catch(e){}
  state.pred=null;
  render()
}
function pollDiagnosisRefresh(id,attempt){return}

function bind(){document.querySelectorAll('[data-home-close]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.homePage=null;state.pickCircuit=null;state.aiStatsTrack=null;state.raceStack=[];state.track=null;state.race=null;state.picker=false;render();window.scrollTo(0,0)}});document.querySelectorAll('[data-home-page]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.raceStack=[];state.homePage=this.getAttribute('data-home-page')||null;state.pickCircuit=null;state.aiStatsTrack=null;state.track=null;state.race=null;state.picker=false;window.scrollTo(0,0);if(state.homePage==='ai-stats')setTimeout(scheduleDailyAiStats,0);render()}});document.querySelectorAll('[data-pick-circuit]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.pickCircuit=this.getAttribute('data-pick-circuit')||null;window.scrollTo(0,0);render()}});document.querySelectorAll('[data-ai-stats-track]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.aiStatsTrack=this.getAttribute('data-ai-stats-track')||null;window.scrollTo(0,0);render()}});document.querySelectorAll('[data-detail-retry]').forEach(function(el){el.onclick=function(e){e.preventDefault();openRace(el.getAttribute('data-detail-retry'),true,true,true)}});document.querySelectorAll('[data-selected-section]').forEach(function(el){el.ontoggle=function(){var k=el.getAttribute('data-selected-section');if(k==='selected')selectedSectionsOpen[k]=!!el.open}});document.querySelectorAll('[data-selected-circuit]').forEach(function(el){el.ontoggle=function(){var k=el.getAttribute('data-selected-circuit'),c=el.getAttribute('data-pick-circuit');if(k==='selected'&&(c==='中央'||c==='地方'))selectedCircuitSectionsOpen[k][c]=!!el.open}});document.querySelectorAll('[data-panel]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}var key=el.getAttribute('data-panel'),opening=state.openPanel!==key;if(key==='bets'){state.subPageReturnPanel=state.openPanel||'entry';state.subPage='bets';window.scrollTo(0,0);render();return}if(key==='detail'&&state.race&&!state.detailHorseNo){var hs=(state.race.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)});if(hs.length)state.detailHorseNo=n(hs[0].horseNumber)}state.openPanel=opening?key:null;render();if(opening&&key==='result'&&state.race&&isFinal(state.race)&&!(((state.race.result||{}).payouts||[]).length))setTimeout(function(){refreshPayoutsOnly(0)},0)}});document.querySelectorAll('[data-action="odds-update"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}refreshOddsOnly(true)}});document.querySelectorAll('[data-action="copy-bet"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}copyCurrentBet()}});document.querySelectorAll('[data-action="open-bets-page"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.subPageReturnPanel=state.openPanel||'entry';state.subPage='bets';window.scrollTo(0,0);render()}});document.querySelectorAll('[data-action="close-race-subpage"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.subPage=null;state.openPanel=state.subPageReturnPanel||'entry';state.subPageReturnPanel=null;window.scrollTo(0,0);render()}});document.querySelectorAll('[data-action="live-open"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}liveCenterOpen=true;liveCenterTrack='';liveCenterCircuit='';render()}});document.querySelectorAll('[data-action="live-close"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}liveCenterOpen=false;render();setTimeout(fastReflectNow,150)}});document.querySelectorAll('[data-action="today-return"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}returnToToday()}});document.querySelectorAll('[data-live-track]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}liveCenterTrack=this.getAttribute('data-live-track')||'';liveCenterCircuit=this.getAttribute('data-live-circuit')||'';render()}});document.querySelectorAll('[data-dashboard-tab]').forEach(function(el){el.onclick=function(){state.detailTab=el.getAttribute('data-dashboard-tab');var id=el.getAttribute('data-tab-race');if(state.race&&String(state.race.id)===id)render();else openRace(id,false,false)}});document.querySelectorAll('.cinema-venue img').forEach(function(img){img.onerror=function(){this.style.display='none';var parent=this.parentElement;if(parent&&!parent.querySelector('.venue-photo-missing')){var label=document.createElement('span');label.className='venue-photo-missing';label.textContent='写真を読み込めません';parent.appendChild(label)}}});document.querySelectorAll('[data-date]').forEach(function(el){el.onclick=function(){++state.detailSeq;state.raceLoading=null;state.date=el.getAttribute('data-date');state.openPanel=null;state.subPage=null;state.detailHorseNo=null;state.race=null;state.track=null;state.picker=false;load()}});document.querySelectorAll('[data-detail-tab]').forEach(function(el){el.onclick=function(){state.detailTab=el.getAttribute('data-detail-tab');render()}});var els=document.querySelectorAll('[data-circuit]'),i;for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.circuit=this.getAttribute('data-circuit');state.homePage=null;state.aiStatsTrack=null;state.openPanel=null;state.track=null;state.race=null;state.picker=false;load()};var d=document.getElementById('date');if(d)d.onchange=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.date=this.value;if(!state.homePage){state.aiStatsTrack=null;state.pickCircuit=null}state.openPanel=null;state.track=null;state.race=null;state.picker=false;load()};els=document.querySelectorAll('[data-track]');for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.race=null;state.pred=null;state.picker=false;state.track=this.getAttribute('data-track');var dc=this.getAttribute('data-circuit');if(dc)state.circuit=dc;state.openPanel=null;state.subPage=null;state.detailHorseNo=null;state.detailTab='出走表';mergeCachedVolatilityForTrack(state.track);window.scrollTo(0,0);render()};els=document.querySelectorAll('[data-special-fold]');for(i=0;i<els.length;i++)els[i].ontoggle=function(){state.specialForecastOpen=!!this.open;try{localStorage.setItem('arvexq-special-forecast-open',this.open?'1':'0')}catch(e){}};els=document.querySelectorAll('[data-race]');for(i=0;i<els.length;i++)els[i].onclick=function(){var id=this.getAttribute('data-race'),row=state.races.find(function(x){return String(x.id)===String(id)}),preserve=this.getAttribute('data-preserve-panel')==='1';if(state.homePage&&(state.homePage==='selected'||state.homePage==='special')){state.raceReturnHomePage=state.homePage;state.raceReturnPickCircuit=state.pickCircuit}else{state.raceReturnHomePage=null;state.raceReturnPickCircuit=null}if(row){state.track=row.track;if(row.circuit)state.circuit=row.circuit}window.scrollTo(0,0);openRace(id,false,false,preserve)};els=document.querySelectorAll('[data-past-race]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openPastRace(this.getAttribute('data-past-race'))};var b=document.querySelectorAll('[data-action="back"]');for(i=0;i<b.length;i++)b[i].onclick=goBack;var rr=document.querySelectorAll('[data-action="reload"]');for(i=0;i<rr.length;i++)rr[i].onclick=reloadCurrent;var fi=document.querySelectorAll('[data-action="fetch-all-info"]');for(i=0;i<fi.length;i++)fi[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(null)};var rh=document.querySelectorAll('[data-action="retry-history"]');for(i=0;i<rh.length;i++)rh[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(null)};els=document.querySelectorAll('[data-horse-fetch]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(this.getAttribute('data-horse-fetch'))};var ar=document.querySelectorAll('[data-action="all-races"]');for(i=0;i<ar.length;i++)ar[i].onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};var pn=document.querySelector('[data-action="pace-next"]');if(pn)pn.onclick=function(){var x=nextRace();if(x){openRace(x.id,false,false,true)}};var pp=document.querySelector('[data-action="pace-pick"]');if(pp)pp.onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};els=document.querySelectorAll('[data-horse-check]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}if(state.race)toggleHorseChecked(state.race,this.getAttribute('data-horse-check'))};els=document.querySelectorAll('[data-horse-open]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openHorseDetailPage(this.getAttribute('data-horse-open'))};els=document.querySelectorAll('[data-detail-horse]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.detailHorseNo=n(this.getAttribute('data-detail-horse'));state.openPanel='detail';render();var panel=document.getElementById('section-detail');if(panel)setTimeout(function(){panel.scrollIntoView({block:'start',behavior:'smooth'})},0)};els=document.querySelectorAll('[data-detail-prev]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveDetailHorse(-1)};els=document.querySelectorAll('[data-detail-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveDetailHorse(1)};els=document.querySelectorAll('[data-horse-close]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}closeHorseModal()};els=document.querySelectorAll('[data-horse-prev]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(-1)};els=document.querySelectorAll('[data-horse-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(1)};els=document.querySelectorAll('[data-scenario-code]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.scenarioCode=this.getAttribute('data-scenario-code');state.paceStage=0;render()};els=document.querySelectorAll('[data-pace-open]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openPaceStagePage(this.getAttribute('data-pace-open'))};els=document.querySelectorAll('[data-pace-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openPaceStagePage(this.getAttribute('data-pace-next'))};els=document.querySelectorAll('[data-pace-stage]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}drawPaceStage(n(this.getAttribute('data-pace-stage'),0))};var board=document.getElementById('pace-board');if(board){board.onclick=function(e){if(e&&e.target&&e.target.closest&&e.target.closest('button,a,input,select,textarea'))return;var rect=board.getBoundingClientRect(),plan=activeScenarioPlan(state.pred),len=(plan&&plan.stages?plan.stages.length:0);if(!len)return;var cur=n(state.paceStage,0),dir=(e.clientX-rect.left)<rect.width/2?-1:1,nx=(cur+dir+len)%len;drawPaceStage(nx)}}var panel=document.getElementById('horse-modal-panel');if(panel){panel.onclick=function(e){if(e&&e.target&&e.target.closest&&e.target.closest('button,a,input,select,textarea,summary'))return;var rect=panel.getBoundingClientRect();moveHorseModal((e.clientX-rect.left)<rect.width/2?-1:1)}}}
function initPaceBoard(){return}

function hydrateInstantFromDevice(rows){
  var count=0;
  (rows||[]).forEach(function(r){
    if(!r||!r.id)return;
    var d=loadDetailCache(r.id);
    if(d){instantTrackDetails[String(r.id)]=d;count++}
  });
  return count
}
function applyMorningArchive(rows){
  var archive=state.morningArchive;
  if(!archive||archive.date!==state.date||!Array.isArray(archive.races))return rows;
  var picks={};
  archive.races.forEach(function(x){if(x&&x.id)picks[String(x.id)]=x});
  (rows||[]).forEach(function(r){
    if(!r||!r.id)return;
    var frozen=picks[String(r.id)];
    if(!frozen)return;
    var m={
      version:'v1',fixedAt:archive.fixedAt,scope:archive.scope,
      selected:frozen.selected===true,selectedScore:n(frozen.selectedScore,0),
      special:frozen.special===true,assessed:frozen.assessed!==false,
       primaryType:String(frozen.primaryType||''),types:Array.isArray(frozen.types)?frozen.types.slice():[],
       selectionReason:String(frozen.selectionReason||''),
       ticketKinds:Array.isArray(frozen.ticketKinds)?frozen.ticketKinds.slice():[],
       ticketEvidence:frozen.ticketEvidence||null
    };
    if(!m.ticketEvidence&&window.ARVEXQSavedTicketReceipt)m.ticketEvidence=window.ARVEXQSavedTicketReceipt.recover(r,m);
    r.morningPickVersion='v1';
    r.morningPickFixedAt=archive.fixedAt;
    r.morningPickScope=archive.scope;
    r.morningSelected=m.selected;r.morningSelectedScore=m.selectedScore;
    r.morningSpecial=m.special;r.morningAssessed=m.assessed;
     r.morningPrimaryType=m.primaryType;r.morningSelectedTypes=m.types.slice();
     r.morningSelectionReason=m.selectionReason;r.morningTicketKinds=m.ticketKinds.slice();
     r.morningTicketEvidence=m.ticketEvidence;
     if(m.ticketEvidence&&window.ARVEXQMorningEvidence&&window.ARVEXQMorningEvidence.verify(r,m.ticketEvidence)){
       var d=instantTrackDetails[String(r.id)];
       if(d&&String(d.date||'')===String(r.date))d.morningTicketEvidence=m.ticketEvidence;
     }
    r.volatility=Object.assign({},r.volatility||{},{morningPicks:m});
    r.environmentMeta=Object.assign({},r.environmentMeta||{},{morningPicks:m})
  });
  return rows
}
function mergeBootstrap(body){
  var rows=(body&&body.races)||[],details=(body&&body.details)||[],pvol={};
  state.bootstrapReady=!!(body&&body.complete===true);
  details.forEach(function(d){
    if(!d||!d.id)return;
    instantTrackDetails[String(d.id)]=d;
    saveDetailCache(d.id,d);
    if(d.volatility)pvol[String(d.id)]=d.volatility
  });
  rows.forEach(function(r){
    var d=instantTrackDetails[String(r.id)];
    if(d){
      if(d.volatility){
        var morning=morningPickOf(r);
        r.volatility=Object.assign({},d.volatility);
        if(morning)r.volatility.morningPicks=morning
      }
      if(d.weather&&d.weather!=='不明')r.weather=d.weather;
      if(d.condition&&d.condition!=='不明')r.condition=d.condition;
      if(d.oddsUpdatedAt)r.oddsUpdatedAt=d.oddsUpdatedAt
    }else if(pvol[String(r.id)]){
      r.volatility=pvol[String(r.id)]
    }
  });
  return applyMorningArchive(rows)
}


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
function fastReflectNow(){
  if(document.visibilityState==='hidden'||liveCenterOpen)return;
  var now=Date.now();if(now-n(fastReflectNow._lastAt,0)<2500)return;fastReflectNow._lastAt=now;
  try{
    if(state.race&&state.race.id){refreshOddsOnly(true);return}
    if(!state.track&&!state.picker&&typeof fastTopRefresh==='function')fastTopRefresh()
  }catch(e){}
}
window.addEventListener('pageshow',function(){setTimeout(fastReflectNow,120)},{passive:true});
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')setTimeout(fastReflectNow,120)},{passive:true});
setInterval(function(){
  if(document.visibilityState==='hidden'||state.date!==today()||state.race||state.raceLoading||
     state.track||state.picker||state.homePage)return;
  var shared=window.ARVEXQUnifiedHome;
  if(!shared||!document.querySelector('.smart-shell.smart-home .arv-all-panel'))return;
  shared.syncLiveUI('horse',state.races||[],state.date,document);
},10000);
installNavigation();installEdgeBack();installPullRefresh();installPwaCache();evictRetiredRaceCaches();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);
})();
