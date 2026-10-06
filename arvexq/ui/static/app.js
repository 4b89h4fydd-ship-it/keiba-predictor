window.ARVEXQ_BUILD="v325";

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
function courseProfile(r){return COURSE[r.track]||{lap:1400,straight:300,dir:-1,shape:"wide",turn:"右",firstTurn:300}}
function firstTurnDistance(r){r=r||{};var direct=n(r.firstTurnDistance||r.startToFirstTurn||r.firstCornerDistance||r.firstCornerMeters,0);return direct>0?direct:n(courseProfile(r).firstTurn,300)}
function coursePathD(p){if(p.shape==="straight")return "M18 92 L182 92";if(p.shape==="round")return "M174 90 C174 42 142 18 97 18 C50 18 22 46 22 90 C22 134 50 162 97 162 C142 162 174 138 174 90 Z";if(p.shape==="long")return "M184 90 C184 53 160 34 126 34 L67 34 C34 34 16 54 16 90 C16 126 34 146 67 146 L126 146 C160 146 184 127 184 90 Z";if(p.shape==="boxy")return "M178 90 C178 57 158 36 130 32 L66 32 C36 36 20 58 20 90 C20 122 36 144 66 148 L130 148 C158 144 178 123 178 90 Z";if(p.shape==="pocket")return "M176 91 C176 52 151 29 116 27 L69 30 C36 33 18 56 20 91 C21 126 40 147 73 151 L124 147 C157 142 176 122 176 91 Z";if(p.shape==="spiral")return "M178 91 C178 52 154 31 118 29 L72 31 C38 33 18 56 20 91 C22 128 44 148 78 149 L125 145 C157 140 178 120 178 91 Z";if(p.shape==="egg")return "M177 91 C177 49 147 25 106 24 C66 23 31 43 21 78 C11 113 31 146 71 154 C115 162 158 142 174 111 C178 103 179 97 177 91 Z";return "M176 90 C176 51 151 28 116 28 L72 28 C38 28 20 51 20 90 C20 129 38 152 72 152 L116 152 C151 152 176 129 176 90 Z"}
function normFrac(x){x=x%1;return x<0?x+1:x}
function courseStageFrac(r,st){var p=courseProfile(r);if(p.shape==="straight")return st===0?.05:(st===1?.67:.92);var laps=Math.max(.1,n(r.distance,1200)/p.lap),start=normFrac(.965-p.dir*(laps%1)),prog=st===0?.015:(st===1?.81:.965);return normFrac(start+p.dir*laps*prog)}
var app=document.getElementById("app");
var state={date:today(),circuit:"地方",races:[],track:null,race:null,raceLoading:null,picker:false,loading:false,error:null,timer:null,anim:null,simSpeed:5,simTarget:20,simRunning:false,simPaused:false,simStopped:false,simIndex:0,simDone:0,simCounts:null,simCurrentT:0,pred:null,requestSeq:0,detailSeq:0,raceReturnPicker:false,historyTimer:null,raceStack:[],historyPrefetch:{},paceStage:0,horseModalNo:null,detailHorseNo:null,collectingHorse:null,collectTimer:null,scenarioCode:null,analysisSaved:{},openPanel:null,oddsBusy:false,oddsRefreshAt:{},oddsTimer:null,environmentTimer:null,environmentBusy:false,bootstrapReady:false,bootstrapProgress:null,resultTimer:null};
var dailyAiStats={date:"",loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,centralPodiumHits:0,centralPodiumTotal:0,localPodiumHits:0,localPodiumTotal:0,markedPodiumSum:0,holePlaceHits:0,top2Hits:0,top3Hits:0,candidateOrderMisses:0,candidateMisses:0,highConfHits:0,highConfTotal:0,brierSum:0,logLossSum:0,reasons:{},error:""},dailyAiStatsJob=0;
var liveCenterOpen=false,liveCenterTrack="",liveCenterCircuit="";

function cacheKey(d,c){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":races:"+d+":"+(c||state.circuit||"")}
function loadRaceCache(d,c){try{var raw=localStorage.getItem(cacheKey(d,c));if(!raw)return null;var x=JSON.parse(raw);if(!x||!Array.isArray(x.rows))return null;if(d>=today()&&Date.now()-n(x.ts)>2*60000)return null;return x.rows}catch(e){return null}}
function saveRaceCache(d,c,rows){try{localStorage.setItem(cacheKey(d,c),JSON.stringify({ts:Date.now(),rows:rows}))}catch(e){}}
function fullBundleKey(d){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":fullbundle:"+String(d||"")}
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
function detailCacheKey(id){return "arvexq:"+String(window.ARVEXQ_BUILD||"dev")+":detail:"+String(id||"")}
function loadDetailCache(id){try{var raw=localStorage.getItem(detailCacheKey(id));if(!raw)return null;var x=JSON.parse(raw);if(!x||!x.row)return null;var age=Date.now()-n(x.ts);if(x.row.date>=today()&&age>2*60000)return null;var r=x.row;if(!raceDisplayCoreReady(r,r))return null;return r}catch(e){return null}}
function saveDetailCache(id,row){try{if(!id||!row||!raceDisplayCoreReady(row,row))return;localStorage.setItem(detailCacheKey(id),JSON.stringify({ts:Date.now(),row:row}))}catch(e){}}
function installPwaCache(){
  try{
    if(!("serviceWorker" in navigator))return;
    var reloading=false;
    navigator.serviceWorker.addEventListener("controllerchange",function(){
      if(reloading)return;
      reloading=true;
      try{
        if(localStorage.getItem("arvexq-sw-reload")!=="v325-home-race-boxes-20261006"){
          localStorage.setItem("arvexq-sw-reload","v325-home-race-boxes-20261006");
          location.reload()
        }
      }catch(e){}
    });
    navigator.serviceWorker.register("/sw-v325-reset.js",{scope:"/"}).then(function(reg){
      try{reg.update()}catch(e){}
    }).catch(function(){})
  }catch(e){}
}
function today(){var d=new Date(Date.now()+9*3600000);return d.toISOString().slice(0,10)}
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
function hasResultData(r){var fs=((r&&r.result||{}).finishers||[]).filter(function(x){return n(x&&x.finish)>0});var ranks={};fs.forEach(function(x){ranks[n(x.finish)]=1});return !!(ranks[1]&&ranks[2]&&ranks[3])}
function mins(t){var m=String(t||"").match(/^(\d{1,2}):(\d{2})/);return m?n(m[1])*60+n(m[2]):9999}
function nowMins(){var d=new Date(Date.now()+9*3600000);return d.getUTCHours()*60+d.getUTCMinutes()}
function timeHtml(r){var a=String(r.startTime||"—"),o=String(r.scheduledStartTime||a),c=!!r.startTimeChanged||(a!==o&&a!=="—"&&o!=="—");return c?'<span class="time-old">'+esc(o)+'</span><span class="time-changed">'+esc(a)+' 修正</span>':esc(a)}
function header(title,back,sub){return '<header class="header"><div class="header-row">'+(back?'<button data-action="back">‹</button>':'')+'<div class="header-title"><h1>'+esc(title)+'</h1>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div><span class="build-badge" aria-label="ARVEXQ">ARVEXQ</span><button data-action="reload">↻</button></div></header>'}
function recencyWeights(len){var a=[],i;for(i=0;i<len;i++)a.push(Math.pow(.82,i));return a}
function weightedRate(vals,weights,def){var s=0,w=0,i;for(i=0;i<vals.length;i++){if(vals[i]==null)continue;var q=weights&&weights[i]!=null?weights[i]:1;s+=n(vals[i])*q;w+=q}return w?s/w:(def==null?.5:def)}
function raceField(rr){return Math.max(4,n(rr&&rr.fieldSize,12))}
function firstCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[0],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
function lastCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[p.length-1],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
function styleRates(h,r){var pc=h&&h.precomputedMetrics&&h.precomputedMetrics.style;if(pc&&n(pc.samples)>0)return{front:n(pc.front),stalk:n(pc.stalk),mid:n(pc.mid),close:n(pc.close),early3:n(pc.early3),moved3:n(pc.moved3),ten:n(pc.ten,.5),samples:n(pc.samples),unknown:false};var rs=(h.allPastRuns||h.recentRaces||[]),rw=recencyWeights(rs.length),c=[0,0,0,0],den=0,earlyDen=0,early3=0,moved3=0,tempoVals=[],tempoW=[],i,rr,p,pos,fs,norm,ww,delta,rel,j,bestLater;for(i=0;i<rs.length;i++){rr=rs[i];p=rr.cornerPositions||[];pos=n(p[0],0);if(!pos)continue;fs=raceField(rr);norm=(pos-1)/Math.max(1,fs-1);delta=Math.abs(n(rr.distance)-n(r&&r.distance));rel=1;if(delta<=100)rel*=1.22;else if(delta<=300)rel*=1.08;else if(delta>=700)rel*=.74;if(r&&rr.track===r.track)rel*=1.10;if(r&&sameCondition(rr.condition,r.condition))rel*=1.05;ww=rw[i]*rel;den+=ww;earlyDen+=ww;if(pos===1)c[0]+=ww;else if(pos<=3||norm<=.22)c[1]+=ww;else if(norm<=.62)c[2]+=ww;else c[3]+=ww;if(pos<=3)early3+=ww;bestLater=99;for(j=1;j<p.length;j++){var z=n(p[j],0);if(z&&z<bestLater)bestLater=z}if(pos>3&&bestLater<=3)moved3+=ww;tempoVals.push(clamp(1-(pos-1)/Math.max(3,fs-1),0,1));tempoW.push(ww)}if(!den)return{front:0,stalk:0,mid:0,close:0,early3:0,moved3:0,ten:.5,samples:0,unknown:true};return{front:c[0]/den,stalk:c[1]/den,mid:c[2]/den,close:c[3]/den,early3:earlyDen?early3/earlyDen:0,moved3:earlyDen?moved3/earlyDen:0,ten:weightedRate(tempoVals,tempoW,.5),samples:tempoVals.length,unknown:false}}
function tenScore(h,r){var rt=styleRates(h,r),rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),v=[],ws=[],i,rr,p,fs,delta,rel;for(i=0;i<rs.length;i++){rr=rs[i];p=rr.cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rr);delta=Math.abs(n(rr.distance)-n(r&&r.distance));rel=delta<=100?1.18:(delta<=300?1.05:.88);v.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1));ws.push((w[i]||1)*rel)}return clamp(weightedRate(v,ws,rt.ten)*.72+rt.front*.18+rt.early3*.10,0,1)}
function firstThreeType(h){var rr=(h.recentRaces||[])[0],p=rr&&rr.cornerPositions||[],j;if(!p.length)return"不明";if(n(p[0])>0&&n(p[0])<=3)return"最初から前";for(j=1;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3)return"途中から上昇";return"前走は中後方"}
function fadeRate(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),e=0,f=0,i,p,first,last,fin,fs,ww,sev;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];first=n(p[0]);if(!first||first>4)continue;ww=w[i];fs=raceField(rs[i]);e+=ww;last=n(p[p.length-1]);fin=n(rs[i].finish);sev=0;if(last)sev=Math.max(sev,clamp((last-first)/Math.max(3,fs-1)*2.2,0,1));if(fin)sev=Math.max(sev,clamp((fin-first)/Math.max(3,fs-1)*1.8,0,1));if((last&&last>=first+2)||(fin&&fin>=first+3))sev=Math.max(sev,.55);f+=ww*sev}return e?clamp(f/e,0,1):.25}
function moveRate(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),e=0,g=0,i,p,a,b,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(p.length<2)continue;a=n(p[0]);b=n(p[p.length-1]);if(!a||!b)continue;ww=w[i];e+=ww;if(b<=a-2)g+=ww}return e?g/e:.2}
function holdRate(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),e=0,g=0,i,p,a,b,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);b=n(p[p.length-1]);if(!a||a>4)continue;ww=w[i];e+=ww;if((b&&b<=4)||n(rs[i].finish)<=4)g+=ww}return e?g/e:.5}
function yieldFlex(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),e=0,g=0,i,p,a,fin,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);if(!a||a===1||a>5)continue;ww=w[i];e+=ww;if(fin>0&&fin<=4)g+=ww}return e?g/e:.45}

function breakReliability(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),v=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);v.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1))}return weightedRate(v,w,.5)}
function lateGainScore(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),v=[],i,p,a,b,fin,fs,g;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!p.length)continue;a=n(p[p.length-1]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||!fin)continue;g=(a-fin)/Math.max(3,fs-1);v.push(clamp(.5+g*1.8,0,1))}return weightedRate(v,w,.5)}
function positionConsistency(h){var rs=(h.allPastRuns||h.recentRaces||[]),vals=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);vals.push((n(p[0])-1)/Math.max(3,fs-1))}if(vals.length<2)return.5;var m=mean(vals),vv=0;for(i=0;i<vals.length;i++)vv+=(vals[i]-m)*(vals[i]-m);vv/=vals.length;return clamp(1-Math.sqrt(vv)*2.1,0,1)}
function positionTrend(h){var rs=(h.allPastRuns||h.recentRaces||[]).slice(0,5),vals=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);vals.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1))}if(vals.length<3)return 0;var cut=Math.min(2,vals.length-1),recent=mean(vals.slice(0,cut)),older=mean(vals.slice(cut));return clamp(recent-older,-.45,.45)}
function earlyCollapseSeverity(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),vals=[],ws=[],i,p,a,fin,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||a>4||!fin)continue;vals.push(clamp((fin-a)/Math.max(3,fs-1),0,1));ws.push(w[i])}return weightedRate(vals,ws,.18)}
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
function sameDayCorrectionProfileV313(r,rows){
  rows=rows||[];
  var date=String(r&&r.date||state.date||''),circuit=String(r&&r.circuit||state.circuit||''),track=String(r&&r.track||state.track||''),raceNo=n(r&&r.raceNumber,99),
      completed=0,markRaces=0,fullHit=0,styleN=0,podiumFront=0,podiumLate=0,missN=0,missFront=0,missLate=0,frameN=0,inner=0,outer=0,source=[];
  (state.races||[]).forEach(function(z){
    if(!z||String(z.date||date)!==date||String(z.circuit||'')!==circuit||String(z.track||'')!==track||n(z.raceNumber,99)>=raceNo)return;
    var d=resultDetailForTrend(z),fs=((d&&d.result||{}).finishers||[]).filter(function(x){return n(x&&x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)}).slice(0,3);
    if(fs.length<3)return;
    completed++;source.push(n(z.raceNumber));
    var marks=aiStoredMarks(d),marked={};marks.forEach(function(x){if(['◎','○','▲','☆+','☆','△','注+','注'].indexOf(String(x.mark||''))>=0)marked[n(x.no)]=1});
    var comparable=Object.keys(marked).length>0;if(comparable){markRaces++;var all=fs.every(function(f){return !!marked[n(f.horseNumber)]});if(all)fullHit++}
    var field=Math.max(1,n(d.fieldSize,(d.horses||[]).length||fs.length)),frontCut=Math.max(2,Math.ceil(field*.25)),lateCut=Math.max(frontCut+1,Math.ceil(field*.55));
    fs.forEach(function(f){
      var cp=(f.cornerPositions||[]).filter(function(v){return n(v)>0}),pos=n(cp[0],0),isFront=pos>0&&pos<=frontCut,isLate=pos>0&&pos>=lateCut;
      if(pos){styleN++;if(isFront)podiumFront++;if(isLate)podiumLate++}
      var h=(d.horses||[]).find(function(q){return n(q.horseNumber)===n(f.horseNumber)})||{},fr=n(f.frameNumber,n(h.frameNumber,0));
      if(fr){frameN++;var maxFrame=Math.max(2,Math.min(8,Math.ceil(field/2))),inside=clamp(1-(fr-1)/Math.max(1,maxFrame-1),0,1);inner+=inside;outer+=1-inside}
      if(comparable&&!marked[n(f.horseNumber)]){missN++;if(isFront)missFront++;if(isLate)missLate++}
    })
  });
  var sample=completed>=2?clamp((completed-1)/4,0,1):0,coverage=markRaces?fullHit/markRaces:.83,deficit=markRaces?clamp((.83-coverage)/.50,0,1):0,
      frontShare=styleN?podiumFront/styleN:.34,lateShare=styleN?podiumLate/styleN:.26,innerShare=frameN?inner/frameN:.5,
      missFrontShare=missN?missFront/missN:.33,missLateShare=missN?missLate/missN:.33,
      evidence=clamp(sample*(.62+.38*Math.min(1,styleN/9))*(.72+.28*Math.min(1,completed/4)),0,1),
      frontSignal=clamp((frontShare-.34)*2.15+(missFrontShare-.33)*deficit*.80,-.42,.42)*evidence,
      lateSignal=clamp((lateShare-.26)*2.30+(missLateShare-.33)*deficit*.88,-.42,.42)*evidence,
      innerSignal=clamp((innerShare-.5)*1.65,-.30,.30)*evidence,byNo={};
  rows.forEach(function(z){
    var h=z.horse||{},rt=styleRates(h,r),early=clamp(rt.front*.52+rt.stalk*.30+rt.early3*.18,0,1),late=clamp(rt.mid*.30+rt.close*.48+rt.moved3*.22,0,1),
        fr=n(h.frameNumber,0),maxFrame=Math.max(2,Math.min(8,Math.ceil(Math.max(2,rows.length)/2))),inside=fr?clamp(1-(fr-1)/Math.max(1,maxFrame-1),0,1):.5,
        raw=frontSignal*(early-late)+lateSignal*(late-early)+innerSignal*(inside-.5)*1.35,
        coreScale=markRaces>=3?1:(markRaces>=2?.55:.35),
        markBoost=clamp(raw,-.06,.06),winBoost=clamp(raw*.18*coreScale,-.012,.012),p2Boost=clamp(raw*.38*coreScale,-.030,.030),p3Boost=clamp(raw*.65*(.75+.25*deficit)*coreScale,-.055,.055);
    byNo[n(h.horseNumber)]={markBoost:markBoost,winBoost:winBoost,p2Boost:p2Boost,p3Boost:p3Boost,early:early,late:late,inside:inside}
  });
  var flow=(lateSignal>=.055&&lateSignal>=Math.abs(frontSignal)*.85)?'差し・追込':((frontSignal>=.055&&frontSignal>=Math.abs(lateSignal)*.85)?'前残り':(frontSignal<=-.055?'前不利':(lateSignal<=-.055?'差し不利':'')));
  if(!flow&&Math.abs(innerSignal)>=.06)flow=innerSignal>0?'内寄り':'外寄り';
  return {active:evidence>=.18&&completed>=2,completed:completed,markRaces:markRaces,evidence:evidence,coverage:coverage,deficit:deficit,frontSignal:frontSignal,lateSignal:lateSignal,innerSignal:innerSignal,flowLabel:flow||'中立',sourceRaces:source,byNo:byNo}
}
function sameDayTrendSignatureV313(r,rows){
  var a=raceLiveBias(r,rows),d=sameDayCorrectionProfileV313(r,rows);
  return JSON.stringify([a.sourceRaces,Math.round(a.frameBias*1000),Math.round(a.frontBias*1000),Math.round(a.lateBias*1000),d.sourceRaces,Math.round(d.evidence*1000),d.markRaces,Math.round(d.coverage*1000),Math.round(d.frontSignal*1000),Math.round(d.lateSignal*1000),Math.round(d.innerSignal*1000)])
}
function stylePoint(rt){return rt.front+2*rt.stalk+3*rt.mid+4*rt.close}
function styleName(pt){if(pt<1.65)return"逃げ";if(pt<2.35)return"先行";if(pt<3.15)return"差し";return"追込"}
function earlyOcc(r){var hs=r.horses||[],nums=[],early=[],moved=[],i,rr,p,j,hit;for(i=0;i<hs.length;i++){rr=(hs[i].recentRaces||[])[0];if(!rr)continue;p=rr.cornerPositions||[];hit=false;for(j=0;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3){hit=true;break}if(hit){nums.push(n(hs[i].horseNumber));if(n(p[0])<=3)early.push(n(hs[i].horseNumber));else moved.push(n(hs[i].horseNumber))}}return{nums:nums,early:early,moved:moved,rate:hs.length?nums.length/hs.length:0}}
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
function buildRows(r){var hs=r.horses||[],tmp=[],speeds=[],prizes=[],i,h,rt,pt,sr,fit,ct=courseTraits(r),cp=courseProfile(r),field=Math.max(1,hs.length);for(i=0;i<hs.length;i++){h=hs[i];rt=styleRates(h,r);pt=rt.samples?stylePoint(rt):9;sr=speedRaw(h,n(r.distance));fit=conditionFit(h,r);var cf=rt.samples?rt.front:.08,cs=rt.samples?rt.stalk:.28,cm=rt.samples?rt.mid:.40,cc=rt.samples?rt.close:.24,ce=rt.samples?rt.early3:.24,cmo=rt.samples?rt.moved3:.08;tmp.push({horse:h,front:cf,stalk:cs,mid:cm,close:cc,rawFront:rt.front,rawStalk:rt.stalk,rawMid:rt.mid,rawClose:rt.close,early3:ce,moved3:cmo,styleSamples:rt.samples,styleUnknown:!rt.samples,ten:tenScore(h,r),fade:fadeRate(h),move:moveRate(h),hold:holdRate(h),yieldFlex:yieldFlex(h),breakRel:breakReliability(h),lateGain:lateGainScore(h),posCons:positionConsistency(h),collapse:earlyCollapseSeverity(h),score:pt,pastStyle:rt.samples?styleName(pt):"履歴なし",expected:rt.samples?styleName(pt):"不明",speedRaw:sr,fit:fit});speeds.push(sr);prizes.push(n(h.prizeMoneyAtRace))}
for(i=0;i<tmp.length;i++){var x=tmp[i],hh=x.horse,rf=recentFirst(hh),rd=recentDistance(hh),distChange=rd?rd-n(r.distance):0,shorten=distChange>=150?1:0,lengthen=distChange<=-150?1:0,lengthenScale=rd?clamp((n(r.distance)-rd)/600,0,1):0,no=n(hh.horseNumber),draw=(no-1)/Math.max(1,field-1),outer=draw>.70?1:0,edge=no===field?1:0,inner=draw<.28?1:0,recentEarly=(rf<99?clamp((8-rf)/7,0,1):.5),posTrend=positionTrend(hh),jp=hh.jockeyProfile||{},jockeyFront=n(jp.early3Rate,0),leadHabit=n(jp.leaderRate,0),needLead=clamp(x.front*.78+Math.max(0,x.front-x.stalk)*.48+leadHabit*.10,0,1),flexibility=clamp(x.yieldFlex*.58+x.stalk*.25+x.mid*.12+(1-needLead)*.05,0,1),shortenBoost=shorten*(x.front*.12+x.stalk*.08+x.ten*.07),shortenPenalty=shorten*Math.max(0,.52-x.ten)*.18,lengthenBoost=lengthen*(x.stalk*.07+x.mid*.11+x.close*.05+(1-x.ten)*.055)+lengthenScale*.045,firstTurnRush=clamp(1-firstTurnDistance(r)/650,0,1),outerStress=outer*firstTurnRush*ct.turnLoad*(edge?.45:1),drawAdj=inner*ct.turnLoad*.055+edge*(1-ct.outerLoad)*.055-outerStress*.095,jf=hh.jockeyProfile?roleProfileScore(hh.jockeyProfile):genericRoleScore(hh.jockeyStats),tf=hh.trainerProfile?roleProfileScore(hh.trainerProfile):genericRoleScore(hh.trainerStats),trackFit=confidenceBlend(x.fit.track,x.fit.counts.track),distFit=confidenceBlend(x.fit.distance,x.fit.counts.distance),condFit=confidenceBlend(x.fit.condition,x.fit.counts.condition),weatherFit=confidenceBlend(x.fit.weather,x.fit.counts.weather),seasonFit=confidenceBlend(x.fit.season,x.fit.counts.season),levelFit=confidenceBlend(x.fit.level,x.fit.counts.level),speed=normalize(speeds,x.speedRaw),prize=normalize(prizes,n(hh.prizeMoneyAtRace)),baseAbility=recentFinishScore(hh)*.20+speed*.18+distFit*.11+trackFit*.08+condFit*.07+levelFit*.10+prize*.06+jf*.07+tf*.035+seasonFit*.02+weatherFit*.015+weightScore(hh)*.025+bodyWeightConditionScore(hh)*.040+ageSexScore(hh,r)*.025+x.lateGain*.025,dataN=Math.min(8,(hh.recentRaces||[]).length),coverage=clamp(dataN/5,0,1)*.60+clamp((x.fit.counts.distance+x.fit.counts.track)/4,0,1)*.22+clamp(n(jp.starts)/30,0,1)*.18,frontIntent=clamp(x.front*.36+x.stalk*.17+x.ten*.18+x.early3*.10+jockeyFront*.07+leadHabit*.05+needLead*.07+posTrend*.10,0,1.25),goBase=clamp(frontIntent+shortenBoost+lengthenBoost+drawAdj-shortenPenalty,0,1.25);x.forward=frontIntent;x.goProbBase=clamp(goBase*.72+x.breakRel*.14+x.ten*.14,0,1);x.goProb=x.goProbBase;x.needLead=needLead;x.flexibility=flexibility;x.positionTrend=posTrend;x.ability=clamp(baseAbility*.90+x.posCons*.035+(1-x.collapse)*.035+x.lateGain*.03,0,1);x.speedScore=speed;x.prizeScore=prize;x.jockeyScore=jf;x.trainerScore=tf;x.trackFit=trackFit;x.distFit=distFit;x.condFit=condFit;x.weatherFit=weatherFit;x.seasonFit=seasonFit;x.levelFit=levelFit;x.weightSuit=weightScore(hh);x.bodyWeightSuit=bodyWeightConditionScore(hh);x.bodyWeightKnown=!!currentBodyWeight(hh);x.ageSexSuit=ageSexScore(hh,r);x.coverage=coverage;x.draw=draw;x.outer=outer;x.edge=edge;x.inner=inner;x.outerStress=outerStress;x.shorten=shorten;x.lengthen=lengthen;x.lengthenScale=lengthenScale;x.leadVacancyBoost=0;x.distanceChange=distChange;x.course=ct;x.jockeyFront=jockeyFront;x.stamina=clamp((1-x.fade)*.35+x.hold*.26+distFit*.15+x.posCons*.10+x.ability*.09+(rd>n(r.distance)?.05:0),0,1);x.holdFront=clamp(x.hold*.33+(1-x.fade)*.30+x.stamina*.15+x.ability*.12+distFit*.06+ct.frontBias*.04,0,1);x.latePower=clamp(x.lateGain*.28+x.move*.25+x.close*.14+x.mid*.07+x.ability*.18+(1-x.fade)*.08,0,1);x.turnSkill=clamp(trackFit*.22+x.move*.18+x.flexibility*.18+x.posCons*.16+(1-ct.turnLoad)*.06+x.ability*.20,0,1);x.breakSkill=clamp(x.breakRel*.32+x.ten*.30+x.goProbBase*.20+recentEarly*.10+jockeyFront*.08,0,1);x.trafficTol=clamp(x.flexibility*.34+x.move*.24+x.posCons*.18+x.turnSkill*.18+x.lateGain*.06,0,1)}
for(i=0;i<tmp.length;i++){var lx=tmp[i],le=lx.horse&&lx.horse.integratedEvaluation||{},lc=le.components||{},rawLap=(lc.lapScore!=null?lc.lapScore:(lx.horse&&lx.horse.lapScore));lx.lapScore=clamp(n(rawLap,.5),0,1);lx.sectionalSamples=n(lx.horse&&lx.horse.officialSectionalSamples,0)}
var clearFrontCount=tmp.filter(function(z){return n(z.goProbBase)>=.53}).length;
if(clearFrontCount<=1){
  for(i=0;i<tmp.length;i++){
    var lv=tmp[i],reposition=clamp(n(lv.lengthenScale)*.52+n(lv.breakRel)*.15+n(lv.ten)*.09+n(lv.positionTrend)*.08+n(lv.jockeyFront)*.08+(1-n(lv.needLead))*.08,0,1),drawChance=lv.edge?.055:(lv.inner?.035:.045),vacancyBoost=clamp(reposition*(clearFrontCount===0?.16:.10)+n(lv.lengthenScale)*.045+drawChance*(1-n(lv.outerStress)),0,.18);
    lv.leadVacancyBoost=vacancyBoost;
    lv.goProbBase=clamp(lv.goProbBase+vacancyBoost,0,1);
    lv.goProb=lv.goProbBase
  }
}
var p0=pressureInfo(tmp);for(i=0;i<tmp.length;i++){var y=tmp[i],q=p0[n(y.horse.horseNumber)]||{},pressurePenalty=(q.conflict||0)*(.055+.055*y.needLead)+(q.sandwich||0)*.075*(1-y.flexibility)+(q.lineMiddle||0)*.045*(.4+.6*y.needLead)+y.outerStress*.055-(q.lineEndRelief||0)*.025;y.leftPressure=q.left||0;y.rightPressure=q.right||0;y.sandwichRisk=q.sandwich||0;y.escapeSideRisk=q.escapeSide||0;y.frontLineRole=q.lineRole||'単独';y.frontLineMiddle=q.lineMiddle||0;y.frontLineEnd=q.lineEnd||0;y.lineEndRelief=q.lineEndRelief||0;y.frontCost=clamp(pressurePenalty,0,.30);y.goProb=clamp(y.goProbBase-pressurePenalty+(q.freeOuter||0)*.08+(q.lineEndRelief||0)*.05,0,1);if(y.goProb>=.68&&y.front>=.16&&y.ten>=.55)y.expected="逃げ候補";else if(y.goProb>=.54)y.expected="先行";else if(y.goProb>=.40||y.stalk>=.32)y.expected="好位";else if(y.close>=.42&&y.mid<.36)y.expected="後方";else y.expected="中団";if(y.styleUnknown)y.expected="不明";y.frontStay=clamp(y.goProb*.34+y.holdFront*.34+(1-y.fade)*.12+y.ability*.12+y.course.frontBias*.08-y.frontCost*.30+(q.lineEndRelief||0)*.035,0,1);y.comeFromBehind=clamp(y.latePower*.46+y.move*.20+y.ability*.16+y.course.moveRoom*.10+(1-y.goProb)*.08,0,1)}return tmp}
function rowByNo(rows,no){var i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===n(no))return rows[i];return null}
function pressureInfo(rows){var sorted=rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),p={},attacks=[],hot=[],segFor=[],segments=[],i,x,l,r,lp,rp,base,current=null;function attack(z){if(!z)return 0;base=z.goProbBase!=null?z.goProbBase:z.goProb;return clamp(base*(.46+.34*z.needLead+.20*z.ten),0,1.2)}for(i=0;i<sorted.length;i++){attacks[i]=attack(sorted[i]);hot[i]=attacks[i]>.50&&n(sorted[i].goProbBase,sorted[i].goProb)>=.44}for(i=0;i<sorted.length;i++){if(hot[i]){if(!current||i===0||!hot[i-1]||n(sorted[i].horse.horseNumber)-n(sorted[i-1].horse.horseNumber)!==1){current={idx:[]};segments.push(current)}current.idx.push(i);segFor[i]=current}else current=null}for(i=0;i<sorted.length;i++){x=sorted[i];l=i?sorted[i-1]:null;r=i<sorted.length-1?sorted[i+1]:null;lp=l&&n(x.horse.horseNumber)-n(l.horse.horseNumber)===1?attacks[i-1]:0;rp=r&&n(r.horse.horseNumber)-n(x.horse.horseNumber)===1?attacks[i+1]:0;var leftHot=lp>.50,rightHot=rp>.50,sandwich=leftHot&&rightHot?1:0,escapeSide=(leftHot||rightHot)&&!sandwich?1:0,adj=(leftHot?1:0)+(rightHot?1:0),near2=0;if(i>1&&n(x.horse.horseNumber)-n(sorted[i-2].horse.horseNumber)===2)near2+=attacks[i-2]*.14;if(i<sorted.length-2&&n(sorted[i+2].horse.horseNumber)-n(x.horse.horseNumber)===2)near2+=attacks[i+2]*.14;var seg=segFor[i]||null,clusterLen=seg?seg.idx.length:0,clusterPos=seg?seg.idx.indexOf(i):-1,lineMiddle=clusterLen>=3&&clusterPos>0&&clusterPos<clusterLen-1?1:0,lineEnd=clusterLen>=2&&(clusterPos===0||clusterPos===clusterLen-1)?1:0,innerEnd=lineEnd&&clusterPos===0?1:0,outerEnd=lineEnd&&clusterPos===clusterLen-1?1:0,lineEndRelief=lineEnd?(.05+.08*x.flexibility):0;if(outerEnd&&!rightHot)lineEndRelief+=.04;if(innerEnd&&!leftHot)lineEndRelief+=.025;var conflict=(lp+rp)*(.43+.38*x.needLead+.19*x.ten)*(1-.42*x.flexibility)+near2+lineMiddle*(.10+.10*x.needLead)+(clusterLen>=4?.04:0);conflict=Math.max(0,conflict-lineEndRelief*.42);var freeOuter=x.edge?(.055+.075*x.flexibility):0,lineRole=lineMiddle?'先行列中央':(outerEnd?'先行列外端':(innerEnd?'先行列最内':(lineEnd?'先行列端':'単独/飛び')));p[n(x.horse.horseNumber)]={adj:adj,sandwich:sandwich,escapeSide:escapeSide,conflict:clamp(conflict,0,1.7),freeOuter:freeOuter,left:lp,right:rp,leftHot:leftHot,rightHot:rightHot,selfAttack:attacks[i],clusterLen:clusterLen,lineMiddle:lineMiddle,lineEnd:lineEnd,innerEnd:innerEnd,outerEnd:outerEnd,lineEndRelief:lineEndRelief,lineRole:lineRole}}return p}
function frontArrangement(rows,pressure){pressure=pressure||pressureInfo(rows);var field=Math.max(1,rows.length),front=rows.filter(function(x){return x.goProb>=.50}).sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),segments=[],cur=[],i,x,no,prev=0;for(i=0;i<front.length;i++){x=front[i];no=n(x.horse.horseNumber);if(!cur.length||no===prev+1)cur.push(x);else{segments.push(cur);cur=[x]}prev=no}if(cur.length)segments.push(cur);var adjacentPairs=0,longest=0;for(i=0;i<segments.length;i++){longest=Math.max(longest,segments[i].length);adjacentPairs+=Math.max(0,segments[i].length-1)}var pattern=!front.length?'前候補なし':(front.length===1?'単独':(adjacentPairs===0?'飛び飛び':(longest>=3?'連続':'一部連続'))),innerCut=Math.ceil(field*.35),outerCut=Math.floor(field*.65)+1,innerCount=front.filter(function(z){return n(z.horse.horseNumber)<=innerCut}).length,outerCount=front.filter(function(z){return n(z.horse.horseNumber)>=outerCut}).length,innerShare=front.length?innerCount/front.length:0,outerShare=front.length?outerCount/front.length:0,concentrationText=innerShare>=.60?'内枠に集中':(outerShare>=.60?'外枠に集中':'内外に分散'),scored=rows.slice();for(i=0;i<scored.length;i++){x=scored[i];var q=pressure[n(x.horse.horseNumber)]||{};x.canYield=clamp(x.flexibility*.62+x.stalk*.20+(1-x.needLead)*.18,0,1)>=.55;x.leaderScore=clamp(x.goProb*.38+x.ten*.20+x.needLead*.17+x.breakSkill*.13+x.jockeyFront*.05+x.front*.05+(q.lineEndRelief||0)*.05-(q.conflict||0)*.04,0,1.3);x.secondScore=clamp(x.goProb*.34+x.stalk*.22+x.flexibility*.16+x.holdFront*.12+x.ability*.08+(q.lineEndRelief||0)*.05-(q.conflict||0)*.04,0,1.3);x.positionScore=clamp(x.goProb*.23+x.stalk*.24+x.mid*.13+x.flexibility*.13+x.ability*.12+x.turnSkill*.09+(1-x.frontCost)*.06,0,1.2)}var leadOrder=scored.filter(function(z){return z.goProb>=.48}).sort(function(a,b){return b.leaderScore-a.leaderScore||n(a.horse.horseNumber)-n(b.horse.horseNumber)}),leadMax=leadOrder.length?leadOrder[0].leaderScore:0,leadCandidates=leadOrder.filter(function(z,idx){return idx<3&&z.leaderScore>=leadMax-.085&&z.goProb>=.53}),leadTop=leadCandidates[0]||leadOrder[0]||null,secondCandidates=scored.filter(function(z){return !leadTop||n(z.horse.horseNumber)!==n(leadTop.horse.horseNumber)}).filter(function(z){return z.goProb>=.42||z.stalk>=.28}).sort(function(a,b){return b.secondScore-a.secondScore}).slice(0,3),positionCandidates=scored.filter(function(z){return z.goProb>=.34||z.stalk>=.30||z.mid>=.34}).sort(function(a,b){return b.positionScore-a.positionScore}).slice(0,4),escapeSide=leadCandidates.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.escapeSide}),sandwich=leadCandidates.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.sandwich}),middleFront=front.filter(function(z){var q=pressure[n(z.horse.horseNumber)]||{};return q.lineMiddle}),highFade=front.filter(function(z){return z.fade>=.50}),hardLead=leadCandidates.filter(function(z){return z.needLead>=.58&&z.canYield===false});return{front:front,segments:segments,pattern:pattern,longest:longest,adjacentPairs:adjacentPairs,innerShare:innerShare,outerShare:outerShare,concentrationText:concentrationText,leadCandidates:leadCandidates,secondCandidates:secondCandidates,positionCandidates:positionCandidates,escapeSide:escapeSide,sandwich:sandwich,middleFront:middleFront,highFade:highFade,hardLeadCount:hardLead.length}}
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
function scenarioPlan(r,rows,sc,suit,pressure,arr){var scenario=sc.slice().sort(function(a,b){return b.prob-a.prob})[0],code=scenario.code;pressure=pressure||pressureInfo(rows);arr=arr||frontArrangement(rows,pressure);var p=pressure,ct=courseTraits(r),S=[{},{},{},{},{},{}],L=[{},{},{},{},{},{}],i,x,no,q,scfit,markScore={},leadLoad;for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=p[no]||{};leadLoad=x.goProb*(.045+.055*x.needLead)+x.frontCost*.13;S[0][no]=x.breakSkill*.20+x.ten*.20+x.goProb*.22+x.leaderScore*.20+x.needLead*.06+x.jockeyFront*.04+(q.freeOuter||0)*.05+(q.lineEndRelief||0)*.04-x.frontCost*.08;L[0][no]=clamp(Math.round((x.draw-.5)*5),-3,3);S[1][no]=S[0][no]*.40+x.goProb*.17+x.holdFront*.13+x.turnSkill*.11+x.flexibility*.06+x.ability*.08-x.frontCost*.09-x.outerStress*.05-(q.lineMiddle||0)*.035+(q.lineEndRelief||0)*.025;L[1][no]=clamp(L[0][no]+(x.edge&&x.goProb>.55?-1:0)+(q.sandwich&&x.flexibility<.45?1:0),-3,3);scfit=scenarioSuit(x,code,p);S[2][no]=S[1][no]*.31+x.ability*.16+x.holdFront*.15+x.stamina*.13+x.stalk*.07+x.mid*.04+scfit*.11-(code==='C'?leadLoad*.12:leadLoad*.05)+(code==='A'?x.goProb*.06:0)+(x.canYield&&x.needLead>.45?.008:0);L[2][no]=clamp(L[1][no]+(x.move>.52&&x.goProb<.46?1:0),-3,3);S[3][no]=S[2][no]*.27+x.ability*.16+x.move*.16+x.turnSkill*.11+scfit*.14+x.latePower*.09+x.holdFront*.04-(x.fade*x.goProb)*(code==='C'?.10:.045)+(code==='C'?x.collapseBeneficiary*.055:0);L[3][no]=clamp(L[2][no]+(x.move>.56?1:0),-3,3);S[4][no]=S[3][no]*.24+scfit*.20+x.ability*.18+x.holdFront*.11+x.move*.10+x.latePower*.10+(1-x.fade)*.05-(q.sandwich||0)*.025-(q.lineMiddle||0)*.018+(code==='C'?x.collapseBeneficiary*.06:0);L[4][no]=clamp(L[3][no]+(x.latePower>.61?1:0),-3,3);var su=suit[no]||{rankScore:.5};markScore[no]=S[4][no]*.31+su.rankScore*.42+x.ability*.10+x.latePower*.08+x.stamina*.05+x.coverage*.02+(1-x.fade)*.02;if(code==='A')markScore[no]+=x.frontStay*.045;if(code==='C')markScore[no]+=x.comeFromBehind*.035+x.collapseBeneficiary*.030;S[5][no]=markScore[no];L[5][no]=L[4][no]}var labels=['スタート','1コーナー','向正面','3コーナー','4コーナー','直線'],packs=[],stages=[];for(i=0;i<6;i++){packs[i]=packScenarioStage(r,rows,S[i],L[i],i);stages.push({key:['start','first','back','turn3','turn4','straight'][i],label:labels[i],pack:packs[i]})}return{scenario:scenario,stages:stages,start:rowsFromPack(rows,packs[0]),corner:rowsFromPack(rows,packs[4]),straight:rowsFromPack(rows,packs[5]),markScore:markScore}}
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
function assignOverallGradesCentral(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,fitScore,representative,resultsScore,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    fitScore=clamp(n(x.distFit,.5)*.43+n(x.trackFit,.5)*.34+n(x.condFit,.5)*.23,0,1);
    resultsScore=clamp(recentFinishScore(x.horse)*.38+n(x.speedScore,.5)*.22+n(x.levelFit,.5)*.25+n(x.prizeScore,.5)*.15,0,1);
    representative=clamp(n(x.speedScore,.5)*.30+n(x.levelFit,.5)*.28+recentFinishScore(x.horse)*.24+x.posCons*.10+x.latePower*.08,0,1);
    raw=
      resultsScore*.30+
      x.ability*.25+
      fitScore*.22+
      representative*.13+
      n(su.overall,.5)*.05+
      n(x.jockeyScore,.5)*.02+
      n(x.bodyWeightSuit,.5)*.01+
      x.coverage*.02;
    x.resultsScore=resultsScore;x.fitComposite=fitScore;x.representativeScore=representative;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(resultsScore>=.62)x.overallReasons.push('近走実績評価高め');
    if(fitScore>=.62)x.overallReasons.push('適性評価高め');
    if(representative>=.64)x.overallReasons.push('代表走評価高め');
    if(n(x.levelFit)>=.60)x.overallReasons.push('相手レベル適性');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}
function assignOverallGradesNar(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,q,fitScore,resultsScore,representative,positionEdge,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};q=pressure[no]||{};
    fitScore=clamp(n(x.trackFit,.5)*.41+n(x.distFit,.5)*.37+n(x.condFit,.5)*.22,0,1);
    // Local racing: class/opponent level and repeatable course-distance performance matter more
    // than a single tactical projection. Pace/position remains a modifier, not the core rank.
    resultsScore=clamp(recentFinishScore(x.horse)*.38+n(x.speedScore,.5)*.22+n(x.levelFit,.5)*.25+n(x.prizeScore,.5)*.15,0,1);
    representative=clamp(n(x.speedScore,.5)*.28+n(x.levelFit,.5)*.30+recentFinishScore(x.horse)*.25+x.posCons*.10+x.latePower*.07,0,1);
    positionEdge=clamp(x.goProb*.28+x.frontStay*.24+x.holdFront*.15+x.breakSkill*.10+n(x.jockeyFront,.0)*.08+(1-clamp(n(q.conflict),0,1))*.08+n(q.freeOuter,0)*.07,0,1);
    raw=
      resultsScore*.30+
      x.ability*.24+
      fitScore*.22+
      representative*.12+
      n(su.overall,.5)*.05+
      positionEdge*.03+
      n(x.jockeyScore,.5)*.015+
      x.posCons*.01+
      n(x.bodyWeightSuit,.5)*.005+
      x.coverage*.01-
      x.frontCost*.015-
      x.outerStress*.005;
    x.resultsScore=resultsScore;x.fitComposite=fitScore;x.representativeScore=representative;x.positionEdge=positionEdge;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(resultsScore>=.62)x.overallReasons.push('近走実績評価高め');
    if(fitScore>=.62)x.overallReasons.push('適性評価高め');
    if(representative>=.64)x.overallReasons.push('代表走評価高め');
    if(n(x.levelFit)>=.60)x.overallReasons.push('相手レベル適性');
    if(positionEdge>=.68)x.overallReasons.push('隊列は加点材料');
    if(n(x.trackFit)>=.60)x.overallReasons.push('同場適性');
    if(q.sandwich)x.overallReasons.push('逃げハサミ警戒');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}
function assignOverallGradesJump(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,fitScore,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    fitScore=mean([n(x.distFit,.5),n(x.trackFit,.5),n(x.condFit,.5)]);
    raw=
      x.ability*.25+
      x.stamina*.18+
      n(su.overall,.5)*.17+
      fitScore*.13+
      x.posCons*.08+
      x.hold*.06+
      x.latePower*.05+
      n(x.jockeyScore,.5)*.04+
      (1-x.fade)*.025+
      x.coverage*.025;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(x.stamina>=.62)x.overallReasons.push('障害スタミナ');
    if(x.posCons>=.62)x.overallReasons.push('位置取り安定');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}
function assignOverallGradesDebut(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    raw=
      x.ability*.20+
      n(x.jockeyScore,.5)*.18+
      n(x.trainerScore,.5)*.15+
      n(x.prizeScore,.5)*.10+
      n(x.distFit,.5)*.08+
      n(x.trackFit,.5)*.07+
      n(x.weightSuit,.5)*.06+
      n(x.ageSexSuit,.5)*.05+
      n(su.overall,.5)*.05+
      x.breakSkill*.04+
      x.coverage*.02;
    x.overallRaw=clamp(raw,0,1);x.overallReasons=['新馬専用評価'];
    if(n(x.jockeyScore)>=.60)x.overallReasons.push('騎手評価');
    if(n(x.trainerScore)>=.60)x.overallReasons.push('厩舎評価');
    if(x.coverage<.35)x.overallReasons.push('実戦データ限定');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}
function assignOverallGrades(r,rows,suit,sc,pressure){
  var p=predictionProfile(r);
  if(p.code==='NAR')return assignOverallGradesNar(r,rows,suit,pressure);
  if(p.code==='JUMP')return assignOverallGradesJump(r,rows,suit,pressure);
  if(p.code==='DEBUT')return assignOverallGradesDebut(r,rows,suit,pressure);
  return assignOverallGradesCentral(r,rows,suit,pressure)
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
var V207_WINNER_WEIGHTS={p1_saved:.09627194216236537,eval_score:.1679542499142859,race_perf:.1109979898310441,representative:.15169717690190784,distance:.08793497370101384,track:.06426941305845313,going:.036567118849402995,level:.03389237013978389,lap:.017947472883332174,jockey:.04752026893280671,trainer:.06245542349478168,body:.018494658513940915,condition_change:.01366060056696039,early3:.012600191153762295,ten:.015217007009379167,late_role:.044806043242146286,evidence:.017713099644633336};
function v207Unit(v,d){var x=Number(v);if(!isFinite(x))return d==null?.5:d;if(x>1.5)x/=100;return clamp(x,0,1)}
function v207Comp(e,names,d){var c=e&&e.components||{},i;for(i=0;i<names.length;i++)if(c[names[i]]!=null)return v207Unit(c[names[i]],d);return d}
function v207WinnerScoreHorse(h){
  h=h||{};var e=h.integratedEvaluation||{},pm=h.precomputedMetrics||{},fit=pm.fit||{},st=pm.style||{},samples=Math.max(n(st.samples),n(e.samples)),full=clamp(n(e.dataCompleteness,50)/100,0,1),evidence=clamp(.55*Math.min(1,samples/5)+.45*full,0,1),late=clamp(.42*v207Unit(st.moved3,0)+.32*v207Unit(st.mid,0)+.26*v207Unit(st.close,0),0,1),legacy=v207Unit(e.legacyP1Score!=null?e.legacyP1Score:e.p1Score,.5),f={
    p1_saved:legacy,eval_score:v207Unit(e.score,.5),race_perf:v207Comp(e,['racePerformance'],.5),representative:v207Comp(e,['representative'],.5),distance:v207Comp(e,['distanceFit'],v207Unit(fit.distance,.5)),track:v207Comp(e,['courseFit'],v207Unit(fit.track,.5)),going:v207Comp(e,['goingFit'],v207Unit(fit.condition,.5)),level:v207Comp(e,['opponentLevelScore'],v207Unit(fit.level,.5)),lap:v207Comp(e,['lapScore'],.5),jockey:v207Comp(e,['jockeyScore','jockeyResults'],.5),trainer:v207Comp(e,['trainerScore','trainerResults'],.5),body:v207Comp(e,['bodyWeightScore'],.5),condition_change:v207Comp(e,['conditionChangeScore'],.5),early3:v207Unit(st.early3,0),ten:v207Unit(st.ten,.5),late_role:late,evidence:evidence
  },sum=0,k;for(k in V207_WINNER_WEIGHTS)sum+=V207_WINNER_WEIGHTS[k]*f[k];return clamp(sum,0,1)
}
function v207UsesWinnerModel(r){return String(r&&r.circuit||'')==='地方'}

// v312 recall guard: one dedicated third-place rescue candidate.
// This is intentionally circuit-specific and market-independent.  It does NOT
// widen the winner model; it only protects against the recurring "one horse
// missing" failure where a lower win-ranked runner still has a credible P3 path.
function thirdRescueScoreV312(r,z,field){
  field=Math.max(1,n(field,1));z=z||{};
  var e=z.horse&&z.horse.integratedEvaluation||{},a=e.v218Audit||e.v217Audit||z.v218Audit||z.v217Audit||{},uniform=1/field,
      p3rel=clamp(n(z.p3Probability)/(Math.max(.0001,uniform)*1.55),0,1),p3rank=clamp((7-n(z.p3Rank,99))/6,0,1),
      trueRun=clamp(n(a.trueRun,.5),0,1),sectional=clamp(n(a.sectional,n(z.lapScore,.5)),0,1),scenario=clamp(n(a.positionScenario,n(z.paceScore,50)/100),0,1),
      coverage=clamp(n(z.edgeEvidence,n(z.coverage,.5)),0,1),recent3=recentTop3Rate(z.horse),live=clamp((n(z.liveDrawFit,.5)+n(z.liveStyleFit,.5))/2,0,1),roleRecall=clamp(n(z.p3RecallScore,0),0,1),score;
  if(String(r&&r.circuit||'')==='中央'){
    var frag=clamp(n(z.winnerRisk)*.45+n(z.frontCost)*.24+n(z.fade)*n(z.needLead)*.21+n(z.outerStress)*.10,0,1);
    score=.21*p3rel+.12*p3rank+.13*clamp(n(z.latePower,.5),0,1)+.12*trueRun+.10*sectional+.09*scenario+.06*clamp(n(z.move,.5),0,1)+.05*coverage+.12*roleRecall;
    score-=.050*frag;
  }else{
    score=.20*p3rel+.12*p3rank+.12*clamp(n(z.posCons,.5),0,1)+.11*clamp(n(z.trackFit,.5),0,1)+.10*scenario+.07*clamp(n(z.move,.5),0,1)+.06*recent3+.05*live+.05*coverage+.12*roleRecall;
  }
  return clamp(score,0,1)
}
function thirdRescueCandidateV312(r,rows,exclude){
  rows=rows||[];exclude=exclude||[];var field=Math.max(1,rows.length),uniform=1/field,cand=rows.filter(function(z){
    if(!z||exclude.indexOf(z)>=0)return false;
    var p3=n(z.p3Probability),rank=n(z.p3Rank,99),hist=(z.horse&&z.horse.recentRaces||[]).length;
    return (rank<=6||p3>=uniform*.78)&&(n(z.coverage)>=.25||n(z.styleSamples)>=2||hist>=2)
  });
  cand.forEach(function(z){z.thirdRescueScore=thirdRescueScoreV312(r,z,field)});
  cand.sort(function(a,b){return n(b.thirdRescueScore)-n(a.thirdRescueScore)||n(a.p3Rank,99)-n(b.p3Rank,99)||n(b.p3Probability)-n(a.p3Probability)});
  var q=cand[0]||null;if(!q)return null;
  var floor=String(r&&r.circuit||'')==='中央'?.47:.48;
  return n(q.thirdRescueScore)>=floor?q:null
}
function comboHasV312(list,combo){var k=(combo||[]).join('>');return (list||[]).some(function(c){return (c||[]).join('>')===k})}
function appendRescueRankedV312(base,ranked,rescueNo,maxExtra,minRatio,thirdOnly){
  base=base||[];ranked=ranked||[];rescueNo=n(rescueNo);if(!rescueNo||!ranked.length)return base;var top=n(ranked[0]&&ranked[0].score),added=0,i,z,c;
  for(i=0;i<ranked.length&&added<maxExtra;i++){
    z=ranked[i];c=z&&z.combo;if(!c||c.indexOf(rescueNo)<0)continue;if(thirdOnly&&n(c[2])!==rescueNo)continue;
    if(top>0&&n(z.score)<top*minRatio)continue;if(comboHasV312(base,c))continue;base.push(c.slice());added++
  }
  return base
}

function assignEdgeEngine(r,rows,suit,sc,pressure){
  pressure=pressure||{};sc=sc||[];
  var liveBias=raceLiveBias(r,rows),field=Math.max(1,rows.length),uniform=1/field,p1Raw=[],publicRaw=[],role2Raw=[],role3Raw=[],i,x,no,su,q,fit,pace,shift,peak,trip,reset,resetLift,evidence,publicScore,p1Strength,p2Strength,p3Strength,top3Hist,winnerCore,winnerRisk,lb,liveDrawFit,liveStyleFit,
      oddsCount=0,popCount=0,actualOddsCount=0,forecastOddsCount=0,coverageAvg=mean(rows.map(function(z){return n(z.coverage)})),temp=.074+(1-coverageAvg)*.045;
  var collapse=0,front=0;
  sc.forEach(function(z){if(z.code==='C')collapse=n(z.prob);if(z.code==='A')front=n(z.prob)});
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{win:.5,place:.5,show:.5,rankScore:.5,overall:.5};q=pressure[no]||{};
    lb=liveBias.byNo[no]||{drawFit:.5,styleFit:.5};liveDrawFit=n(lb.drawFit,.5);liveStyleFit=n(lb.styleFit,.5);x.liveDrawFit=liveDrawFit;x.liveStyleFit=liveStyleFit;x.liveBiasEvidence=n(liveBias.evidence,0);
    trip=tripRecoveryProfile(x,r);
    reset=sparseResetProfile(x,r,q);resetLift=reset.score>=.25?reset.score:0;
    // v244: historical draw remains in the server score; this live overlay adds TODAY'S
    // same-venue frame/style bias.  Small samples are automatically shrunk to 0.5.
    fit=clamp(n(x.distFit,.5)*.39+n(x.trackFit,.5)*.34+n(x.condFit,.5)*.18+n(x.levelFit,.5)*.09+(liveDrawFit-.5)*.16,0,1);
    pace=clamp(n(su.rankScore,.5)*.64+n(su.win,.5)*.24+Math.max(n(x.frontStay),n(x.comeFromBehind))*.12+(liveStyleFit-.5)*.16,0,1.15);
    shift=clamp(fit*.52+(1-clamp(n(q.conflict),0,1))*.09+n(x.bodyWeightSuit,.5)*.06+n(x.jockeyScore,.5)*.06+n(x.flexibility,.5)*.06+n(x.breakSkill,.5)*.05+resetLift*.06+liveDrawFit*.05+liveStyleFit*.05,0,1);
    peak=recentPeakScore(x.horse,r);top3Hist=recentTop3Rate(x.horse);
    evidence=clamp(n(x.coverage)*.66+clamp(n(x.styleSamples)/4,0,1)*.16+clamp(((x.horse.recentRaces||[]).length)/5,0,1)*.18,0,1);

    // v14: P1 is a pure winner model. Market EDGE/BOMB never participates in this score.
    // Repeatable ability, current-condition fit and opponent level dominate; tactical reset is only a tiny tiebreaker.
    winnerCore=clamp(
      n(x.overallRaw,.5)*.25+
      n(x.resultsScore,.5)*.18+
      n(x.representativeScore,.5)*.15+
      n(x.ability,.5)*.105+
      fit*.105+
      n(su.win,.5)*.07+
      n(x.levelFit,.5)*.04+
      n(x.posCons,.5)*.035+
      (1-n(x.fade,.5))*.025+
      n(x.jockeyScore,.5)*.025+
      n(x.bodyWeightSuit,.5)*.015+
      evidence*.01,
      0,1.15
    );
    winnerRisk=clamp(
      n(x.frontCost)*.30+
      n(x.outerStress)*.16+
      clamp(n(q.conflict),0,1)*.22+
      (n(x.needLead)*n(x.fade))* .20+
      n(x.collapse)*.12,
      0,1
    );
    var savedEval=x.horse&&x.horse.integratedEvaluation||{},savedP1=clamp(n(savedEval.p1Score,50)/100,0,1);
    p1Strength=clamp((winnerCore-winnerRisk*.055+trip.score*.008+resetLift*.007)*.72+savedP1*.28,0,1.15);

    // v217 client tactical overlay. This is also used for JRA, where the 499-race
    // local-only trained role model is intentionally not reused. No odds enter this score.
    var v217Neutral=clamp(1-front-collapse,0,1),
        v217Pure=clamp(n(x.overallRaw,.5)*.24+n(x.resultsScore,.5)*.17+n(x.representativeScore,.5)*.14+n(x.ability,.5)*.11+fit*.10+n(x.levelFit,.5)*.06+n(x.speedScore,.5)*.07+n(x.lapScore,.5)*.06+n(x.jockeyScore,.5)*.05,0,1),
        v217True=clamp(n(x.resultsScore,.5)*.20+n(x.speedScore,.5)*.16+n(x.lapScore,.5)*.10+peak*.15+trip.score*.14+n(x.representativeScore,.5)*.10+n(x.lateGain,.5)*.07+n(x.posCons,.5)*.05+(1-n(x.fade,.5))*.03,0,1),
        v217Sectional=clamp(n(x.lapScore,.5)*.55+n(x.speedScore,.5)*.25+peak*.20,0,1),
        v217Scenario=clamp(front*n(x.frontStay,.5)+collapse*n(x.comeFromBehind,.5)+v217Neutral*pace+(liveStyleFit-.5)*.12,0,1),
        v217Conditions=clamp(fit*.49+shift*.21+n(su.win,.5)*.16+liveDrawFit*.08+liveStyleFit*.06,0,1),
        v217Opponent=clamp(n(x.levelFit,.5)*.62+fit*.38,0,1),
        v217State=clamp(evidence*.30+n(x.posCons,.5)*.20+n(x.bodyWeightSuit,.5)*.15+(1-n(x.fade,.5))*.15+n(x.flexibility,.5)*.10+n(x.resultsScore,.5)*.10,0,1),
        v239Client=clamp(.21*v217Pure+.17*v217True+.12*v217Sectional+.14*v217Scenario+.22*v217Conditions+.08*v217Opponent+.06*v217State,0,1);
    v239Client=.5+(v239Client-.5)*(.58+.42*evidence);
    x.v239Composite=v239Client;
    x.v217Audit={pure:v217Pure,trueRun:v217True,sectional:v217Sectional,hiddenEffort:trip.score,positionScenario:v217Scenario,conditions:v217Conditions,opponentLevel:v217Opponent,stateConsistency:v217State,sevenAxisScore:v239Client,evidence:evidence,liveBias:{evidence:liveBias.evidence,completed:liveBias.completed,drawFit:liveDrawFit,styleFit:liveStyleFit,frameBias:liveBias.frameBias,frontBias:liveBias.frontBias,lateBias:liveBias.lateBias},scenarioProbabilities:{front:front,neutral:v217Neutral,collapse:collapse}};

    var legacyP1Strength=p1Strength,v207P1Strength=v207WinnerScoreHorse(x.horse);
    // v239: keep the validated/statistical backbone, but make the agreed seven-axis
    // model a meaningful race-by-race overlay for both central and local racing.
    p1Strength=clamp((v207UsesWinnerModel(r)?v207P1Strength:p1Strength)*.70+v239Client*.30,0,1.15);
    x.legacyP1Strength=legacyP1Strength;x.v207WinnerStrength=v207P1Strength;

    // v245 P2: runner-up ability is not just the old role ranker.
    // Reward repeatability, TRUE RUN, current scenario/conditions and the ability to
    // hold or improve position.  Today's live draw/style bias is already embedded
    // in v217Scenario/v217Conditions, so P2 now reacts to the actual course flow.
    p2Strength=clamp(
      n(x.resultsScore,.5)*.135+
      n(su.place,.5)*.125+
      n(x.posCons,.5)*.115+
      v217True*.115+
      v217Scenario*.10+
      v217Conditions*.09+
      n(x.holdFront,.5)*.075+
      n(x.flexibility,.5)*.06+
      (1-n(x.fade,.5))*.055+
      n(x.move,.5)*.045+
      v217State*.04+
      v217Pure*.025+
      n(x.jockeyScore,.5)*.015+
      evidence*.005,
      0,1.15
    );
    p2Strength=clamp(p2Strength*.84+clamp(n(savedEval.p2Score,50)/100,0,1)*.16,0,1.15);

    // v245 P3: widen the rescue net. Third place often comes from a horse that is
    // not a win candidate but owns late power, a recent peak, top-3 memory, or an
    // improving trip.  SECTIONAL/TRUE RUN and live scenario fit are therefore
    // explicit instead of relying mostly on the legacy marginal.
    p3Strength=clamp(
      n(su.show,.5)*.105+
      top3Hist*.105+
      peak*.095+
      v217True*.095+
      v217Sectional*.09+
      v217Scenario*.085+
      n(x.latePower,.5)*.085+
      n(x.move,.5)*.08+
      n(x.flexibility,.5)*.065+
      v217Conditions*.065+
      v217State*.055+
      n(x.representativeScore,.5)*.04+
      trip.score*.025+
      evidence*.01,
      0,1.15
    );
    p3Strength=clamp(p3Strength*.86+clamp(n(savedEval.p3Score,50)/100,0,1)*.14,0,1.15);

    publicScore=clamp(
      recentFinishScore(x.horse)*.29+
      n(x.speedScore,.5)*.16+
      n(x.representativeScore,.5)*.13+
      n(x.jockeyScore,.5)*.10+
      n(x.prizeScore,.5)*.08+
      n(x.overallRaw,.5)*.19+
      n(x.trackFit,.5)*.025+
      n(x.distFit,.5)*.025,
      0,1
    );
    x.tripScore=Math.round(trip.score*100);x.tripReasons=trip.reasons;
    x.sparseReset=reset.score;x.sparseResetReasons=reset.reasons;x.frontMemoryScore=reset.frontMemory;x.frontMemoryCount=reset.frontMemoryCount;x.fadeRecoveryReset=reset.fadeRecovery;
    if(resetLift&&x.overallReasons){reset.reasons.forEach(function(t){if(x.overallReasons.indexOf(t)<0)x.overallReasons.push(t)})}
    x.winnerCore=winnerCore;x.winnerRisk=winnerRisk;x.winStrength=p1Strength;x.p2Strength=p2Strength;x.p3Strength=p3Strength;x.publicAppeal=publicScore;x.paceScore=Math.round(clamp(pace,0,1)*100);x.shiftScore=Math.round(shift*100);x.edgeEvidence=evidence;
    x.tacticalReset=reset.score;
    p1Raw.push(p1Strength);role2Raw.push(p2Strength);role3Raw.push(p3Strength);publicRaw.push(publicScore);
    if(Number(x.horse.winOdds||0)>1){oddsCount++;if(x.horse.oddsForecast||/予想|forecast/i.test(String(x.horse.oddsSource||'')))forecastOddsCount++;else actualOddsCount++}
    if(n(x.horse.popularity,0)>0)popCount++
  }
  function roleZ(vals){var m=mean(vals),v=mean(vals.map(function(q){q=n(q)-m;return q*q})),sd=Math.sqrt(Math.max(1e-8,v));return vals.map(function(q){return (n(q)-m)/sd})}
  var v213Ready=v207UsesWinnerModel(r)&&rows.length&&rows.every(function(z){var e=z&&z.horse&&z.horse.integratedEvaluation||{};return isFinite(Number(e.v218P1Utility!=null?e.v218P1Utility:(e.v217P1Utility!=null?e.v217P1Utility:(e.v215P1Utility!=null?e.v215P1Utility:e.v213P1Utility))))&&isFinite(Number(e.v213P2Utility))&&isFinite(Number(e.v213P3Utility))}),
      liveP2Z=roleZ(role2Raw),liveP3Z=roleZ(role3Raw),
      p1P=v213Ready?edgeSoftmax(rows.map(function(z){var e=z.horse.integratedEvaluation||{};return Number(e.v218P1Utility!=null?e.v218P1Utility:(e.v217P1Utility!=null?e.v217P1Utility:(e.v215P1Utility!=null?e.v215P1Utility:e.v213P1Utility)))}),1):edgeSoftmax(p1Raw,temp),
      p2P=v213Ready?edgeSoftmax(rows.map(function(z,idx){return Number((z.horse.integratedEvaluation||{}).v213P2Utility)*.64+liveP2Z[idx]*.36}),1):edgeSoftmax(role2Raw,temp+.014),
      p3P=v213Ready?edgeSoftmax(rows.map(function(z,idx){return Number((z.horse.integratedEvaluation||{}).v213P3Utility)*.58+liveP3Z[idx]*.42}),1):edgeSoftmax(role3Raw,temp+.024),predMarket=edgeSoftmax(publicRaw,.105),market=[],marketSource='予測市場';
  if(oddsCount>=Math.max(2,Math.ceil(field*.75))){
    marketSource=actualOddsCount>=Math.max(2,Math.ceil(field*.55))?'実オッズ':'予想オッズ';var imp=[],impSum=0;
    for(i=0;i<rows.length;i++){
      var od=Number(rows[i].horse.winOdds||0),v=od>1?1/od:predMarket[i]*.85;
      imp.push(v);impSum+=v
    }
    market=imp.map(function(z){return impSum?z/impSum:uniform})
  }else if(popCount>=Math.max(2,Math.ceil(field*.70))){
    marketSource='人気順位';var rw=[],rwSum=0;
    for(i=0;i<rows.length;i++){
      var pop=n(rows[i].horse.popularity,0),w=pop>0?1/Math.pow(pop,1.18):predMarket[i];rw.push(w);rwSum+=w
    }
    market=rw.map(function(z){return rwSum?z/rwSum:uniform})
  }else market=predMarket;
  var p1Sum=0,p2Sum=0,p3Sum=0;
  for(i=0;i<rows.length;i++){
    x=rows[i];var conf=.58+.42*clamp(n(x.edgeEvidence),0,1),trainedConf=.86+.14*clamp(n(x.edgeEvidence),0,1),adj1=v213Ready?uniform+(p1P[i]-uniform)*trainedConf:uniform+(p1P[i]-uniform)*conf,adj2=v213Ready?uniform+(p2P[i]-uniform)*trainedConf:uniform+(p2P[i]-uniform)*conf,adj3=v213Ready?uniform+(p3P[i]-uniform)*trainedConf:uniform+(p3P[i]-uniform)*conf;
    x.v213RoleReady=v213Ready;x.winProbabilityRaw=Math.max(.001,adj1);x.p2ProbabilityRaw=Math.max(.001,adj2);x.p3ProbabilityRaw=Math.max(.001,adj3);p1Sum+=x.winProbabilityRaw;p2Sum+=x.p2ProbabilityRaw;p3Sum+=x.p3ProbabilityRaw
  }
  var rawP1=rows.map(function(z){return z.winProbabilityRaw/p1Sum}),rawP2=rows.map(function(z){return z.p2ProbabilityRaw/p2Sum}),rawP3=rows.map(function(z){return z.p3ProbabilityRaw/p3Sum}),
      evidences=rows.map(function(z){return n(z.edgeEvidence,n(z.coverage,.5))}),guardP1=conservativeProbabilityGuard(rawP1,evidences,'p1'),guardP2=conservativeProbabilityGuard(rawP2,evidences,'p2'),guardP3=conservativeProbabilityGuard(rawP3,evidences,'p3');
  for(i=0;i<rows.length;i++){
    rows[i].rawP1Probability=rawP1[i];rows[i].rawP2Probability=rawP2[i];rows[i].rawP3Probability=rawP3[i];
    rows[i].winProbability=guardP1[i];rows[i].p1Probability=guardP1[i];rows[i].evWinProbability=guardP1[i];
    rows[i].p2Probability=guardP2[i];rows[i].p3Probability=guardP3[i];rows[i].probabilityGuard='evidence-shrink-v300'
  }
  // v300: probability guard is deliberately conservative and market-independent.
  // It is NOT a claim of fitted calibration; it only shrinks weak-evidence races toward the field prior.
  // Odds/popularity remain display + EDGE/EV inputs only and NEVER alter P1/P2/P3 or AI marks.
  for(i=0;i<rows.length;i++){rows[i].pureWinProbability=rows[i].p1Probability;rows[i].marketBlendWeight=0}
  var p1Sorted=rows.slice().sort(function(a,b){return n(b.p1Probability)-n(a.p1Probability)||n(b.winnerCore)-n(a.winnerCore)||n(b.overallRaw)-n(a.overallRaw)||n(a.horse.horseNumber)-n(b.horse.horseNumber)}),
      p2Sorted=rows.slice().sort(function(a,b){return n(b.p2Probability)-n(a.p2Probability)||n(b.posCons)-n(a.posCons)||n(b.p1Probability)-n(a.p1Probability)}),
      p3Sorted=rows.slice().sort(function(a,b){return n(b.p3Probability)-n(a.p3Probability)||n(b.latePower)-n(a.latePower)||n(b.p2Probability)-n(a.p2Probability)});
  p1Sorted.forEach(function(z,idx){z.winRank=idx+1;z.p1Rank=idx+1});p2Sorted.forEach(function(z,idx){z.p2Rank=idx+1});p3Sorted.forEach(function(z,idx){z.p3Rank=idx+1});
  for(i=0;i<rows.length;i++){
    x=rows[i];var pWin=Math.max(.001,n(x.pureWinProbability,x.p1Probability)),pMarket=Math.max(.001,n(market[i],uniform)),ratio=pWin/pMarket,delta=pWin-pMarket,log2=Math.log(ratio)/Math.LN2,
        edge=clamp(50+log2*20+delta*115,0,100),positiveEdge=clamp((edge-50)/36,0,1),viable=clamp(pWin/Math.max(uniform*1.30,.045),0,1),
        peak2=recentPeakScore(x.horse,r),roleUpside=clamp((Math.max(n(x.p2Probability),n(x.p3Probability))-uniform)/Math.max(uniform,.04)+.5,0,1),bomb,eReasons=[];
    edge=50+(edge-50)*(.66+.34*clamp(n(x.edgeEvidence),0,1));
    bomb=clamp(
      positiveEdge*.34+
      viable*.14+
      roleUpside*.14+
      n(x.p3Probability)/Math.max(uniform,.04)*.035+
      peak2*.065+
      n(x.move,.5)*.055+
      n(x.latePower,.5)*.055+
      n(x.sparseReset)*.055+
      n(x.edgeEvidence)*.045+
      n(x.p2Probability)/Math.max(uniform,.04)*.025,
      0,1
    );
    if(edge<55)bomb*=.70;
    if(pWin<uniform*.48&&n(x.p2Rank)>5&&n(x.p3Rank)>6)bomb*=.78;
    if(n(x.frontCost)>=.14&&n(x.needLead)>=.58)bomb*=.94;
    if(n(x.fade)>=.60&&n(x.goProb)>=.52)bomb*=.94;
    x.marketProbability=pMarket;x.marketSource=marketSource;x.edgeRatio=ratio;x.edgeDelta=delta;
    x.edgeScore=Math.round(edge);x.bombScore=Math.round(bomb*100);x.upsetScore=x.bombScore;x.roleUpside=Math.round(roleUpside*100);
    if(edge>=61&&pWin>pMarket)eReasons.push('P1が市場評価を上回る');
    if(n(x.p2Rank)<=4&&n(x.winRank)>=4)eReasons.push('2着役で上昇');
    if(n(x.p3Rank)<=5&&n(x.winRank)>=5)eReasons.push('3着役で上昇');
    if(n(x.sparseReset)>=.25)eReasons.push((x.sparseResetReasons||[])[0]||'限定RESET成立');
    if(n(x.goProb)>=.58&&n(x.frontStay)>=.58&&front>=.30)eReasons.push('前残り展開で残せる');
    if(n(x.comeFromBehind)>=.64&&collapse>=.28)eReasons.push('前崩れで差し浮上');
    if(peak2>=.64)eReasons.push('近5走に高いピーク');
    if(n(q.lineEndRelief)>=.05||n(q.freeOuter)>=.05)eReasons.push('隊列の自由度');
    if(!eReasons.length&&n(x.edgeScore)>=55)eReasons.push('能力と市場評価に小さなズレ');
    x.upsetReasons=eReasons.slice(0,4)
  }
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
function raceSelectionProfile(r,p){
  var rows=(p&&p.rows||[]).slice(),activeVals=rows.map(function(x){return clamp(n(x.p1Probability),0,1)}),localV213=String(r&&r.circuit||'')==='地方'&&rows.length&&rows.every(function(z){return !!z.v213RoleReady}),vals;
  if(localV213){var core=edgeSoftmax(rows.map(function(z){var e=z&&z.horse&&z.horse.integratedEvaluation||{};return Number(e.v213P1Utility)}),1);vals=core.slice()}else vals=activeVals.slice();
  vals.sort(function(a,b){return b-a});var top=vals[0]||0,second=vals[1]||0,top3=(vals[0]||0)+(vals[1]||0)+(vals[2]||0),margin=top-second,cov=n(p&&p.coverage,0),ent=0,den=Math.log(Math.max(2,vals.length)),selected=false;
  vals.forEach(function(q){q=Math.max(1e-12,q);ent-=q*Math.log(q)});ent=den>0?ent/den:1;
  if(localV213)selected=top3>=.71&&ent<=.82;
  else selected=top3>.613258&&((margin<=.046088)||(margin>.163086));
  var score=Math.round(clamp(top3*.55+(1-ent)*.25+cov*.12+(selected?.08:0),0,1)*100);
  return{selected:selected,score:score,top:top,top3mass:top3,margin:margin,entropy:ent,coverage:cov,model:localV213?'v213-selection+v218-conditional-order':'legacy',holdoutWinnerTop1:localV213?.448:0,holdoutWinnerTop3:localV213?.724:0}
}

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
function v317NormComponent(z,names,defv){
  var e=z&&z.horse&&z.horse.integratedEvaluation||{},c=e.components||{};
  for(var i=0;i<names.length;i++){if(c[names[i]]!==undefined&&c[names[i]]!==null)return clamp(n(c[names[i]],defv),0,1)}
  return clamp(n(defv,.5),0,1)
}
function v317Audit(z){var e=z&&z.horse&&z.horse.integratedEvaluation||{};return e.v218Audit||e.v217Audit||z.v218Audit||z.v217Audit||{}}
function v317FactorWeights(r,central,sparse){
  var w=central
    ?(sparse?{ability:.12,classLevel:.06,form:.07,pace:.14,suitability:.23,connections:.18,pedigree:.20}:{ability:.26,classLevel:.12,form:.14,pace:.18,suitability:.16,connections:.08,pedigree:.06})
    :(sparse?{ability:.10,classLevel:.06,form:.07,pace:.18,suitability:.25,connections:.20,pedigree:.14}:{ability:.24,classLevel:.08,form:.16,pace:.20,suitability:.18,connections:.09,pedigree:.05});
  var dist=n(r&&r.distance,0),surface=String((r&&r.surface)||'');
  function shift(a,b,x){w[a]+=x;w[b]-=x}
  if(dist&&dist<=1400){shift('pace','pedigree',.025);shift('ability','classLevel',.015)}
  else if(dist>=2300){shift('suitability','pace',.030);shift('classLevel','form',.015)}
  if(/ダ/.test(surface)){shift('pace','pedigree',.020);shift('suitability','ability',.015)}
  if(!central){shift('pace','classLevel',.015);shift('suitability','pedigree',.010)}
  var sum=0;Object.keys(w).forEach(function(k){w[k]=Math.max(.01,w[k]);sum+=w[k]});Object.keys(w).forEach(function(k){w[k]/=sum});return w
}
function v317ConsensusFactors(z,r,central){
  var a=v317Audit(z),e=z&&z.horse&&z.horse.integratedEvaluation||{},samples=n(e.samples,0),sparse=!!e.neutralPrior||samples<2,
      pure=clamp(n(a.pure,n(z.overallRaw,.5)),0,1),tr=clamp(n(a.trueRun,.5),0,1),sec=clamp(n(a.sectional,n(z.lapScore,.5)),0,1),
      scen=clamp(n(a.positionScenario,n(z.paceScore)/100),0,1),cond=clamp(n(a.conditions,n(z.shiftScore)/100),0,1),opp=clamp(n(a.opponentLevel,n(z.levelFit,.5)),0,1),state=clamp(n(a.stateConsistency,n(z.posCons,.5)),0,1),
      perf=v317NormComponent(z,['racePerformance'],.5),rep=v317NormComponent(z,['representative'],.5),course=v317NormComponent(z,['courseFit'],n(z.trackFit,.5)),dist=v317NormComponent(z,['distanceFit'],n(z.distFit,.5)),going=v317NormComponent(z,['goingFit'],n(z.condFit,.5)),
      level=v317NormComponent(z,['opponentLevelScore'],opp),lap=v317NormComponent(z,['lapScore'],sec),jockey=v317NormComponent(z,['jockeyScore','jockeyResults'],n(z.jockeyScore,.5)),trainer=v317NormComponent(z,['trainerScore','trainerResults'],n(z.trainerScore,.5)),
      body=v317NormComponent(z,['bodyWeightScore'],n(z.bodyWeightSuit,.5)),change=v317NormComponent(z,['conditionChangeScore'],.5),ped=v317NormComponent(z,['pedigreeScore'],.5),ds=v317NormComponent(z,['distanceSuitabilityScore'],dist),ss=v317NormComponent(z,['surfaceSuitabilityScore'],.5),draw=v317NormComponent(z,['drawScore'],n(z.liveDrawFit,.5)),
      live=clamp((n(z.liveDrawFit,.5)+n(z.liveStyleFit,.5))/2,0,1),recent=clamp(n(recentTop3Rate(z.horse),.5),0,1),frag=clamp(n(z.winnerRisk)*.50+n(z.frontCost)*.24+n(z.fade)*n(z.needLead)*.18+n(z.outerStress)*.08,0,1),
      ability=clamp(.28*pure+.27*tr+.17*sec+.16*perf+.12*rep,0,1),
      classLevel=clamp(.46*opp+.26*level+.16*n(z.prizeScore,.5)+.12*perf,0,1),
      form=clamp(.30*state+.26*recent+.24*perf+.12*rep+.08*(1-frag),0,1),
      pace=clamp(.34*scen+.16*lap+.15*n(z.flexibility,.5)+.12*n(z.latePower,.5)+.10*n(z.posCons,.5)+.13*(1-frag),0,1),
      suitability=clamp(.16*cond+.17*course+.17*dist+.13*going+.12*ds+.09*ss+.08*draw+.08*live,0,1),
      connections=clamp(.33*jockey+.25*trainer+.19*body+.15*change+.08*state,0,1),
      pedigree=clamp(.52*ped+.28*ds+.20*ss,0,1),w=v317FactorWeights(r,central,sparse),f={ability:ability,classLevel:classLevel,form:form,pace:pace,suitability:suitability,connections:connections,pedigree:pedigree};
  var score=0;Object.keys(w).forEach(function(k){score+=w[k]*f[k]});
  var win=clamp(score*(1-(central?.13:.08)*frag),0,1),place=clamp(.28*score+.20*form+.20*pace+.18*suitability+.08*connections+.06*(1-frag),0,1),show=clamp(.22*score+.22*form+.20*suitability+.16*pace+.08*connections+.07*pedigree+.05*(1-frag),0,1);
  return{factors:f,weights:w,score:score,win:win,place:place,show:show,fragility:frag,sparse:sparse,evidence:clamp(n(a.evidence,n(z.coverage,.5)),0,1)}
}
function v312CircuitMethod(r){
  var central=String((r&&r.circuit)||'')==='中央';
  return central?{
    id:'central-v317',winner:{p1:.28,winEvidence:.42,pairwise:.30,fragPenalty:.13},
    gate:{ready:.68,cov:.50,top3:.60,evidence:.44,scenario:.30,confidence:.64,score:69,top:.16,uniform:1.50,margin:.028},
    value:{cov:.58,ready:.68,oddsCoverage:.90,ev:1.32,edge:70,evidence:.58,kelly:.035,score:72}
  }:{
    id:'local-v317',winner:{p1:.34,winEvidence:.38,pairwise:.28,fragPenalty:.08},
    gate:{ready:.61,cov:.42,top3:.60,evidence:.36,scenario:.22,confidence:.59,score:63,top:.145,uniform:1.38,margin:.018},
    value:{cov:.52,ready:.64,oddsCoverage:.85,ev:1.25,edge:66,evidence:.52,kelly:.030,score:68}
  }
}
function strictSelectedRaceProfile(r,p){
  var base=raceSelectionProfile(r,p),rows=(p&&p.rows||[]).slice(),field=rows.length,ready=dataReadinessProfile(r,p),method=v312CircuitMethod(r),g=method.gate,dayCorr=sameDayCorrectionProfileV313(r,rows);
  if(field<5)return{selected:false,score:0,reason:'頭数不足',base:base,readiness:ready,model:method.id};
  var vals=rows.map(function(x){return clamp(n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability))),0,1)}).sort(function(a,b){return b-a}),
      top=vals[0]||0,second=vals[1]||0,top3=(vals[0]||0)+(vals[1]||0)+(vals[2]||0),margin=top-second,
      cov=n(p&&p.coverage,0),ent=0,den=Math.log(Math.max(2,vals.length));
  vals.forEach(function(q){q=Math.max(1e-12,q);ent-=q*Math.log(q)});ent=den>0?ent/den:1;
  var scenarios=((p&&p.scenarios)||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)}),scenarioProb=n((scenarios[0]||{}).prob,0),
      ranked=rows.slice().sort(function(a,b){return n(b.winnerDecisionProbability,n(b.winnerConsensusProbability,n(b.p1Probability)))-n(a.winnerDecisionProbability,n(a.winnerConsensusProbability,n(a.p1Probability)))}),topRows=ranked.slice(0,3),evidence=0,trueRun=0,conditions=0,positionScenario=0;
  topRows.forEach(function(x){var e=x&&x.horse&&x.horse.integratedEvaluation||{},a=e.v218Audit||e.v217Audit||x.v218Audit||x.v217Audit||{};evidence+=n(a.evidence,n(x.coverage));trueRun+=n(a.trueRun,.5);conditions+=n(a.conditions,.5);positionScenario+=n(a.positionScenario,.5)});
  var d=Math.max(1,topRows.length);evidence/=d;trueRun/=d;conditions/=d;positionScenario/=d;
  var leader=ranked[0]||{},winnerStable=!!leader.winnerDecisionStable,winnerConf=clamp(n(leader.axisConfidence),0,1),uniform=1/Math.max(1,field),
      qReady=clamp((ready.prediction-.50)/.36,0,1),qTop3=clamp((top3-.50)/.30,0,1),qMargin=clamp(margin/.11,0,1),qEnt=clamp((.94-ent)/.28,0,1),qScenario=clamp((scenarioProb-.20)/.36,0,1),qEvidence=clamp((evidence-.30)/.48,0,1),qWin=clamp((winnerConf-.46)/.40,0,1),qTrue=clamp((trueRun-.40)/.32,0,1),qCond=clamp((conditions-.40)/.32,0,1),qPos=clamp((positionScenario-.40)/.32,0,1);
  var authAxis=rows.filter(function(z){return z&&z.predMark==='◎'})[0]||null,authAxisNo=n(authAxis&&authAxis.horse&&authAxis.horse.horseNumber),mh=((leader.horse||{}).integratedEvaluation||{}).multiHead||{},mhSummary=(r&&r.multiHeadSummary)||{},mhReady=String(mhSummary.modelVersion||'').indexOf('arvexq-multi-head-')===0,leaderNo=n(leader.horse&&leader.horse.horseNumber),mhWinner=n(mhSummary.winnerHorseNumber),authAgree=!authAxisNo||leaderNo===authAxisNo,mhAgree=authAgree&&(!mhReady||(mhWinner>0&&leaderNo===mhWinner&&n(mh.winRank,999)===1&&n(mhSummary.winnerGap,0)>0));
  var score=Math.round(clamp(qReady*.14+qTop3*.17+qMargin*.15+qEnt*.10+qScenario*.09+qEvidence*.10+qWin*.13+qTrue*.05+qCond*.04+qPos*.03,0,1)*100),
      hard=(ready.prediction>=g.ready&&cov>=g.cov&&top3>=g.top3&&evidence>=g.evidence&&scenarioProb>=g.scenario&&winnerStable&&winnerConf>=g.confidence),
      separation=(top>=Math.max(g.top,uniform*g.uniform)||margin>=g.margin),selected=hard&&separation&&score>=g.score&&mhAgree;
  var failed=[];if(ready.prediction<g.ready)failed.push('data');if(cov<g.cov)failed.push('coverage');if(top3<g.top3)failed.push('top3');if(evidence<g.evidence)failed.push('evidence');if(scenarioProb<g.scenario)failed.push('scenario');if(!winnerStable||winnerConf<g.confidence)failed.push('winner');if(!separation)failed.push('separation');if(score<g.score)failed.push('score');if(!mhAgree)failed.push('multihead');
  return{selected:selected,score:score,top:top,top3mass:top3,margin:margin,entropy:ent,coverage:cov,scenarioProb:scenarioProb,evidence:evidence,trueRun:trueRun,conditions:conditions,positionScenario:positionScenario,winnerConfidence:winnerConf,winnerStable:winnerStable,multiHeadReady:mhReady,multiHeadAgreement:mhAgree,multiHeadGap:mhSummary.winnerGap,multiHeadWinner:mhWinner,readiness:ready,failed:failed,reason:selected?'厳選ゲート通過':('見送り: '+failed.join(',')),base:base,model:method.id};
}
function assignPredictionMarks(rows,r){
  var field=Math.max(1,rows.length),uniform=1/field,selected=[],attention=[];
  rows.forEach(function(z){z.predMark='';z.predRank=999;z.attentionReason='';z.axisProbability=0;z.axisRank=999;z.axisConfidence=0;z.axisFragility=0;z.winEvidenceProbability=0;z.winEvidenceRank=999;z.winnerConsensusProbability=0;z.winnerConsensusRank=999;z.winnerDecisionProbability=0;z.winnerDecisionRank=999;z.winDecisionReason='';z.winDecisionOverride=false;z.winnerDecisionStable=false});
  function p1(z){return clamp(n(z.pureWinProbability,z.p1Probability),0,1)}
  function audit(z){var e=z&&z.horse&&z.horse.integratedEvaluation||{};return e.v218Audit||e.v217Audit||z.v218Audit||z.v217Audit||{}}
  function seven(z){var a=audit(z);return clamp(n(a.sevenAxisScore,n(z.v239Composite,n(z.overallRaw,.5))),0,1)}
  function pure(z){return clamp(n(audit(z).pure,n(z.overallRaw,.5)),0,1)}
  function trueRun(z){return clamp(n(audit(z).trueRun,.5),0,1)}
  function sectional(z){return clamp(n(audit(z).sectional,n(z.lapScore,.5)),0,1)}
  function scenario(z){return clamp(n(audit(z).positionScenario,n(z.paceScore)/100),0,1)}
  function conditions(z){return clamp(n(audit(z).conditions,n(z.shiftScore)/100),0,1)}
  function opponent(z){return clamp(n(audit(z).opponentLevel,n(z.levelFit,.5)),0,1)}
  function stateFit(z){return clamp(n(audit(z).stateConsistency,n(z.posCons,.5)),0,1)}
  function liveBias(z){return clamp((n(z.liveDrawFit,.5)+n(z.liveStyleFit,.5))/2,0,1)}
  function fragile(z){return clamp(n(z.winnerRisk)*.50+n(z.frontCost)*.24+n(z.fade)*n(z.needLead)*.18+n(z.outerStress)*.08,0,1)}
  function robust(z){return clamp(seven(z)*.48+n(z.overallRaw,.5)*.20+n(z.edgeEvidence,n(z.coverage,.5))*.17+(1-fragile(z))*.15,0,1)}
  if(!rows.length)return;

  // v312: central/local winner evidence is genuinely separate.
  // Central: pace pressure / sectional / opponent class matter more, with a stronger fragility penalty.
  // Local: preserve the validated local backbone and track-position repeatability.
  var method=v312CircuitMethod(r),centralRace=method.id==='central-v317',dayCorr=sameDayCorrectionProfileV313(r,rows)||{active:false,completed:0,markRaces:0,evidence:0,coverage:.83,deficit:0,frontSignal:0,lateSignal:0,innerSignal:0,flowLabel:'中立',sourceRaces:[],byNo:{}};
  var research=rows.map(function(z){return v317ConsensusFactors(z,r,centralRace)});
  rows.forEach(function(z,i){z.researchFactors=research[i].factors;z.researchFactorWeights=research[i].weights;z.researchConsensusScore=research[i].score;z.researchSparse=research[i].sparse;z.researchModel='v317-expert-ai-consensus'});
  var winEvidenceRaw=rows.map(function(z,i){
    var legacy=centralRace
      ?(.18*pure(z)+.22*trueRun(z)+.17*sectional(z)+.17*scenario(z)+.09*conditions(z)+.10*opponent(z)+.04*stateFit(z)+.03*n(z.flexibility,.5))
      :(.27*pure(z)+.22*trueRun(z)+.13*sectional(z)+.14*scenario(z)+.09*conditions(z)+.06*opponent(z)+.04*stateFit(z)+.05*liveBias(z));
    var q=.72*research[i].win+.28*legacy;return clamp(q*(1-method.winner.fragPenalty*fragile(z)),.001,1)
  }),winEvidence=edgeSoftmax(winEvidenceRaw,centralRace?.090:.100);
  rows.forEach(function(z,i){z.winEvidenceScore=winEvidenceRaw[i];z.winEvidenceProbability=winEvidence[i]});
  rows.slice().sort(function(a,b){return n(b.winEvidenceProbability)-n(a.winEvidenceProbability)||n(b.researchConsensusScore)-n(a.researchConsensusScore)||p1(b)-p1(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)}).forEach(function(z,i){z.winEvidenceRank=i+1});

  // Direct duel is a separate race-relative check. P1 weight is deliberately lower
  // than v251 so that it validates the winner model instead of echoing it.
  function duelProb(a,b){
    var fa=a.researchFactors||{},fb=b.researchFactors||{},ev=Math.min(n(a.edgeEvidence,n(a.coverage,.5)),n(b.edgeEvidence,n(b.coverage,.5))),raw;
    raw=.08*(p1(a)-p1(b))+.22*(n(fa.ability,.5)-n(fb.ability,.5))+.11*(n(fa.classLevel,.5)-n(fb.classLevel,.5))+.13*(n(fa.form,.5)-n(fb.form,.5))+.18*(n(fa.pace,.5)-n(fb.pace,.5))+.16*(n(fa.suitability,.5)-n(fb.suitability,.5))+.06*(n(fa.connections,.5)-n(fb.connections,.5))+.06*(n(fa.pedigree,.5)-n(fb.pedigree,.5));
    raw+=centralRace?.07*(research[rows.indexOf(b)].fragility-research[rows.indexOf(a)].fragility):.04*(research[rows.indexOf(b)].fragility-research[rows.indexOf(a)].fragility);
    raw*=.50+.50*clamp(ev,0,1);return 1/(1+Math.exp(-8*raw))
  }
  var duelRates=rows.map(function(a){var sumD=0,cntD=0;rows.forEach(function(b){if(a===b)return;sumD+=duelProb(a,b);cntD++});return cntD?sumD/cntD:.5}),duelDist=edgeSoftmax(duelRates,.085);
  rows.forEach(function(z,i){z.pairwiseWinRate=duelRates[i];z.pairwiseProbability=duelDist[i]});
  rows.slice().sort(function(a,b){return n(b.pairwiseWinRate)-n(a.pairwiseWinRate)||p1(b)-p1(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)}).forEach(function(z,i){z.pairwiseRank=i+1});

  function v312WinnerBaseWeights(){return method.winner}
  // Consensus: statistical P1 is the backbone; independent win evidence and direct
  // duels can resolve close calls. P2/P3 and market data never enter this layer.
  var learning=(r&&r.winnerLearningProfile)||{},baseW=v312WinnerBaseWeights(),lw=(learning&&learning.weights)||baseW,wP1=n(lw.p1,baseW.p1),wWin=n(lw.winEvidence,baseW.winEvidence),wPair=n(lw.pairwise,baseW.pairwise),
      consensusRaw=rows.map(function(z){return Math.max(1e-12,wP1*p1(z)+wWin*n(z.winEvidenceProbability)+wPair*n(z.pairwiseProbability))}),pow=learning.active?clamp(n(learning.power,1),.55,1.65):1,shr=learning.active?clamp(n(learning.shrink,0),0,.25):0;
  if(pow!==1)consensusRaw=consensusRaw.map(function(v){return Math.pow(v,pow)});var cs=consensusRaw.reduce(function(a,b){return a+b},0)||1,factorEv=mean(research.map(function(q){return n(q.evidence,.5)})),evidenceShrink=clamp((.68-factorEv)*.22,0,.12);shr=Math.max(shr,evidenceShrink);
  rows.forEach(function(z,i){z.winnerConsensusProbability=(1-shr)*(consensusRaw[i]/cs)+shr/field;z.winnerLearningActive=!!learning.active;z.winnerLearningProfileId=String(learning.profileId||'baseline');z.researchConfidenceShrink=shr});
  var consensus=rows.slice().sort(function(a,b){return n(b.winnerConsensusProbability)-n(a.winnerConsensusProbability)||p1(b)-p1(a)||n(b.winEvidenceProbability)-n(a.winEvidenceProbability)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
  consensus.forEach(function(z,i){z.winnerConsensusRank=i+1});
  var core=rows.slice().sort(function(a,b){return p1(b)-p1(a)||n(b.winnerCore)-n(a.winnerCore)||n(b.overallRaw)-n(a.overallRaw)||n(a.horse.horseNumber)-n(b.horse.horseNumber)}),
      topP1=core[0],p1Gap=core.length>1?p1(core[0])-p1(core[1]):1,winLeader=topP1,best=consensus[0]||topP1;
  if(topP1&&best&&best!==topP1){
    var gap=p1(topP1)-p1(best),topC=n(topP1.winnerConsensusProbability),bestC=n(best.winnerConsensusProbability),topPair=n(topP1.pairwiseProbability),bestPair=n(best.pairwiseProbability),topEv=n(topP1.winEvidenceProbability),bestEv=n(best.winEvidenceProbability),ev=n(best.edgeEvidence,n(best.coverage,.5));
    if(centralRace){
      if(gap<=.045&&ev>=.30&&bestC>=topC*1.015&&bestPair>=topPair*.995&&bestEv>=topEv*.995)winLeader=best;
      else if(gap<=.070&&ev>=.34&&fragile(topP1)>=.55&&bestC>=topC*1.06&&bestPair>=topPair*1.01&&bestEv>=topEv*1.02)winLeader=best
    }else{
      if(gap<=.025&&ev>=.26&&bestC>=topC*.995&&bestPair>=topPair*.985)winLeader=best;
      else if(gap<=.045&&ev>=.30&&bestC>=topC*1.04&&bestPair>=topPair*1.01&&bestEv>=topEv*1.02)winLeader=best;
      else if(gap<=.060&&fragile(topP1)>=.58&&bestC>=topC*1.075&&bestPair>=topPair*1.035&&bestEv>=topEv*1.04)winLeader=best
    }
  }
  var runner=consensus.filter(function(z){return z!==winLeader})[0]||null,consMargin=n(winLeader&&winLeader.winnerConsensusProbability)-n(runner&&runner.winnerConsensusProbability),
      rawAgreement=!!(winLeader&&topP1&&winLeader===topP1),evLeader=n(winLeader&&winLeader.edgeEvidence,n(winLeader&&winLeader.coverage,.5)),frLeader=fragile(winLeader||{}),
      conf=clamp(.27+consMargin*Math.max(5.5,field*.60)+(rawAgreement?.13:.075)+Math.min(.11,p1Gap*2.0)+evLeader*.21-frLeader*.16,0,1),
      consensusTop=consensus[0]||winLeader,consensusSupports=!!winLeader&&n(winLeader.winnerConsensusProbability)>=n(consensusTop&&consensusTop.winnerConsensusProbability)*.985,
      stableFloor=centralRace?.64:.56,marginFloor=uniform*(centralRace?.075:.050),
      stable=!!winLeader&&conf>=stableFloor&&consensusSupports&&(rawAgreement||consMargin>=Math.max(.006,marginFloor));
  // Decision distribution is what ordered tickets/strict selection use. If the
  // independent consensus is unstable, fall back to P1 instead of forcing a false precision.
  var decisionProb=rows.map(function(z){return stable?n(z.winnerConsensusProbability):p1(z)}),ds=decisionProb.reduce(function(a,b){return a+b},0)||1;decisionProb=decisionProb.map(function(v){return v/ds});
  if(winLeader){var li=rows.indexOf(winLeader),mi=0;for(var di=1;di<decisionProb.length;di++)if(decisionProb[di]>decisionProb[mi])mi=di;if(li>=0&&mi!==li&&decisionProb[mi]>decisionProb[li]){var tmp=decisionProb[li];decisionProb[li]=decisionProb[mi];decisionProb[mi]=tmp}}
  rows.forEach(function(z,i){z.axisConfidence=conf;z.winnerDecisionStable=stable;z.winnerDecisionProbability=decisionProb[i]});
  rows.slice().sort(function(a,b){return n(b.winnerDecisionProbability)-n(a.winnerDecisionProbability)||p1(b)-p1(a)}).forEach(function(z,i){z.winnerDecisionRank=i+1});
  if(winLeader){winLeader.winDecisionOverride=winLeader!==topP1;winLeader.winDecisionReason=winLeader===topP1?'P1首位を独立1着評価・対戦比較でも維持':(p1Gap<=.025?'P1僅差を独立1着評価＋対戦比較で逆転':'P1首位の脆さを独立1着評価＋対戦比較で逆転')}

  // v312: podium-recall is now the primary mark objective.
  // Winner / second-place / third-place candidates are scored independently and
  // only then merged into a compact 5-7 horse mark set.  This is deliberately
  // circuit-specific: central and local do not share the same recall recipe.
  var axisSeven=edgeSoftmax(rows.map(seven),.11),axisRobust=edgeSoftmax(rows.map(robust),.12),scores=[],sum=0;
  rows.forEach(function(z,i){var q=.30*p1(z)+.16*clamp(n(z.p2Probability),0,1)+.12*clamp(n(z.p3Probability),0,1)+.24*n(research[i].score)+.10*n(research[i].place)+.08*n(axisRobust[i]),fr=fragile(z);q*=1-.06*fr;z.axisFragility=fr;scores.push(Math.max(.0001,q));sum+=Math.max(.0001,q)});
  rows.forEach(function(z,i){z.axisProbability=scores[i]/Math.max(.0001,sum)});
  var general=rows.slice().sort(function(a,b){return n(b.axisProbability)-n(a.axisProbability)||p1(b)-p1(a)||n(b.overallRaw)-n(a.overallRaw)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});general.forEach(function(z,i){z.axisRank=i+1});
  var sorted=[];if(winLeader)sorted.push(winLeader);general.forEach(function(z){if(sorted.indexOf(z)<0)sorted.push(z)});
  function take(row,mark){if(!row||selected.indexOf(row)>=0)return false;row.predMark=mark;selected.push(row);return true}

  function secondRecall(z){
    var recent=recentTop3Rate(z.horse),q;
    if(centralRace){
      q=.28*clamp(n(z.p2Probability),0,1)+.12*p1(z)+.30*n(research[rows.indexOf(z)].place)+.08*trueRun(z)+.06*sectional(z)+.06*scenario(z)+.04*opponent(z)+.03*robust(z)+.03*recent;
      q*=1-.07*fragile(z);
    }else{
      q=.30*clamp(n(z.p2Probability),0,1)+.10*p1(z)+.30*n(research[rows.indexOf(z)].place)+.08*clamp(n(z.posCons,.5),0,1)+.07*clamp(n(z.trackFit,.5),0,1)+.06*scenario(z)+.03*liveBias(z)+.03*recent+.03*robust(z);
      q*=1-.035*fragile(z);
    }
    var dc=(dayCorr.byNo||{})[n(z.horse&&z.horse.horseNumber)]||{};q+=n(dc.p2Boost,0);
    return clamp(q,0,1)
  }
  function thirdRecall(z){
    var recent=recentTop3Rate(z.horse),q;
    if(centralRace){
      q=.27*clamp(n(z.p3Probability),0,1)+.34*n(research[rows.indexOf(z)].show)+.09*clamp(n(z.latePower,.5),0,1)+.08*trueRun(z)+.06*sectional(z)+.06*scenario(z)+.04*clamp(n(z.move,.5),0,1)+.03*opponent(z)+.03*robust(z);
      q*=1-.045*fragile(z);
    }else{
      q=.29*clamp(n(z.p3Probability),0,1)+.34*n(research[rows.indexOf(z)].show)+.09*clamp(n(z.posCons,.5),0,1)+.08*clamp(n(z.trackFit,.5),0,1)+.07*scenario(z)+.05*recent+.03*liveBias(z)+.03*clamp(n(z.move,.5),0,1)+.02*robust(z);
      q*=1-.025*fragile(z);
    }
    var dc=(dayCorr.byNo||{})[n(z.horse&&z.horse.horseNumber)]||{};q+=n(dc.p3Boost,0);
    return clamp(q,0,1)
  }
  rows.forEach(function(z){
    var dc=(dayCorr.byNo||{})[n(z.horse&&z.horse.horseNumber)]||{};
    z.p2RecallScore=secondRecall(z);z.p3RecallScore=thirdRecall(z);z.sameDayMarkBoost=n(dc.markBoost,0);z.sameDayFlowActive=!!dayCorr.active;z.sameDayFlowLabel=dayCorr.flowLabel;
    // A podium candidate can enter through any of the three finishing roles.
    z.podiumRecallScore=clamp(Math.max(p1(z)*.86+n(dc.winBoost,0),z.p2RecallScore,z.p3RecallScore)*.72+robust(z)*.18+n(z.edgeEvidence,n(z.coverage,.5))*.10+n(dc.markBoost,0)*.10,0,1)
  });
  var p2Recall=rows.slice().sort(function(a,b){return n(b.p2RecallScore)-n(a.p2RecallScore)||n(a.p2Rank,99)-n(b.p2Rank,99)||n(b.axisProbability)-n(a.axisProbability)}),
      p3Recall=rows.slice().sort(function(a,b){return n(b.p3RecallScore)-n(a.p3RecallScore)||n(a.p3Rank,99)-n(b.p3Rank,99)||n(b.axisProbability)-n(a.axisProbability)}),
      podiumRecall=rows.slice().sort(function(a,b){return n(b.podiumRecallScore)-n(a.podiumRecallScore)||n(b.axisProbability)-n(a.axisProbability)||p1(b)-p1(a)});
  p2Recall.forEach(function(z,i){z.p2RecallRank=i+1});p3Recall.forEach(function(z,i){z.p3RecallRank=i+1});podiumRecall.forEach(function(z,i){z.podiumRecallRank=i+1});

  // v316: independent-route diversity guard.  A frequent failure was one horse
  // missing from the marked set even though it ranked highly on a different route.
  // This is market-independent and only affects the lower coverage lanes.
  function dimRank(fn){var a=rows.slice().sort(function(x,y){return n(fn(y))-n(fn(x))||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),m={};a.forEach(function(z,i){m[n(z.horse.horseNumber)]=i+1});return m}
  var dimMaps=[dimRank(function(z){return n((z.researchFactors||{}).ability,.5)}),dimRank(function(z){return n((z.researchFactors||{}).form,.5)}),dimRank(function(z){return n((z.researchFactors||{}).pace,.5)}),dimRank(function(z){return n((z.researchFactors||{}).suitability,.5)}),dimRank(function(z){return n((z.researchFactors||{}).connections,.5)})];
  rows.forEach(function(z){var no=n(z.horse.horseNumber),rs=dimMaps.map(function(m){return n(m[no],99)}),hits=rs.filter(function(v){return v<=4}).length,best=Math.min.apply(null,rs);z.recallDiversityHits=hits;z.recallDiversityBest=best;z.recallDiversityScore=clamp(n(z.podiumRecallScore)*.52+n(z.p3RecallScore)*.18+n(z.p2RecallScore)*.10+robust(z)*.10+(hits/5)*.08+(best<=2?.04:0),0,1)});

  // ◎ = winner role. ○ = dedicated second-role. ▲ = best remaining podium role.
  take(winLeader||sorted[0],'◎');
  var secondPick=p2Recall.find(function(z){return selected.indexOf(z)<0})||sorted.find(function(z){return selected.indexOf(z)<0});
  take(secondPick,'○');
  var thirdCore=podiumRecall.find(function(z){return selected.indexOf(z)<0&&(n(z.p2RecallRank)<=5||n(z.p3RecallRank)<=5||n(z.axisRank)<=4)})||podiumRecall.find(function(z){return selected.indexOf(z)<0});
  take(thirdCore,'▲');

  // ☆+ is reserved for a remaining runner that still owns genuine first-place upside.
  var plusPool=rows.filter(function(z){return selected.indexOf(z)<0&&p1(z)>=uniform*.72&&n(z.podiumRecallScore)>=.48&&(trueRun(z)>=.46||scenario(z)>=.50||n(z.p2RecallRank)<=4)});
  plusPool.sort(function(a,b){var au=p1(a)*.34+n(a.podiumRecallScore)*.34+n(a.p2RecallScore)*.16+n(a.p3RecallScore)*.16,bu=p1(b)*.34+n(b.podiumRecallScore)*.34+n(b.p2RecallScore)*.16+n(b.p3RecallScore)*.16;return bu-au});
  var plus=plusPool[0]||null;if(plus){take(plus,'☆+');plus.attentionReason='1着余地＋2/3着役の複線候補'}

  // ☆ is the strongest remaining third-place role, independent of win rank.
  var showPick=p3Recall.find(function(z){return selected.indexOf(z)<0&&(n(z.p3RecallRank)<=6||n(z.p3Probability)>=uniform*.72)})||p3Recall.find(function(z){return selected.indexOf(z)<0});
  if(showPick){take(showPick,'☆');showPick.attentionReason='3着役 '+Math.round(n(showPick.p3RecallScore)*100)+'/100｜'+(centralRace?'上がり・TRUE RUN・区間/展開':'位置取り再現・同場/展開・近走3着内')}

  // △ remains the dedicated rescue lane: a horse can be weak on win rank but
  // cannot be discarded if it has a different credible route into third.
  var rescue=thirdRescueCandidateV312(r,rows,selected);
  if(rescue){take(rescue,'△');rescue.thirdRescue=true;rescue.attentionReason='3着救済 '+Math.round(n(rescue.thirdRescueScore)*100)+'/100｜'+(centralRace?'上がり・TRUE RUN・区間/展開':'位置取り再現・同場/展開・近走3着内')}
  // If the race itself is uncertain, keep one softer third-role lane instead of
  // pretending the remaining field is safely discardable.
  if(!rescue&&field>=10&&(!stable||(dayCorr.active&&dayCorr.deficit>=.22))){var softRescue=p3Recall.find(function(z){return selected.indexOf(z)<0&&n(z.p3RecallRank)<=7&&n(z.edgeEvidence,n(z.coverage,.5))>=.20});if(softRescue){take(softRescue,'△');softRescue.thirdRescue=true;softRescue.attentionReason='難解戦の3着保険｜P3 '+Math.round(n(softRescue.p3RecallScore)*100)+'/100'}}

  // The final coverage lane protects role diversity. Hard/unstable 10-11 runner
  // races may use the seventh mark; strong/easy races remain compact.
  var hardRecallRace=!stable||conf<(centralRace?.70:.64)||(dayCorr.active&&dayCorr.deficit>=.22),
      targetMarks=Math.min(field,field>=12?7:(field>=10&&hardRecallRace?7:(field>=7?6:Math.min(field,5))));
  var diversityPool=rows.filter(function(z){return selected.indexOf(z)<0&&n(z.edgeEvidence,n(z.coverage,.5))>=.22&&(n(z.recallDiversityHits)>=2||n(z.recallDiversityBest)<=2)&&n(z.podiumRecallScore)>=.36}).sort(function(a,b){return n(b.recallDiversityScore)-n(a.recallDiversityScore)||n(b.p3RecallScore)-n(a.p3RecallScore)});
  if(selected.length<targetMarks&&diversityPool.length){var dv=diversityPool[0];take(dv,'注+');dv.attentionReason='独立根拠の拾い漏れ防止｜'+n(dv.recallDiversityHits)+'軸上位 / P3 '+Math.round(n(dv.p3RecallScore)*100)}
  var coveragePool=rows.filter(function(z){return selected.indexOf(z)<0}).sort(function(a,b){
    var ar=Math.min(n(a.p2RecallRank,99),n(a.p3RecallRank,99),n(a.axisRank,99)),br=Math.min(n(b.p2RecallRank,99),n(b.p3RecallRank,99),n(b.axisRank,99));
    var au=n(a.podiumRecallScore)*.56+n(a.p2RecallScore)*.17+n(a.p3RecallScore)*.20+n(a.edgeEvidence,n(a.coverage,.5))*.07+(ar<=5?.05:0),
        bu=n(b.podiumRecallScore)*.56+n(b.p2RecallScore)*.17+n(b.p3RecallScore)*.20+n(b.edgeEvidence,n(b.coverage,.5))*.07+(br<=5?.05:0);
    return bu-au||ar-br||n(b.axisProbability)-n(a.axisProbability)
  });
  var alertLabels=selected.some(function(z){return z.predMark==='注+'})?['注']:['注+','注'],ci=0;
  while(selected.length<targetMarks&&ci<coveragePool.length&&alertLabels.length){
    var z=coveragePool[ci++],eligible=(n(z.podiumRecallScore)>=.43||n(z.p2RecallRank)<=5||n(z.p3RecallRank)<=6||n(z.axisRank)<=6);
    if(!eligible)continue;
    var strong=n(z.podiumRecallScore)>=.56&&(n(z.p2RecallRank)<=4||n(z.p3RecallRank)<=4||scenario(z)>=.58||liveBias(z)>=.68),mark;
    if(strong&&alertLabels.indexOf('注+')>=0)mark='注+';else if(alertLabels.indexOf('注')>=0)mark='注';else mark=alertLabels[0];
    alertLabels.splice(alertLabels.indexOf(mark),1);take(z,mark);z.attentionReason=(mark==='注+'?'複数役で上位圏まで警戒':'候補完全包含の最終ガード')+'｜P2 '+Math.round(n(z.p2RecallScore)*100)+' / P3 '+Math.round(n(z.p3RecallScore)*100)
  }
  // v316 shadow swap: only the lowest alert lane can be replaced. Core marks
  // (◎○▲☆+☆△) are never rewritten by this guard.
  var shadowPool=rows.filter(function(z){return selected.indexOf(z)<0&&n(z.recallDiversityHits)>=2&&n(z.edgeEvidence,n(z.coverage,.5))>=.24}).sort(function(a,b){return n(b.recallDiversityScore)-n(a.recallDiversityScore)}),
      weakPool=selected.filter(function(z){return z.predMark==='注'||z.predMark==='注+'}).sort(function(a,b){return n(a.recallDiversityScore)-n(b.recallDiversityScore)});
  if(shadowPool.length&&weakPool.length){var sh=shadowPool[0],wk=weakPool[0];if(n(sh.recallDiversityScore)>=n(wk.recallDiversityScore)+.055){var mk=wk.predMark;wk.predMark='';selected.splice(selected.indexOf(wk),1);take(sh,mk);sh.attentionReason='最終シャドー救済｜独立'+n(sh.recallDiversityHits)+'軸で上位'}}
  if(dayCorr.active){selected.forEach(function(z){if(n(z.sameDayMarkBoost)>.012){z.attentionReason=(z.attentionReason?z.attentionReason+'｜':'')+'当日'+dayCorr.flowLabel+'補正'}})}
  var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注+':7,'注':8};rows.slice().sort(function(a,b){return n(order[a.predMark],99)-n(order[b.predMark],99)||n(b.axisProbability)-n(a.axisProbability)||p1(b)-p1(a)}).forEach(function(z,idx){z.predRank=idx+1});
  if(winLeader){winLeader.circuitMethod=method.id;winLeader.sameDayCorrection=dayCorr;winLeader.axisReason=method.id+' / 共通因子7＋相対比較 / '+winLeader.winDecisionReason+' / P1差 '+(p1Gap*100).toFixed(1)+'pt / 独立1着 '+(n(winLeader.winEvidenceProbability)*100).toFixed(1)+'% / 対戦 '+(n(winLeader.pairwiseWinRate)*100).toFixed(1)+'% / 統合 '+(n(winLeader.winnerConsensusProbability)*100).toFixed(1)+'% / 軸信頼 '+Math.round(conf*100)+'/100'+(dayCorr.active?' / 当日'+dayCorr.flowLabel+'補正 '+Math.round(dayCorr.evidence*100)+'/100':'')}
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
    var score=n(x.overallScore,50),coverage=n(x.coverage,0);
    x.modelScore=score;
    x.evidenceScore=null;
    x.evaluation={
      score:score,
      grade:x.overallGrade||'C',
      modelScore:score,
      evidenceScore:null,
      predictionModel:(predictionProfile(r)||{}).version||'',
      confidence:coverage>=.72?'高':(coverage>=.45?'中':'低'),
      tier:coverage>=.72?'フルデータ評価':(coverage>=.45?'限定データ評価':'基礎データ評価'),
      mode:'近走5走・通過順・展開・市場乖離',
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

function applyServerAuthoritativeMarks(rows,r){
  rows=rows||[];r=r||{};
  var byNo={},lock=r.preRacePrediction||{},locked=Array.isArray(lock.horses)?lock.horses:[],i,x,no,mark;
  for(i=0;i<locked.length;i++){x=locked[i]||{};no=n(x.horseNumber,0);mark=String(x.mark||'');if(no&&mark)byNo[no]=mark}
  if(!Object.keys(byNo).length){
    for(i=0;i<(r.horses||[]).length;i++){
      x=r.horses[i]||{};var e=x.integratedEvaluation||{};no=n(x.horseNumber,0);mark=String(e.mark||'');
      if(no&&mark&&String(e.markEngineVersion||r.markEngineVersion||'').indexOf('arvexq-four-pillar-marks-')===0)byNo[no]=mark
    }
  }
  if(!Object.keys(byNo).length)return false;
  var order={'◎':1,'○':2,'▲':3,'☆+':4,'☆':5,'△':6,'注':7};
  for(i=0;i<rows.length;i++){
    x=rows[i]||{};no=n(x.horse&&x.horse.horseNumber,0);mark=byNo[no]||'';
    x.frontendComputedMark=String(x.predMark||'');
    x.predMark=mark;
    x.predRank=order[mark]||999;
    x.authoritativeMark=!!mark;
  }
  return true
}
function predict(r){if(r._prediction)return r._prediction;var modelRace=analysisRace(r),profile=predictionProfile(modelRace),rows=buildRows(modelRace),occ=earlyOcc(modelRace),tactical=tacticalContext(modelRace,rows),pressure=tactical.pressure,arrangement=tactical.arrangement,sc=scenarioModel(r,rows,pressure,arrangement),suit=suitability(rows,sc,pressure),plans={},i;assignOverallGrades(modelRace,rows,suit,sc,pressure);assignEdgeEngine(modelRace,rows,suit,sc,pressure);integratedGrades(r,rows);assignPredictionMarks(rows,modelRace);applyServerAuthoritativeMarks(rows,modelRace);for(i=0;i<sc.length;i++){var code=sc[i].code,candidates=rows.slice().sort(function(a,b){return scenarioSuit(b,code,pressure)-scenarioSuit(a,code,pressure)});sc[i].horses=candidates.slice(0,3).map(function(x){return x.horse});plans[code]=scenarioPlan(r,rows,[sc[i]],suit,pressure,arrangement)}var top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0],plan=plans[top.code]||scenarioPlan(r,rows,sc,suit,pressure,arrangement),cov=mean(rows.map(function(x){return x.coverage}));var result={rows:rows,occ:occ,scenarios:sc,plan:plan,plans:plans,suit:suit,coverage:cov,pressure:pressure,arrangement:arrangement,profile:profile,engineVersion:'arvexq-edge-2026.10-v53-consensus-rebuild',markEngineVersion:'v317-consensus-rebuild',researchAudit:{expertAIConsensusV317:true,marketBlindFactorsV317:true,podiumRecallV312:true,sameDayFlowV313:true,sectional:true,probabilityRegularization:true,conservativeProbabilityGuardV260:true,predictionMarketIndependent:true,marketUsedForEdgeEvOnly:true,liveTrackBias:true,robustLiveTrackSpeedV300:true,historicalDrawBias:true,strongerP2P3Roles:true,conditionalPlaceRoles:true,markRolesV246:true,winnerSelectorV300Independent:true,immutablePreRaceAuditV300:true,dateBlockedWinnerLearningV300:true,raceTypeTicketV300:true,pairwiseDuelV300:true,fullOrderSequential:true,strictReadinessV300:true,actualOddsEvOnlyV300:true,oddsCoverageV247:true}};Object.defineProperty(r,"_prediction",{value:result,configurable:true,writable:true,enumerable:false});return result}
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
function runnerDetailBody(r,p,x){
  var h=x.horse,displayName=horseDisplayName(r,h),recent=(h.recentRaces||[]).slice(0,5),reasons=(x.overallReasons||[]).slice(0,3),bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明';
  return '<div class="horse-detail"><div class="horse-detail-identity">'+badge(h)+'<div class="horse-detail-identity-text"><strong>'+esc(displayName)+'</strong><span>'+esc(h.sex||'—')+esc(h.age||'—')+'　'+esc(h.jockey||'騎手不明')+'　'+esc(carriedWeightText(h))+'</span></div></div>'+
    '<div class="runner-overall-box"><div class="runner-overall-head"><span class="label">AI総合評価</span><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'C')+'</strong><span class="runner-overall-mark" data-ai-mark="'+esc(x.predMark||'')+'">'+esc(x.predMark||'—')+'</span><button type="button" class="runner-check '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+'</button><span class="runner-overall-score">総合 '+esc(overallScoreText(x))+'</span></div>'+
    (reasons.length?'<div class="overall-reasons">'+reasons.map(function(z){var warn=String(z).indexOf('注意')>=0||String(z).indexOf('不足')>=0;return '<i class="'+(warn?'warn':'good')+'">'+esc(z)+'</i>'}).join('')+'</div>':'')+'</div>'+
    '<div class="detail-heading">基本情報</div><div class="horse-info-grid"><div class="horse-info-cell"><small>馬番 / 枠</small><b>'+esc(h.horseNumber)+'番 / '+esc(h.frameNumber||frame(h))+'枠</b></div><div class="horse-info-cell"><small>性齢 / 斤量</small><b>'+esc(h.sex||'—')+esc(h.age||'—')+' / '+esc(carriedWeightText(h))+'</b></div><div class="horse-info-cell"><small>脚質</small><b>'+esc(styleTxt)+'</b></div><div class="horse-info-cell"><small>騎手</small><b>'+esc(h.jockey||'—')+'</b></div><div class="horse-info-cell"><small>調教師</small><b>'+esc(h.trainer||'—')+'</b></div><div class="horse-info-cell"><small>馬体重</small><b>'+(bodyTxt?esc(bodyTxt):'—')+'</b></div></div>'+
    '<div class="recent-list-title">近走データ（直近5走）</div>'+(recent.length?recent.map(function(rr){var rid=rr.raceId||((r.circuit==='地方'&&rr.date&&rr.track&&n(rr.raceNumber))?('nar-'+rr.date+'-'+rr.track+'-'+String(n(rr.raceNumber)).padStart(2,'0')):'');return '<div class="recent"><div class="recent-head"><b>'+esc(rr.date)+' '+esc(rr.track)+' '+(n(rr.raceNumber)?esc(rr.raceNumber)+'R ':'')+esc(rr.distance)+'m</b><strong>'+esc(rr.finish||'—')+'着</strong></div><div>'+fmtTime(rr.timeSeconds)+'　'+esc(rr.condition||'不明')+' / '+esc(rr.weather||'不明')+'</div><div class="muted">'+(rr.title?esc(rr.title)+'　':'')+'通過 '+esc((rr.cornerPositions||[]).join('-')||'—')+'　頭数 '+esc(rr.fieldSize||'—')+(saneCarriedWeightValue(rr.carriedWeight,rr.bodyWeight)?'　斤量 '+esc(String(saneCarriedWeightValue(rr.carriedWeight,rr.bodyWeight)).replace(/\.0$/,''))+'kg':'')+(rr.jockey?'　騎手 '+esc(rr.jockey):'')+'</div>'+(rid?'<button type="button" class="recent-open" data-past-race="'+esc(rid)+'">この過去レースを見る</button>':'')+'</div>'}).join(''):'<div class="empty compact">過去データを確認できませんでした</div>')+'</div>'
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
    +'?t='+Date.now()
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
    if(reflectUseful(v))out[key]=v
  });
  ['winOdds','popularity','bodyWeight','bodyWeightChange','status','updatedAt'].forEach(function(key){
    if(liveH[key]!=null&&liveH[key]!=='')out[key]=liveH[key]
  });
  if(liveH.horseNumber)out.horseNumber=liveH.horseNumber;
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
  var oldResult=base.result||{},newResult=incoming.result||{};
  var oldFinish=(oldResult.finishers||[]).length,newFinish=(newResult.finishers||[]).length;
  if(newFinish>=oldFinish&&reflectUseful(newResult))out.result=newResult;
  else if(reflectUseful(oldResult))out.result=oldResult;
  var oldBy={},newBy={},liveBy={},order=[];
  (base.horses||[]).forEach(function(h){var no=n(h&&h.horseNumber,0);if(no){oldBy[no]=h;order.push(no)}});
  (incoming.horses||[]).forEach(function(h){var no=n(h&&h.horseNumber,0);if(no){newBy[no]=h;if(order.indexOf(no)<0)order.push(no)}});
  (oddsRows||[]).forEach(function(z){var q=edgeOddsRow(z),no=n(q.horseNumber,0);if(no){liveBy[no]=q;if(order.indexOf(no)<0)order.push(no)}});
  if(order.length){
    order.sort(function(a,b){return a-b});
    out.horses=order.map(function(no){return mergeHorseReflection(oldBy[no],newBy[no],liveBy[no])})
  }
  if((oddsRows||[]).length){
    out.oddsUpdatedAt=String((oddsRows||[]).reduce(function(mx,z){return Math.max(mx,n(z&&((z.updatedAt!=null)?z.updatedAt:z.updated_at),0))},0)||out.oddsUpdatedAt||'');
    out.liveFieldsMerged=true
  }
  return mergeResultHorseFields(out)
}
function raceDisplayCoreReady(d,row){
  if(!d)return false;
  var hs=(d.horses||[]).filter(function(h){return h&&n(h.horseNumber)>0});
  if(!hs.length){
    var fs=d.result&&d.result.finishers||[];
    return isFinal(d)&&fs.filter(function(x){return x&&n(x.horseNumber)>0&&String(x.name||'').trim()}).length>=3
  }
  var expected=n((row||d).fieldSize,0);
  if(expected>=4&&hs.length<Math.max(3,Math.ceil(expected*.70)))return false;
  var active=hs.filter(function(h){return !isScratchHorse(h)});
  if(!active.length)active=hs;
  var named=active.filter(function(h){return String(h.name||'').trim()}).length;
  if(named<active.length)return false;
  var core=active.filter(function(h){
    var jockey=String(h.jockey||'').trim(),cw=n(h.carriedWeight!=null?h.carriedWeight:h.weight,0);
    return !!jockey&&cw>0
  }).length;
  if(active.length>=4&&core<Math.ceil(active.length*.70))return false;
  return true
}

function edgeFetchJson(url,timeoutMs){
  timeoutMs=n(timeoutMs,6500);
  var controller=(typeof AbortController!=='undefined')?new AbortController():null,timer=null,opts={cache:'no-store'};
  if(controller){opts.signal=controller.signal;timer=setTimeout(function(){try{controller.abort()}catch(e){}},timeoutMs)}
  return fetch(url,opts).then(function(res){if(!res.ok)throw Error('http '+res.status);return res.json()}).finally(function(){if(timer)clearTimeout(timer)})
}
function edgeDayRaceFallback(id,date,cached){
  date=String(date||state.date||today());
  return edgeFetchJson('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+encodeURIComponent(date)+'&details=1&t='+Date.now(),7000)
    .then(function(body){
      var details=(body&&body.details)||[],summaries=(body&&body.races)||[],d=null,summary=null,i;
      for(i=0;i<details.length;i++)if(String(details[i]&&details[i].id||'')===String(id)){d=details[i];break}
      for(i=0;i<summaries.length;i++)if(String(summaries[i]&&summaries[i].id||'')===String(id)){summary=summaries[i];break}
      var merged=mergeRaceReflection(cached,d,null,summary||null);
      if(!raceDisplayCoreReady(merged,summary||merged))return raceDisplayCoreReady(cached,cached)?cached:null;
      instantTrackDetails[String(id)]=merged;saveDetailCache(id,merged);return merged
    })
    .catch(function(){return cached||null})
}
function fetchEdgeRace(id,forceNetwork){
  if(!id)return Promise.resolve(null);
  var cached=instantTrackDetails[String(id)]||loadDetailCache(id),
      row=(state.races||[]).find(function(x){return String(x&&x.id||'')===String(id)})||null,
      date=String((row&&row.date)||(cached&&cached.date)||state.date||today()),
      historical=!!(cached&&cached.date&&String(cached.date)<today());
  if(!forceNetwork&&historical&&raceDisplayCoreReady(cached,row||cached)){instantTrackDetails[String(id)]=cached;return Promise.resolve(cached)}

  return edgeFetchJson(edgeRaceUrl(id),6500)
    .then(function(body){
      var d=body&&body.detail?body.detail:null,odds=(body&&body.odds)||[],summary=(body&&body.summary)||row||{};
      var merged=mergeRaceReflection(cached,d,odds,summary);
      if(body&&body.analysis_ready&&merged)merged.preparedMeta=Object.assign({},merged.preparedMeta||{},{diagnosisReady:true});
      if(!raceDisplayCoreReady(merged,summary||row||merged))throw Error('edge core detail incomplete');
      instantTrackDetails[String(id)]=merged;saveDetailCache(id,merged);return merged
    })
    .catch(function(){return edgeDayRaceFallback(id,date,cached)})
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
function refreshOddsOnly(force){
  if(!state.race||state.oddsBusy)return Promise.resolve(false);
  var id=String(state.race.id||'');if(!id)return Promise.resolve(false);
  state.oddsBusy=true;
  var status=document.getElementById('odds-status');if(status)status.textContent=' 最新データ確認中…';
  return fetchEdgeRace(id,true).then(function(fresh){
    if(!fresh||!state.race||String(state.race.id)!==id)return false;
    var before='';try{before=JSON.stringify(state.race)}catch(e){}
    var next=applySummaryEnvironment(mergeRaceReflection(state.race,fresh,null,null)),after='';try{after=JSON.stringify(next)}catch(e){}
    var changed=!before||!after||before!==after;
    if(changed){
      state.race=next;
      instantTrackDetails[id]=next;
      try{delete state.race._prediction}catch(e){}
      state.pred=null;
      saveDetailCache(id,state.race);
      render()
    }else{
      var st=document.getElementById('odds-status');
      if(st)st.textContent=(raceBodyWeightComplete(state.race)&&raceOddsComplete(state.race))?' 最新データ反映済み':' オッズ・馬体重更新待ち'
    }
    return changed
  }).catch(function(){var st=document.getElementById('odds-status');if(st)st.textContent=' 更新待ち';return false}).finally(function(){state.oddsBusy=false})
}
function ensureAutoOdds(r){
  if(!r)return;
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  if(r.date!==today())return;
  var start=mins(r.startTime),remain=start-nowMins(),after=start<9999?nowMins()-start:-9999;
  var needWeight=!raceBodyWeightComplete(r),needOdds=!raceOddsComplete(r);
  var needResult=start<9999&&after>=0&&after<=90&&!isFinal(r);
  if(isFinal(r))return;
  var delay=needResult?4000:((needWeight||needOdds)?5000:(remain>0?8000:5000));
  state.oddsTimer=setTimeout(function(){
    if(state.race&&String(state.race.id)===String(r.id))refreshOddsOnly(false)
  },delay)
}
function overallScoreText(x){var v=x&&x.overallScoreExact!=null?Number(x.overallScoreExact):Number(x&&x.overallScore);return isFinite(v)?(Math.round(v*10)/10).toFixed(1):'—'}
function aiBetStoreKey(id){return 'arvexq:prebet:v300:'+String(id||'')}
function loadStoredAiBet(id,allowLegacy){try{var keys=[aiBetStoreKey(id)],i,x;if(allowLegacy){['v218','v217','v215','v213','v212','v211','v210','v207','v205','v181','v180'].forEach(function(v){keys.push('arvexq:prebet:'+v+':'+String(id||''))})}for(i=0;i<keys.length;i++){x=JSON.parse(localStorage.getItem(keys[i])||'null');if(x&&((x.items&&x.items.length)||x.decision==='見送り'))return x}return null}catch(e){return null}}
function saveStoredAiBet(r,plan){try{if(!r||!r.id||!plan||isFinal(r))return;var st=mins(r.startTime),started=(r.date===today()&&st<9999&&nowMins()>=st);if(started||loadStoredAiBet(r.id,false))return;plan.fixedAt=new Date().toISOString();localStorage.setItem(aiBetStoreKey(r.id),JSON.stringify(plan))}catch(e){}}
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
  return !!(r&&(raceIsGraded(r)||
    (String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))||(sel&&sel.selected)))
}
function buildV213AiBetPlan(r,p,rows,featured){
  function no(x){return x&&x.horse?n(x.horse.horseNumber):0}
  function ev(x){return x&&x.horse&&x.horse.integratedEvaluation||{}}
  function util(x,k){var e=ev(x);if(k===1&&e.v218P1Utility!=null)return Number(e.v218P1Utility);if(k===1&&e.v217P1Utility!=null)return Number(e.v217P1Utility);if(k===1&&e.v215P1Utility!=null)return Number(e.v215P1Utility);return Number(e['v213P'+k+'Utility'])}
  function entropy(ps){var z=0,den=Math.log(Math.max(2,ps.length));ps.forEach(function(q){q=Math.max(1e-12,n(q));z-=q*Math.log(q)});return den>0?z/den:1}
  function key2(a,b){a=n(a);b=n(b);return a<b?a+'-'+b:b+'-'+a}
  function pushMap(map,key,score,combo){if(!map[key])map[key]={combo:combo,score:0};map[key].score+=score}
  function rankMap(map){return Object.keys(map).map(function(k){return map[k]}).sort(function(a,b){return b.score-a.score})}
  function topCombos(list,max){var out=[],i;for(i=0;i<list.length&&out.length<max;i++)if(list[i]&&list[i].combo&&list[i].combo.every(function(v){return n(v)>0}))out.push(list[i].combo.slice());return out}
  function compactCombos(list,max,minRatio,minCount){var out=[],top=list&&list[0]?n(list[0].score):0,i;minCount=minCount||1;for(i=0;i<(list||[]).length&&out.length<max;i++){var z=list[i];if(!z||!z.combo||!z.combo.every(function(v){return n(v)>0}))continue;if(out.length>=minCount&&top>0&&n(z.score)<top*minRatio)break;out.push(z.combo.slice())}return out}
  function normWeights(ws){var sum=ws.reduce(function(a,b){return a+Math.max(0,n(b))},0)||1;return ws.map(function(v){return Math.max(0,n(v))/sum})}
  function audit(x){var e=ev(x);return e.v218Audit||e.v217Audit||x.v218Audit||x.v217Audit||{}}
  function roleFit(x,k){var e=ev(x),a=audit(x),legacy;if(k===2&&e.v218P2RoleFit!=null)legacy=clamp(n(e.v218P2RoleFit),0,1);else if(k===3&&e.v218P3RoleFit!=null)legacy=clamp(n(e.v218P3RoleFit),0,1);else legacy=clamp(n(k===2?a.secondRole:a.thirdRole,.5),0,1);var live=clamp(n(k===2?x.p2Strength:x.p3Strength,.5),0,1);return clamp(legacy*.58+live*.42,0,1)}
  function scenarioMix(x,role){
    var scenarios=(p.scenarios||[]),sum=0,den=0;
    if(!scenarios.length)return 1;
    scenarios.forEach(function(sc){var pr=Math.max(0,n(sc.prob)),title=String(sc.title||sc.code||''),fit=.5;
      if(/前|残|逃|スロー/.test(title))fit=role===1?clamp(n(x.frontStay,.5),0,1):(role===2?clamp(.55*n(x.posCons,.5)+.45*n(x.frontStay,.5),0,1):clamp(.55*n(x.posCons,.5)+.45*n(x.latePower,.5),0,1));
      else if(/差|崩|ハイ|消耗/.test(title))fit=role===1?clamp(n(x.comeFromBehind,.5),0,1):(role===2?clamp(.48*n(x.comeFromBehind,.5)+.52*n(x.posCons,.5),0,1):clamp(.62*n(x.latePower,.5)+.38*n(x.comeFromBehind,.5),0,1));
      else fit=role===1?clamp(n(x.paceScore,50)/100,0,1):(role===2?clamp(n(x.posCons,.5),0,1):clamp(.55*n(x.latePower,.5)+.45*n(x.posCons,.5),0,1));
      sum+=pr*fit;den+=pr
    });
    return .78+.44*(den?sum/den:.5)
  }
  function pairFactor(first,second){
    var a=audit(first),b=audit(second),f=scenarioMix(second,2)*(.84+.32*roleFit(second,2));
    var firstFront=clamp(n(first.frontStay,.5),0,1),secondFront=clamp(n(second.frontStay,.5),0,1);
    // Two highly aggressive runners are less likely to occupy 1-2 together when the winner already paid the early cost.
    if(firstFront>=.62&&secondFront>=.62)f*=.88;
    if(n(first.frontCost)>=.16&&n(second.goProb)>=.58)f*=.91;
    if(a.positionPressure&&a.positionPressure.sandwich&&secondFront>=.60)f*=.94;
    f*=.92+.16*clamp(n(second.posCons,.5),0,1);
    f*=.94+.12*clamp(n(b.trueRun,.5),0,1);
    return clamp(f,.62,1.48)
  }
  function thirdFactor(first,second,third){
    var c=audit(third),f=scenarioMix(third,3)*(.84+.32*roleFit(third,3));
    var firstFront=clamp(n(first.frontStay,.5),0,1),secondFront=clamp(n(second.frontStay,.5),0,1),thirdFront=clamp(n(third.frontStay,.5),0,1);
    // If the first two are both forward, leave more room for a late/position-gain horse in third.
    if(firstFront>=.56&&secondFront>=.56)f*=.88+.26*clamp(n(third.latePower,.5),0,1);
    // Avoid blindly stacking three identical front profiles in a pressured race.
    if(firstFront>=.62&&secondFront>=.62&&thirdFront>=.62)f*=.78;
    f*=.91+.17*clamp(n(third.latePower,.5),0,1);
    f*=.93+.14*clamp(n(c.trueRun,.5),0,1);
    return clamp(f,.58,1.55)
  }
  var p1=normWeights(rows.map(function(x){return Math.max(.0001,n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,.0001))))})),
      p2=normWeights(rows.map(function(x){return Math.max(.0001,n(x.p2Probability))})),
      p3=normWeights(rows.map(function(x){return Math.max(.0001,n(x.p3Probability))})),tri=[],i,j,k;
  // Sequential conditional-order model:
  // P(1st=i) * P(2nd=j | i) * P(3rd=k | i,j).
  for(i=0;i<rows.length;i++){
    var w2=rows.map(function(x,idx){return idx===i?0:p2[idx]*pairFactor(rows[i],x)}),c2=normWeights(w2);
    for(j=0;j<rows.length;j++)if(i!==j){
      var w3=rows.map(function(x,idx){return (idx===i||idx===j)?0:p3[idx]*thirdFactor(rows[i],rows[j],x)}),c3=normWeights(w3);
      for(k=0;k<rows.length;k++)if(k!==i&&k!==j){var q=p1[i]*c2[j]*c3[k];if(q>0)tri.push({combo:[no(rows[i]),no(rows[j]),no(rows[k])],score:q})}
    }
  }
  tri.sort(function(a,b){return b.score-a.score});
  var exactMap={},quinMap={},trioMap={},wideMap={};
  tri.forEach(function(z){var a=z.combo[0],b=z.combo[1],c=z.combo[2],tk=[a,b,c].slice().sort(function(x,y){return x-y}).join('-');pushMap(exactMap,a+'>'+b,z.score,[a,b]);pushMap(quinMap,key2(a,b),z.score,[a,b].sort(function(x,y){return x-y}));pushMap(trioMap,tk,z.score,[a,b,c].sort(function(x,y){return x-y}));pushMap(wideMap,key2(a,b),z.score,[a,b].sort(function(x,y){return x-y}));pushMap(wideMap,key2(a,c),z.score,[a,c].sort(function(x,y){return x-y}));pushMap(wideMap,key2(b,c),z.score,[b,c].sort(function(x,y){return x-y}))});
  var exactaRank=rankMap(exactMap),wideRank=rankMap(wideMap),quinRank=rankMap(quinMap),trioRank=rankMap(trioMap),p1Rows=rows.map(function(x,i){return{x:x,p:p1[i]}}).sort(function(a,b){return b.p-a.p}),p2Rows=rows.map(function(x,i){return{x:x,p:p2[i]}}).sort(function(a,b){return b.p-a.p}),p3Rows=rows.map(function(x,i){return{x:x,p:p3[i]}}).sort(function(a,b){return b.p-a.p}),p1vals=p1.slice().sort(function(a,b){return b-a}),p1Top=p1vals[0]||0,p1Second=p1vals[1]||0,p1Margin=p1Top-p1Second,top2mass=p1Top+p1Second,top3mass=top2mass+(p1vals[2]||0),ent=entropy(p1),sel=strictSelectedRaceProfile(r,p),autoSelected=!!(sel&&sel.selected),normalGate=top3mass>=.60&&ent<=.94,canIssue=featured||normalGate,strong=autoSelected,items=[];
  // All ticket types below are marginals of the SAME sequential joint distribution.
  // 馬単=P(1,2), 馬連=sum both 1-2 orders, ワイド=sum all top-3 placements,
  // 3連複=sum all 6 orders, 3連単=one exact ordered path.
  if(canIssue){
    var ec=compactCombos(exactaRank,strong?2:1,strong?.68:.78,1);if(ec.length)items.push({level:strong?'本線':'通常',kind:'馬単',combos:ec,confidence:strong?'高':'中'});
    var qc=compactCombos(quinRank,2,strong?.70:.78,1);if(qc.length)items.push({level:strong?'本線':'通常',kind:'馬連',combos:qc,confidence:strong?'高':'中'});
    var wc=compactCombos(wideRank,2,strong?.74:.82,1);if(wc.length)items.push({level:strong?'本線':'通常',kind:'ワイド',combos:wc,confidence:strong?'高':'中'});
    var tc=compactCombos(trioRank,strong?3:2,strong?.60:.72,strong?2:1),rescue3=thirdRescueCandidateV312(r,rows,[]);if(rescue3)appendRescueRankedV312(tc,trioRank,no(rescue3),1,strong?.34:.40,false);if(tc.length)items.push({level:strong?'押さえ':'通常',kind:'3連複',combos:tc,confidence:strong?'高':'中'});
  }
  var triVals=tri.map(function(z){return z.score}),triTop=tri[0]?tri[0].score:0,triSecond=tri[1]?tri[1].score:1e-9,triRatio=triTop/Math.max(1e-9,triSecond),triTop6=tri.slice(0,6).reduce(function(a,z){return a+n(z.score)},0),orderEntropy=entropy(triVals),orderConfidence=clamp((1-orderEntropy)*.45+Math.min(1,triTop6/.16)*.35+Math.min(1,triRatio/1.35)*.20,0,1),triGate=strong&&triTop>=.022&&triRatio>=1.10&&triTop6>=.095&&orderConfidence>=.39;
  if(triGate){var triMax=orderConfidence>=.55?4:6,triCut=orderConfidence>=.55?.56:.46,t3=compactCombos(tri,triMax,triCut,2);if(rescue3)appendRescueRankedV312(t3,tri,no(rescue3),orderConfidence>=.55?1:2,.27,true);if(t3.length)items.push({level:'3連単チャレンジ',kind:'3連単',combos:t3,confidence:orderConfidence>=.55?'高':'中'})}
  items.forEach(function(z){z.points=(z.combos||[]).length;z.combo=betComboText(z.kind,z.combos)});items=items.filter(function(z){return z.points>0});
  var decision=strong?'強く買う':(canIssue?'通常買い':'見送り'),quality=canIssue?Math.round(clamp(45+top3mass*42+(1-ent)*18+(strong?10:0),50,96)):0,reason=strong?'厳選ゲート通過。v220は共通の条件付き着順分布から5券種を生成し、上位確率が離れた地点で買い目を自動打ち切りします。3連単は順序信頼ゲート通過時のみ最大6点です。':(featured?'メイン・重賞・高知ファイナル等の対象レースなので、役割順位から本線を出します。':(canIssue?'通常ゲート通過。役割順位の集中度から買い目を作成。':'通常ゲート未通過。'));
  return{raceId:String(r.id||''),engineVersion:'arvexq-bets-2026.10-v317-consensus-rebuild',decision:decision,featuredRace:featured,betQuality:quality,scenario:((p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)})[0]||{title:'平均',prob:0}).title,scenarioProb:n(((p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)})[0]||{}).prob),trifectaReviewed:true,trifectaDecision:triGate?'採用':'見送り',trifectaReason:triGate?'v220条件付き順序ゲート通過・点数圧縮。':'1着→2着→3着の条件付き順序集中度が基準未満。',winnerModel:(String((r&&r.circuit)||'')==='中央'?'central-v317-consensus-rebuild':'local-v317-consensus-rebuild')+'+walkforward+precision-order',p2Model:'v245-v213+seven-axis-live-role+conditional',p3Model:'v245-v213+sectional-live-role+conditional',selectionAudit:sel,roles:{p1:p1Rows.slice(0,4).map(function(z){return{no:no(z.x),p:z.p}}),p2:p2Rows.slice(0,5).map(function(z){return{no:no(z.x),p:z.p}}),p3:p3Rows.slice(0,6).map(function(z){return{no:no(z.x),p:z.p}})},audit:{field:rows.length,coverage:n(p.coverage),p1Top:p1Top,p1Margin:p1Margin,top2mass:top2mass,top3mass:top3mass,entropy:ent,exactaTop:exactaRank[0]?exactaRank[0].score:0,exactaRatio:(exactaRank[0]?n(exactaRank[0].score):0)/Math.max(1e-9,exactaRank[1]?n(exactaRank[1].score):1e-9),quinTop:quinRank[0]?quinRank[0].score:0,quinRatio:(quinRank[0]?n(quinRank[0].score):0)/Math.max(1e-9,quinRank[1]?n(quinRank[1].score):1e-9),wideTop:wideRank[0]?wideRank[0].score:0,wideRatio:(wideRank[0]?n(wideRank[0].score):0)/Math.max(1e-9,wideRank[1]?n(wideRank[1].score):1e-9),trioTop:trioRank[0]?trioRank[0].score:0,trioRatio:(trioRank[0]?n(trioRank[0].score):0)/Math.max(1e-9,trioRank[1]?n(trioRank[1].score):1e-9),triTop:triTop,triRatio:triRatio,triTop6:triTop6,orderEntropy:orderEntropy,orderConfidence:orderConfidence,selected:autoSelected,normalGate:normalGate,ticketDistribution:'sequential-joint-v300-winner-consensus'},items:items,reason:reason}
}


function arvexqRaceType(base,p){
  var a=base&&base.audit||{},field=Math.max(4,n(a.field,(p&&p.rows||[]).length)),
      p1=n(a.p1Top),margin=n(a.p1Margin),top2=n(a.top2mass),top3=n(a.top3mass),ent=clamp(n(a.entropy,.94),0,1),order=clamp(n(a.orderConfidence),0,1),code='standard',label='標準';
  if(p1>=Math.max(.28,1/field*2.45)&&margin>=Math.max(.045,1/field*.35)){code='dominant';label='1強'}
  else if(top2>=.54&&margin<=Math.max(.075,1/field*.55)){code='two-strong';label='2強'}
  else if(top3>=.68&&ent<=.90){code='clustered';label='上位集中'}
  else if(ent>=.945||top3<.50){code='chaos';label='混戦'}
  return{code:code,label:label,orderReadable:order>=.50,orderScore:Math.round(order*100),p1Top:p1,margin:margin,top2:top2,top3:top3,entropy:ent}
}

// v243: bet construction is a separate decision engine with an explicit axis-safety gate.
// The joint-order model may generate several ticket marginals internally, but the
// customer-facing plan uses one primary ticket type and, only in unusually strong
// cases, one complementary secondary type. This avoids buying the same opinion five ways.
function rebuildBetStrategyV242(base,r,p){
  if(!base)return base;
  var source=(base.items||[]).slice(),byKind={};
  source.forEach(function(z){if(z&&z.kind&&!byKind[z.kind])byKind[z.kind]=z});
  var a=base.audit||{},roles=base.roles||{},p1=(roles.p1||[]).slice().sort(function(x,y){return n(y.p)-n(x.p)}),
      p1Top=p1.length?n(p1[0].p):n(a.p1Top),p1Second=p1.length>1?n(p1[1].p):Math.max(0,p1Top-n(a.p1Margin)),
      p1Margin=a.p1Margin!=null?n(a.p1Margin):Math.max(0,p1Top-p1Second),
      top2=a.top2mass!=null?n(a.top2mass):((p1[0]?n(p1[0].p):0)+(p1[1]?n(p1[1].p):0)),
      top3=a.top3mass!=null?n(a.top3mass):(top2+(p1[2]?n(p1[2].p):0)),
      order=clamp(n(a.orderConfidence),0,1),quality=n(base.betQuality),selected=!!(base.selectionAudit&&base.selectionAudit.selected),
      field=Math.max(4,n(a.field,(p&&p.rows||[]).length)),entropyVal=clamp(n(a.entropy,.92),0,1),
      liveRows=(p&&p.rows||[]).slice(),axisRow=liveRows.filter(function(z){return z&&z.predMark==='◎'})[0]||null,
      axisNo=axisRow&&axisRow.horse?n(axisRow.horse.horseNumber):0,axisConfidence=clamp(n(axisRow&&axisRow.axisConfidence),0,1),
      coreP1No=p1.length?n(p1[0].no):0,axisAgreement=!!(axisNo&&coreP1No&&axisNo===coreP1No),axisStable=!!(axisRow&&axisRow.winnerDecisionStable),centralRace=String((r&&r.circuit)||'')==='中央',axisLocked=axisStable&&axisAgreement&&axisConfidence>=(centralRace?.68:.62),
      raceType=arvexqRaceType(base,p),readiness=dataReadinessProfile(r,p),qualityGate=selected||(!!base.featuredRace&&axisLocked&&top3>=(centralRace?.58:.60));
  if(readiness.prediction<(centralRace?.68:.60)||!qualityGate){base.items=[];base.decision='見送り';base.betQuality=0;base.betStrategy=centralRace?'v313-central':'v313-local';base.dataReadiness=readiness;base.reason='予想データの充足度が不足しているため買い目を固定しません。';base.trifectaDecision='見送り';base.trifectaReason='データ充足待ち。';return base}
  function ratioScore(v,lo,hi){return clamp((n(v)-lo)/Math.max(.0001,hi-lo),0,1)}
  function concentration(v,scale){return clamp(n(v)/Math.max(.0001,scale),0,1)}
  var winClarity=clamp(.58*ratioScore(p1Margin,Math.max(.006,1/field*.05),Math.max(.040,1/field*.34))+.42*ratioScore(p1Top,1/field*1.05,Math.min(.48,1/field*2.75)),0,1),
      pairStrength=clamp(.55*concentration(n(a.quinTop),.10)+.25*ratioScore(n(a.quinRatio),1.02,1.55)+.20*clamp(top2/.62,0,1),0,1),
      trioStrength=clamp(.50*concentration(n(a.trioTop),.075)+.25*ratioScore(n(a.trioRatio),1.02,1.55)+.25*clamp(top3/.72,0,1),0,1),
      exactStrength=clamp(.48*concentration(n(a.exactaTop),.075)+.27*ratioScore(n(a.exactaRatio),1.02,1.55)+.25*winClarity,0,1),
      wideStrength=clamp(.45*concentration(n(a.wideTop),.22)+.25*ratioScore(n(a.wideRatio),1.01,1.40)+.30*clamp(top3/.74,0,1),0,1),
      triStrength=clamp(.30*winClarity+.34*order+.20*ratioScore(n(a.triRatio),1.03,1.48)+.16*concentration(n(a.triTop6),.15),0,1),
      uncertainty=clamp(.60*entropyVal+.40*(1-winClarity),0,1);
  var candidates=[];
  function add(kind,score,why){if(byKind[kind])candidates.push({kind:kind,score:clamp(score,0,1),why:why,item:byKind[kind]})}
  // Ordered tickets require an identifiable winner; unordered tickets are preferred when the top pair/trio is clear but order is not.
  add('3連単',triStrength,'1着固定と2・3着順序まで読める');
  add('馬単',clamp(.42*winClarity+.33*exactStrength+.15*order+.10*(1-uncertainty),0,1),'1着軸が明確で2着まで絞れる');
  add('馬連',clamp(.48*pairStrength+.27*top2/Math.max(.52,top2)+.25*(1-order),0,1),'上位2頭は強いが順番は固定しすぎない');
  add('3連複',clamp(.50*trioStrength+.25*clamp(top3/.70,0,1)+.25*uncertainty,0,1),'上位3頭の組み合わせが強く順序依存が小さい');
  add('ワイド',clamp(.48*wideStrength+.30*clamp(top3/.72,0,1)+.22*uncertainty,0,1),'上位候補は安定するが着順の断定は弱い');
  // v300 race-type layer chooses the ticket family before point-count trimming.
  // It never changes horse probabilities; it only avoids using an ordered ticket
  // in a race whose probability shape says the order itself is unclear.
  candidates.forEach(function(c){
    if(raceType.code==='dominant'){if(c.kind==='3連単'||c.kind==='馬単')c.score*=1.08;else if(c.kind==='ワイド')c.score*=.92}
    else if(raceType.code==='two-strong'){if(c.kind==='馬連')c.score*=1.10;else if(c.kind==='馬単')c.score*=raceType.orderReadable?1.03:.92;else if(c.kind==='3連複')c.score*=1.03}
    else if(raceType.code==='clustered'){if(c.kind==='3連複')c.score*=1.10;else if(c.kind==='3連単')c.score*=raceType.orderReadable?1.04:.88}
    else if(raceType.code==='chaos'){if(c.kind==='3連単'||c.kind==='馬単')c.score*=.64;else if(c.kind==='ワイド')c.score*=1.10;else if(c.kind==='3連複')c.score*=1.06}
    c.score=clamp(c.score,0,1)
  });
  candidates.sort(function(x,y){return y.score-x.score});
  if(selected){
    function hitPriority(c){
      if(c.kind==='ワイド')return .42+.58*wideStrength;
      if(c.kind==='馬連')return .34+.66*pairStrength;
      if(c.kind==='3連複')return .30+.70*trioStrength;
      if(c.kind==='馬単')return .18+.52*exactStrength+.30*winClarity;
      if(c.kind==='3連単')return .08+.46*triStrength+.46*winClarity;
      return n(c.score)
    }
    candidates.sort(function(x,y){return hitPriority(y)-hitPriority(x)||y.score-x.score})
  }

  // 3連単/馬単 are allowed only when the displayed ◎ agrees with core P1,
  // the axis confidence is high, and an actual generated combo starts from that ◎.
  function hasAxisFirst(item){return !!(axisNo&&item&&(item.combos||[]).some(function(c){return c&&n(c[0])===axisNo}))}
  candidates=candidates.filter(function(c){
    if(c.kind==='3連単')return axisLocked&&hasAxisFirst(c.item)&&winClarity>=(centralRace?.60:.50)&&order>=(centralRace?.56:.46)&&n(a.triRatio)>=(centralRace?1.14:1.10)&&n(a.triTop6)>=(centralRace?.100:.090);
    if(c.kind==='馬単')return axisLocked&&hasAxisFirst(c.item)&&winClarity>=(centralRace?.48:.38)&&exactStrength>=(centralRace?.46:.42);
    if(c.kind==='馬連')return pairStrength>=.38;
    if(c.kind==='3連複')return trioStrength>=.38;
    if(c.kind==='ワイド')return wideStrength>=.38;
    return false
  });
  var primary=candidates[0]||null,threshold=(selected ? (centralRace?.58:.54) : (base.featuredRace ? (centralRace?.64:.60) : (centralRace?.68:.65)))+(raceType.code==='chaos'?.04:0);
  if(!primary||primary.score<threshold){
    base.items=[];base.decision='見送り';base.betQuality=Math.round(clamp(quality*.72,0,70));
    base.betStrategy=centralRace?'v313-central':'v313-local';base.raceType=raceType;base.primaryKind='';base.secondaryKind='';base.axisNo=axisNo;base.axisConfidence=Math.round(axisConfidence*100);base.axisAgreement=axisAgreement;base.axisLocked=axisLocked;
    base.reason='券種選択ゲート未通過。予想上位がいても、買い方として優位な形が作れないため見送りします。';
    base.trifectaDecision='見送り';base.trifectaReason='順序信頼または1着固定力が不足。';
    return base
  }
  function cloneLimited(src,max,level,confidence){
    var z=Object.assign({},src),pool=(src.combos||[]).slice();
    if((src.kind==='馬単'||src.kind==='3連単')&&axisNo)pool=pool.filter(function(c){return c&&n(c[0])===axisNo});
    var cs=pool.slice(0,max);z.combos=cs;z.points=cs.length;z.combo=betComboText(z.kind,cs);z.level=level;z.confidence=confidence;return z
  }
  var maxByKind={'3連単':4,'馬単':2,'馬連':2,'3連複':3,'ワイド':2},
      mainLevel=primary.score>=.72?'本線':'通常',mainConf=primary.score>=.72?'高':'中',
      items=[cloneLimited(primary.item,maxByKind[primary.kind]||2,mainLevel,mainConf)],secondary=null;
  // A secondary ticket is exceptional, not automatic. It must be complementary and substantially strong.
  if((selected||quality>=88)&&primary.score>=.72){
    var allowed={
      '3連単':['馬単'],
      '馬単':['3連複'],
      '馬連':['3連複'],
      '3連複':['ワイド'],
      'ワイド':[]
    }[primary.kind]||[];
    for(var i=1;i<candidates.length;i++){
      var c=candidates[i];if(allowed.indexOf(c.kind)<0||c.score<.64||c.score<primary.score-.14)continue;secondary=c;break
    }
    if(secondary)items.push(cloneLimited(secondary.item,secondary.kind==='3連複'?2:1,'押さえ',secondary.score>=.72?'高':'中'))
  }
  base.items=items.filter(function(z){return z.points>0});
  base.decision=primary.score>=.74?'強く買う':'通常買い';
  base.betQuality=Math.round(clamp(52+primary.score*35+(secondary?4:0)+(selected?5:0),55,96));
  base.betStrategy='v309-precision';base.raceType=raceType;base.primaryKind=primary.kind;base.secondaryKind=secondary?secondary.kind:'';base.axisNo=axisNo;base.axisConfidence=Math.round(axisConfidence*100);base.axisAgreement=axisAgreement;base.axisLocked=axisLocked;
  base.ticketScores={};candidates.forEach(function(c){base.ticketScores[c.kind]=Math.round(c.score*100)});
  base.reason='レース型 '+raceType.label+'。主軸は'+primary.kind+'。'+primary.why+'ため、この券種に集中'+(secondary?'し、'+secondary.kind+'だけを補助に使用':'')+'。'+(axisLocked?'◎専用モデルの軸固定ゲート通過。':'◎専用モデルの安定度が不足しているため、馬単・3連単の1着固定は使いません。');
  base.trifectaDecision=primary.kind==='3連単'?'採用':'見送り';
  base.trifectaReason=primary.kind==='3連単'?'1着固定・条件付き2着/3着・順序信頼ゲート通過。':'3連単より適した券種を優先、または順序信頼不足。';
  base.orderScore=Math.round(order*100);base.dataReadiness=readiness;
  return base
}

function buildAiBetPlan(r,p){
  var started=r&&r.date===today()&&mins(r.startTime)<9999&&nowMins()>=mins(r.startTime),terminal=isFinal(r)||started,
      stored=loadStoredAiBet(r&&r.id,terminal);
  if(terminal&&stored)return stored;
  if(terminal&&!stored)return null;
  var rows=(p&&p.rows||[]).slice().filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)});
  if(rows.length<4)return null;
  var featured=isFeaturedBetRace(r,p),v213Ready=String(r&&r.circuit||'')==='地方'&&rows.every(function(x){var e=x&&x.horse&&x.horse.integratedEvaluation||{};return isFinite(Number(e.v218P1Utility!=null?e.v218P1Utility:(e.v217P1Utility!=null?e.v217P1Utility:e.v213P1Utility)))&&isFinite(Number(e.v213P2Utility))&&isFinite(Number(e.v213P3Utility))});
  if(v213Ready){var vp=rebuildBetStrategyV242(buildV213AiBetPlan(r,p,rows,featured),r,p);vp=forceMandatoryTrifecta(vp,r,p);saveStoredAiBet(r,vp);return vp}
  var field=rows.length,cov=n(p&&p.coverage,0),scenarios=(p.scenarios||[]).slice().sort(function(a,b){return n(b.prob)-n(a.prob)}),mainSc=scenarios[0]||{prob:0,title:'平均'},useV207=v207UsesWinnerModel(r);
  function no(x){return x&&x.horse?n(x.horse.horseNumber):0}
  function unitSaved(x,key,fallback){var e=x&&x.horse&&x.horse.integratedEvaluation||{},v=e[key];return v!=null?v207Unit(v,.5):clamp(n(fallback),0,1)}
  function softFrom(vals,temp){return edgeSoftmax(vals,temp||.095)}
  function normalize(vals){var s=vals.reduce(function(a,b){return a+Math.max(0,n(b))},0)||1;return vals.map(function(v){return Math.max(0,n(v))/s})}
  function entropy(ps){var z=0,i,q,den=Math.log(Math.max(2,ps.length));for(i=0;i<ps.length;i++){q=Math.max(1e-12,n(ps[i]));z-=q*Math.log(q)}return den>0?z/den:0}
  /* v212 ticket roles are read from the server-side pre-race role models so the
     production combination logic matches the historical audit. */
  var activeP1=normalize(rows.map(function(x){return Math.max(.0001,n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,unitSaved(x,'p1Score',.5)))))})),
      ticketP2=normalize(rows.map(function(x){return unitSaved(x,'p2Score',x.p2Probability)})),
      ticketP3=softFrom(rows.map(function(x){return unitSaved(x,'p3Score',x.p3Probability)}),.115),
      legacyP1=softFrom(rows.map(function(x){return unitSaved(x,'legacyP1Score',x.legacyP1Strength)}),.095);
  rows.forEach(function(x,i){x.ticketP1Probability=activeP1[i]||0;x.ticketP2Probability=ticketP2[i]||0;x.ticketP3Probability=ticketP3[i]||0;x.ticketLegacyP1Probability=legacyP1[i]||x.ticketP1Probability});
  function winActive(x){return clamp(n(x.ticketP1Probability),0,1)}
  function role(x,k){return clamp(n(x&&x['ticketP'+k+'Probability']),0,1)}
  function key2(a,b){a=n(a);b=n(b);return a<b?a+'-'+b:b+'-'+a}
  function pushMap(map,key,score,combo){if(!map[key])map[key]={combo:combo,score:0};map[key].score+=score}
  function rankMap(map){return Object.keys(map).map(function(k){return map[k]}).sort(function(a,b){return b.score-a.score})}
  function fallbackSecondFactor(first,second){
    var sc=((p.scenarios||[]).slice().sort(function(x,y){return n(y.prob)-n(x.prob)})[0]||{}),title=String(sc.title||''),f=1;
    if(/前|残|逃|スロー/.test(title))f*=.82+.34*clamp(.55*n(second.posCons,.5)+.45*n(second.frontStay,.5),0,1);
    else if(/差|崩|ハイ|消耗/.test(title))f*=.82+.34*clamp(.52*n(second.posCons,.5)+.48*n(second.comeFromBehind,.5),0,1);
    else f*=.88+.24*clamp(n(second.posCons,.5),0,1);
    if(n(first.frontStay,.5)>=.62&&n(second.frontStay,.5)>=.62)f*=.88;
    if(n(first.frontCost)>=.16&&n(second.goProb)>=.58)f*=.91;
    return clamp(f,.64,1.44)
  }
  function fallbackThirdFactor(first,second,third){
    var sc=((p.scenarios||[]).slice().sort(function(x,y){return n(y.prob)-n(x.prob)})[0]||{}),title=String(sc.title||''),f=1;
    if(/前|残|逃|スロー/.test(title))f*=.82+.34*clamp(.52*n(third.posCons,.5)+.48*n(third.latePower,.5),0,1);
    else if(/差|崩|ハイ|消耗/.test(title))f*=.80+.38*clamp(.60*n(third.latePower,.5)+.40*n(third.comeFromBehind,.5),0,1);
    else f*=.86+.28*clamp(.55*n(third.latePower,.5)+.45*n(third.posCons,.5),0,1);
    if(n(first.frontStay,.5)>=.58&&n(second.frontStay,.5)>=.58)f*=.88+.24*clamp(n(third.latePower,.5),0,1);
    if(n(first.frontStay,.5)>=.62&&n(second.frontStay,.5)>=.62&&n(third.frontStay,.5)>=.62)f*=.79;
    return clamp(f,.60,1.52)
  }
  // Central and fallback races now use the SAME sequential joint distribution as local races.
  var tri=[],i,j,k;
  for(i=0;i<rows.length;i++){
    var w2=rows.map(function(x,idx){return idx===i?0:role(x,2)*fallbackSecondFactor(rows[i],x)}),c2=normalize(w2);
    for(j=0;j<rows.length;j++)if(i!==j){
      var w3=rows.map(function(x,idx){return (idx===i||idx===j)?0:role(x,3)*fallbackThirdFactor(rows[i],rows[j],x)}),c3=normalize(w3);
      for(k=0;k<rows.length;k++)if(k!==i&&k!==j){var q=winActive(rows[i])*c2[j]*c3[k];if(q>0)tri.push({combo:[no(rows[i]),no(rows[j]),no(rows[k])],score:q})}
    }
  }
  tri.sort(function(a,b){return b.score-a.score});
  var exactaMap={},quinellaMap={},trioMap={},wideMap={};
  tri.forEach(function(z){var t=z.combo,a=t[0],b=t[1],c=t[2],tk=t.slice().sort(function(x,y){return x-y}).join('-');pushMap(exactaMap,a+'>'+b,z.score,[a,b]);pushMap(quinellaMap,key2(a,b),z.score,[a,b].sort(function(x,y){return x-y}));pushMap(trioMap,tk,z.score,t.slice().sort(function(x,y){return x-y}));pushMap(wideMap,key2(a,b),z.score,[a,b].sort(function(x,y){return x-y}));pushMap(wideMap,key2(a,c),z.score,[a,c].sort(function(x,y){return x-y}));pushMap(wideMap,key2(b,c),z.score,[b,c].sort(function(x,y){return x-y}))});
  var exactaRank=rankMap(exactaMap),wideRank=rankMap(wideMap),quinellaRank=rankMap(quinellaMap),trioRank=rankMap(trioMap),p1Rows=rows.slice().sort(function(a,b){return winActive(b)-winActive(a)}),p2Rows=rows.slice().sort(function(a,b){return role(b,2)-role(a,2)}),p3Rows=rows.slice().sort(function(a,b){return role(b,3)-role(a,3)}),legacyRows=rows.slice().sort(function(a,b){return n(b.ticketLegacyP1Probability)-n(a.ticketLegacyP1Probability)});
  var p1vals=rows.map(winActive).sort(function(a,b){return b-a}),p1Top=p1vals[0]||0,p1Second=p1vals[1]||0,p1Margin=p1Top-p1Second,p1Entropy=entropy(rows.map(winActive)),top2mass=(p1vals[0]||0)+(p1vals[1]||0),top3mass=top2mass+(p1vals[2]||0),
      qTop=quinellaRank[0]?quinellaRank[0].score:0,qSecond=quinellaRank[1]?quinellaRank[1].score:1e-9,qRatio=qTop/Math.max(1e-9,qSecond),
      trioTop=trioRank[0]?trioRank[0].score:0,trioSecond=trioRank[1]?trioRank[1].score:1e-9,trioRatio=trioTop/Math.max(1e-9,trioSecond),
      wideTop=wideRank[0]?wideRank[0].score:0,wideSecond=wideRank[1]?wideRank[1].score:1e-9,wideRatio=wideTop/Math.max(1e-9,wideSecond),
      exactaTop=exactaRank[0]?exactaRank[0].score:0,exactaSecond=exactaRank[1]?exactaRank[1].score:1e-9,exactaRatio=exactaTop/Math.max(1e-9,exactaSecond),
      triTop=tri[0]?tri[0].score:0,triSecond=tri[1]?tri[1].score:1e-9,triRatio=triTop/Math.max(1e-9,triSecond),triTop6=tri.slice(0,6).reduce(function(a,z){return a+n(z.score)},0),triEntropy=entropy(tri.map(function(z){return z.score})),
      orderConfidence=clamp((1-triEntropy)*.45+Math.min(1,triTop6/.16)*.35+Math.min(1,triRatio/1.35)*.20,0,1),
      /* Corrected role audit: this gate was trained/validated using reconstructed P2/P3 rather than missing-role=.5. */
      normalGate=(qTop<=.06060?p1Margin<=.02422:(trioTop<=.04057?top2mass<=.64574:true)),
      strongGate=normalGate&&qTop>.06060&&trioTop>.04057&&top3mass>.61,
      canIssue=useV207?(normalGate||featured):featured,
      decision=strongGate?'強く買う':(canIssue?'通常買い':'見送り'),items=[];
  function topCombos(list,max){var out=[],i;for(i=0;i<list.length&&out.length<max;i++){if(list[i]&&list[i].combo&&list[i].combo.every(function(v){return n(v)>0}))out.push(list[i].combo.slice())}return out}
  function compactCombos(list,max,minRatio,minCount){var out=[],top=list&&list[0]?n(list[0].score):0,i;minCount=minCount||1;for(i=0;i<(list||[]).length&&out.length<max;i++){var z=list[i];if(!z||!z.combo||!z.combo.every(function(v){return n(v)>0}))continue;if(out.length>=minCount&&top>0&&n(z.score)<top*minRatio)break;out.push(z.combo.slice())}return out}
  if(canIssue){
    var ec=compactCombos(exactaRank,strongGate?2:1,strongGate?.68:.78,1);if(ec.length)items.push({level:strongGate?'本線':'通常',kind:'馬単',combos:ec,confidence:strongGate?'高':'中',modelScore:0});
    var qc=compactCombos(quinellaRank,2,strongGate?.70:.78,1);if(qc.length)items.push({level:strongGate?'本線':'通常',kind:'馬連',combos:qc,confidence:strongGate?'高':'中',modelScore:0});
    var wc=compactCombos(wideRank,2,strongGate?.74:.82,1);if(wc.length)items.push({level:strongGate?'本線':'通常',kind:'ワイド',combos:wc,confidence:strongGate?'高':'中',modelScore:0});
    var tc=compactCombos(trioRank,strongGate?3:2,strongGate?.60:.72,strongGate?2:1),rescue3=thirdRescueCandidateV312(r,rows,[]),recallGuard=rows.filter(function(z){return ['△','注+','注'].indexOf(String(z.predMark||''))>=0}).sort(function(a,b){return n(b.p3RecallScore)-n(a.p3RecallScore)||n(b.recallDiversityScore)-n(a.recallDiversityScore)})[0]||null;if(rescue3)appendRescueRankedV312(tc,trioRank,no(rescue3),1,strongGate?.34:.40,false);if(recallGuard&&(!rescue3||no(recallGuard)!==no(rescue3)))appendRescueRankedV312(tc,trioRank,no(recallGuard),1,strongGate?.31:.36,false);if(tc.length)items.push({level:strongGate?'押さえ':'通常',kind:'3連複',combos:tc,confidence:strongGate?'高':'中',modelScore:0});
  }
  var triGate=canIssue&&strongGate&&triTop>=.018&&triRatio>=1.06&&triTop6>=.080&&orderConfidence>=.34;
  if(triGate){var triMax=orderConfidence>=.52?4:6,triCut=orderConfidence>=.52?.56:.46,t3=compactCombos(tri,triMax,triCut,2);if(rescue3)appendRescueRankedV312(t3,tri,no(rescue3),orderConfidence>=.52?1:2,.27,true);if(recallGuard&&(!rescue3||no(recallGuard)!==no(rescue3)))appendRescueRankedV312(t3,tri,no(recallGuard),1,.24,true);if(t3.length)items.push({level:'3連単チャレンジ',kind:'3連単',combos:t3,confidence:orderConfidence>=.52?'高':'中',modelScore:0});}
  items=items.filter(function(z){z.points=(z.combos||[]).length;z.combo=betComboText(z.kind,z.combos);return z.points>0});
  if(!items.length&&canIssue){var fallback=topCombos(wideRank,3);if(fallback.length)items.push({level:'通常',kind:'ワイド',combos:fallback,points:fallback.length,combo:betComboText('ワイド',fallback),confidence:'中',modelScore:0})}
  var sel=null;try{sel=strictSelectedRaceProfile(r,p)}catch(e){}
  var betQuality=canIssue?Math.round(clamp(48+top3mass*30+(1-p1Entropy)*12+(featured?7:0)+(strongGate?8:0),50,92)):0,
      reason=featured?'厳選ゲート通過、または必須予想の重賞/高知ファイナル対象。必須予想は厳選扱いしません。':(canIssue?'通常レースの買い目ゲート通過。5券種は同じ条件付き着順分布から派生。':'通常レースの買い目ゲート未通過。'),
      plan={raceId:String(r.id||''),engineVersion:'arvexq-bets-2026.10-v317-consensus-rebuild',decision:decision,featuredRace:featured,betQuality:betQuality,scenario:mainSc.title||'平均',scenarioProb:n(mainSc.prob),trifectaReviewed:true,trifectaDecision:triGate?'採用':'見送り',trifectaReason:triGate?'v220条件付き順序ゲート通過・点数圧縮。':'条件付き順序集中度が3連単基準未満。',winnerModel:(String((r&&r.circuit)||'')==='中央'?'central-v317-consensus-rebuild':'local-v317-consensus-rebuild')+'+walkforward+precision-order',p2Model:useV207?'v212-role+v220-conditional':'legacy-central+v220-conditional',p3Model:'role-marginal+v220-conditional',selectionAudit:sel,
        roles:{p1:p1Rows.slice(0,4).map(function(z){return{no:no(z),p:winActive(z)}}),p2:p2Rows.slice(0,5).map(function(z){return{no:no(z),p:role(z,2)}}),p3:p3Rows.slice(0,6).map(function(z){return{no:no(z),p:role(z,3)}}),legacyP1:legacyRows.slice(0,4).map(function(z){return{no:no(z),p:n(z.ticketLegacyP1Probability)}})},
        audit:{field:field,coverage:cov,p1Top:p1Top,p1Margin:p1Margin,top2mass:top2mass,top3mass:top3mass,entropy:p1Entropy,exactaTop:exactaTop,exactaRatio:exactaRatio,wideTop:wideTop,wideRatio:wideRatio,quinTop:qTop,quinRatio:qRatio,trioTop:trioTop,trioRatio:trioRatio,triTop:triTop,triRatio:triRatio,triTop6:triTop6,orderConfidence:orderConfidence,normalGate:normalGate,strongGate:strongGate,featured:featured,ticketDistribution:'sequential-joint-v300-winner-consensus'},items:items,reason:reason};
  plan=rebuildBetStrategyV242(plan,r,p);plan=forceMandatoryTrifecta(plan,r,p);saveStoredAiBet(r,plan);return plan
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
  if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り'&&!mandatoryTrifectaRace(r))lines.push('3連単｜検討済み｜順序信頼不足で見送り｜'+String(plan.orderScore||0)+'/100');
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
function aiBetRecommendation(r,p){
  var plan=buildAiBetPlan(r,p);
  if(!plan)return '<div class="ai-bet-box"><div class="ai-bet-title">AI買い目</div><div class="muted">発走前の予想データが揃ってから表示します。発走後に買い目を作り直すことはしません。</div></div>';
  var vote=officialRaceLinks(r).vote,rows=(plan.items||[]).map(function(z){return '<div class="ai-bet-row level-'+(z.level==='本線'?'main':z.level==='押さえ'?'cover':z.level==='強気'?'attack':'trifecta')+'"><span class="ai-bet-level">'+esc(z.level)+'</span><b>'+esc(z.kind)+'</b><strong>'+esc(z.combo)+'</strong><em>'+esc(z.points)+'点'+(z.confidence?' / '+esc(z.confidence):'')+'</em></div>'}).join('');
  if(plan.decision==='見送り')rows='<div class="ai-bet-row level-cover"><span class="ai-bet-level">見送り</span><b>全券種</b><strong>無理に買わない</strong><em>'+esc(plan.betQuality||0)+'/100</em></div>';
  if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')rows+='<div class="ai-bet-row level-trifecta"><span class="ai-bet-level">3連単</span><b>検討済み</b><strong>順序信頼不足で見送り</strong><em>'+esc(plan.orderScore||0)+'/100</em></div>';
  return '<div class="ai-bet-box"><div class="ai-bet-head ai-bet-head-v224"><div class="ai-bet-title">AI買い目</div><div class="ai-bet-meta"><span><b>'+esc(plan.scenario)+'</b> '+Math.round(n(plan.scenarioProb)*100)+'%</span><span>信頼 <b>'+esc(plan.betQuality||0)+'</b>/100</span><span>発走前固定</span></div><span class="ai-bet-brand">ARVEXQ</span></div><div class="ai-bet-list">'+rows+'</div><div class="bet-mark-guide"><b>印の見方</b><div class="bet-mark-grid"><span><i>◎</i>1着本命</span><span><i>○</i>1着対抗・2着本線</span><span><i>▲</i>1〜3着の有力馬</span><span><i>☆+</i>強穴・1着まで</span><span><i>☆</i>基本3着の能力穴</span><span><i>△</i>押さえ・3着候補</span><span><i>注+</i>条件ハマりで2着以上</span><span><i>注</i>特殊条件・展開ハマり待ち</span></div></div><p>'+esc(plan.reason||'')+'</p><small class="ai-bet-note">現行：中央/地方を別エンジンで評価し、能力・相手レベル・近況・展開/ラップ・条件適性・騎手/厩舎/状態・血統・全頭相対比較を統合。当日の同場傾向は弱い補正に限定し、1〜3着の全頭包含を最優先KPIに維持します。</small></div>'
}
function aiMarksPanel(r,p){
  var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.predRank)-n(b.predRank)});
  return '<section id="section-aimarks" class="card"><h2>AI印予想</h2><p class="muted">現行モデルは「1〜3着を全頭印内へ」を最優先。中央/地方を別モデルで評価し、当日の同場傾向は後半の印へ弱く補正。◎は1着、○は2着役、☆・△は3着役を別々に評価し、5〜7頭へ統合します。買い目の絞り込みは印抽出とは別ゲートです。</p><div class="ai-mark-list">'+rows.map(function(x){var h=x.horse,mark=x.predMark||'—',bw=horseBodyWeightText(h)||(isFinal(r)?'結果確認中':'取得中'),bomb=n(x.bombScore),reason=(x.attentionReason||(x.upsetReasons||[]).slice(0,2).join('・')),wp=(n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.winProbability)))*100).toFixed(1),mp=(n(x.marketProbability)*100).toFixed(1);return '<button class="ai-mark-row" data-horse-open="'+esc(h.horseNumber)+'"><span class="ai-mark-symbol">'+esc(mark)+'</span>'+badge(h)+'<span class="ai-mark-name"><b>'+esc(h.name)+'</b><small>1着 '+esc(wp)+'%　P2 '+(n(x.p2Probability)*100).toFixed(1)+'%　P3 '+(n(x.p3Probability)*100).toFixed(1)+'%</small><small>市場 '+esc(mp)+'%　EDGE '+esc(x.edgeScore||50)+'</small><small>'+esc(x.overallGrade||'C')+' '+esc(overallScoreText(x))+'　馬体重 '+esc(bw)+'</small>'+(bomb>=55?'<small class="upset-line">BOMB '+esc(bomb)+'/100'+(reason?'　'+esc(reason):'')+'</small>':'')+'</span><span class="ai-mark-rank">勝率'+esc(x.winnerDecisionRank||x.winnerConsensusRank||x.winRank||'—')+'位</span></button>'}).join('')+'</div></section>'
}
function betPanel(r,p){return '<section id="section-bets" class="card bet-card-clean">'+aiBetRecommendation(r,p)+'</section>'}
function diagnosisPanel(r,p){
  var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.horse&&a.horse.horseNumber,999)-n(b.horse&&b.horse.horseNumber,999)});
  var details='<div class="diagnosis-merged-list">'+rows.map(function(x,i){
    var h=x.horse,e=x.evaluation||{},confidence=esc(e.confidence||'低'),rank=n(x.overallRank,i+1),bw=horseBodyWeightText(h),refbw=!bw?referenceBodyWeight(h):0,bwLabel=bw?bw:(refbw?('前走 '+refbw+'kg'):(isFinal(r)?'結果確認中':'計量待ち'));
    var reason=(x.overallReasons||[]).join(' / ')+(n(x.bombScore)>=65?' / BOMB '+n(x.bombScore)+' EDGE '+n(x.edgeScore)+' '+(x.upsetReasons||[]).slice(0,2).join('・'):'')+((x.predMark==='注'||x.predMark==='注+')&&x.attentionReason?' / 注目理由 '+x.attentionReason:'');
    return '<article class="horse-card diagnosis-merged-row">'
      +'<div class="diagnosis-merged-head">'
        +'<span class="diag-check-cell"><span class="rc-horse-check '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+'</span></span>'
        +'<button class="diagnosis-horse-main" data-detail-horse="'+esc(h.horseNumber)+'">'+badge(h)+'<span class="diagnosis-horse-name"><b>'+esc(h.name)+'</b><small>総合'+rank+'位　馬体重 '+esc(bwLabel)+'</small></span></button>'
        +'<span class="diagnosis-eval"><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'C')+'</strong><b>'+esc(overallScoreText(x))+'</b><i class="diagnosis-ai-mark" data-ai-mark="'+esc(x.predMark||'')+'">'+esc(x.predMark||'—')+'</i></span>'
      +'</div>'
      +'<div class="diag-confidence">データ信頼度 <strong>'+confidence+'</strong>　勝率 '+(n(x.winProbability)*100).toFixed(1)+'% / 市場 '+(n(x.marketProbability)*100).toFixed(1)+'%</div>'
      +'<p class="diag-explain">'+esc(reason||'総合バランス型')+'</p>'
    +'</article>'
  }).join('')+'</div>';
  return '<section id="section-diagnosis" class="card"><h2>全頭診断</h2><p class="muted diagnosis-tap-note">馬名をタップすると、その馬の詳細へ移動します。</p>'+details+'</section>'
}
function historyPanel(r){return '<section id="section-history" class="card"><h2>過去走（直近5走）</h2>'+(r.horses||[]).map(function(h){var runs=(h.allPastRuns||h.recentRaces||[]).slice(0,5),count=runs.length,status=h.debutNoHistory?'新馬・既走なし':(count>=5?'5/5走取得済':count+'/5走・履歴補完中');return '<article class="horse-card"><button data-horse-open="'+esc(h.horseNumber)+'">'+esc(h.horseNumber)+' '+esc(h.name)+'</button><small class="muted" style="margin-left:8px">'+esc(status)+'</small>'+ (runs.length?runs.map(function(z){return '<div class="recent">'+esc(z.date||'—')+' '+esc(z.track||'—')+' '+esc(z.title||'')+' '+esc(z.distance||'—')+'m　'+esc(z.finish||z.finishStatus||'—')+'着　通過 '+esc((z.cornerPositions||[]).join('-')||'—')+'</div>'}).join(''): '<p>'+(h.debutNoHistory?'新馬：既走データなし':'履歴補完中。取得できた実走だけを表示します。')+'</p>')+'</article>'}).join('')+'</section>'}
function pacePanel(r,p){return '<section id="section-pace" class="card pace-panel-direct">'+paceBoard(r,p)+'</section>'}
function detailPanel(r,p){
  var rows=sortedHorseRows(p.rows),field=rows.length;
  if(!field)return '<section class="card"><h2>詳細</h2><div class="muted">詳細データを取得中です。</div></section>';
  var no=n(state.detailHorseNo,0),idx=rows.findIndex(function(z){return n(z.horse.horseNumber)===no});
  if(idx<0){idx=0;state.detailHorseNo=n(rows[0].horse.horseNumber)}
  var x=rows[idx],h=x.horse,e=h.integratedEvaluation||{},a=e.v218Audit||e.v217Audit||x.v218Audit||x.v217Audit||{},
      recent=(h.recentRaces||h.allPastRuns||[]).slice(0,5),bodyTxt=horseBodyWeightText(h)||((referenceBodyWeight(h)>0)?('前走 '+referenceBodyWeight(h)+'kg'):'計量待ち'),
      styleTxt=x.expected||x.pastStyle||'不明',score=Math.round(clamp(n(a.sevenAxisScore,x.v239Composite!=null?x.v239Composite:n(x.overallRaw,.5)),0,1)*100),
      grade=score>=84?'S':score>=74?'A':score>=62?'B':'C';
  var recentHtml=recent.length?recent.map(function(rr){
    var rid=rr.raceId||((r.circuit==='地方'&&rr.date&&rr.track&&n(rr.raceNumber))?('nar-'+rr.date+'-'+rr.track+'-'+String(n(rr.raceNumber)).padStart(2,'0')):'');
    return '<div class="recent detail-recent-v239"><div class="recent-head"><b>'+esc(rr.date||'—')+' '+esc(rr.track||'—')+' '+(n(rr.raceNumber)?esc(rr.raceNumber)+'R ':'')+esc(rr.distance||'—')+'m</b><strong>'+esc(rr.finish||rr.finishPosition||'—')+'着</strong></div>'+
      '<div>'+fmtTime(rr.timeSeconds)+'　'+esc(rr.condition||'不明')+' / '+esc(rr.weather||'不明')+'</div>'+
      '<div class="muted">'+(rr.title?esc(rr.title)+'　':'')+'通過 '+esc((rr.cornerPositions||[]).join('-')||'—')+(saneCarriedWeightValue(rr.carriedWeight,rr.bodyWeight)?'　斤量 '+esc(String(saneCarriedWeightValue(rr.carriedWeight,rr.bodyWeight)).replace(/\.0$/,''))+'kg':'')+'</div>'+
      (rid?'<button type="button" class="recent-open" data-past-race="'+esc(rid)+'">この過去レースを見る</button>':'')+'</div>'
  }).join(''):'<div class="empty compact">近走データを確認できませんでした</div>';
  return '<section id="section-detail" class="card detail-panel-v223 detail-panel-v239">'
    +'<div class="detail-nav-v223">'
      +'<button type="button" data-detail-prev="1" aria-label="前の馬">‹</button>'
      +'<span class="detail-check-v223 rc-horse-check '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+'</span>'
      +badge(h)+'<strong class="detail-name-v223">'+esc(h.name)+'</strong>'
      +'<button type="button" data-detail-next="1" aria-label="次の馬">›</button>'
      +'<span class="detail-count-v223">'+(idx+1)+'/'+field+'頭</span>'
    +'</div>'
    +'<div class="detail-ai-card-v223 detail-ai-v239"><div class="detail-ai-label-v223">AI総合評価</div><div class="detail-ai-main-v223"><strong class="overall-grade '+gradeClass(grade)+'">'+grade+'</strong><b>'+score+'</b><i data-ai-mark="'+esc(x.predMark||'')+'">'+esc(x.predMark||'—')+'</i></div><div class="detail-ai-sub-v223"><span>1着 '+(n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability)))*100).toFixed(1)+'%</span><span>2着 '+(n(x.p2Probability)*100).toFixed(1)+'%</span><span>3着 '+(n(x.p3Probability)*100).toFixed(1)+'%</span></div></div>'
    +'<div class="detail-simple-section-v239"><h3>基本情報</h3><div class="horse-info-grid">'
      +'<div class="horse-info-cell"><small>性齢</small><b>'+esc(h.sex||'—')+esc(h.age||'—')+'</b></div>'
      +'<div class="horse-info-cell"><small>脚質</small><b>'+esc(styleTxt)+'</b></div>'
      +'<div class="horse-info-cell"><small>騎手</small><b>'+esc(h.jockey||'—')+'</b></div>'
      +'<div class="horse-info-cell"><small>斤量</small><b>'+esc(carriedWeightText(h))+'</b></div>'
      +'<div class="horse-info-cell"><small>調教師</small><b>'+esc(h.trainer||'—')+'</b></div>'
      +'<div class="horse-info-cell"><small>馬体重</small><b>'+esc(bodyTxt)+'</b></div>'
    +'</div></div>'
    +'<div class="detail-simple-section-v239"><h3>近走データ</h3>'+recentHtml+'</div>'
  +'</section>'
}
function moveDetailHorse(dir){
  if(!state.pred)return;var rows=sortedHorseRows(state.pred.rows);if(!rows.length)return;
  var idx=rows.findIndex(function(z){return n(z.horse.horseNumber)===n(state.detailHorseNo)});if(idx<0)idx=0;
  state.detailHorseNo=n(rows[(idx+dir+rows.length)%rows.length].horse.horseNumber);state.openPanel='detail';render()
}
function resultPanel(r){var final=isFinal(r),flash=isFlash(r),any=hasAnyResultData(r);return '<section id="section-result" class="card"><h2>レース結果</h2>'+(any?renderResult(r)+(final?renderPayouts(r):'<section class="card"><div class="section-title">払い戻し <span class="muted">確定待ち</span></div><div class="muted">速報中です。確定後に自動反映します。</div></section>')+renderActualFlow(r):(flash?'<div class="muted">速報を取得中です。着順が入り次第ここに表示します。</div>':(final?'<div class="muted">確定済み・結果詳細を取得中です。自動更新します。</div>':'<div class="muted">結果はまだ出ていません。</div>')))+'</section>'}
function detailTabs(r,p){var key=state.openPanel;if(key==='entry')return '<div id="section-entry" class="accordion-panel">'+runnerStyleSection(r,p)+'</div>';if(key==='diagnosis')return '<div class="accordion-panel">'+diagnosisPanel(r,p)+'</div>';if(key==='detail')return '<div class="accordion-panel">'+detailPanel(r,p)+'</div>';if(key==='pace')return '<div class="accordion-panel">'+pacePanel(r,p)+'</div>';if(key==='bets')return '<div class="accordion-panel">'+betPanel(r,p)+'</div>';if(key==='result')return '<div class="accordion-panel">'+resultPanel(r)+'</div>';return '<div class="accordion-idle">出走表・全頭診断・詳細・展開予想・買い目から見たい項目を押してください。</div>'}
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
    +'<div class="race-nav-v230-row race-nav-v230-top">'+tab('出走表','entry')+tab('全頭診断','diagnosis')+tab('詳細','detail')+'</div>'
    +'<div class="race-nav-v230-row race-nav-v230-bottom">'+tab('展開予想','pace')+tab('買い目','bets')+'</div>'
    +'</div>'
}
function cinematicFeature(r){if(!r)return '';var count=n(r.fieldSize,(r.horses||[]).length),surface=r.surface||'—',course=COURSE[r.track]||{},turn=r.turn||course.turn||'—';return '<section class="cinema-feature" aria-label="選択したレース"><div class="cinema-feature-photo" aria-hidden="true"></div><div class="cinema-feature-info"><div class="cinema-feature-heading"><h1>'+esc(r.track)+' '+esc(r.raceNumber)+'R</h1>'+cinematicGrade(r)+'</div><h2>'+esc(r.title||'レース詳細')+'</h2><div class="cinema-feature-meta">'+timeHtml(r)+' 発走　'+esc(surface)+' '+esc(r.distance||'—')+'m ('+esc(turn)+')　<span>'+esc(r.weather||'')+' '+esc(r.condition||'')+'</span></div><div class="cinema-metrics">'+[[r.distance?r.distance+'m':'—','距離'],[turn,'コース'],[surface,'馬場'],[r.raceClass||r.className||raceMode(r),'条件'],[count?count+'頭':'—','頭数']].map(function(x){return '<div><b>'+esc(x[0])+'</b><small>'+esc(x[1])+'</small></div>'}).join('')+'</div></div><button class="cinema-feature-open" data-race="'+esc(r.id)+'" aria-label="レース詳細を開く">›</button>'+cinematicTabs(r)+'</section>'}
function otherRaces(r){var ctx=cinematicContext(r),rows=ctx.races.filter(function(x){return !r||x.id!==r.id});return '<section class="cinema-others"><div class="cinema-section-heading"><h2>◷ '+(state.date===today()?'本日の他レース':'この日の他レース')+'</h2><button data-action="all-races">全レース一覧 ›</button></div><div class="cinema-other-list">'+(rows.length?rows.map(function(x){return '<button data-race="'+esc(x.id)+'" class="cinema-other-row '+(isFinal(x)?'final':'')+'"><span>'+esc(x.track)+'</span><b>'+esc(x.raceNumber)+'R</b><span class="other-title">'+esc(x.title||'')+'</span><time>'+timeHtml(x)+'</time><span class="other-distance">'+esc(x.surface||'')+' '+esc(x.distance||'—')+'m</span><span class="other-condition">'+esc(x.condition||'')+'</span><span class="other-status">'+(isFinal(x)?'結果確定':(isFlash(x)?'結果速報':'レース詳細'))+' ›</span></button>'}).join(''):'<div class="cinema-empty">他のレースはありません</div>')+'</div></section>'}
function cinematicFooter(){return '<footer class="cinema-footer">ARVEXQ　<small>PACE · POSITION · VALUE · BUILD v324</small></footer>'}
function smartTopBar(back,title,sub){
  return '<header class="smart-topbar smart-topbar-clean smart-section-topbar">'+
    '<button class="smart-reload" data-action="reload" aria-label="更新">↻</button>'+ 
    '<div class="smart-head-copy smart-head-copy-clean"><strong>'+esc(title||'開催場')+'</strong><small>'+esc(sub||'')+'</small></div>'+ 
    (back?'<button class="smart-section-close" data-action="back" aria-label="トップへ戻る">×</button>':'<span class="smart-back-space"></span>')+
  '</header>'
}
function smartRaceTopBar(r){
  var rows=(state.races||[]).filter(function(x){return x&&r&&x.circuit===r.circuit&&x.track===r.track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),idx=-1;
  for(var i=0;i<rows.length;i++){if(String(rows[i].id)===String(r.id)){idx=i;break}}
  var prev=idx>0?rows[idx-1]:null,next=idx>=0&&idx<rows.length-1?rows[idx+1]:null;
  return '<header class="smart-topbar smart-topbar-clean smart-race-topbar">'+
    '<button class="smart-reload" data-action="reload" aria-label="更新">↻</button>'+ 
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
  // v261: prefer the immutable server-side pre-race lock. Fallback only supports
  // older saved races that predate the lock.
  var lock=detail&&detail.preRacePrediction||{},locked=Array.isArray(lock.horses)?lock.horses:[];
  if(locked.length)return locked.map(function(x){return{no:n(x.horseNumber),mark:String(x.mark||''),p:n(x.decisionProbability),axes:x.axes||{},confidence:n(lock.winnerConfidence),stable:!!lock.winnerStable}}).filter(function(x){return x.no>0});
  var rows=[];(detail&&detail.horses||[]).forEach(function(h){var e=h&&h.integratedEvaluation||{},mark=String(e.mark||'');if(mark)rows.push({no:n(h.horseNumber),mark:mark,p:n(e.winnerConsensusProbability),axes:(e.v218Audit||e.v217Audit||{}),confidence:n(e.axisConfidence),stable:!!e.winnerDecisionStable})});return rows
}
function aiDailyOne(detail){
  if(!detail||!isFinal(detail))return null;
  var finishers=(detail.result&&detail.result.finishers||[]).filter(function(x){return n(x.finish)>0}).sort(function(a,b){return n(a.finish)-n(b.finish)});if(!finishers.length)return null;
  var winner=n(finishers[0].horseNumber),top3={};finishers.slice(0,3).forEach(function(x){top3[n(x.horseNumber)]=1});
  var marks=aiStoredMarks(detail);if(!marks.length)return null;
  var hon=marks.find(function(x){return x.mark==='◎'}),marked={};marks.forEach(function(x){if(['◎','○','▲','☆+','☆','△','注+','注'].indexOf(x.mark)>=0)marked[x.no]=x.mark});
  var holePlace=marks.some(function(x){return (x.mark==='☆'||x.mark==='☆+'||x.mark==='注'||x.mark==='注+')&&top3[x.no]});
  var ranked=marks.slice().sort(function(a,b){return n(b.p)-n(a.p)||n(a.no)-n(b.no)}),wr=ranked.findIndex(function(x){return x.no===winner})+1,wrow=marks.find(function(x){return x.no===winner}),audit=detail.predictionAudit||{};
  var winHit=!!(hon&&hon.no===winner),markHit=!!marked[winner],confidence=n(audit.winnerConfidence,hon&&hon.confidence),reason=String(audit.reason||'');
  var podiumNos=finishers.slice(0,3).map(function(x){return n(x.horseNumber)}).filter(function(x){return x>0}),markedPodiumCount=podiumNos.filter(function(no){return !!marked[no]}).length,fullPodiumHit=podiumNos.length===3&&markedPodiumCount===3,circuit=String(detail.circuit||'');
  if(!reason&&!winHit)reason=markHit?'候補内の1着順位付け':'候補抽出';
  if(!fullPodiumHit&&markedPodiumCount===2)reason=reason||'印内3頭完全包含で1頭抜け';
  var brier=n(audit.brier,0),logLoss=n(audit.logLoss,0);
  if(!brier&&wrow){marks.forEach(function(x){var y=x.no===winner?1:0;brier+=Math.pow(n(x.p)-y,2)});logLoss=-Math.log(Math.max(1e-9,n(wrow.p)))}
  return {winHit:winHit,markHit:markHit,fullPodiumHit:fullPodiumHit,markedPodiumCount:markedPodiumCount,circuit:circuit,holePlace:holePlace,top2:wr>0&&wr<=2,top3:wr>0&&wr<=3,candidateOrderMiss:!winHit&&markHit,candidateMiss:!markHit,highConf:confidence>=.70,highConfHit:confidence>=.70&&winHit,brier:brier,logLoss:logLoss,reason:reason,winnerMark:String(marked[winner]||'')}
}
function resetDailyAiStats(date){dailyAiStats={date:date||'',loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,centralPodiumHits:0,centralPodiumTotal:0,localPodiumHits:0,localPodiumTotal:0,markedPodiumSum:0,holePlaceHits:0,top2Hits:0,top3Hits:0,candidateOrderMisses:0,candidateMisses:0,highConfHits:0,highConfTotal:0,brierSum:0,logLossSum:0,reasons:{},error:''}}
function scheduleDailyAiStats(){
  if(dailyAiStats.date!==state.date)resetDailyAiStats(state.date);
  if(dailyAiStats.loading)return;
  var targetDate=state.date,dayRaces=(state.races||[]).filter(function(r){return r&&r.id});
  var allFinished=dayRaces.length>0&&dayRaces.every(function(r){return isFinal(r)});
  if(!allFinished){dailyAiStats.done=false;dailyAiStats.total=0;dailyAiStats.finalCount=0;return}
  var finals=dayRaces.slice();
  if(dailyAiStats.done&&dailyAiStats.finalCount===finals.length)return;
  var token=++dailyAiStatsJob,cursor=0,results=[];dailyAiStats.loading=true;dailyAiStats.done=false;dailyAiStats.error='';
  render();
  function worker(){
    if(token!==dailyAiStatsJob||cursor>=finals.length)return Promise.resolve();
    var row=finals[cursor++];
    return fetchEdgeRace(row.id,false).then(function(d){var z=aiDailyOne(d);if(z)results.push(z)}).catch(function(){}).then(worker)
  }
  Promise.all([worker(),worker()]).then(function(){
    if(token!==dailyAiStatsJob||state.date!==targetDate)return;
    dailyAiStats.loading=false;dailyAiStats.done=true;dailyAiStats.total=results.length;dailyAiStats.finalCount=finals.length;
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
function raceIsGraded(r){var t=String(r&&r.title||''),c=String(r&&r.raceClass||r&&r.className||'');return /(?:Jpn\s*)?G\s*[ⅠⅡⅢ123]|(?:Jpn\s*)[ⅠⅡⅢ123]|\b(?:S|H|M)\s*[ⅠⅡⅢ123]\b|SP\s*[ⅠⅡⅢ123]|重賞|グランプリ|ダービー|優駿|賞\s*\(重賞\)/i.test(t+' '+c)}
function mandatoryTrifectaRace(r){
  var title=String(r&&r.title||'');
  return !!(r&&(raceIsGraded(r)||(String(r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r.raceNumber)===12))))
}
function forceMandatoryTrifecta(plan,r,p){
  if(!plan||!mandatoryTrifectaRace(r))return plan;
  var rows=(p&&p.rows||[]).slice().filter(function(x){return x&&x.horse&&!isScratchHorse(x.horse)});
  if(rows.length<3)return plan;
  function no(x){return x&&x.horse?n(x.horse.horseNumber):0}
  function win(x){return n(x.winnerDecisionProbability,n(x.winnerConsensusProbability,n(x.p1Probability,0)))}
  var axis=rows.filter(function(x){return String(x.predMark||'')==='◎'})[0]||rows.slice().sort(function(a,b){return win(b)-win(a)})[0]||null;
  var axisNo=no(axis);if(!axisNo)return plan;
  var markOrder={'○':0,'▲':1,'☆+':2,'☆':3,'△':4,'注+':5,'注':6,'':7};
  var mates=rows.filter(function(x){return no(x)!==axisNo}).sort(function(a,b){
    var ma=String(a.predMark||''),mb=String(b.predMark||''),ra=markOrder.hasOwnProperty(ma)?markOrder[ma]:8,rb=markOrder.hasOwnProperty(mb)?markOrder[mb]:8;
    return ra-rb||win(b)-win(a)||no(a)-no(b)
  }).slice(0,3),combos=[];
  for(var i=0;i<mates.length;i++)for(var j=0;j<mates.length;j++)if(i!==j)combos.push([axisNo,no(mates[i]),no(mates[j])]);
  if(!combos.length)return plan;
  plan.items=(plan.items||[]).filter(function(z){return !(z&&z.kind==='3連単')});
  plan.items.push({level:'3連単チャレンジ',kind:'3連単',combos:combos,points:combos.length,combo:betComboText('3連単',combos),confidence:'チャレンジ',mandatory:true});
  plan.trifectaReviewed=true;plan.trifectaDecision='採用';plan.trifectaReason='重賞・高知ファイルは3連単チャレンジ必須。◎1着固定で相手上位3頭を2・3着入替。';
  if(plan.decision==='見送り')plan.decision='通常買い';
  plan.mandatoryTrifecta=true;
  return plan
}
function explicitSelectedRace(r){return !!(r&&(r.arvexqSelected||r.selectedRace||r.isSelected||r.recommendedRace||r.aiSelected))}
function mainRaceForTrack(rows){
  rows=(rows||[]).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;
  var explicit=rows.find(function(r){return r.isMain||r.mainRace||r.featured||/メイン/.test(String(r.title||''))});if(explicit)return explicit;
  var r11=rows.find(function(r){return n(r.raceNumber)===11});if(r11)return r11;
  return rows.length>=2?rows[rows.length-2]:rows[rows.length-1]
}
function kochiFinalRace(rows){rows=(rows||[]).filter(function(r){return r.track==='高知'}).slice().sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});if(!rows.length)return null;return rows.find(function(r){return /ファイナル/i.test(String(r.title||''))})||rows[rows.length-1]}
function raceChronologicalCompare(a,b){
  var ra=(a&&a.race)||a||{},rb=(b&&b.race)||b||{},ta=mins(ra.startTime),tb=mins(rb.startTime);
  if(ta!==tb)return ta-tb;
  var tc=String(ra.track||'').localeCompare(String(rb.track||''),'ja');if(tc)return tc;
  return n(ra.raceNumber)-n(rb.raceNumber)
}
function eliteSelectedRaceCut(rows){
  rows=(rows||[]).slice().sort(function(a,b){
    return n(b.selection&&b.selection.score)-n(a.selection&&a.selection.score)||
      n(b.selection&&b.selection.winnerConfidence)-n(a.selection&&a.selection.winnerConfidence)||
      n(b.selection&&b.selection.evidence)-n(a.selection&&a.selection.evidence)
  });
  if(!rows.length)return [];
  var best=n(rows[0].selection&&rows[0].selection.score),central=String((rows[0].race&&rows[0].race.circuit)||'')==='中央',floor=Math.max(central?82:80,best-2),limit=1;
  var elite=rows.filter(function(z){var t=z.selection||{},rd=t.readiness||{},central=String((z.race&&z.race.circuit)||'')==='中央';return n(t.score)>=floor&&n(rd.prediction)>=(central?.74:.72)&&n(t.coverage)>=(central?.60:.58)&&n(t.top3mass)>=(central?.68:.70)&&n(t.evidence)>=(central?.55:.53)&&n(t.scenarioProb)>=(central?.30:.28)&&!!t.winnerStable&&n(t.winnerConfidence)>=.72});
  return elite.slice(0,limit).sort(raceChronologicalCompare)
}
function selectedRaceCandidates(circuit){
  var all=(state.races||[]).filter(function(r){return r&&r.id&&(!circuit||String(r.circuit||'')===String(circuit))}),map={};
  function add(r,t){if(!r)return;var k=String(r.id);map[k]={race:r,tags:['厳選'],selection:t}}
  // v304: every race on the card is evaluated first. Clock time is NEVER a
  // selection factor. A second full-card quality cut keeps only true elite races.
  all.forEach(function(r){try{
    var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id);if(!d||isFinal(d))return;
    var p=predict(d),t=strictSelectedRaceProfile(d,p);if(t.selected)add(r,t)
  }catch(e){}});
  return eliteSelectedRaceCut(Object.keys(map).map(function(k){return map[k]}))
}
function expectedValueRaceProfile(r,p){
  var rows=(p&&p.rows||[]).slice(),field=rows.length,cov=n(p&&p.coverage,0),uniform=1/Math.max(1,field),ready=dataReadinessProfile(r,p),strict=strictSelectedRaceProfile(r,p),method=v312CircuitMethod(r),vg=method.value;
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
  var st=fixedPickLoadStatus(circuit),label='厳選判定';
  if(!st.complete)return '<div class="fixed-pick-empty"><b>選定中</b><small>'+label+'用データ '+st.loaded+'/'+st.expected+'</small></div>';
  return '<div class="fixed-pick-empty"><b>該当なし</b><small>'+label+'基準を通過したレースなし</small></div>'
}
function fixedSelectedBox(circuit,picks){
  var body=picks.length?picks.map(function(z){var r=z.race,t=z.selection||{};return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>厳選 '+esc(t.score||'—')+'</em></button>'}).join(''):fixedPickEmpty('selected',circuit),open=!!(selectedCircuitSectionsOpen.selected&&selectedCircuitSectionsOpen.selected[circuit]);
  return '<details class="fixed-pick-box fixed-pick-circuit" data-selected-circuit="selected" data-pick-circuit="'+esc(circuit)+'" '+(open?'open':'')+'><summary class="fixed-pick-box-head"><b>'+esc(circuit)+'</b><span class="fixed-pick-summary-right"><em>'+picks.length+'レース</em><i>⌄</i></span></summary><div class="fixed-pick-box-body">'+body+'</div></details>'
}
function selectedRaceBetPreview(r){
  var d=instantTrackDetails[String(r.id)]||loadDetailCache(r.id),st=mins(r.startTime),started=r.date===today()&&st<9999&&nowMins()>=st,plan=loadStoredAiBet(r.id,isFinal(r)||started),p=null;if(d&&!plan&&!isFinal(d)&&!started){try{p=predict(d);plan=buildAiBetPlan(d,p)}catch(e){}}
  if(!plan)return '<div class="selected-bet-pending">ARVEXQの買い目　準備中</div>';
  if(plan.decision==='見送り')return '<div class="selected-bet-pending">ARVEXQ買い目　見送り（'+esc(plan.betQuality||0)+'/100）</div>';
  var lines=(plan.items||[]).map(function(z){return '<span class="selected-bet-chip '+(z.level==='3連単チャレンジ'?'tri':'')+'"><b>'+esc(z.level)+'</b> '+esc(z.kind)+' '+esc(z.combo)+'</span>'}).join('');if(plan.trifectaReviewed&&plan.trifectaDecision==='見送り')lines+='<span class="selected-bet-chip tri"><b>3連単</b> 検討済み・見送り</span>';
  var result='';if(d&&isFinal(d)){var hit=aiBetPlanHit(d,plan),lv=hit&&hit.levels||{},hits=[];['本線','押さえ','強気'].forEach(function(k){if(lv[k])hits.push(k+'HIT')});result='<div class="selected-result '+(hit&&hit.hit?'hit':'miss')+'">結果　'+(hits.length?hits.join(' / '):'通常買い目不的中')+(hit&&hit.tri?'　<strong>3連単HIT</strong>':'')+'</div>'}
  return '<div class="selected-bets">'+lines+'</div>'+result
}
function smartSelectedRaces(){
  var central=selectedRaceCandidates('中央'),local=selectedRaceCandidates('地方'),open=!!selectedSectionsOpen.selected,total=central.length+local.length;
  return '<details class="smart-fixed-picks" data-selected-section="selected" '+(open?'open':'')+'><summary class="smart-fixed-picks-head"><span><b>厳選レース</b><small>基準未達なら0件・本当に強い時だけ</small></span><span class="smart-fixed-summary-right"><em>'+total+'レース</em><i>⌄</i></span></summary><div class="smart-fixed-pick-grid">'+fixedSelectedBox('中央',central)+fixedSelectedBox('地方',local)+'</div></details>'
}
function specialForecastRaceCandidates(){
  var rows=(state.races||[]).filter(function(r){return r&&r.id}),out=[],seen={},groups={};
  function add(r){var id=String(r&&r.id||'');if(!id||seen[id])return;seen[id]=1;out.push(r)}
  rows.forEach(function(r){if(raceIsGraded(r))add(r);var key=String(r.circuit||'')+'|'+String(r.track||'');(groups[key]||(groups[key]=[])).push(r)});
  Object.keys(groups).forEach(function(k){add(mainRaceForTrack(groups[k]))});
  add(kochiFinalRace(rows));
  return out.sort(raceChronologicalCompare)
}
function specialForecastRaceTag(r){
  var title=String(r&&r.title||'');
  if(raceIsGraded(r))return '重賞';
  if(String(r&&r.track||'')==='高知'&&(/ファイナル/i.test(title)||n(r&&r.raceNumber)===12))return '高知ファイナル';
  return 'メイン'
}
function smartSpecialForecastRaces(){
  var picks=specialForecastRaceCandidates(),body=picks.length?picks.map(function(r){
    var tag=specialForecastRaceTag(r);
    return '<button type="button" class="fixed-pick-row" data-race="'+esc(r.id)+'"><span><b>'+esc(r.track)+' '+esc(r.raceNumber)+'R</b><small>'+esc(r.title||'')+'</small></span><time>'+esc(r.startTime||'--:--')+'</time><em>'+tag+'</em></button>'
  }).join(''):'<div class="fixed-pick-empty"><b>該当なし</b><small>本日のメイン・重賞・高知ファイナルなし</small></div>';
  return '<section class="smart-fixed-picks smart-special-picks"><div class="smart-fixed-picks-head"><span><b>特別予想</b><small>メイン・重賞・高知ファイナル</small></span><span class="smart-fixed-summary-right"><em>'+picks.length+'レース</em></span></div><div class="smart-fixed-pick-grid"><div class="fixed-pick-box fixed-pick-circuit"><div class="fixed-pick-box-body">'+body+'</div></div></div></section>'
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
  return '<section class="smart-live-section"><div class="smart-live-heading"><b>リアルタイムのレース</b><small>各会場から1レース</small></div>'+
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
  state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.date=today();state.openPanel=null;state.race=null;state.track=null;state.picker=false;state.horseModalNo=null;state.detailHorseNo=null;state.scenarioCode=null;state.paceStage=0;
  window.scrollTo(0,0);load()
}
function smartHomeHero(){
  return '<section class="smart-home-hero">'+
    '<img class="smart-home-hero-image" src="/arvexq-racing-hero.webp" alt="ARVEXQ hero">'+
    '<div class="smart-home-hero-overlay"></div>'+
    '<div class="smart-home-hero-date smart-home-hero-date-left">'+esc((state.date||'').replace(/-/g,'.'))+'</div>'+
    '<label class="smart-hero-calendar-left" title="開催日を選択"><span class="calendar-mark" aria-hidden="true">▦</span><span>日付選択</span><input id="date" type="date" value="'+esc(state.date)+'" aria-label="開催日を選択"></label>'+
    '<button class="smart-hero-refresh smart-hero-refresh-right" data-action="reload" aria-label="更新">↻</button>'+
    
  '</section>'
}
function renderHome(){
  return '<div class="smart-shell smart-home">'+
    smartHomeHero()+
    '<main class="smart-main smart-home-main">'+
      smartLiveLauncher()+
      smartPageControls()+
      smartSelectedRaces()+
      smartSpecialForecastRaces()+
      smartDailyAiStats()+
      (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
      smartLiveRaceSection()+
      smartVenueCards()+
    '</main>'+ 
    cinematicFooter()+
  '</div>'
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
    '<button class="smart-venue-reload" data-action="reload" aria-label="更新">↻</button>'+ 
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
  return '<button type="button" class="smart-inline-result '+(final?'final':(flash?'flash':''))+'" data-panel="result"><span>レース結果</span><strong>'+(final?(ready?'確定':'取得中'):(flash?(any?'速報':'速報待ち'):'未確定'))+'</strong></button>'
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
  var u=officialRaceLinks(r);
  return '<div class="smart-official-actions smart-official-vote-only" aria-label="公式投票">'+
    '<a class="smart-official-btn vote" href="'+esc(u.vote)+'" target="_blank" rel="noopener noreferrer" aria-label="'+esc(u.voteLabel)+'を開く"><span>投票</span><small>'+esc(u.voteLabel.replace(' 投票',''))+'</small></a>'+ 
  '</div>'
}
function smartRaceHead(r){
  var count=n(r.fieldSize,(r.horses||[]).length);
  return '<section class="smart-race-head smart-race-head-compact smart-race-head-v222">'+
    '<div class="smart-race-head-layout">'+
      '<div class="smart-race-left-stack">'+
        '<div class="smart-race-head-left"><span class="smart-circuit-chip">'+esc(r.circuit||state.circuit)+'</span><div class="smart-race-title-stack"><h1>'+esc(r.title||'レース詳細')+'</h1><div class="smart-race-meta">'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc(r.weather||'')+' '+esc(r.condition||'')+'　'+count+'頭</div></div>'+cinematicGrade(r)+'</div>'+ 
        officialRaceActions(r)+
      '</div>'+ 
      '<div class="smart-race-result-side"><time>'+timeHtml(r)+' 発走</time>'+smartInlineResult(r)+'</div>'+ 
    '</div>'+ 
  '</section>'
}
function renderRaceLoading(){
  var row=state.races.find(function(x){return String(x.id)===String(state.raceLoading)});
  return '<div class="smart-shell">'+
    row?smartRaceTopBar(row):smartTopBar(true,state.track||'レース','レース詳細')+
    '<main class="smart-main smart-race-page">'+
      (row?smartRaceHead(row):'')+
      '<div class="smart-loading"><span class="smart-loading-dot"></span><b>'+(state.error?'レース詳細の同期待ち':'レース詳細を読み込み中')+'</b><small>'+(state.error?esc(state.error):'選択したレースだけ取得しています。開催場一覧は先に表示します。')+'</small>'+(state.error&&row?'<button type="button" class="smart-refresh" data-race="'+esc(row.id)+'">再試行</button>':'')+'</div>'+
    '</main>'+cinematicFooter()+
  '</div>'
}
function mergeResultHorseFields(r){
  if(!r)return r;
  var fs=r.result&&r.result.finishers||[],by={};
  fs.forEach(function(f){var no=n(f&&f.horseNumber,0);if(no)by[no]=f});
  (r.horses||[]).forEach(function(h){var f=by[n(h.horseNumber,0)];if(!f)return;['bodyWeight','bodyWeightChange','popularity','winOdds'].forEach(function(k){if((h[k]==null||h[k]==='')&&f[k]!=null&&f[k]!=='')h[k]=f[k]})});
  return r
}
function renderRace(){
  var r=applySummaryEnvironment(mergeResultHorseFields(state.race)),p=predict(r);
  state.race=r;state.pred=p;
  if(!state.openPanel)state.openPanel='entry';
  var top=p.scenarios.slice().sort(function(a,b){return b.prob-a.prob})[0];
  if(!state.scenarioCode||!p.plans||!p.plans[state.scenarioCode])state.scenarioCode=top?top.code:null;
  return '<div class="smart-shell">'+
    smartRaceTopBar(r)+
    '<main class="smart-main smart-race-page">'+
      smartRaceHead(r)+
      cinematicTabs(r)+
      '<div class="smart-race-content">'+detailTabs(r,p)+'</div>'+
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
function renderResult(r){if(!hasAnyResultData(r))return"";var final=isFinal(r),label=final?"確定":"速報",badgeCls=final?"final-badge":"flash-badge",results=(r.result.finishers||[]).slice();(r.horses||[]).forEach(function(h){if(!results.some(function(z){return n(z.horseNumber)===n(h.horseNumber)}))results.push({horseNumber:h.horseNumber,name:h.name,finishLabel:h.status||"結果待ち"})});var f=results.sort(function(a,b){return (n(a.finish)||999)-(n(b.finish)||999)}),top=f.slice(0,5),rest=f.slice(5);return'<section class="card result-card"><div class="section-title">レース結果 <span class="'+badgeCls+'">'+label+'</span></div>'+(final?'':'<div class="muted" style="margin-bottom:7px">速報値です。確定まで自動更新します。</div>')+'<div class="muted" style="margin-bottom:7px">馬場 '+esc(r.condition||'不明')+' / 天候 '+esc(r.weather||'不明')+'</div>'+top.map(function(x){return resultRowHtml(r,x)}).join("")+(rest.length?'<details class="result-more"><summary>6着以下を見る　'+rest.length+'頭</summary><div class="result-more-list">'+rest.map(function(x){return resultRowHtml(r,x)}).join("")+'</div></details>':'')+'</section>'}
function gradeRank(g){return g==='S'?0:(g==='A'?1:(g==='B'?2:(g==='C'?3:9)))}

function actualNumberArrowList(r,items){return (items||[]).map(function(it){var x=it&&it.x?it.x:it,h=horseByNo(r,x.horseNumber)||x;return badge(h)}).join('<i>→</i>')}
function renderActualFlow(r){if(!hasAnyResultData(r))return"";var count=actualCornerCount(r),html='<section class="card actual-flow"><div class="section-title">実際の展開順序</div>';if(!count)html+='<div class="muted">コーナー通過順データなし</div>';for(var j=0;j<count;j++){var a=actualOrderAt(r,j);html+='<div class="actual-stage"><b>'+actualCornerLabel(j,count)+'</b><div class="actual-order actual-order-compact">'+actualNumberArrowList(r,a)+'</div></div>'}var f=(r.result.finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)});html+='<div class="actual-stage"><b>ゴール</b><div class="actual-order actual-order-compact">'+actualNumberArrowList(r,f)+'</div></div></section>';return html}
function roleDetail(label,stats,profile){stats=stats||{};profile=profile||{};var st=n(stats.starts)||n(profile.starts),w=n(stats.wins),s=n(stats.seconds),t=n(stats.thirds);if(!st)return'<div class="role-box"><b>'+esc(label)+'</b><div>過去データ未取得 / 該当履歴なし</div></div>';var wr=Math.round(w/st*100),rr=Math.round((w+s)/st*100),pr=Math.round((w+s+t)/st*100),bits=['出走 '+st,'1着 '+w,'2着 '+s,'3着 '+t,'勝率 '+wr+'%','連対 '+rr+'%','複勝 '+pr+'%'];if(n(profile.starts)>0){bits.push('競馬場 '+Math.round(n(profile.track)*100)+'%');bits.push('距離 '+Math.round(n(profile.distance)*100)+'%');if(profile.condition!=null)bits.push('馬場 '+Math.round(n(profile.condition)*100)+'%');if(n(profile.early3Rate,0))bits.push('序盤3番手内 '+Math.round(n(profile.early3Rate)*100)+'%');if(n(profile.leaderRate,0))bits.push('逃げ '+Math.round(n(profile.leaderRate)*100)+'%')}return'<div class="role-box"><b>'+esc(label)+'</b><div>'+bits.join(' / ')+'</div></div>'}
function styleDisplayPcts(x){if(!x||!n(x.styleSamples))return[null,null,null,null];var raw=[n(x.rawFront,x.front),n(x.rawStalk,x.stalk),n(x.rawMid,x.mid),n(x.rawClose,x.close)],vals=[],sum=0,i,maxi=0;for(i=0;i<4;i++){vals[i]=Math.max(0,Math.round(raw[i]*100));sum+=vals[i];if(raw[i]>raw[maxi])maxi=i}vals[maxi]+=100-sum;return vals}
function styleCell(label,val,active,cls){var unk=val==null||!isFinite(Number(val));return '<div class="style-rate '+cls+(active?' dominant':'')+(unk?' unknown':'')+'"><div class="style-rate-head"><span>'+label+'</span><b>'+(unk?'—':val+'%')+'</b></div><div class="style-bar"><i style="width:'+(unk?0:Math.max(2,val))+'%"></i></div></div>'}
function positionBucket(x){if(x.expected==="逃げ候補")return"逃げ候補";if(x.expected==="先行")return"先行";if(x.expected==="好位")return"好位";if(x.expected==="後方")return"後方";if(x.expected==="不明")return"不明";return"中団"}
function stylePositionMap(r,p){var rows=(p.rows||[]).slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),labels=['逃げ候補','先行','好位','中団','後方','不明'],field=Math.max(1,(r.horses||[]).length),html='<div class="style-position-map"><div class="style-map-axis"><span>内枠</span><b>脚質マップ＋枠順</b><span>外枠</span></div>';for(var j=0;j<labels.length;j++){var lab=labels[j];html+='<div class="style-lane"><div class="style-lane-label">'+lab+'</div><div class="style-lane-track">';for(var i=0;i<rows.length;i++){var x=rows[i],h=x.horse;if(positionBucket(x)!==lab)continue;var left=field<=1?50:6+(n(h.horseNumber)-1)/Math.max(1,field-1)*88,shift=x.pastStyle!==x.expected&&!(x.pastStyle==='先行'&&x.expected==='好位');html+='<span class="style-map-horse'+(shift?' shifted':'')+'" style="left:'+left+'%" title="'+esc(h.name)+'｜過去 '+esc(x.pastStyle)+' → 今回 '+esc(x.expected)+'｜'+esc(x.frontLineRole||'')+'">'+badge(h)+'</span>'}html+='</div></div>'}html+='<div class="style-map-note"><b>水色縁</b>＝過去脚質から今回条件で位置想定が動いた馬。馬番順で内→外を維持。</div>';html+='<div class="style-map-rate-list">'+rows.map(function(x){var h=x.horse,ps=styleDisplayPcts(x),fade=x.styleSamples?Math.round(x.fade*100):null;function cell(l,v,cls){return'<span class="style-map-rate-cell '+(cls||'')+'">'+l+'<strong class="'+(cls==='fade'&&v!=null&&v>=55?'high':'')+'">'+(v==null?'—':v+'%')+'</strong></span>'}return'<div class="style-map-rate-row"><span class="style-map-rate-horse">'+badge(h)+'<b>'+esc(h.name||'')+'</b></span>'+cell('逃',ps[0])+cell('先',ps[1])+cell('差',ps[2])+cell('追',ps[3])+cell('下',fade,'fade')+'</div>'}).join('')+'</div>';var arr=p.arrangement||{};html+='<div class="style-map-summary"><b>先行列：</b>'+esc(arr.pattern||'—')+'　<b>配置：</b>'+esc(arr.concentrationText||'—')+'　<b>初角まで：</b>'+Math.round(firstTurnDistance(r))+'m'+((r.firstTurnDistance||r.startToFirstTurn||r.firstCornerDistance||r.firstCornerMeters)?'':'（コース推定）')+'</div></div>';return html}
function runnerStyleSection(r,p){
  function oddsCells(h){
    var ok=h&&h.winOdds!=null&&h.winOdds!==''&&n(h.winOdds)>0,o=ok?n(h.winOdds):0,pop=n(h&&h.popularity,0),forecast=!!(h&&h.oddsForecast)||/予想|forecast/i.test(String(h&&h.oddsSource||''));
    var os=ok?(Math.round(o*10)/10).toFixed(1):'取得中';
    return '<span class="odd '+(o>0&&o<10?'single':'')+'">'+esc(os)+'</span><span class="pop">'+(forecast?'予想 ':'')+(pop>0?esc(pop)+'人気':(ok?'参考':'更新中'))+'</span>';
  }
  var diagnosisReady=diagnosisCurrent(r),cadenceText=(raceBodyWeightComplete(r)&&raceOddsComplete(r))?'オッズ・馬体重取得済み':'オッズ・馬体重を自動取得',dayCorr=sameDayCorrectionProfileV313(r,p.rows||[]),dayNote=dayCorr.active?('<div class="diagnosis-refresh-note" style="margin:7px 0"><b>当日補正 ON</b>　前'+dayCorr.completed+'R反映 / '+(dayCorr.markRaces?('印内3頭 '+Math.round(dayCorr.coverage*100)+'%'):'印比較待ち')+' / '+esc(dayCorr.flowLabel)+'傾向　<small>同場の発走済みレースだけで後半の印を微調整</small></div>'):'';
  return '<section class="card"><h2>出走表</h2><button data-action="odds-update">オッズ・馬体重更新</button><span id="odds-status" role="status"> '+cadenceText+'</span>'
    +dayNote
    +(!diagnosisReady?'<div class="diagnosis-refresh-note busy" style="margin:7px 0">取得済みデータでAI評価を先に計算中。更新後は全頭診断へ反映します。</div>':'')
    +'<div class="racecard-table">'
    +(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){
      var scratch=isScratchHorse(h),x=(p.rows||[]).find(function(z){return n(z.horse.horseNumber)===n(h.horseNumber)});
      var fr=clamp(n(h.frameNumber,h.horseNumber),1,8),bw=horseBodyWeightText(h),refbw=!bw?referenceBodyWeight(h):0,st=String(h.status||(h.scratched||h.withdrawn?'出走取消':'欠場'));
      return '<div class="racecard-row'+(scratch?' scratched':'')+'" '+(scratch?'aria-disabled="true"':'')+'>'
        +'<span class="rc-check-cell"><span class="rc-horse-check '+(isHorseChecked(r,h.horseNumber)?'checked':'')+'" data-horse-check="'+esc(h.horseNumber)+'">'+horseCheckGlyph(r,h.horseNumber)+'</span></span>'
        +'<span class="rc-number frame'+fr+'">'+esc(h.horseNumber)+'</span>'
        +'<span class="rc-horse">'
          +'<span class="rc-horse-top"><b class="rc-horse-name">'+esc(h.name)+'</b>'+(scratch?'<small class="rc-scratch">'+esc(st)+'</small>':'<small class="rc-bodyweight '+(bw?'':'pending')+'">'+(bw?('馬体重 '+esc(bw)):(refbw?('前走 '+esc(refbw)+'kg'):'計量待ち'))+'</small>')+'</span>'
          +'<span class="rc-horse-meta"><span class="rc-meta-left"><span>'+esc(h.sex||'—')+esc(h.age||'—')+'</span></span><span class="jockey">'+esc(h.jockey||'—')+'</span><span class="carry">斤量 '+esc(carriedWeightText(h))+'</span></span>'
        +'</span>'
        +'<span class="rc-odds" data-odds-no="'+esc(h.horseNumber)+'">'+oddsCells(h)+'</span>'
        +'<span class="rc-ai-mark" data-ai-mark="'+esc(x&&x.predMark||'')+'">'+esc(x&&x.predMark||'—')+'</span>'
        +'</div>'
    }).join('')
    +'</div></section>'
}
function rowName(x){return x&&x.horse?(x.horse.horseNumber+' '+x.horse.name):'—'}
function stageNarrative(p,idx){var rows=p.rows||[],plan=activeScenarioPlan(p),stages=visiblePaceStages(plan),st=stages[clamp(idx,0,Math.max(0,stages.length-1))],pack=st&&st.pack||[],prev=idx>0?((stages[idx-1]||{}).pack||[]):[],by={},rank={},prevRank={},i;for(i=0;i<rows.length;i++)by[n(rows[i].horse.horseNumber)]=rows[i];for(i=0;i<pack.length;i++)rank[n(pack[i].no)]=i+1;for(i=0;i<prev.length;i++)prevRank[n(prev[i].no)]=i+1;var lead=pack.length?by[n(pack[0].no)]:null,arr=p.arrangement||{},gainers=[],droppers=[],bits=[],key=String(st&&st.key||'');for(i=0;i<rows.length;i++){var x=rows[i],no=n(x.horse.horseNumber),d=(prevRank[no]||rank[no]||99)-(rank[no]||99);if(idx>0&&d>=2)gainers.push({x:x,d:d});if(idx>0&&d<=-2)droppers.push({x:x,d:-d})}gainers.sort(function(a,b){return b.d-a.d});droppers.sort(function(a,b){return b.d-a.d});if(lead)bits.push('<b>先頭想定 '+esc(rowName(lead))+'</b>');if(key==='start'){if((arr.leadCandidates||[]).length)bits.push('ハナ候補 '+(arr.leadCandidates||[]).map(function(x){return esc(rowName(x))}).join('・'));if((arr.secondCandidates||[]).length)bits.push('2番手 '+(arr.secondCandidates||[]).slice(0,3).map(function(x){return esc(rowName(x))}).join('・'))}else if(key==='turn3'||key==='turn4'){if(gainers.length)bits.push('<span class="event-good">進出 '+gainers.slice(0,3).map(function(z){return esc(rowName(z.x))}).join('・')+'</span>');if(droppers.length)bits.push('<span class="event-warn">後退 '+droppers.slice(0,3).map(function(z){return esc(rowName(z.x))}).join('・')+'</span>')}else if(key==='straight'){var stay=rows.slice().sort(function(a,b){return b.frontStay-a.frontStay}).slice(0,2),closers=rows.slice().sort(function(a,b){return (b.comeFromBehind+b.collapseBeneficiary*.25)-(a.comeFromBehind+a.collapseBeneficiary*.25)}).slice(0,2);bits.push('前残り適性 '+stay.map(function(x){return esc(rowName(x))}).join('・'));bits.push('差し込み適性 '+closers.map(function(x){return esc(rowName(x))}).join('・'))}return bits.join('　｜　')}
function activeScenarioPlan(p){return p&&p.plan?p.plan:null}
function visiblePaceStages(plan){var wanted={start:1,turn3:1,turn4:1,straight:1};return ((plan&&plan.stages)||[]).filter(function(s){return !!wanted[String(s&&s.key||'')]})}
function scenarioProbabilitySection(p){return''}
function paceBoard(r,p){var hs=(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}),plan=activeScenarioPlan(p)||p.plan,stages=visiblePaceStages(plan),cp=courseProfile(r);return'<section class="card ai-flow-card"><div class="ai-flow-head"><span class="ai-flow-bars"><i></i><i></i><i></i></span><div class="ai-flow-copy"><div class="ai-flow-title">AI展開予想</div><div class="ai-flow-sub">直近5走・通過順・脚質・枠順・隣接圧力・コース形状から局面ごとの隊列を表示</div></div></div><div class="ai-stage-tabs">'+stages.map(function(s,i){var label=s.key==='turn3'?'3C':(s.key==='turn4'?'4C':s.label);return'<button data-pace-stage="'+i+'" class="'+(i===0?'active':'')+'">'+esc(label)+'</button>'}).join('')+'</div><div class="ai-race-swipe-hint">図の左半分タップ＝前の局面　／　右半分タップ＝次の局面</div><div class="ai-race-topline"><div class="ai-race-meta-chip">'+esc(r.track)+'　'+esc(r.distance)+'m　'+esc(cp.turn)+(cp.shape==='straight'?'':'回り')+'</div><div class="ai-race-axis-strip"><span>← 後方</span><span>前方・先頭 →</span></div></div><div class="ai-race-board-wrap"><div id="pace-board" class="ai-race-visual">'+hs.map(function(h){return'<div class="ai-race-runner" data-horse="'+esc(h.horseNumber)+'" style="left:10%;top:50%">'+badge(h)+'</div>'}).join('')+'</div></div><div id="course-order" class="ai-race-order-panel">隊列を準備中</div><div id="pace-event" class="ai-stage-event">展開イベントを準備中</div><div class="ai-race-note">スタート → 3C → 4C → 直線。右が先頭、左が後方です。</div></section>'}
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
function scheduleResultRefresh(){
  if(state.resultTimer){clearTimeout(state.resultTimer);state.resultTimer=null}
  var r=state.race;if(!r||!r.id||String(r.date||'')!==today()||(isFinal(r)&&hasResultData(r))||!r.startTime)return;
  var id=String(r.id),delta=mins(r.startTime)-nowMins(),wait;
  if(delta>3)wait=Math.min(300000,Math.max(30000,(delta-2)*60000));
  else wait=20000;
  state.resultTimer=setTimeout(function(){
    if(!state.race||String(state.race.id)!==id)return;
    fetchEdgeRace(id,true).then(function(body){
      if(!body||!state.race||String(state.race.id)!==id)return;
      var hadResult=hasResultData(state.race),becameFinal=!isFinal(state.race)&&isFinal(body);
      state.race=applySummaryEnvironment(body);
      instantTrackDetails[id]=state.race;saveDetailCache(id,state.race);
      // v237: live/result refresh must never close or replace the panel the user opened.
      render()
    }).catch(function(){scheduleResultRefresh()})
  },wait)
}

function refreshPayoutsOnly(attempt){
  var r=state.race;
  if(!r||!r.id||state.payoutBusy)return;
  state.payoutBusy=true;
  fetchEdgeRace(r.id,true)
    .then(function(body){
      if(!body||!state.race||String(state.race.id)!==String(r.id))return;
      state.race=applySummaryEnvironment(body);
      saveDetailCache(r.id,state.race);
      render()
    })
    .catch(function(){})
    .finally(function(){state.payoutBusy=false})
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
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  state.oddsBusy=false;
  if(state.environmentTimer){clearTimeout(state.environmentTimer);state.environmentTimer=null}
  // v235: when moving with the race < / > controls, keep the currently selected panel.
  // Normal venue/top selections still open the racecard first.
  var preservedPanel=preservePanel?(state.openPanel||'entry'):null;
  state.openPanel=preservedPanel||'entry';
  var seq=++state.detailSeq;
  if(!keepStack){state.raceStack=[];state.raceReturnPicker=state.picker}
  state.horseModalNo=null;state.detailHorseNo=null;
  if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
  state.error=null;
  state.picker=false;
  state.scenarioCode=null;
  state.paceStage=0;

  var cached=instantTrackDetails[String(id)]||loadDetailCache(id);
  var hasCached=!!(cached&&raceDisplayCoreReady(cached,(state.races||[]).find(function(x){return String(x&&x.id||'')===String(id)})||cached));

  if(hasCached){
    state.raceLoading=null;
    state.race=applySummaryEnvironment(cached);
    render();
    if(String(cached.date||'')===today()){
      fetchEdgeRace(id,true).then(function(body){
        if(seq!==state.detailSeq||!body||!state.race||String(state.race.id)!==String(id))return;
        var beforeFinal=isFinal(state.race),afterFinal=isFinal(body);
        state.race=applySummaryEnvironment(body);
        instantTrackDetails[String(id)]=state.race;
        saveDetailCache(id,state.race);
        // v237: keep the current panel even when final/result data arrives in the background.
        render()
      }).catch(function(){})
    }
    return
  }

  state.raceLoading=String(id);
  state.race=null;
  render();

  fetchEdgeRace(id)
    .then(function(body){
      if(seq!==state.detailSeq)return;
      if(!body)throw Error('edge detail missing');
      state.raceLoading=null;
      state.race=applySummaryEnvironment(body);
      instantTrackDetails[String(id)]=state.race;
      saveDetailCache(id,state.race);
      render()
    })
    .catch(function(){
      if(seq!==state.detailSeq)return;
      state.raceLoading=null;
      var fallback=instantTrackDetails[String(id)]||loadDetailCache(id);
      if(fallback){
        state.race=applySummaryEnvironment(fallback);
        render();
        return
      }
      state.error='詳細データを取得できませんでした。再試行してください。';
      state.raceLoading=String(id);
      render()
    })
}
function openPastRace(id){if(!id)return;if(state.race)state.raceStack.push(state.race);openRace(id,true,true)}
function reloadCurrent(){
  if(state.loading)return;

  if(state.race&&state.race.id){
    var id=state.race.id,previous=state.race,seq=++state.detailSeq;
    state.raceLoading=String(id);
    state.race=null;
    render();

    fetchEdgeRace(id,true)
      .then(function(body){
        if(seq!==state.detailSeq)return;
        state.raceLoading=null;
        if(body){
          state.race=applySummaryEnvironment(body);
          instantTrackDetails[String(id)]=state.race;
          saveDetailCache(id,state.race);
        }else{
          state.race=previous;
          state.error='Cloudflare同期待ちです。'
        }
        render()
      })
      .catch(function(){
        if(seq!==state.detailSeq)return;
        state.raceLoading=null;
        state.race=previous;
        state.error='更新に失敗しました';
        render()
      });
    return
  }

  try{localStorage.removeItem(cacheKey(state.date,state.circuit))}catch(e){}
  state.races=[];
  load(true)
}
function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,predictionInputChanged=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h,old;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){if(String(h.winOdds||'')!==String(z.winOdds))changed=true;h.winOdds=z.winOdds}if(z.popularity!=null&&String(z.popularity)!==''){if(String(h.popularity||'')!==String(z.popularity))changed=true;h.popularity=z.popularity}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){old=String(h.bodyWeight||'');if(old!==String(z.bodyWeight)){changed=true;predictionInputChanged=true}h.bodyWeight=z.bodyWeight}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){old=String(h.bodyWeightChange||'');if(old!==String(z.bodyWeightChange)){changed=true;predictionInputChanged=true}h.bodyWeightChange=z.bodyWeightChange}if(z.status!=null&&String(z.status)!==''){old=String(h.status||'');if(old!==String(z.status)){changed=true;predictionInputChanged=true}h.status=z.status}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;if(predictionInputChanged){try{delete state.race._prediction}catch(e){}state.pred=null;state.analysisSaved={}}return changed}
function refreshRaceAfterCollect(id,attempt){reloadCurrent()}
function collectRaceInfo(no){reloadCurrent()}
function stopTimer(){if(state.timer){clearTimeout(state.timer);state.timer=null}if(state.anim){cancelAnimationFrame(state.anim);state.anim=null}state.simRunning=false}
function drawPaceStage(idx){if(!state.race||!state.pred)return;var plan=activeScenarioPlan(state.pred);if(!plan||!plan.stages)return;var stages=visiblePaceStages(plan),st=stages[clamp(idx,0,stages.length-1)],r=state.race,board=document.getElementById('pace-board');if(!st||!board)return;state.paceStage=clamp(idx,0,stages.length-1);var order=[],i,z,chip,left,top,rank,rowIdx;for(i=0;i<st.pack.length;i++){z=st.pack[i];rank=i;rowIdx=rank%4;chip=board.querySelector('[data-horse="'+z.no+'"]');if(!chip)continue;left=clamp(90-rank*5.9-n(z.gap)*58,8,92);top=clamp(16+rowIdx*20+n(z.lane)*2.4,12,88);chip.style.left=left+'%';chip.style.top=top+'%';order.push(z.no)}var label=st.key==='turn3'?'3C':(st.key==='turn4'?'4C':st.label),ob=document.getElementById('course-order');if(ob)ob.innerHTML='<b>'+esc(label)+'</b><span>'+order.map(function(no){var h=horseByNo(r,no);return esc(no)+(h?' '+esc(h.name):'')}).join(' → ')+'</span>';var ev=document.getElementById('pace-event');if(ev)ev.innerHTML=stageNarrative(state.pred,idx);var bs=document.querySelectorAll('[data-pace-stage]');for(i=0;i<bs.length;i++)bs[i].className=n(bs[i].getAttribute('data-pace-stage'))===idx?'active':''}
function render(){var savedY=window.scrollY;syncLocation();stopTimer();try{var view=state.raceLoading?renderRaceLoading():(state.race?renderRace():(state.picker?renderPicker():(state.track?renderVenue():renderHome())));app.innerHTML=view+smartTodayReturn();syncLiveCenterOverlay();bind();if(state.race){initPaceBoard();scheduleResultRefresh();ensureAutoOdds(state.race);scheduleRaceBiasRefresh(700)}else if(state.track&&!state.picker){scheduleVenueTrendRefresh(350)}window.scrollTo(0,savedY)}catch(e){app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(e&&e.message||e)+'<br><button onclick="location.reload()">再読み込み</button></div>'}}
function canGoBack(){return !!(state.horseModalNo||state.raceLoading||state.race||state.picker||state.track)}
function goBack(){
    if(!canGoBack())return;
    if(state.horseModalNo){closeHorseModal();return}
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
        // Venue full race list returns to the top venue list.
        state.track=null;
        state.picker=false
    }

    // Do not use browser history for the × button; keep app hierarchy deterministic.
    routeKey=null;
    render();
    window.scrollTo(0,0)
}
var navigationRestoring=false,routeKey=null;
function locationState(){return {tab:state.detailTab||'出走表',date:state.date,circuit:state.circuit,track:state.track,picker:state.picker,race_id:String(state.raceLoading||(state.race&&state.race.id)||''),horse:null,stack:state.raceStack.map(function(r){return r.id}),returnPicker:state.raceReturnPicker}}
function syncLocation(){if(navigationRestoring||!window.history)return;var view=locationState(),key=JSON.stringify(view);if(key===routeKey)return;var u=new URL(window.location.href);u.pathname=view.race_id?'/race':(view.track?'/venue':'/');['date','circuit','track','race_id','horse','tab'].forEach(function(k){if(view[k])u.searchParams.set(k,view[k]);else u.searchParams.delete(k)});if(view.picker)u.searchParams.set('picker','1');else u.searchParams.delete('picker');u.searchParams.delete('pwa');var prior=window.history.state||{},depth=n(prior.keibaDepth);if(routeKey===null)window.history.replaceState({keibaDepth:depth,view:view},'',u);else window.history.pushState({keibaDepth:depth+1,view:view},'',u);routeKey=key}
function normalizeInitialAppLaunch(){
  try{
    var standalone=!!((window.matchMedia&&window.matchMedia('(display-mode: standalone)').matches)||window.navigator.standalone===true);
    if(!standalone)return;
    var u=new URL(window.location.href),t=today(),d=u.searchParams.get('date');
    // A fresh ARVEXQ app launch always starts from today's home. Historical
    // navigation inside the running app is still preserved and has the 今日へ button.
    if(d&&d!==t){
      u.searchParams.set('date',t);
      ['race_id','track','picker','horse','tab'].forEach(function(k){u.searchParams.delete(k)});
      window.history.replaceState({},'',u.pathname+(u.searchParams.toString()?'?'+u.searchParams.toString():'')+u.hash);
    }
  }catch(e){}
}
function restoreLocation(){var u=new URL(window.location.href),saved=(window.history.state||{}).view||{},id=u.searchParams.get('race_id');navigationRestoring=true;++state.detailSeq;state.raceLoading=null;state.race=null;state.horseModalNo=n(u.searchParams.get('horse'))||null;state.detailTab=u.searchParams.get('tab')||'出走表';state.date=u.searchParams.get('date')||today();state.circuit=u.searchParams.get('circuit')||'中央';state.track=u.searchParams.get('track')||null;state.picker=u.searchParams.get('picker')==='1';state.raceReturnPicker=!!saved.returnPicker;state.raceStack=(saved.stack||[]).map(loadDetailCache).filter(Boolean);if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}var horse=state.horseModalNo;if(id){var cached=loadDetailCache(id);if(cached){state.race=cached;render()}else{openRace(id,true,true);state.horseModalNo=horse}}else render();navigationRestoring=false;routeKey=null;syncLocation()}
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

function bind(){document.querySelectorAll('[data-selected-section]').forEach(function(el){el.ontoggle=function(){var k=el.getAttribute('data-selected-section');if(k==='selected')selectedSectionsOpen[k]=!!el.open}});document.querySelectorAll('[data-selected-circuit]').forEach(function(el){el.ontoggle=function(){var k=el.getAttribute('data-selected-circuit'),c=el.getAttribute('data-pick-circuit');if(k==='selected'&&(c==='中央'||c==='地方'))selectedCircuitSectionsOpen[k][c]=!!el.open}});document.querySelectorAll('[data-panel]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}var key=el.getAttribute('data-panel'),opening=state.openPanel!==key;if(key==='detail'&&state.race&&!state.detailHorseNo){var hs=(state.race.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)});if(hs.length)state.detailHorseNo=n(hs[0].horseNumber)}state.openPanel=opening?key:null;render();if(opening&&key==='result'&&state.race&&isFinal(state.race)&&!(((state.race.result||{}).payouts||[]).length))setTimeout(function(){refreshPayoutsOnly(0)},0)}});document.querySelectorAll('[data-action="odds-update"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}refreshOddsOnly(true)}});document.querySelectorAll('[data-action="copy-bet"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}copyCurrentBet()}});document.querySelectorAll('[data-action="live-open"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}liveCenterOpen=true;liveCenterTrack='';liveCenterCircuit='';render()}});document.querySelectorAll('[data-action="live-close"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}liveCenterOpen=false;render();setTimeout(fastReflectNow,150)}});document.querySelectorAll('[data-action="today-return"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}returnToToday()}});document.querySelectorAll('[data-live-track]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}liveCenterTrack=this.getAttribute('data-live-track')||'';liveCenterCircuit=this.getAttribute('data-live-circuit')||'';render()}});document.querySelectorAll('[data-dashboard-tab]').forEach(function(el){el.onclick=function(){state.detailTab=el.getAttribute('data-dashboard-tab');var id=el.getAttribute('data-tab-race');if(state.race&&String(state.race.id)===id)render();else openRace(id,false,false)}});document.querySelectorAll('.cinema-venue img').forEach(function(img){img.onerror=function(){this.style.display='none';var parent=this.parentElement;if(parent&&!parent.querySelector('.venue-photo-missing')){var label=document.createElement('span');label.className='venue-photo-missing';label.textContent='写真を読み込めません';parent.appendChild(label)}}});document.querySelectorAll('[data-date]').forEach(function(el){el.onclick=function(){++state.detailSeq;state.raceLoading=null;state.date=el.getAttribute('data-date');state.openPanel=null;state.race=null;state.track=null;state.picker=false;load()}});document.querySelectorAll('[data-detail-tab]').forEach(function(el){el.onclick=function(){state.detailTab=el.getAttribute('data-detail-tab');render()}});var els=document.querySelectorAll('[data-circuit]'),i;for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.circuit=this.getAttribute('data-circuit');state.openPanel=null;state.track=null;state.race=null;state.picker=false;load()};var d=document.getElementById('date');if(d)d.onchange=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.date=this.value;state.openPanel=null;state.track=null;state.race=null;state.picker=false;load()};els=document.querySelectorAll('[data-track]');for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.race=null;state.pred=null;state.picker=false;state.track=this.getAttribute('data-track');var dc=this.getAttribute('data-circuit');if(dc)state.circuit=dc;state.openPanel=null;state.detailTab='出走表';mergeCachedVolatilityForTrack(state.track);window.scrollTo(0,0);render()};els=document.querySelectorAll('[data-race]');for(i=0;i<els.length;i++)els[i].onclick=function(){var id=this.getAttribute('data-race'),row=state.races.find(function(x){return String(x.id)===String(id)}),preserve=this.getAttribute('data-preserve-panel')==='1';if(row){state.track=row.track;if(row.circuit)state.circuit=row.circuit}window.scrollTo(0,0);openRace(id,false,false,preserve)};els=document.querySelectorAll('[data-past-race]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openPastRace(this.getAttribute('data-past-race'))};var b=document.querySelectorAll('[data-action="back"]');for(i=0;i<b.length;i++)b[i].onclick=goBack;var rr=document.querySelectorAll('[data-action="reload"]');for(i=0;i<rr.length;i++)rr[i].onclick=reloadCurrent;var fi=document.querySelectorAll('[data-action="fetch-all-info"]');for(i=0;i<fi.length;i++)fi[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(null)};var rh=document.querySelectorAll('[data-action="retry-history"]');for(i=0;i<rh.length;i++)rh[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(null)};els=document.querySelectorAll('[data-horse-fetch]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(this.getAttribute('data-horse-fetch'))};var ar=document.querySelectorAll('[data-action="all-races"]');for(i=0;i<ar.length;i++)ar[i].onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};var pn=document.querySelector('[data-action="pace-next"]');if(pn)pn.onclick=function(){var x=nextRace();if(x){openRace(x.id,false,false,true)}};var pp=document.querySelector('[data-action="pace-pick"]');if(pp)pp.onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};els=document.querySelectorAll('[data-horse-check]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}if(state.race)toggleHorseChecked(state.race,this.getAttribute('data-horse-check'))};els=document.querySelectorAll('[data-horse-open]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openHorseModal(this.getAttribute('data-horse-open'))};els=document.querySelectorAll('[data-detail-horse]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.detailHorseNo=n(this.getAttribute('data-detail-horse'));state.openPanel='detail';render();var panel=document.getElementById('section-detail');if(panel)setTimeout(function(){panel.scrollIntoView({block:'start',behavior:'smooth'})},0)};els=document.querySelectorAll('[data-detail-prev]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveDetailHorse(-1)};els=document.querySelectorAll('[data-detail-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveDetailHorse(1)};els=document.querySelectorAll('[data-horse-close]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}closeHorseModal()};els=document.querySelectorAll('[data-horse-prev]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(-1)};els=document.querySelectorAll('[data-horse-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(1)};els=document.querySelectorAll('[data-scenario-code]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.scenarioCode=this.getAttribute('data-scenario-code');state.paceStage=0;render()};els=document.querySelectorAll('[data-pace-stage]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}drawPaceStage(n(this.getAttribute('data-pace-stage'),0))};var board=document.getElementById('pace-board');if(board){board.onclick=function(e){if(e&&e.target&&e.target.closest&&e.target.closest('button,a,input,select,textarea'))return;var rect=board.getBoundingClientRect(),plan=activeScenarioPlan(state.pred),len=(plan&&plan.stages?plan.stages.length:0);if(!len)return;var cur=n(state.paceStage,0),dir=(e.clientX-rect.left)<rect.width/2?-1:1,nx=(cur+dir+len)%len;drawPaceStage(nx)}}var panel=document.getElementById('horse-modal-panel');if(panel){panel.onclick=function(e){if(e&&e.target&&e.target.closest&&e.target.closest('button,a,input,select,textarea,summary'))return;var rect=panel.getBoundingClientRect();moveHorseModal((e.clientX-rect.left)<rect.width/2?-1:1)}}}
function initPaceBoard(){if(!state.pred)return;var plan=activeScenarioPlan(state.pred),stages=visiblePaceStages(plan);if(!stages.length)return;drawPaceStage(clamp(state.paceStage,0,stages.length-1))}

function hydrateInstantFromDevice(rows){
  var count=0;
  (rows||[]).forEach(function(r){
    if(!r||!r.id)return;
    var d=loadDetailCache(r.id);
    if(d){instantTrackDetails[String(r.id)]=d;count++}
  });
  return count
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
      if(d.volatility)r.volatility=d.volatility;
      if(d.weather&&d.weather!=='不明')r.weather=d.weather;
      if(d.condition&&d.condition!=='不明')r.condition=d.condition;
      if(d.oddsUpdatedAt)r.oddsUpdatedAt=d.oddsUpdatedAt
    }else if(pvol[String(r.id)]){
      r.volatility=pvol[String(r.id)]
    }
  });
  return rows
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
      return fetch(
        '/api/v1/races?date='+encodeURIComponent(d)
        +'&circuit=&bundle=0&v=131&t='+Date.now(),
        {cache:'no-store'}
      )
      .then(function(res){
        if(!res.ok)throw Error('render-list '+res.status);
        return res.json()
      })
      .then(function(body){
        return Array.isArray(body)?body:(body.races||[])
      })
    })
    .then(function(rows){
      if(rows==null)return;
      if(seq!==state.requestSeq||state.date!==d)return;

      if(rows.length){
        var old={};
        state.races.forEach(function(r){
          if(r&&r.id)old[String(r.id)]=r
        });

        rows.forEach(function(r){
          var z=old[String(r.id)];
          if(!z)return;
          ['volatility','weather','condition','oddsUpdatedAt','environmentMeta']
            .forEach(function(k){
              if(z[k]!=null&&z[k]!==''&&z[k]!=='不明')r[k]=z[k]
            })
        });

        state.races=rows;
        saveRaceCache(d,'__ALL__',rows);
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
    detailsInFlight=true;
    selectedRacePreload.date=d;selectedRacePreload.fullLoading=true;selectedRacePreload.lastError='';
    selectedRacePreload.expectedCount=(state.races||[]).filter(function(r){return r&&r.id}).length;
    function scheduleTopRefresh(){
      if(selectedRacePreload.timer){clearTimeout(selectedRacePreload.timer);selectedRacePreload.timer=null}
      if(d===today())selectedRacePreload.timer=setTimeout(function(){
        if(liveCenterOpen){scheduleTopRefresh();return}
        if(seq===state.requestSeq&&state.date===d&&!state.race&&!state.track&&!state.picker)requestDetails(0)
      },300000)
    }
    fetch('https://kraiz-api.4b89h4fydd.workers.dev/api/day?date='+encodeURIComponent(d)+'&details=1&t='+Date.now(),{cache:'no-store'})
      .then(function(res){if(!res.ok)throw Error('cloudflare-details '+res.status);return res.json()})
      .then(function(body){
        if(seq!==state.requestSeq||state.date!==d)return;
        var details=(body&&body.details)||[],summaryRows=(body&&body.races)||[];
        if(summaryRows.length){
          var oldBy={};(state.races||[]).forEach(function(x){if(x&&x.id)oldBy[String(x.id)]=x});
          state.races=summaryRows.map(function(z){
            var old=oldBy[String(z.id)]||{},out=Object.assign({},old);
            Object.keys(z||{}).forEach(function(k){if(reflectUseful(z[k]))out[k]=z[k]});
            return out
          });
          saveRaceCache(d,'__ALL__',state.races)
        }
        var summaryBy={};(state.races||[]).forEach(function(x){if(x&&x.id)summaryBy[String(x.id)]=x});
        details.forEach(function(z){
          if(!z||!z.id)return;
          var id=String(z.id),old=instantTrackDetails[id]||loadDetailCache(id)||null;
          instantTrackDetails[id]=mergeRaceReflection(old,z,null,summaryBy[id]||null)
        });
        var ids=(state.races||[]).filter(function(r){return r&&r.id}).map(function(r){return String(r.id)}),loaded=0,analysisReady=0;
        ids.forEach(function(id){var z=instantTrackDetails[id];if(z&&raceDisplayCoreReady(z,summaryBy[id]||z)){loaded++;if(isFinal(z)||diagnosisCurrent(z))analysisReady++}});
        selectedRacePreload.expectedCount=ids.length||n(body&&body.raceCount,0);
        selectedRacePreload.loadedCount=loaded;
        selectedRacePreload.fullLoaded=!!ids.length&&loaded>=ids.length;
        selectedRacePreload.fullLoading=false;
        selectedRacePreload.analysisReady=analysisReady;
        lastDetailsAt=Date.now();
        render();scheduleTopRefresh()
      })
      .catch(function(err){
        if(seq!==state.requestSeq||state.date!==d)return;
        selectedRacePreload.fullLoading=false;selectedRacePreload.lastError=String(err&&err.message||err||'');
        if(attempt<1)setTimeout(function(){requestDetails(attempt+1)},900);else render()
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
installNavigation();installEdgeBack();installPwaCache();normalizeInitialAppLaunch();restoreLocation();setTimeout(load,0);
})();
