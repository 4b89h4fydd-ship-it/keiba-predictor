
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
function coursePathD(p){if(p.shape==="straight")return "M18 92 L182 92";if(p.shape==="round")return "M174 90 C174 42 142 18 97 18 C50 18 22 46 22 90 C22 134 50 162 97 162 C142 162 174 138 174 90 Z";if(p.shape==="long")return "M184 90 C184 53 160 34 126 34 L67 34 C34 34 16 54 16 90 C16 126 34 146 67 146 L126 146 C160 146 184 127 184 90 Z";if(p.shape==="boxy")return "M178 90 C178 57 158 36 130 32 L66 32 C36 36 20 58 20 90 C20 122 36 144 66 148 L130 148 C158 144 178 123 178 90 Z";if(p.shape==="pocket")return "M176 91 C176 52 151 29 116 27 L69 30 C36 33 18 56 20 91 C21 126 40 147 73 151 L124 147 C157 142 176 122 176 91 Z";if(p.shape==="spiral")return "M178 91 C178 52 154 31 118 29 L72 31 C38 33 18 56 20 91 C22 128 44 148 78 149 L125 145 C157 140 178 120 178 91 Z";if(p.shape==="egg")return "M177 91 C177 49 147 25 106 24 C66 23 31 43 21 78 C11 113 31 146 71 154 C115 162 158 142 174 111 C178 103 179 97 177 91 Z";return "M176 90 C176 51 151 28 116 28 L72 28 C38 28 20 51 20 90 C20 129 38 152 72 152 L116 152 C151 152 176 129 176 90 Z"}
function normFrac(x){x=x%1;return x<0?x+1:x}
function courseStageFrac(r,st){var p=courseProfile(r);if(p.shape==="straight")return st===0?.05:(st===1?.67:.92);var laps=Math.max(.1,n(r.distance,1200)/p.lap),start=normFrac(.965-p.dir*(laps%1)),prog=st===0?.015:(st===1?.81:.965);return normFrac(start+p.dir*laps*prog)}
var app=document.getElementById("app");
var state={date:today(),circuit:"地方",races:[],track:null,race:null,raceLoading:null,picker:false,loading:false,error:null,timer:null,anim:null,simSpeed:5,simTarget:20,simRunning:false,simPaused:false,simStopped:false,simIndex:0,simDone:0,simCounts:null,simCurrentT:0,pred:null,requestSeq:0,detailSeq:0,raceReturnPicker:false,historyTimer:null,raceStack:[],historyPrefetch:{},paceStage:0,horseModalNo:null,collectingHorse:null,collectTimer:null,scenarioCode:null,analysisSaved:{},openPanel:null,oddsBusy:false,oddsRefreshAt:{},oddsTimer:null,environmentTimer:null,environmentBusy:false,bootstrapReady:false,bootstrapProgress:null};
var autoDiagnosisJobs={},autoDiagnosisAttempts={};


function cacheKey(d,c){return "keiba:v86:races:"+d+":"+(c||state.circuit||"")}
function loadRaceCache(d,c){try{var raw=localStorage.getItem(cacheKey(d,c));if(!raw)return null;var x=JSON.parse(raw);if(!x||!Array.isArray(x.rows))return null;if(d>=today()&&Date.now()-n(x.ts)>90*60000)return null;return x.rows}catch(e){return null}}
function saveRaceCache(d,c,rows){try{localStorage.setItem(cacheKey(d,c),JSON.stringify({ts:Date.now(),rows:rows}))}catch(e){}}
function fullBundleKey(d){return "kraiz:v128:fullbundle:"+String(d||"")}
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
    if(d>=today()&&age>6*3600000)return null;
    return x.body
  }catch(e){return null}
}
function detailCacheKey(id){return "keiba:v90:detail:"+String(id||"")}
function loadDetailCache(id){try{var raw=localStorage.getItem(detailCacheKey(id));if(!raw)return null;var x=JSON.parse(raw);if(!x||!x.row)return null;var age=Date.now()-n(x.ts);if(x.row.date>=today()&&age>12*3600000)return null;var r=x.row,hs=r&&r.horses||[];if(!hs.length)return null;return r}catch(e){return null}}
function saveDetailCache(id,row){try{if(!id||!row)return;var hs=row.horses||[];if(!hs.length)return;localStorage.setItem(detailCacheKey(id),JSON.stringify({ts:Date.now(),row:row}))}catch(e){}}
function installPwaCache(){
  try{if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js',{scope:'/'}).then(function(reg){reg.update().catch(function(){})}).catch(function(){})}catch(e){}
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
function sourceCollectionSection(h,r){var src=(r.dataSources||[]).slice(),es=h.collectionState||{},ped=h&&h.pedigree||{},sm=h&&h.smartRc||{},busy=es.status==='running',hasBase=!!(h&&(h.name||h.jockey||h.trainer)),hasRich=!!(h&&((h.recentRaces||[]).length||ped.sire||ped.dam||ped.damsire||Object.keys(sm).length||h.owner||h.producer||h.debutNoHistory||Object.keys(h.extraSources||{}).length)),txt=busy?'取得中':(hasRich||es.status==='complete'?'取得済':(es.status==='error'?'再取得可':(hasBase?'基本情報取得済':'未取得')));return'<div class="detail-heading">情報取得</div><button type="button" class="horse-fetch-btn" data-horse-fetch="'+esc(h.horseNumber)+'">'+(busy?'取得中…':'この馬の情報取得')+'</button><div class="horse-fetch-note">JRA/NAR公式を優先し、netkeiba・SmartRc・設定済み補助ソースを横断。新馬は過去走0件でも正常、障害は障害実績を優先します。</div><div class="source-strip"><span class="source-chip '+(busy?'busy':(hasRich||es.status==='complete'?'good':'neutral'))+'">'+esc(txt)+'</span>'+src.map(function(z){return'<span class="source-chip good">'+esc(z)+'</span>'}).join('')+'</div>'+(es.error?'<div class="muted">'+esc(es.error)+'</div>':'')}
function raceSourceStrip(r){var src=r.dataSources||[],es=r.enrichmentSearch||{},chips=[];for(var i=0;i<src.length;i++)chips.push('<span class="source-chip good">'+esc(src[i])+'</span>');if(!chips.length)chips.push('<span class="source-chip neutral">自動取得待ち</span>');if(es.status==='running')chips.unshift('<span class="source-chip busy">情報取得中</span>');return'<div class="source-strip">'+chips.join('')+'</div>'}
function horseByNo(r,no){var hs=r.horses||[],i;for(i=0;i<hs.length;i++)if(n(hs[i].horseNumber)===n(no))return hs[i];return null}
function isFinal(r){return !!(r&&r.result&&(r.result.status==="確定"||(r.result.finishers||[]).length))}
function mins(t){var m=String(t||"").match(/^(\d{1,2}):(\d{2})/);return m?n(m[1])*60+n(m[2]):9999}
function nowMins(){var d=new Date(Date.now()+9*3600000);return d.getUTCHours()*60+d.getUTCMinutes()}
function timeHtml(r){var a=String(r.startTime||"—"),o=String(r.scheduledStartTime||a),c=!!r.startTimeChanged||(a!==o&&a!=="—"&&o!=="—");return c?'<span class="time-old">'+esc(o)+'</span><span class="time-changed">'+esc(a)+' 修正</span>':esc(a)}
function header(title,back,sub){return '<header class="header"><div class="header-row">'+(back?'<button data-action="back">‹</button>':'')+'<div class="header-title"><h1>'+esc(title)+'</h1>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div><span class="build-badge" aria-label="KRAIZ">KRAIZ</span><button data-action="reload">↻</button></div></header>'}
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
function earlyCollapseSeverity(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),vals=[],ws=[],i,p,a,fin,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||a>4||!fin)continue;vals.push(clamp((fin-a)/Math.max(3,fs-1),0,1));ws.push(w[i])}return weightedRate(vals,ws,.18)}
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
function weightScore(h){var rs=(h.recentRaces||[]).slice(0,3),vals=[],i;for(i=0;i<rs.length;i++)if(n(rs[i].carriedWeight)>0)vals.push(n(rs[i].carriedWeight));if(!vals.length||!n(h.carriedWeight))return.5;var avg=mean(vals),diff=n(h.carriedWeight)-avg;return clamp(.55-diff*.035,.28,.72)}
function conditionFit(h,r){var pc=h&&h.precomputedMetrics&&h.precomputedMetrics.fit;if(pc&&pc.counts)return pc;var c=contextualRuns(h,r);return{track:listQuality(c.track,n(r.distance)),distance:listQuality(c.distance,n(r.distance)),condition:listQuality(c.condition,n(r.distance)),weather:listQuality(c.weather,n(r.distance)),season:listQuality(c.season,n(r.distance)),level:listQuality(c.level,n(r.distance)),counts:{track:c.track.length,distance:c.distance.length,condition:c.condition.length,weather:c.weather.length,season:c.season.length,level:c.level.length}}}
function confidenceBlend(score,count){var q=clamp(n(count)/3,0,1);return .5*(1-q)+score*q}
function buildRows(r){var hs=r.horses||[],tmp=[],speeds=[],prizes=[],i,h,rt,pt,sr,fit,ct=courseTraits(r),cp=courseProfile(r),field=Math.max(1,hs.length);for(i=0;i<hs.length;i++){h=hs[i];rt=styleRates(h,r);pt=rt.samples?stylePoint(rt):9;sr=speedRaw(h,n(r.distance));fit=conditionFit(h,r);var cf=rt.samples?rt.front:.08,cs=rt.samples?rt.stalk:.28,cm=rt.samples?rt.mid:.40,cc=rt.samples?rt.close:.24,ce=rt.samples?rt.early3:.24,cmo=rt.samples?rt.moved3:.08;tmp.push({horse:h,front:cf,stalk:cs,mid:cm,close:cc,rawFront:rt.front,rawStalk:rt.stalk,rawMid:rt.mid,rawClose:rt.close,early3:ce,moved3:cmo,styleSamples:rt.samples,styleUnknown:!rt.samples,ten:tenScore(h,r),fade:fadeRate(h),move:moveRate(h),hold:holdRate(h),yieldFlex:yieldFlex(h),breakRel:breakReliability(h),lateGain:lateGainScore(h),posCons:positionConsistency(h),collapse:earlyCollapseSeverity(h),score:pt,pastStyle:rt.samples?styleName(pt):"履歴なし",expected:rt.samples?styleName(pt):"不明",speedRaw:sr,fit:fit});speeds.push(sr);prizes.push(n(h.prizeMoneyAtRace))}
for(i=0;i<tmp.length;i++){var x=tmp[i],hh=x.horse,rf=recentFirst(hh),rd=recentDistance(hh),distChange=rd?rd-n(r.distance):0,shorten=distChange>=150?1:0,lengthen=distChange<=-150?1:0,no=n(hh.horseNumber),draw=(no-1)/Math.max(1,field-1),outer=draw>.70?1:0,edge=no===field?1:0,inner=draw<.28?1:0,recentEarly=(rf<99?clamp((8-rf)/7,0,1):.5),jp=hh.jockeyProfile||{},jockeyFront=n(jp.early3Rate,0),leadHabit=n(jp.leaderRate,0),needLead=clamp(x.front*.78+Math.max(0,x.front-x.stalk)*.48+leadHabit*.10,0,1),flexibility=clamp(x.yieldFlex*.58+x.stalk*.25+x.mid*.12+(1-needLead)*.05,0,1),shortenBoost=shorten*(x.front*.12+x.stalk*.08+x.ten*.07),lengthenBoost=lengthen*(x.stalk*.05+x.mid*.06),firstTurnRush=clamp(1-n(cp.firstTurn,300)/650,0,1),outerStress=outer*firstTurnRush*ct.turnLoad*(edge?.45:1),drawAdj=inner*ct.turnLoad*.055+edge*(1-ct.outerLoad)*.055-outerStress*.095,jf=hh.jockeyProfile?roleProfileScore(hh.jockeyProfile):genericRoleScore(hh.jockeyStats),tf=hh.trainerProfile?roleProfileScore(hh.trainerProfile):genericRoleScore(hh.trainerStats),trackFit=confidenceBlend(x.fit.track,x.fit.counts.track),distFit=confidenceBlend(x.fit.distance,x.fit.counts.distance),condFit=confidenceBlend(x.fit.condition,x.fit.counts.condition),weatherFit=confidenceBlend(x.fit.weather,x.fit.counts.weather),seasonFit=confidenceBlend(x.fit.season,x.fit.counts.season),levelFit=confidenceBlend(x.fit.level,x.fit.counts.level),speed=normalize(speeds,x.speedRaw),prize=normalize(prizes,n(hh.prizeMoneyAtRace)),baseAbility=recentFinishScore(hh)*.20+speed*.18+distFit*.11+trackFit*.08+condFit*.07+levelFit*.10+prize*.06+jf*.07+tf*.035+seasonFit*.02+weatherFit*.015+weightScore(hh)*.035+ageSexScore(hh,r)*.025+x.lateGain*.025,dataN=Math.min(8,(hh.recentRaces||[]).length),coverage=clamp(dataN/5,0,1)*.60+clamp((x.fit.counts.distance+x.fit.counts.track)/4,0,1)*.22+clamp(n(jp.starts)/30,0,1)*.18,frontIntent=clamp(x.front*.36+x.stalk*.17+x.ten*.18+x.early3*.10+jockeyFront*.07+leadHabit*.05+needLead*.07,0,1.25),goBase=clamp(frontIntent+shortenBoost+lengthenBoost+drawAdj,0,1.25);x.forward=frontIntent;x.goProbBase=clamp(goBase*.72+x.breakRel*.14+x.ten*.14,0,1);x.goProb=x.goProbBase;x.needLead=needLead;x.flexibility=flexibility;x.ability=clamp(baseAbility*.90+x.posCons*.035+(1-x.collapse)*.035+x.lateGain*.03,0,1);x.speedScore=speed;x.prizeScore=prize;x.jockeyScore=jf;x.trainerScore=tf;x.trackFit=trackFit;x.distFit=distFit;x.condFit=condFit;x.weatherFit=weatherFit;x.seasonFit=seasonFit;x.levelFit=levelFit;x.weightSuit=weightScore(hh);x.ageSexSuit=ageSexScore(hh,r);x.coverage=coverage;x.draw=draw;x.outer=outer;x.edge=edge;x.inner=inner;x.outerStress=outerStress;x.shorten=shorten;x.lengthen=lengthen;x.distanceChange=distChange;x.course=ct;x.jockeyFront=jockeyFront;x.stamina=clamp((1-x.fade)*.35+x.hold*.26+distFit*.15+x.posCons*.10+x.ability*.09+(rd>n(r.distance)?.05:0),0,1);x.holdFront=clamp(x.hold*.33+(1-x.fade)*.30+x.stamina*.15+x.ability*.12+distFit*.06+ct.frontBias*.04,0,1);x.latePower=clamp(x.lateGain*.28+x.move*.25+x.close*.14+x.mid*.07+x.ability*.18+(1-x.fade)*.08,0,1);x.turnSkill=clamp(trackFit*.22+x.move*.18+x.flexibility*.18+x.posCons*.16+(1-ct.turnLoad)*.06+x.ability*.20,0,1);x.breakSkill=clamp(x.breakRel*.32+x.ten*.30+x.goProbBase*.20+recentEarly*.10+jockeyFront*.08,0,1);x.trafficTol=clamp(x.flexibility*.34+x.move*.24+x.posCons*.18+x.turnSkill*.18+x.lateGain*.06,0,1)}
var p0=pressureInfo(tmp);for(i=0;i<tmp.length;i++){var y=tmp[i],q=p0[n(y.horse.horseNumber)]||{},pressurePenalty=(q.conflict||0)*(.055+.055*y.needLead)+(q.sandwich||0)*.075*(1-y.flexibility)+y.outerStress*.055;y.leftPressure=q.left||0;y.rightPressure=q.right||0;y.sandwichRisk=q.sandwich||0;y.frontCost=clamp(pressurePenalty,0,.28);y.goProb=clamp(y.goProbBase-pressurePenalty+(q.freeOuter||0)*.08,0,1);if(y.goProb>=.68&&y.front>=.16&&y.ten>=.55)y.expected="逃げ候補";else if(y.goProb>=.54)y.expected="先行";else if(y.goProb>=.40||y.stalk>=.32)y.expected="好位";else if(y.close>=.42&&y.mid<.36)y.expected="後方";else y.expected="中団";if(y.styleUnknown)y.expected="不明";y.frontStay=clamp(y.goProb*.34+y.holdFront*.34+(1-y.fade)*.12+y.ability*.12+y.course.frontBias*.08-y.frontCost*.30,0,1);y.comeFromBehind=clamp(y.latePower*.46+y.move*.20+y.ability*.16+y.course.moveRoom*.10+(1-y.goProb)*.08,0,1)}return tmp}
function rowByNo(rows,no){var i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===n(no))return rows[i];return null}
function pressureInfo(rows){var sorted=rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),p={},i,x,l,r,lp,rp,base;function attack(z){if(!z)return 0;base=z.goProbBase!=null?z.goProbBase:z.goProb;return clamp(base*(.46+.34*z.needLead+.20*z.ten),0,1.2)}for(i=0;i<sorted.length;i++){x=sorted[i];l=i?sorted[i-1]:null;r=i<sorted.length-1?sorted[i+1]:null;lp=attack(l);rp=attack(r);var leftHot=lp>.50,rightHot=rp>.50,sandwich=leftHot&&rightHot?1:0,adj=(leftHot?1:0)+(rightHot?1:0),near2=0;if(i>1)near2+=attack(sorted[i-2])*.16;if(i<sorted.length-2)near2+=attack(sorted[i+2])*.16;var conflict=(lp+rp)*(.43+.38*x.needLead+.19*x.ten)*(1-.42*x.flexibility)+near2,freeOuter=x.edge&&adj===0?(.08+.08*x.flexibility):0;p[n(x.horse.horseNumber)]={adj:adj,sandwich:sandwich,conflict:clamp(conflict,0,1.6),freeOuter:freeOuter,left:lp,right:rp,leftHot:leftHot,rightHot:rightHot}}return p}
function scenarioModel(r,rows){var p=pressureInfo(rows),front=rows.slice().sort(function(a,b){return b.goProb-a.goProb}),active=front.filter(function(x){return x.goProb>.50}),lead=front.filter(function(x){return x.goProb>.60&&x.ten>.52}),top=active.slice(0,Math.min(5,active.length)),fade=top.length?mean(top.map(function(x){return x.fade})):0,hold=top.length?mean(top.map(function(x){return x.holdFront})):0,conf=top.length?mean(top.map(function(x){return (p[n(x.horse.horseNumber)]||{}).conflict||0})):0,sand=top.length?mean(top.map(function(x){return (p[n(x.horse.horseNumber)]||{}).sandwich||0})):0,outer=top.length?mean(top.map(function(x){return x.outerStress||0})):0,flex=top.length?mean(top.map(function(x){return x.flexibility})):0,ct=rows.length?rows[0].course:courseTraits(r),clear=front.length>1?clamp((front[0].goProb-front[1].goProb)*1.8+front[0].holdFront*.10+(front[0].edge?0.04:0),0,.42):.25,adjPairs=0,i,j;for(i=0;i<active.length;i++)for(j=i+1;j<active.length;j++)if(Math.abs(n(active[i].horse.horseNumber)-n(active[j].horse.horseNumber))===1)adjPairs+=active[i].needLead*active[j].needLead;var adjDensity=active.length>1?clamp(adjPairs/(active.length-1),0,1):0,leadCount=lead.length,frontVolume=clamp(active.length/Math.max(1,rows.length),0,1),A=.29+ct.frontBias*.23+clear*.23+hold*.15+(1-fade)*.07+(1-clamp(conf,0,1))*.05-flex*.015,C=.18+(1-ct.frontBias)*.10+ct.moveRoom*.10+fade*.19+clamp(conf,0,1)*.13+sand*.10+adjDensity*.08+outer*.06+Math.max(0,leadCount-1)*.025,B=.34+flex*.07+(1-Math.abs(A-C))*.035;C+=Math.max(0,frontVolume-.45)*.055;A+=leadCount===1?.035:0;A=clamp(A,.15,.68);B=clamp(B,.20,.50);C=clamp(C,.12,.58);var sum=A+B+C;A/=sum;B/=sum;C/=sum;return[{code:"A",title:"前残り",prob:A},{code:"B",title:"平均",prob:B},{code:"C",title:"前崩れ・差し届く",prob:C}]}
function startOrder(rows){var p=pressureInfo(rows);return rows.slice().sort(function(a,b){function s(x){var q=p[n(x.horse.horseNumber)]||{};return x.goProb+x.needLead*.12+(q.freeOuter||0)-q.conflict*.035}return s(b)-s(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function scenarioSuit(x,code,pressure){var q=pressure[n(x.horse.horseNumber)]||{},earlyCost=(q.conflict||0)*x.goProb*(.34+.42*x.needLead)*(1-.34*x.flexibility)+x.outerStress*.06,frontStay=x.goProb*.27+x.holdFront*.31+(1-x.fade)*.12+x.ability*.18+x.stamina*.07+x.course.frontBias*.05-earlyCost*.16,balanced=x.ability*.34+x.holdFront*.14+x.latePower*.13+x.move*.10+x.stamina*.10+x.goProb*.08+x.flexibility*.06+(1-x.fade)*.05,close=x.ability*.27+x.latePower*.28+x.move*.17+x.mid*.08+x.close*.09+x.course.moveRoom*.07+x.trafficTol*.06-x.goProb*.02;if(code==="A")return clamp(frontStay,0,1.25);if(code==="C")return clamp(close,0,1.25);return clamp(balanced,0,1.25)}
function suitability(rows,sc){var out={},pressure=pressureInfo(rows),i,x,win,place,show,j,q,scenarioScores=[];for(i=0;i<rows.length;i++){x=rows[i];win=place=show=0;scenarioScores=[];for(j=0;j<sc.length;j++){q=scenarioSuit(x,sc[j].code,pressure);scenarioScores.push({code:sc[j].code,score:q});win+=sc[j].prob*(q*.72+x.ability*.20+x.hold*.08);place+=sc[j].prob*(q*.57+x.ability*.20+(1-x.fade)*.13+x.flexibility*.06+x.hold*.04);show+=sc[j].prob*(q*.46+x.ability*.20+(1-x.fade)*.14+x.move*.09+x.flexibility*.06+x.hold*.05)}var overall=win*.54+place*.29+show*.17;out[n(x.horse.horseNumber)]={win:win,place:place,show:show,overall:overall,rankScore:win*.62+place*.24+show*.14,scenario:scenarioScores}}return out}
function cornerScores(r,rows,sc,suit){var pressure=pressureInfo(rows),top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0].code,out=[],i,x,z,q,s,earlyCost;for(i=0;i<rows.length;i++){x=rows[i];z=suit[n(x.horse.horseNumber)]||{overall:.5};q=pressure[n(x.horse.horseNumber)]||{};earlyCost=q.conflict*x.goProb*(.4+.4*x.needLead);s=x.goProb*.25+x.hold*.20+x.ability*.21+x.move*.11+(1-x.fade)*.11+z.overall*.12-earlyCost*.10;if(top==="A")s+=x.goProb*.11+x.hold*.07;if(top==="C")s+=x.move*.12+x.mid*.06+x.close*.08-x.goProb*.02;out.push({row:x,s:s})}return out.sort(function(a,b){return b.s-a.s}).map(function(z){return z.row})}
function seedHash(v){var s=String(v||"race"),h=2166136261,i;for(i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function prng(seed){var a=seed>>>0;return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function jitter(rng){return(rng()+rng()+rng()+rng()+rng()+rng()-3)/3}
function chooseScenario(sc,rng){var u=rng(),c=0,i;for(i=0;i<sc.length;i++){c+=sc[i].prob;if(u<=c)return sc[i].code}return sc.length?sc[sc.length-1].code:"B"}
function packStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,visualRankGap,scoreGap,lane,cp=courseProfile(r);for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);visualRankGap=(stage<2?.0048:(stage<5?.0065:.0085))*i;scoreGap=diff*(stage<2?.030:(stage<5?.043:.060));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&visualRankGap<.02)lane+=((i%3)-1);out.push({no:no,gap:clamp(visualRankGap+scoreGap,0,.42),lane:clamp(lane,-3,3)})}return out}
function stageMap(pack){var o={},i;for(i=0;i<pack.length;i++)o[pack[i].no]=pack[i];return o}
function stageByNo(pack,no){for(var i=0;i<pack.length;i++)if(n(pack[i].no)===n(no))return pack[i];return null}
function simulateOne(r,rows,sc,suit,seed){var rng=prng(seed),code=chooseScenario(sc,rng),pressure=pressureInfo(rows),cp=courseProfile(r),ct=courseTraits(r),dist=n(r.distance,1200),distanceLoad=clamp((dist-1000)/1800,0,1),firstTurnRush=clamp(1-n(cp.firstTurn,300)/650,0,1),paceHeat=0,i,x,no,q,noise;var S0={},S1={},S2={},S3={},S4={},S5={},S6={},S7={},L0={},L1={},L2={},L3={},L4={},L5={},L6={},L7={},energy={};
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
function scenarioPlan(r,rows,sc,suit){var scenario=sc.slice().sort(function(a,b){return b.prob-a.prob})[0],code=scenario.code,p=pressureInfo(rows),ct=courseTraits(r),S=[{},{},{},{},{},{}],L=[{},{},{},{},{},{}],i,x,no,q,scfit,markScore={},leadLoad;for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=p[no]||{};leadLoad=x.goProb*(.045+.055*x.needLead)+x.frontCost*.13;S[0][no]=x.breakSkill*.26+x.ten*.26+x.goProb*.27+x.needLead*.08+x.jockeyFront*.05+(q.freeOuter||0)*.06-x.frontCost*.10;L[0][no]=clamp(Math.round((x.draw-.5)*5),-3,3);S[1][no]=S[0][no]*.40+x.goProb*.17+x.holdFront*.13+x.turnSkill*.11+x.flexibility*.06+x.ability*.08-x.frontCost*.09-x.outerStress*.05;L[1][no]=clamp(L[0][no]+(x.edge&&x.goProb>.55?-1:0)+(q.sandwich&&x.flexibility<.45?1:0),-3,3);scfit=scenarioSuit(x,code,p);S[2][no]=S[1][no]*.31+x.ability*.16+x.holdFront*.15+x.stamina*.13+x.stalk*.07+x.mid*.04+scfit*.11-(code==='C'?leadLoad*.12:leadLoad*.05)+(code==='A'?x.goProb*.06:0);L[2][no]=clamp(L[1][no]+(x.move>.52&&x.goProb<.46?1:0),-3,3);S[3][no]=S[2][no]*.27+x.ability*.16+x.move*.16+x.turnSkill*.11+scfit*.14+x.latePower*.09+x.holdFront*.04-(x.fade*x.goProb)*(code==='C'?.09:.04);L[3][no]=clamp(L[2][no]+(x.move>.56?1:0),-3,3);S[4][no]=S[3][no]*.24+scfit*.20+x.ability*.18+x.holdFront*.11+x.move*.10+x.latePower*.10+(1-x.fade)*.05-(q.sandwich||0)*.025;L[4][no]=clamp(L[3][no]+(x.latePower>.61?1:0),-3,3);var su=suit[no]||{rankScore:.5};markScore[no]=S[4][no]*.31+su.rankScore*.42+x.ability*.10+x.latePower*.08+x.stamina*.05+x.coverage*.02+(1-x.fade)*.02;if(code==='A')markScore[no]+=x.frontStay*.045;if(code==='C')markScore[no]+=x.comeFromBehind*.045;S[5][no]=markScore[no];L[5][no]=L[4][no]}var labels=['スタート','1コーナー','向正面','3コーナー','4コーナー','直線'],packs=[],stages=[];for(i=0;i<6;i++){packs[i]=packScenarioStage(r,rows,S[i],L[i],i);stages.push({key:['start','first','back','turn3','turn4','straight'][i],label:labels[i],pack:packs[i]})}return{scenario:scenario,stages:stages,start:rowsFromPack(rows,packs[0]),corner:rowsFromPack(rows,packs[4]),straight:rowsFromPack(rows,packs[5]),markScore:markScore}}
function gradeClass(g){return g==='S'?'grade-s':(g==='A'?'grade-a':(g==='B'?'grade-b':'grade-c'))}
function predictionProfile(r){
  var mode=raceMode(r);
  if(mode==='障害')return{code:'JUMP',label:'障害専用モデル',version:'KRAIZ-JUMP-v2'};
  if(mode==='新馬')return{code:'DEBUT',label:'新馬専用モデル',version:'KRAIZ-DEBUT-v2'};
  if(r.circuit==='地方')return{code:'NAR',label:'地方専用モデル',version:'KRAIZ-NAR-v2'};
  return{code:'JRA',label:'中央専用モデル',version:'KRAIZ-JRA-v2'}
}
function gradeRowsRelative(rows){
  if(!rows.length)return;
  var lo=Math.min.apply(null,rows.map(function(z){return z.overallRaw})),
      hi=Math.max.apply(null,rows.map(function(z){return z.overallRaw}));
  rows.forEach(function(z){
    var rel=hi===lo?.5:(z.overallRaw-lo)/(hi-lo);
    z.overallScore=Math.round(clamp(z.overallRaw*.80+(.44+.56*rel)*.20,0,1)*100)
  });
  rows.sort(function(a,b){return b.overallScore-a.overallScore||b.ability-a.ability||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
  var m=rows.length;
  rows.forEach(function(z,rank){
    var pct=(rank+1)/m,score=z.overallScore;
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
  if(x.frontCost>=.12)x.overallReasons.push('隣接圧力注意');
  if(x.fade>=.50)x.overallReasons.push('下がり率注意');
  if(x.coverage<.45)x.overallReasons.push('データ量少なめ・基礎評価');
  if((x.horse.recentRaces||[]).length<2||x.styleSamples<2)x.overallReasons.push('限定データ評価')
}
function assignOverallGradesCentral(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,fitScore,representative,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    fitScore=mean([n(x.distFit,.5),n(x.trackFit,.5),n(x.condFit,.5)]);
    representative=clamp(
      n(x.speedScore,.5)*.34+
      n(x.levelFit,.5)*.25+
      x.ability*.21+
      x.latePower*.12+
      x.posCons*.08,0,1
    );
    raw=
      representative*.28+
      x.ability*.20+
      n(su.overall,.5)*.18+
      n(x.levelFit,.5)*.09+
      n(x.distFit,.5)*.07+
      n(x.trackFit,.5)*.05+
      x.latePower*.05+
      x.stamina*.025+
      n(x.jockeyScore,.5)*.025+
      x.coverage*.025+
      (1-x.fade)*.025;
    x.representativeScore=representative;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(representative>=.64)x.overallReasons.push('代表走評価高め');
    if(n(x.levelFit)>=.60)x.overallReasons.push('相手レベル適性');
    if(x.latePower>=.62)x.overallReasons.push('終い性能');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}
function assignOverallGradesNar(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,q,fitScore,positionEdge,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};q=pressure[no]||{};
    fitScore=mean([n(x.distFit,.5),n(x.trackFit,.5),n(x.condFit,.5)]);
    positionEdge=clamp(
      x.goProb*.28+
      x.frontStay*.24+
      x.holdFront*.15+
      x.breakSkill*.10+
      n(x.jockeyFront,.0)*.08+
      (1-clamp(n(q.conflict),0,1))*.08+
      n(q.freeOuter,0)*.07,0,1
    );
    raw=
      positionEdge*.27+
      n(su.overall,.5)*.21+
      x.ability*.14+
      n(x.trackFit,.5)*.09+
      n(x.distFit,.5)*.06+
      n(x.jockeyScore,.5)*.06+
      x.posCons*.05+
      (1-x.fade)*.05+
      x.flexibility*.025+
      x.coverage*.025+
      n(x.condFit,.5)*.025+
      x.stamina*.025-
      x.frontCost*.045-
      x.outerStress*.025;
    x.positionEdge=positionEdge;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(positionEdge>=.63)x.overallReasons.push('隊列優位');
    if(n(x.trackFit)>=.60)x.overallReasons.push('同場適性');
    if(n(x.jockeyScore)>=.60)x.overallReasons.push('騎手条件プラス');
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

function assignPredictionMarks(rows,r){
  var sorted=rows.slice().sort(function(a,b){
    return n(b.overallScore)-n(a.overallScore)||
           n(b.ability)-n(a.ability)||
           Math.max(n(b.frontStay),n(b.comeFromBehind))-Math.max(n(a.frontStay),n(a.comeFromBehind))||
           n(b.posCons)-n(a.posCons)||
           n(b.coverage)-n(a.coverage)||
           n(b.styleSamples)-n(a.styleSamples)||
           n(a.horse.horseNumber)-n(b.horse.horseNumber)
  });
  var base=['◎','○','▲','☆','△'],i,x,fifth=sorted.length>=5?n(sorted[4].overallScore):0,candidates=[],
      provisional=!(r&&diagnosisCurrent(r));
  // 診断データが未完成でも、取得済みの能力・条件・オッズから必ず暫定印を出す。
  // 完全診断が到着したときは predict() の再計算で正式印へ更新する。
  for(i=0;i<sorted.length;i++){
    x=sorted[i];
    x.predRank=i+1;
    x.predMark=i<5?base[i]:'';
    x.predictionStage=provisional?'暫定':'正式';
    x.attentionReason='';
  }

  // 「注」は本当に拾う根拠がある馬だけ。0頭でもよい。最大2頭。
  for(i=5;i<sorted.length;i++){
    x=sorted[i];
    var score=n(x.overallScore),
        gap=Math.max(0,fifth-score),
        strengths=0,
        reasons=[],
        evidence=(n(x.coverage)>=.30)||(n(x.styleSamples)>=2)||((x.horse.recentRaces||[]).length>=2);

    if(n(x.ability)>=.62){strengths++;reasons.push('能力')}
    if(n(x.frontStay)>=.64){strengths++;reasons.push('前残り力')}
    if(n(x.comeFromBehind)>=.64){strengths++;reasons.push('差し込み力')}
    if(n(x.goProb)>=.60){strengths++;reasons.push('先行力')}
    if(n(x.styleSamples)>=2&&n(x.fade)<=.28){strengths++;reasons.push('下がり率低')}
    if((x.overallReasons||[]).some(function(z){return String(z).indexOf('今回条件に実績')>=0})){strengths++;reasons.push('条件実績')}

    var closeToTop=(score>=55&&fifth>=55&&gap<=4&&strengths>=1);
    var hiddenStrength=(gap<=10&&score>=55&&strengths>=2);
    if(evidence&&(closeToTop||hiddenStrength)){
      var attentionScore=score+strengths*2.5+n(x.coverage)*3-gap*.35;
      candidates.push({row:x,score:attentionScore,reasons:reasons})
    }
  }

  candidates.sort(function(a,b){return b.score-a.score||n(a.row.horse.horseNumber)-n(b.row.horse.horseNumber)});
  candidates.slice(0,2).forEach(function(z){
    z.row.predMark='注';
    z.row.attentionReason=z.reasons.slice(0,3).join('・')
  })
}
function raceMode(r){r=r||{};if(['平地','新馬','障害'].indexOf(r.analysisMode)>=0)return r.analysisMode;var title=String(r.title||'');if(r.surface==='障害'||/障害|J[･・.]?G[ⅠⅡⅢ123]|\bJS\b|ジャンプ/i.test(title))return '障害';return /新馬|メイクデビュー/.test(title)?'新馬':'平地'}
function saveRaceAnalysis(r,p){return}
function isScratchHorse(h){var s=String(h&&h.status||'');return !!(h&&(h.scratched===true||h.withdrawn===true||/欠場|取消|除外/.test(s)))}
function analysisRace(r){
  var active=(r.horses||[]).filter(function(h){return !isScratchHorse(h)}).map(function(h){
    var runs=h.allPastRuns||h.recentRaces||[];
    if(raceMode(r)==='障害')runs=runs.filter(function(z){return /障害|ジャンプ|J[・･.]?G|\bJS\b/i.test((z.surface||'')+(z.title||''))});
    return Object.assign({},h,{recentRaces:runs,allPastRuns:runs})
  });
  return Object.assign({},r,{horses:active,fieldSize:active.length||n(r.fieldSize)})
}
function integratedGrades(r,rows){
  var server=((r.aiEvaluation||{}).horses||[]);
  rows.forEach(function(x){
    var h=horseByNo(r,x.horse.horseNumber)||x.horse,no=n(h.horseNumber),e=h.integratedEvaluation||{},i,z;
    if(!e||e.score==null){
      for(i=0;i<server.length;i++){
        z=server[i]||{};
        if(n(z.horseNumber)===no){e=z;break}
      }
    }

    var modelScore=n(x.overallScore,50),
        modelGrade=x.overallGrade||'C',
        evidenceScore=(e&&e.score!=null&&!e.neutralPrior)?n(e.score):null,
        evidenceSamples=n(e&&e.samples,0),
        coverage=n(x.coverage,0),
        hasEvidence=evidenceScore!=null&&((e.components&&Object.keys(e.components).length)||evidenceSamples>0);

    // Specialized JRA/NAR/Jump/Debut model stays dominant.
    // Strong server evidence can refine a few points, never replace the model.
    var blend=0;
    if(hasEvidence){
      blend=coverage>=.70&&evidenceSamples>=4?.18:(coverage>=.45?.10:.05);
    }
    var finalScore=Math.round(clamp((modelScore/100)*(1-blend)+(hasEvidence?(evidenceScore/100)*blend:0),0,1)*100);

    x.modelScore=modelScore;
    x.evidenceScore=hasEvidence?evidenceScore:null;
    x.overallScore=finalScore;
    x.overallGrade=finalScore>=83?'S':(finalScore>=72?'A':(finalScore>=60?'B':'C'));
    x.evaluation=Object.assign({},hasEvidence?e:{},{
      score:finalScore,
      grade:x.overallGrade,
      modelScore:modelScore,
      evidenceScore:hasEvidence?evidenceScore:null,
      predictionModel:(predictionProfile(r)||{}).version||'',
      confidence:coverage>=.72?'高':(coverage>=.45?'中':'低'),
      tier:coverage>=.72?'フルデータ評価':(coverage>=.45?'限定データ評価':'基礎データ評価')
    });
    if(hasEvidence&&e.reasons&&e.reasons.length){
      x.overallReasons=(x.overallReasons||[]).concat(
        e.reasons.filter(function(reason){return (x.overallReasons||[]).indexOf(reason)<0}).slice(0,2)
      )
    }
    x.horse=h
  })
}
function predict(r){if(r._prediction)return r._prediction;var modelRace=analysisRace(r),profile=predictionProfile(modelRace),rows=buildRows(modelRace),occ=earlyOcc(modelRace),sc=scenarioModel(r,rows),suit=suitability(rows,sc),pressure=pressureInfo(rows),plans={},i;assignOverallGrades(modelRace,rows,suit,sc,pressure);integratedGrades(r,rows);assignPredictionMarks(rows,modelRace);for(i=0;i<sc.length;i++){var code=sc[i].code,candidates=rows.slice().sort(function(a,b){return scenarioSuit(b,code,pressure)-scenarioSuit(a,code,pressure)});sc[i].horses=candidates.slice(0,3).map(function(x){return x.horse});plans[code]=scenarioPlan(r,rows,[sc[i]],suit)}var top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0],plan=plans[top.code]||scenarioPlan(r,rows,sc,suit),cov=mean(rows.map(function(x){return x.coverage}));var result={rows:rows,occ:occ,scenarios:sc,plan:plan,plans:plans,suit:suit,coverage:cov,pressure:pressure,profile:profile,engineVersion:'kraiz-commercial-2026.09-v2'};Object.defineProperty(r,"_prediction",{value:result,configurable:true,writable:true,enumerable:false});return result}
function nextRace(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime});a.sort(function(x,y){var ax=mins(x.startTime),ay=mins(y.startTime),now=nowMins(),kx=ax>=now?ax:ax+1440,ky=ay>=now?ay:ay+1440;return kx-ky});return a.length?a[0]:null}
function liveRaces(){if(state.date!==today())return[];var now=nowMins(),a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime&&mins(r.startTime)>=now-25});a.sort(function(x,y){return mins(x.startTime)-mins(y.startTime)});return a.slice(0,4)}
function liveTag(r){var d=mins(r.startTime)-nowMins();if(d<0&&d>=-25)return'<span class="live-tag running">進行中</span>';if(d>=0&&d<=10)return'<span class="live-tag now">まもなく</span>';return'<span class="live-tag">次走</span>'}
function homeVenueMark(track){var t=String(track||"?");return '<span class="venue-mark">'+esc(t.slice(0,1))+'</span>'}
function horseBodyWeightText(h){var raw=h&&h.bodyWeight!=null&&h.bodyWeight!==''?h.bodyWeight:(h&&h.horseWeight!=null&&h.horseWeight!==''?h.horseWeight:(h&&h.currentBodyWeight!=null&&h.currentBodyWeight!==''?h.currentBodyWeight:'')),chg=h&&h.bodyWeightChange!=null&&h.bodyWeightChange!==''?h.bodyWeightChange:(h&&h.weightChange!=null&&h.weightChange!==''?h.weightChange:(h&&h.weightDiff!=null&&h.weightDiff!==''?h.weightDiff:null));if(raw===''||raw==null)return'';var s=String(raw);if(/^-?\d+(\.\d+)?$/.test(s))s+='kg';if(chg!=null&&chg!==''&&!/[()]/.test(s)){var c=n(chg);s+=c>0?' (+'+c+')':' ('+c+')'}return s}
function markStoreKey(r,no){return'keiba:v64:mark:'+[(r&&r.circuit)||'',(r&&r.date)||'',(r&&r.track)||'',(r&&r.raceNumber)||'',no||''].join('|')}
function rowMark(r,row){var v=null;try{v=localStorage.getItem(markStoreKey(r,row&&row.horse?row.horse.horseNumber:''))}catch(e){}if(v===null)return row&&row.predMark?row.predMark:'';return v==='__EMPTY__'?'':v}
function cycleMark(no){if(!state.race||!state.pred)return;var row=rowByNo(state.pred.rows,no);if(!row)return;var cur=rowMark(state.race,row),order=['','◎','○','▲','△','☆','注'],idx=order.indexOf(cur);if(idx<0)idx=0;var nxt=order[(idx+1)%order.length];try{localStorage.setItem(markStoreKey(state.race,no),nxt?nxt:'__EMPTY__')}catch(e){}render()}
function sortedHorseRows(rows){return(rows||[]).slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function openHorseModal(no){state.modalScroll=window.scrollY;if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}state.horseModalNo=n(no)||null;render();document.body.style.overflow='hidden'}
function closeHorseModal(){var y=state.modalScroll||0;state.horseModalNo=null;document.body.style.overflow='';render();window.scrollTo(0,y);if(state.race)scheduleHistoryPoll(state.race.id)}
function moveHorseModal(dir){if(!state.pred)return;var rows=sortedHorseRows(state.pred.rows),idx=rows.findIndex(function(x){return n(x.horse.horseNumber)===n(state.horseModalNo)});if(!rows.length)return;state.horseModalNo=n(rows[(idx+dir+rows.length)%rows.length].horse.horseNumber);render()}
function runnerDetailBody(r,p,x){var h=x.horse,fit=x.fit||{},cnt=fit.counts||{},j=h.jockeyProfile||{},t=h.trainerProfile||{},fade=x.styleSamples?Math.round(x.fade*100):null,q=p.pressure&&p.pressure[n(h.horseNumber)]||{};function fitVal(k){return Math.round(confidenceBlend(fit[k],cnt[k])*100)}function fitText(k){return n(cnt[k])?fitVal(k)+' / '+n(cnt[k])+'走':'— / 0走'}var recent=(h.recentRaces||[]).slice(0,5),distTxt=x.shorten?'短縮 '+Math.abs(x.distanceChange)+'m':(x.lengthen?'延長 '+Math.abs(x.distanceChange)+'m':'同距離帯'),pressureTxt=(q.sandwich?'逃げハサミ警戒':((q.leftHot||q.rightHot)?'逃げ横あり':'隣接圧力弱め')),reasons=(x.overallReasons||[]),bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明',ps=styleDisplayPcts(x),mx=Math.max.apply(null,ps);return'<div class="horse-detail"><p>'+evaluationText(x)+'</p><div class="runner-overall-box"><div class="runner-overall-head"><span class="label">AI総合評価</span><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'C')+'</strong><span class="runner-overall-mark">'+esc(x.predMark||'—')+'</span><span class="runner-overall-score">総合 '+(x.overallScore==null?'—':esc(x.overallScore))+'</span></div>'+(reasons.length?'<div class="overall-reasons">'+reasons.map(function(z){var warn=String(z).indexOf('注意')>=0||String(z).indexOf('不足')>=0;return'<i class="'+(warn?'warn':'good')+'">'+esc(z)+'</i>'}).join('')+'</div>':'')+'</div><div class="detail-heading">基本情報</div><div class="horse-info-grid"><div class="horse-info-cell"><small>馬番 / 枠</small><b>'+esc(h.horseNumber)+'番 / '+esc(h.frameNumber||frame(h))+'枠</b></div><div class="horse-info-cell"><small>性齢 / 斤量</small><b>'+esc(h.sex||'—')+esc(h.age||'—')+' / '+esc(h.carriedWeight||'—')+'kg</b></div><div class="horse-info-cell"><small>脚質</small><b>'+esc(styleTxt)+'</b></div><div class="horse-info-cell"><small>騎手</small><b>'+esc(h.jockey||'—')+'</b></div><div class="horse-info-cell"><small>調教師</small><b>'+esc(h.trainer||'—')+'</b></div><div class="horse-info-cell"><small>馬体重</small><b>'+(bodyTxt?esc(bodyTxt):'—')+'</b></div><div class="horse-info-cell"><small>当時獲得賞金</small><b>'+((h.recentRaces||[]).length||n(h.prizeMoneyAtRace)>0?fmtMoney(h.prizeMoneyAtRace)+'円':'—')+'</b></div><div class="horse-info-cell"><small>今回の位置想定</small><b>'+esc(x.pastStyle)+' → '+esc(x.expected)+'</b></div><div class="horse-info-cell"><small>距離変更</small><b>'+esc(distTxt)+'</b></div><div class="horse-info-cell"><small>前走の前進区分</small><b>'+esc(firstThreeType(h))+'</b></div></div>'+sourceCollectionSection(h,r)+'<div class="horse-position-sheet"><div class="detail-heading">位置取り指標</div><div class="style-rate-grid five-rates">'+styleCell('逃',ps[0],ps[0]===mx,'front')+styleCell('先',ps[1],ps[1]===mx,'stalk')+styleCell('差',ps[2],ps[2]===mx,'mid')+styleCell('追',ps[3],ps[3]===mx,'close')+styleCell('下',fade,fade!=null&&fade>=55,'fade')+'</div></div><div class="detail-heading">脚質詳細</div><div class="runner-detail-scores"><div class="runner-detail-score"><small>脚質点</small><b>'+(x.styleSamples?x.score.toFixed(2):'—')+'</b></div><div class="runner-detail-score"><small>前へ行く</small><b>'+(x.styleSamples?Math.round(x.goProb*100)+'%':'—')+'</b></div><div class="runner-detail-score"><small>テン</small><b>'+(x.styleSamples?Math.round(x.ten*100)+'%':'—')+'</b></div><div class="runner-detail-score"><small>前残り力</small><b>'+(x.styleSamples?Math.round(x.frontStay*100)+'%':'—')+'</b></div></div><div class="detail-heading">今回の位置取り診断</div><div class="pressure-grid"><div class="pressure-chip '+(q.leftHot?'danger':'safe')+'"><small>内隣圧力</small><b>'+Math.round(n(q.left)*100)+'%</b></div><div class="pressure-chip '+(q.rightHot?'danger':'safe')+'"><small>外隣圧力</small><b>'+Math.round(n(q.right)*100)+'%</b></div><div class="pressure-chip '+(q.sandwich?'danger':'')+'"><small>逃げハサミ</small><b>'+(q.sandwich?'成立警戒':'なし')+'</b></div><div class="pressure-chip"><small>判定</small><b>'+esc(pressureTxt)+'</b></div><div class="pressure-chip"><small>最初から3番手内</small><b>'+(x.styleSamples?Math.round(x.early3*100)+'%':'—')+'</b></div><div class="pressure-chip"><small>途中から3番手内</small><b>'+(x.styleSamples?Math.round(x.moved3*100)+'%':'—')+'</b></div><div class="pressure-chip"><small>差し上げ力</small><b>'+Math.round(x.comeFromBehind*100)+'</b></div><div class="pressure-chip"><small>下がり率</small><b>'+(fade==null?'—':fade+'%')+'</b></div></div><div class="detail-heading">今回条件への適性</div><div class="fit-grid"><div class="fit-chip"><small>距離</small><b>'+fitText('distance')+'</b></div><div class="fit-chip"><small>競馬場</small><b>'+fitText('track')+'</b></div><div class="fit-chip"><small>馬場</small><b>'+fitText('condition')+'</b></div><div class="fit-chip"><small>天候</small><b>'+fitText('weather')+'</b></div><div class="fit-chip"><small>季節</small><b>'+fitText('season')+'</b></div><div class="fit-chip"><small>相手レベル</small><b>'+fitText('level')+'</b></div></div>'+roleDetail('騎手成績',h.jockeyStats,j)+roleDetail('調教師成績',h.trainerStats,t)+'<div class="recent-list-title">近走データ（直近5走）</div>'+(recent.length?recent.map(function(rr){var rid=rr.raceId||((r.circuit==='地方'&&rr.date&&rr.track&&n(rr.raceNumber))?('nar-'+rr.date+'-'+rr.track+'-'+String(n(rr.raceNumber)).padStart(2,'0')):'');return'<div class="recent"><div class="recent-head"><b>'+esc(rr.date)+' '+esc(rr.track)+' '+(n(rr.raceNumber)?esc(rr.raceNumber)+'R ':'')+esc(rr.distance)+'m</b><strong>'+esc(rr.finish||'—')+'着</strong></div><div>'+fmtTime(rr.timeSeconds)+'　'+esc(rr.condition||'不明')+' / '+esc(rr.weather||'不明')+'</div><div class="muted">'+(rr.title?esc(rr.title)+'　':'')+'通過 '+esc((rr.cornerPositions||[]).join('-')||'—')+'　頭数 '+esc(rr.fieldSize||'—')+(n(rr.carriedWeight)>0?'　斤量 '+esc(rr.carriedWeight)+'kg':'')+(n(rr.racePrize1)>0?'　1着賞金 '+fmtMoney(rr.racePrize1):'')+(rr.jockey?'　騎手 '+esc(rr.jockey):'')+(rr.trainer?'　調教師 '+esc(rr.trainer):'')+'</div>'+(rid?'<button type="button" class="recent-open" data-past-race="'+esc(rid)+'">この過去レースを見る</button>':'')+'</div>'}).join(''):'<div class="empty compact">過去データを確認できませんでした</div>')+'</div>'}
function horseModal(r,p){var no=n(state.horseModalNo,0);if(!no)return'';var rows=sortedHorseRows(p.rows),idx=-1,i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===no){idx=i;break}if(idx<0)return'';var x=rows[idx],h=x.horse,bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明';return'<div class="horse-modal-layer"><div class="horse-modal-backdrop" data-horse-close="1"></div><section class="horse-modal" role="dialog" aria-modal="true"><div class="horse-modal-head"><button type="button" class="horse-modal-nav" data-horse-prev="1">‹</button><div class="horse-modal-title"><div class="horse-modal-title-top">'+badge(h)+'<div style="min-width:0"><div class="horse-modal-name">'+esc(h.name)+'</div>'+(bodyTxt?'<div class="runner-weight-inline">('+esc(bodyTxt)+')</div>':'')+'</div></div><div class="horse-modal-meta"><span>'+esc(h.sex||'—')+esc(h.age||'—')+'</span><span>'+esc(styleTxt)+'</span><span>'+esc(h.jockey||'騎手不明')+'</span><span>'+esc(h.carriedWeight||'—')+'kg</span></div><div class="horse-modal-sidechips"><span class="horse-modal-chip grade">総合評価 '+esc(x.overallGrade||'C')+'</span><span class="horse-modal-chip">総合点 '+(x.overallScore==null?'—':esc(x.overallScore))+'</span><span class="horse-modal-chip mark">予想印 '+esc(x.predMark||'—')+'</span></div><div class="horse-modal-counter">'+(idx+1)+' / '+rows.length+' 頭</div></div><button type="button" class="horse-modal-nav" data-horse-next="1">›</button><button type="button" class="horse-modal-close" data-horse-close="1">×</button></div><div class="horse-modal-swipe">画面左半分タップ＝前の馬　／　右半分タップ＝次の馬</div><div id="horse-modal-panel" class="horse-modal-body">'+runnerDetailBody(r,p,x)+'</div></section></div>'}
function miniPacePreview(r){return '<div class="home-ai-preview-photo mini-flow-demo"><div class="mini-flow-axis"><span>← 後方</span><b>隊列イメージ</b><span>前方 →</span></div><div class="mini-flow-line"></div><i class="mini-flow-dot d1">1</i><i class="mini-flow-dot d2">4</i><i class="mini-flow-dot d3">7</i><i class="mini-flow-dot d4">10</i><div class="mini-flow-caption">写真背景なし・右が前</div></div>'}
function raceNumbers(r){var track=r?r.track:state.track,rs=state.races.filter(function(x){return x.track===track&&x.circuit===(r?r.circuit:state.circuit)}),out='';for(var i=1;i<=12;i++){var found=rs.find(function(x){return n(x.raceNumber)===i});out+='<button '+(found?'data-race="'+esc(found.id)+'"':'disabled')+' class="'+(r&&n(r.raceNumber)===i?'active':'')+'">'+i+'R</button>'}return '<nav class="race-numbers">'+out+'</nav>'}
function evaluationText(x){var e=x.evaluation||{},p=state.pred&&state.pred.profile||null;return (p?esc(p.label)+'　':'')+esc(e.mode||'基礎')+' / '+esc(e.tier||'基礎データ評価')+'　データ充足度 '+n(e.dataCompleteness)+'%　評価信頼度 '+esc(e.confidence||'低')+(e.tied?'　同点は馬番順':'')}
function oddsText(h){var ok=h&&h.winOdds!=null&&h.winOdds!==''&&n(h.winOdds)>0,pop=n(h&&h.popularity,0);return '単勝 '+(ok?esc((Math.round(n(h.winOdds)*10)/10).toFixed(1))+'倍':'--.-倍')+'　'+(pop>0?esc(pop)+'人気':'--人気')}
function oddsClass(h){var o=n(h&&h.winOdds,0);return o>0&&o<10?'odds-single':''}



var instantTrackDetails={},trackSnapshotJobs={},edgeJobs={},visibleRefreshTimes={};

function edgeRaceUrl(id){
  return 'https://kraiz-api.4b89h4fydd.workers.dev/api/race/'
    +encodeURIComponent(id)
    +'?t='+Date.now()
}

function fetchEdgeRace(id,force){
  if(!id)return Promise.resolve(null);
  var cached=instantTrackDetails[String(id)]||loadDetailCache(id);
  if(!force&&cached&&((cached.horses||[]).length||isFinal(cached)))return Promise.resolve(cached);
  if(edgeJobs[id])return edgeJobs[id];
  var controller=typeof AbortController!=='undefined'?new AbortController():null;
  var timer=controller?setTimeout(function(){controller.abort()},12000):null;
  edgeJobs[id]=fetch(edgeRaceUrl(id),{cache:'no-store',signal:controller?controller.signal:undefined})
    .then(function(res){if(!res.ok)throw Error('edge-race '+res.status);return res.json()})
    .then(function(body){var d=body&&body.detail;if(!d||!((d.horses||[]).length||isFinal(d)))return null;
      instantTrackDetails[String(id)]=d;saveDetailCache(id,d);return d})
    .catch(function(){return null})
    .finally(function(){clearTimeout(timer);delete edgeJobs[id]});
  return edgeJobs[id]
}
function detailNeedsRefresh(r){return !diagnosisCurrent(r)||!raceOddsComplete(r)||!(r.volatility&&r.volatility.ready)}
function refreshVisibleDetail(){
  if(!state.race)return Promise.resolve();
  var id=state.race.id,seq=state.detailSeq,key='race:'+id;
  if(state.visibleRefreshBusy===key)return Promise.resolve();
  state.visibleRefreshBusy=key;
  return fetchEdgeRace(id,true).then(function(d){
    if(seq!==state.detailSeq||!state.race||String(state.race.id)!==String(id))return;
    if(d){mergeTrackPack([d]);persistRaceSummaryCache();state.race=applySummaryEnvironment(d);state.pred=null;state.error=null;render()}
  }).finally(function(){
    visibleRefreshTimes[key]=Date.now();
    if(state.visibleRefreshBusy===key)state.visibleRefreshBusy=null;
    scheduleVisibleRefresh()
  })
}
function scheduleVisibleRefresh(){
  clearTimeout(state.refreshTimer);
  if(document.hidden)return;
  var r=state.race,key,delay;
  if(r){
    key='race:'+r.id;
    if(!detailNeedsRefresh(r)&&(r.date!==today()||isFinal(r)))return;
    delay=detailNeedsRefresh(r)?2500:(oddsRefreshCadence(r)||30000);
    if(state.visibleRefreshBusy===key)return;
    state.refreshTimer=setTimeout(refreshVisibleDetail,Math.max(0,delay-(Date.now()-(visibleRefreshTimes[key]||0))));
  }else if(state.track&&!state.raceLoading){
    key=['venue',state.date,state.circuit,state.track].join(':');
    var pending=state.races.some(function(x){return x.track===state.track&&x.circuit===state.circuit&&!(x.volatility&&x.volatility.ready)});
    if(!pending)return;
    var track=state.track;
    state.refreshTimer=setTimeout(function(){
      visibleRefreshTimes[key]=Date.now();
      warmTrackSnapshots(track,true).finally(scheduleVisibleRefresh)
    },Math.max(1000,10000-(Date.now()-(visibleRefreshTimes[key]||0))));
  }
}

function warmTrackSnapshots(track,high){
  track=track||state.track;
  if(!track)return Promise.resolve(0);

  var requestedDate=state.date,requestedCircuit=state.circuit;
  var key=[requestedDate,requestedCircuit,track].join('|');
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
    return fetchEdgeRace(row.id,!(row.volatility&&row.volatility.ready))
      .then(function(d){
        if(!d)return;count++;
        if(state.date!==requestedDate||state.circuit!==requestedCircuit)return;
        if(mergeTrackPack([d])){persistRaceSummaryCache();if(state.track===track&&!state.race&&!state.raceLoading)render()}
      })
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
  var hs=(r&&r.horses||[]).filter(function(h){return n(h.horseNumber)>0}),got=hs.filter(function(h){return n(h.winOdds)>0}).length;
  return !!hs.length&&got>=Math.max(1,Math.ceil(hs.length*.75))
}
function refreshOddsOnly(force){return refreshVisibleDetail()}
function ensureAutoOdds(r){
  if(!r)return;
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  var archived=r.date!==today()||isFinal(r),
      delay=raceHasOdds(r)?120:30;
  if(!raceOddsComplete(r)||!archived){
    state.oddsTimer=setTimeout(function(){
      if(state.race&&String(state.race.id)===String(r.id))refreshOddsOnly(false)
    },delay)
  }
}
function diagnosisPanel(r,p){
  var ready=diagnosisCurrent(r),rows=(p&&p.rows)||[];
  return '<section id="section-diagnosis" class="card"><h2>全頭診断</h2>'+
    '<div class="diagnosis-refresh-note '+(ready?'':'busy')+'">'+
      (ready?'最新の全頭診断':'暫定診断を表示中・完全診断をCloudflareから自動同期中')+
    '</div>'+
    '<p class="muted">診断完了を待たず、取得済みデータで印・総合評価を先に表示します。完全診断取得後は自動で更新します。</p>'+
    rows.slice().sort(function(a,b){return a.predRank-b.predRank}).map(function(x){
      var head=x.predRank+'位 '+esc(x.predMark||'—')+' '+esc(x.horse.name)+'　'+esc(x.overallGrade||'C')+' '+(x.overallScore==null?'—':x.overallScore);
      return '<article class="horse-card"><button data-horse-open="'+esc(x.horse.horseNumber)+'"><b>'+head+'</b></button><p>'+evaluationText(x)+'</p><p>'+esc((x.overallReasons||[]).join(' / ')+(x.predMark==='注'&&x.attentionReason?' / 注目理由 '+x.attentionReason:''))+'</p></article>'
    }).join('')+'</section>'
}
function historyPanel(r){return '<section id="section-history" class="card"><h2>過去走（直近5走）</h2>'+(r.horses||[]).map(function(h){var runs=(h.allPastRuns||h.recentRaces||[]).slice(0,5);return '<article class="horse-card"><button data-horse-open="'+esc(h.horseNumber)+'">'+esc(h.horseNumber)+' '+esc(h.name)+'</button>'+ (runs.length?runs.map(function(z){return '<div class="recent">'+esc(z.date||'—')+' '+esc(z.track||'—')+' '+esc(z.title||'')+' '+esc(z.distance||'—')+'m　'+esc(z.finish||z.finishStatus||'—')+'着　通過 '+esc((z.cornerPositions||[]).join('-')||'—')+'</div>'}).join(''): '<p>'+(h.debutNoHistory?'新馬：過去走0（正常）':'過去走0件：基礎情報で評価済み')+'</p>')+'</article>'}).join('')+'</section>'}
function pacePanel(r,p){return '<section id="section-pace" class="card"><h2>展開AI</h2><p class="muted">A/B/Cシナリオと隊列予想。利用できるデータ量に応じて評価信頼度を調整します。</p>'+scenarioProbabilitySection(p)+paceBoard(r,p)+'</section>'}
function resultPanel(r){return '<section id="section-result" class="card"><h2>レース結果</h2>'+(isFinal(r)?renderResult(r)+renderPayouts(r)+renderActualFlow(r):'<div class="muted">結果はまだ確定していません。</div>')+'</section>'}
function detailTabs(r,p){var key=state.openPanel;if(key==='entry')return '<div id="section-entry" class="accordion-panel">'+runnerStyleSection(r,p)+'</div>';if(key==='diagnosis')return '<div class="accordion-panel">'+diagnosisPanel(r,p)+'</div>';if(key==='history')return '<div class="accordion-panel">'+historyPanel(r)+'</div>';if(key==='pace')return '<div class="accordion-panel">'+pacePanel(r,p)+'</div>';if(key==='result')return '<div class="accordion-panel">'+resultPanel(r)+'</div>';return '<div class="accordion-idle">出走表・全頭診断・過去走・展開AI・レース結果から見たい項目を押してください。</div>'}
function renderPicker(){var a=state.races.filter(function(r){return r.circuit===state.circuit});a.sort(function(x,y){return (x.track||'').localeCompare(y.track||'ja')||n(x.raceNumber)-n(y.raceNumber)});return'<div class="shell">'+header("全レース",true,state.date+'・'+state.circuit)+'<main class="main"><section class="card"><div class="picker-list">'+(a.length?a.map(function(r){return'<button class="picker-item '+(isFinal(r)?'final':'')+'" data-race="'+esc(r.id)+'"><span>'+esc(r.track)+' '+esc(r.raceNumber)+'R　'+esc(r.title||"")+'</span><span class="picker-side">'+volatilityBadge(r)+'<strong>'+(isFinal(r)?'確定':timeHtml(r))+'</strong></span></button>'}).join(""):'<div class="empty">レースデータなし</div>')+'</div></section></main></div>'}
var VENUE_PHOTOS={};
function cinematicContext(r){var circuit=r&&r.circuit||state.circuit,rows=state.races.filter(function(x){return x.circuit===circuit}),venues=[];(circuit==='中央'?['中山','阪神','札幌','中京'].concat(CENTRAL.filter(function(t){return ['中山','阪神','札幌','中京'].indexOf(t)<0})):LOCAL).forEach(function(track){var races=rows.filter(function(x){return x.track===track});if(races.length)venues.push({track:track,count:races.length})});if(r&&!venues.some(function(v){return v.track===r.track}))venues.push({track:r.track,count:1});var track=r&&r.track||state.track||(venues[0]&&venues[0].track)||'',races=rows.filter(function(x){return x.track===track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)}),featured=r||races.find(function(x){return n(x.raceNumber)===1})||races[0]||null;return{circuit:circuit,venues:venues,track:track,races:races,featured:featured}}
function cinematicHero(){return '<header class="cinema-hero"><img class="cinema-hero-image" src="/kraiz-racing-hero.webp" alt="" fetchpriority="high"><div class="cinema-brand"><div class="cinema-wordmark" aria-label="KRAIZ">KRAI<span class="logo-z">Z</span></div><div class="cinema-subtitle">TACTICAL RACING</div></div><div class="cinema-tools"><time>'+esc(state.date.replace(/-/g,'.'))+'</time><button data-action="reload" aria-label="更新" title="更新">↻</button></div></header>'}
function cinematicControls(circuit){return '<div class="cinema-controls"><div class="cinema-circuit" aria-label="開催区分"><button data-circuit="中央" class="'+(circuit==='中央'?'active':'')+'">中央</button><button data-circuit="地方" class="'+(circuit==='地方'?'active':'')+'">地方</button></div>'+dateStrip()+'<label class="cinema-calendar" title="日付を選択"><span aria-hidden="true">▦</span><input id="date" type="date" value="'+esc(state.date)+'" aria-label="開催日"></label></div>'}
function dateStrip(){var center=new Date(state.date+'T12:00:00'),out='';for(var i=-1;i<=3;i++){var d=new Date(center);d.setDate(d.getDate()+i);var key=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'),label=(d.getMonth()+1)+'/'+d.getDate()+' ('+'日月火水木金土'[d.getDay()]+')';out+='<button data-date="'+key+'" class="'+(key===state.date?'active':'')+'" aria-pressed="'+(key===state.date)+'">'+label+'</button>'}return '<nav class="date-strip" aria-label="開催日">'+out+'</nav>'}
function cinematicVenues(ctx){return '<nav class="cinema-venues">'+ctx.venues.map(function(v){return '<button class="cinema-venue '+(ctx.track===v.track?'active':'')+'" data-track="'+esc(v.track)+'"><strong>'+esc(v.track)+'</strong><small>全'+v.count+'R</small></button>'}).join('')+'</nav>'}
function cinematicNumbers(ctx){return '<nav class="cinema-numbers" aria-label="レース番号">'+Array.from({length:12},function(_,i){var row=ctx.races.find(function(x){return n(x.raceNumber)===i+1});if(!row&&ctx.featured&&n(ctx.featured.raceNumber)===i+1)row=ctx.featured;return '<button '+(row?'data-race="'+esc(row.id)+'"':'disabled')+' class="'+(ctx.featured&&n(ctx.featured.raceNumber)===i+1?'active':'')+'">'+(i+1)+'R</button>'}).join('')+'</nav>'}
function cinematicGrade(r){var g=r.grade||r.gradeLabel||'',match=String(r.title||'').match(/(?:J[・･.]?)?G[ⅠⅡⅢ123]/i);if(!g&&match)g=match[0];return g?'<span class="cinema-grade">'+esc(g)+'</span>':''}
function cinematicTabs(r){
  var navStyle='display:grid!important;grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:5px!important;width:100%!important;overflow:visible!important;padding:7px!important;';
  var btnStyle='width:100%!important;min-width:0!important;max-width:none!important;margin:0!important;flex:none!important;padding:8px 1px!important;box-sizing:border-box!important;';
  return '<nav class="cinema-tabs accordion-tabs" style="'+navStyle+'">'+
    [['出走表','entry'],['全頭診断','diagnosis'],['過去走','history'],['展開AI','pace'],['レース結果','result']]
      .map(function(t){
        var active=state.openPanel===t[1];
        return '<button style="'+btnStyle+'" data-panel="'+t[1]+'" aria-expanded="'+active+'" class="'+(active?'active':'')+'">'+t[0]+'<span class="panel-caret">'+(active?'−':'＋')+'</span></button>'
      }).join('')+
    '</nav>'
}
function cinematicFeature(r){if(!r)return '';var count=n(r.fieldSize,(r.horses||[]).length),surface=r.surface||'—',course=COURSE[r.track]||{},turn=r.turn||course.turn||'—';return '<section class="cinema-feature" aria-label="選択したレース"><div class="cinema-feature-photo" aria-hidden="true"></div><div class="cinema-feature-info"><div class="cinema-feature-heading"><h1>'+esc(r.track)+' '+esc(r.raceNumber)+'R</h1>'+cinematicGrade(r)+'</div><h2>'+esc(r.title||'レース詳細')+'</h2><div class="cinema-feature-meta">'+timeHtml(r)+' 発走　'+esc(surface)+' '+esc(r.distance||'—')+'m ('+esc(turn)+')　<span>'+esc(r.weather||'')+' '+esc(r.condition||'')+'</span></div><div class="cinema-metrics">'+[[r.distance?r.distance+'m':'—','距離'],[turn,'コース'],[surface,'馬場'],[r.raceClass||r.className||raceMode(r),'条件'],[count?count+'頭':'—','頭数']].map(function(x){return '<div><b>'+esc(x[0])+'</b><small>'+esc(x[1])+'</small></div>'}).join('')+'</div></div><button class="cinema-feature-open" data-race="'+esc(r.id)+'" aria-label="レース詳細を開く">›</button>'+cinematicTabs(r)+'</section>'}
function otherRaces(r){var ctx=cinematicContext(r),rows=ctx.races.filter(function(x){return !r||x.id!==r.id});return '<section class="cinema-others"><div class="cinema-section-heading"><h2>◷ '+(state.date===today()?'本日の他レース':'この日の他レース')+'</h2><button data-action="all-races">全レース一覧 ›</button></div><div class="cinema-other-list">'+(rows.length?rows.map(function(x){return '<button data-race="'+esc(x.id)+'" class="cinema-other-row '+(isFinal(x)?'final':'')+'"><span>'+esc(x.track)+'</span><b>'+esc(x.raceNumber)+'R</b><span class="other-title">'+esc(x.title||'')+'</span><time>'+timeHtml(x)+'</time><span class="other-distance">'+esc(x.surface||'')+' '+esc(x.distance||'—')+'m</span><span class="other-condition">'+esc(x.condition||'')+'</span>'+volatilityBadge(x)+'<span class="other-status">'+(isFinal(x)?'結果確定':'レース詳細')+' ›</span></button>'}).join(''):'<div class="cinema-empty">他のレースはありません</div>')+'</div></section>'}
function cinematicFooter(){return '<footer class="cinema-footer">KRAIZ　<small>TACTICAL RACING · BUILD v137</small></footer>'}
function smartTopBar(back,title,sub){
  return '<header class="smart-topbar smart-topbar-clean">'+
    (back?'<button class="smart-back" data-action="home" aria-label="ホームに戻る">×</button>':'<span class="smart-back-space"></span>')+
    '<div class="smart-head-copy smart-head-copy-clean"><strong>'+esc(title||'開催場')+'</strong><small>'+esc(sub||'')+'</small></div>'+
    '<button class="smart-reload" data-action="reload" aria-label="更新">↻</button>'+
  '</header>'
}
function smartPageControls(){
  return '<div class="smart-controls">'+
    '<div class="smart-date-controls smart-date-controls-only">'+dateStrip()+
      '<label class="smart-calendar" title="日付を選択"><span aria-hidden="true">▦</span><input id="date" type="date" value="'+esc(state.date)+'" aria-label="開催日"></label>'+
    '</div>'+
  '</div>'
}
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
        return '<button class="smart-venue-card" data-track="'+esc(track)+'" data-circuit="'+esc(circuit)+'">'+
          '<span class="smart-venue-mark">'+esc(track.slice(0,1))+'</span>'+
          '<span class="smart-venue-name"><b>'+esc(track)+'</b><small>'+rs.length+'レース</small></span>'+
          '<span class="smart-venue-times"><small>'+(first?timeHtml(first):'--:--')+'</small><i>→</i><small>'+(last?timeHtml(last):'--:--')+'</small></span>'+
          '<span class="smart-chevron">›</span>'+
        '</button>'
      }).join(''):(waiting?'<div class="smart-empty">'+esc(waitText)+'</div>':'<div class="smart-empty">本日の開催情報はまだありません</div>'))+
    '</div>'+
  '</section>'
}
function smartVenueCards(){
  return '<div class="smart-group-wrap">'+
    smartVenueGroup('中央','中央')+
    smartVenueGroup('地方','地方')+
  '</div>'
}
function smartHomeHero(){
  return '<section class="smart-home-hero">'+
    '<img class="smart-home-hero-image" src="/kraiz-racing-hero.webp" alt="KRAIZ hero">'+
    '<div class="smart-home-hero-overlay"></div>'+
    '<div class="smart-home-hero-date smart-home-hero-date-left">'+esc((state.date||'').replace(/-/g,'.'))+'</div>'+
    '<button class="smart-hero-refresh smart-hero-refresh-right" data-action="reload" aria-label="更新">↻</button>'+
    '<div class="smart-home-brand smart-home-brand-lower">'+
      '<div class="smart-home-script-logo" aria-label="KRAIZ">Kraiz</div>'+
      '<div class="smart-home-brand-rule"><i></i></div>'+
      '<div class="smart-home-brand-sub">TACTICAL RACING</div>'+
    '</div>'+
  '</section>'
}
function renderHome(){
  return '<div class="smart-shell smart-home">'+
    smartHomeHero()+
    '<main class="smart-main smart-home-main">'+
      smartPageControls()+
      (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
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
    if(v&&v.version==='kraiz-volatility-v1'){
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
    saveDetailCache(d.id,d);
    var r=state.races.find(function(x){return String(x.id)===String(d.id)});
    if(r&&d.volatility){
      var before=JSON.stringify(r.volatility||null),after=JSON.stringify(d.volatility);
      if(before!==after){r.volatility=d.volatility;changed=true}
    }
  });
  return changed
}


function venueRaceRows(){
  var rows=state.races.filter(function(x){return x.circuit===state.circuit&&x.track===state.track}).sort(function(a,b){return n(a.raceNumber)-n(b.raceNumber)});
  return '<section class="smart-section smart-race-section">'+
    '<div class="smart-section-title"><b>'+esc(state.track||'')+' 全レース</b><span>1R〜12R</span></div>'+
    '<div class="smart-race-list">'+
      Array.from({length:12},function(_,idx){
        var no=idx+1,r=rows.find(function(x){return n(x.raceNumber)===no});
        if(!r)return '<div class="smart-race-row disabled"><strong>'+no+'R</strong><span class="smart-race-time">--:--</span><span class="smart-race-title">レース情報待ち</span><span class="race-vol-badge vol-pending"><small>荒れ度</small><b>…</b></span><span></span></div>';
        return '<button class="smart-race-row '+(isFinal(r)?'final':'')+'" data-race="'+esc(r.id)+'">'+
          '<strong>'+no+'R</strong>'+
          '<span class="smart-race-time">'+(isFinal(r)?'確定':timeHtml(r))+'</span>'+
          '<span class="smart-race-title"><b>'+esc(r.title||no+'R')+'</b><small>'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc(r.weather||'不明')+' / '+esc(r.condition||'不明')+'</small></span>'+
          volatilityBadge(r)+
          '<span class="smart-chevron">›</span>'+
        '</button>'
      }).join('')+
    '</div>'+
  '</section>'
}
function venueSwitch(){
  var tracks=[];
  state.races.forEach(function(r){if(r.circuit===state.circuit&&r.track&&tracks.indexOf(r.track)<0)tracks.push(r.track)});
  return '<div class="date-strip">'+tracks.map(function(t){return '<button data-track="'+esc(t)+'" class="date-pill '+(t===state.track?'active':'')+'">'+esc(t)+'</button>'}).join('')+'</div>'
}
function renderVenue(){
  return '<div class="smart-shell">'+
    smartTopBar(true,state.track||'開催場',state.date+'・'+state.circuit)+
    '<main class="smart-main">'+
      '<div class="smart-venue-tools"><div class="smart-venue-circuit-bar"><span class="smart-circuit-chip">'+esc(state.circuit)+'</span></div><div class="smart-date-controls">'+venueSwitch()+'</div></div>'+
      (state.error?'<div class="notice">'+esc(state.error)+'</div>':'')+
      venueRaceRows()+
    '</main>'+
    cinematicFooter()+
  '</div>'
}
function smartRaceHead(r){
  var count=n(r.fieldSize,(r.horses||[]).length);
  return '<section class="smart-race-head">'+
    '<div class="smart-race-headline"><span class="smart-circuit-chip">'+esc(r.circuit||state.circuit)+'</span><strong>'+esc(r.track)+' '+esc(r.raceNumber)+'R</strong>'+cinematicGrade(r)+'<time>'+timeHtml(r)+' 発走</time></div>'+
    '<h1>'+esc(r.title||'レース詳細')+'</h1>'+
    '<div class="smart-race-meta">'+esc(r.surface||'')+' '+esc(r.distance||'—')+'m　'+esc(r.weather||'')+' '+esc(r.condition||'')+'　'+count+'頭</div>'+
  '</section>'
}
function renderRaceLoading(){
  var row=state.races.find(function(x){return String(x.id)===String(state.raceLoading)});
  return '<div class="smart-shell">'+
    smartTopBar(true,row?row.track:(state.track||'レース'),'レース詳細')+
    '<main class="smart-main">'+
      (row?smartRaceHead(row):'')+
      '<div class="smart-loading"><span class="smart-loading-dot"></span><b>全レースを準備中</b><small>サイト表示後は各レースを待たずに開けるよう、全開催を先に読み込んでいます</small></div>'+
    '</main>'+cinematicFooter()+
  '</div>'
}
function renderRace(){
  var r=applySummaryEnvironment(state.race),p=predict(r);
  state.race=r;state.pred=p;
  if(!state.openPanel)state.openPanel='entry';
  var top=p.scenarios.slice().sort(function(a,b){return b.prob-a.prob})[0];
  if(!state.scenarioCode||!p.plans||!p.plans[state.scenarioCode])state.scenarioCode=top?top.code:null;
  return '<div class="smart-shell">'+
    smartTopBar(true,r.track+' '+r.raceNumber+'R',r.date)+
    '<main class="smart-main smart-race-page">'+
      smartRaceHead(r)+
      cinematicTabs(r)+
      '<div class="smart-race-content">'+detailTabs(r,p)+'</div>'+
    '</main>'+
    cinematicFooter()+
  '</div>'+horseModal(r,p)
}

function resultFinish(r,no){var f=r&&r.result&&r.result.finishers||[];for(var i=0;i<f.length;i++)if(n(f[i].horseNumber)===n(no))return n(f[i].finish);return 0}
function actualCornerLeaders(r,idx){var f=r&&r.result&&r.result.finishers||[],best=999,out=[],i,p,v;for(i=0;i<f.length;i++){p=f[i].cornerPositions||[];v=n(p[idx],0);if(v&&v<best){best=v;out=[f[i]]}else if(v&&v===best)out.push(f[i])}return out}
function actualCornerCount(r){var f=r&&r.result&&r.result.finishers||[],m=0,i;for(i=0;i<f.length;i++)m=Math.max(m,(f[i].cornerPositions||[]).length);return m}
function actualCornerLabel(i,count){if(count===1)return"4角";if(count===2)return i===0?"3角":"4角";if(count===3)return["2角","3角","4角"][i];if(count===4)return["1角","2角","3角","4角"][i];return(i+1)+"角"}
function actualOrderAt(r,idx){var f=(r.result&&r.result.finishers||[]).slice(),a=[];for(var i=0;i<f.length;i++){var p=f[i].cornerPositions||[],v=n(p[idx],0);if(v)a.push({x:f[i],pos:v})}a.sort(function(u,v){return u.pos-v.pos||n(u.x.finish)-n(v.x.finish)});return a}
function renderResultLink(r){return '<details class="card result-disclosure"><summary style="cursor:pointer;padding:8px 0;font-weight:700">レース結果　'+(isFinal(r)?'確定 ＞':'未確定 ＞')+'</summary>'+(isFinal(r)?renderResult(r)+renderPayouts(r)+renderActualFlow(r):'<p class="muted">結果はまだ確定していません。</p>')+'</details>'}
function renderPayouts(r){var result=r.result||{},rows=result.payouts||[],types=['単勝','複勝','枠連','馬連','ワイド','馬単','3連複','3連単'],head=state.payoutBusy?'<span class="muted">　取得中…</span>':(rows.length?'':('<span class="muted">　'+esc(result.payoutError||'取得待ち')+'</span>'));return '<section class="card"><div class="section-title">払い戻し'+head+'</div>'+types.map(function(t){var a=rows.filter(function(x){return x.type===t});return '<div style="padding:8px 0;border-bottom:1px solid #e4e7ec"><b>'+t+'</b>　'+(a.length?a.map(function(x){return esc(x.combination)+'　'+(x.amount==null?esc(x.note||'未取得'):fmtMoney(x.amount)+'円')}).join('<br>'):'<span class="muted">'+(state.payoutBusy?'取得中…':'—')+'</span>')+'</div>'}).join('')+'</section>'}
function renderResult(r){if(!isFinal(r))return"";var results=(r.result.finishers||[]).slice();(r.horses||[]).forEach(function(h){if(!results.some(function(z){return n(z.horseNumber)===n(h.horseNumber)}))results.push({horseNumber:h.horseNumber,name:h.name,finishLabel:h.status||"結果未取得"})});var f=results.sort(function(a,b){return (n(a.finish)||999)-(n(b.finish)||999)});return'<section class="card result-card"><div class="section-title">レース結果 <span class="final-badge">確定</span></div><div class="muted" style="margin-bottom:7px">馬場 '+esc(r.condition||'不明')+' / 天候 '+esc(r.weather||'不明')+'</div>'+f.map(function(x){var h=horseByNo(r,x.horseNumber)||x;return'<div class="result-row"><span>'+esc(x.finishLabel||(x.finish?x.finish+'着':'—'))+'</span>'+badge(h)+'<span class="result-name">'+esc(x.name||h.name||"")+'</span><span>'+fmtTime(x.timeSeconds)+'</span></div>'}).join("")+'</section>'}
function gradeRank(g){return g==='S'?0:(g==='A'?1:(g==='B'?2:(g==='C'?3:9)))}

function renderActualFlow(r){if(!isFinal(r))return"";var count=actualCornerCount(r),html='<section class="card actual-flow"><div class="section-title">実際の展開順序</div>';if(!count)html+='<div class="muted">コーナー通過順データなし</div>';for(var j=0;j<count;j++){var a=actualOrderAt(r,j);html+='<div class="actual-stage"><b>'+actualCornerLabel(j,count)+'</b><div class="actual-order">'+a.map(function(z){var h=horseByNo(r,z.x.horseNumber)||z.x;return'<span>'+badge(h)+'<em>'+esc(h.name||z.x.name||"")+'</em></span>'}).join('<i>›</i>')+'</div></div>'}var f=(r.result.finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)});html+='<div class="actual-stage"><b>ゴール</b><div class="actual-order">'+f.map(function(x){var h=horseByNo(r,x.horseNumber)||x;return'<span>'+badge(h)+'<em>'+esc(h.name||x.name||"")+'</em></span>'}).join('<i>›</i>')+'</div></div></section>';return html}
function roleDetail(label,stats,profile){stats=stats||{};profile=profile||{};var st=n(stats.starts)||n(profile.starts),w=n(stats.wins),s=n(stats.seconds),t=n(stats.thirds);if(!st)return'<div class="role-box"><b>'+esc(label)+'</b><div>過去データ未取得 / 該当履歴なし</div></div>';var wr=Math.round(w/st*100),rr=Math.round((w+s)/st*100),pr=Math.round((w+s+t)/st*100),bits=['出走 '+st,'1着 '+w,'2着 '+s,'3着 '+t,'勝率 '+wr+'%','連対 '+rr+'%','複勝 '+pr+'%'];if(n(profile.starts)>0){bits.push('競馬場 '+Math.round(n(profile.track)*100)+'%');bits.push('距離 '+Math.round(n(profile.distance)*100)+'%');if(profile.condition!=null)bits.push('馬場 '+Math.round(n(profile.condition)*100)+'%');if(n(profile.early3Rate,0))bits.push('序盤3番手内 '+Math.round(n(profile.early3Rate)*100)+'%');if(n(profile.leaderRate,0))bits.push('逃げ '+Math.round(n(profile.leaderRate)*100)+'%')}return'<div class="role-box"><b>'+esc(label)+'</b><div>'+bits.join(' / ')+'</div></div>'}
function styleDisplayPcts(x){if(!x||!n(x.styleSamples))return[null,null,null,null];var raw=[n(x.rawFront,x.front),n(x.rawStalk,x.stalk),n(x.rawMid,x.mid),n(x.rawClose,x.close)],vals=[],sum=0,i,maxi=0;for(i=0;i<4;i++){vals[i]=Math.max(0,Math.round(raw[i]*100));sum+=vals[i];if(raw[i]>raw[maxi])maxi=i}vals[maxi]+=100-sum;return vals}
function styleCell(label,val,active,cls){var unk=val==null||!isFinite(Number(val));return '<div class="style-rate '+cls+(active?' dominant':'')+(unk?' unknown':'')+'"><div class="style-rate-head"><span>'+label+'</span><b>'+(unk?'—':val+'%')+'</b></div><div class="style-bar"><i style="width:'+(unk?0:Math.max(2,val))+'%"></i></div></div>'}
function positionBucket(x){if(x.expected==="逃げ候補")return"逃げ候補";if(x.expected==="先行")return"先行";if(x.expected==="好位")return"好位";if(x.expected==="後方")return"後方";if(x.expected==="不明")return"不明";return"中団"}
function stylePositionMap(r,p){var rows=p.rows||[],labels=['逃げ候補','先行','好位','中団','後方','不明'],field=Math.max(1,(r.horses||[]).length),html='<div class="style-position-map"><div class="style-map-axis"><span>内枠</span><b>今回の枠順 × 想定位置</b><span>外枠</span></div>';for(var j=0;j<labels.length;j++){var lab=labels[j];html+='<div class="style-lane"><div class="style-lane-label">'+lab+'</div><div class="style-lane-track">';for(var i=0;i<rows.length;i++){var x=rows[i],h=x.horse;if(positionBucket(x)!==lab)continue;var left=field<=1?50:6+(n(h.horseNumber)-1)/Math.max(1,field-1)*88,shift=x.pastStyle!==x.expected&&!(x.pastStyle==='先行'&&x.expected==='好位');html+='<span class="style-map-horse'+(shift?' shifted':'')+'" style="left:'+left+'%" title="'+esc(h.name)+'｜過去 '+esc(x.pastStyle)+' → 今回 '+esc(x.expected)+'">'+badge(h)+'</span>'}html+='</div></div>'}html+='<div class="style-map-note"><b>水色縁</b>＝過去脚質から今回条件で位置想定が動いた馬。馬番位置は内→外の枠順を維持。</div></div>';return html}
function runnerStyleSection(r,p){
  var partial=!!(r.preparedMeta&&r.preparedMeta.fastPartial);
  function bodyWeightInline(h){
    var bw=n(h&&h.bodyWeight,0),chg=h&&h.bodyWeightChange;
    if(!bw)return '';
    var cs=(chg==null||chg==='')?'':('('+(n(chg)>0?'+':'')+n(chg)+')');
    return esc(bw)+esc(cs);
  }
  function oddsCells(h){
    var ok=h&&h.winOdds!=null&&h.winOdds!==''&&n(h.winOdds)>0,o=ok?n(h.winOdds):0,pop=n(h&&h.popularity,0);
    var os=ok?(Math.round(o*10)/10).toFixed(1):'--.-';
    return '<span class="odd '+(o>0&&o<10?'single':'')+'">'+esc(os)+'</span><span class="pop">'+(pop>0?esc(pop)+'人気':'--人気')+'</span>';
  }
  var diagnosisReady=diagnosisCurrent(r);
  var cadenceText=oddsRefreshCadence(r)===30000?'自動30秒':'自動60秒';
  return '<section class="card"><h2>出走表</h2><button data-action="odds-update">オッズ手動更新</button><span id="odds-status" role="status"> '+cadenceText+'</span>'
    +(!diagnosisReady?'<div class="diagnosis-refresh-note busy" style="margin:7px 0">暫定印を表示中。完全診断はCloudflareから自動同期します。</div>':'')
    +'<div class="racecard-table">'
    +(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){
      var scratch=isScratchHorse(h),x=(p.rows||[]).find(function(z){return n(z.horse.horseNumber)===n(h.horseNumber)}),
          mark=scratch?'—':(x?(x.predMark||'—'):'—'),
          grade=scratch?'—':(x?(x.overallGrade||'C'):'—'),
          score=scratch?'—':(x?(x.overallScore==null?'—':x.overallScore):'—');
      var fr=clamp(n(h.frameNumber,h.horseNumber),1,8),bw=bodyWeightInline(h),st=String(h.status||'欠場');
      return '<button class="racecard-row'+(scratch?' scratched':'')+'" '+(scratch?'disabled aria-disabled="true"':'data-horse-open="'+esc(h.horseNumber)+'"')+'>'
        +'<span class="rc-number frame'+fr+'">'+esc(h.horseNumber)+'</span>'
        +'<span class="rc-pred"><b class="rc-pred-mark" data-ai-mark="'+esc(mark)+'">'+esc(mark)+'</b><small class="rc-eval">'+esc(grade)+' '+esc(score)+'</small></span>'
        +'<span class="rc-horse">'
          +'<span class="rc-horse-top"><b class="rc-horse-name">'+esc(h.name)+'</b>'+(scratch?'<small class="rc-scratch">'+esc(st)+'</small>':(bw?'<small class="rc-bodyweight">'+bw+'kg</small>':''))+'</span>'
          +'<span class="rc-horse-meta"><span>'+esc(h.sex||'—')+esc(h.age||'—')+'</span><span class="jockey">'+esc(h.jockey||'—')+'</span><span class="carry">'+esc(h.carriedWeight||'—')+'</span></span>'
        +'</span>'
        +'<span class="rc-odds" data-odds-no="'+esc(h.horseNumber)+'">'+oddsCells(h)+'</span>'
        +'</button>'
    }).join('')
    +'</div></section>'
}
function rowName(x){return x&&x.horse?(x.horse.horseNumber+' '+x.horse.name):'—'}
function stageNarrative(p,idx){var rows=p.rows||[],plan=activeScenarioPlan(p),st=plan&&plan.stages&&plan.stages[idx],pack=st&&st.pack||[],by={};for(var i=0;i<rows.length;i++)by[n(rows[i].horse.horseNumber)]=rows[i];var lead=pack.length?by[n(pack[0].no)]:null,front=rows.filter(function(x){return x.goProb>=.48}),sand=front.filter(function(x){return x.sandwichRisk}),wide=front.filter(function(x){return x.outerStress>=.18}),fade=front.filter(function(x){return x.fade>=.50}),movers=rows.filter(function(x){return x.move>=.40&&x.goProb<.50}).sort(function(a,b){return b.comeFromBehind-a.comeFromBehind}),closers=rows.slice().sort(function(a,b){return b.comeFromBehind-a.comeFromBehind}),bits=[];if(lead)bits.push('<b>先頭想定 '+esc(rowName(lead))+'</b>');if(idx===0){var h=front.slice().sort(function(a,b){return b.goProb-a.goProb}).slice(0,4);if(h.length)bits.push('前へ '+h.map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===1){if(sand.length)bits.push('<span class="event-warn">被され/控え警戒 '+sand.map(function(x){return esc(rowName(x))}).join('・')+'</span>');if(wide.length)bits.push('外枠テン負荷 '+wide.map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===2){var lowHold=front.filter(function(x){return x.holdFront<.52});if(lowHold.length)bits.push('前で維持力注意 '+lowHold.slice(0,3).map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===3||idx===4){if(movers.length)bits.push('<span class="event-good">位置を上げる候補 '+movers.slice(0,3).map(function(x){return esc(rowName(x))}).join('・')+'</span>');if(fade.length)bits.push('<span class="event-warn">下がり警戒 '+fade.slice(0,3).map(function(x){return esc(rowName(x))}).join('・')+'</span>');if(fade.length&&closers.length)bits.push('下がった前の後ろで得 '+closers.slice(0,2).map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===5){var stay=rows.slice().sort(function(a,b){return b.frontStay-a.frontStay}).slice(0,2);bits.push('前残り適性 '+stay.map(function(x){return esc(rowName(x))}).join('・'));bits.push('差し込み適性 '+closers.slice(0,2).map(function(x){return esc(rowName(x))}).join('・'))}return bits.join('　｜　')}
function horseBadgeList(items){var a=items||[],out=[],i,it,h,no;if(!Array.isArray(a))a=[a];for(i=0;i<a.length;i++){it=a[i];h=null;no=0;if(it&&it.horse){h=it.horse;no=n(h.horseNumber)}else if(it&&it.horseNumber!=null){h=it;no=n(h.horseNumber)}else{no=n(it,0);if(state.race&&no)h=horseByNo(state.race,no)}if(!h&&no)h={horseNumber:no,frameNumber:no};if(h&&n(h.horseNumber)>0)out.push(badge(h))}return'<span class="scenario-horses">'+(out.length?out.join(''):'<span class="muted">—</span>')+'</span>'}
function activeScenarioPlan(p){if(!p)return null;var code=state.scenarioCode||'';if(code&&p.plans&&p.plans[code])return p.plans[code];return p.plan||null}
function scenarioProbabilitySection(p){var top=p.scenarios.slice().sort(function(a,b){return b.prob-a.prob})[0],active=(state.scenarioCode&&p.plans&&p.plans[state.scenarioCode])?state.scenarioCode:top.code,front=p.rows.filter(function(x){return x.goProb>=.52}),sand=front.filter(function(x){return x.sandwichRisk}),highFade=front.filter(function(x){return x.fade>=.50}),occ=p.occ||{rate:0,early:[],moved:[]},activeScenario=p.scenarios.filter(function(s){return s.code===active})[0]||top;return'<section class="card pace-card"><div class="section-title">展開シナリオ</div><div class="scenario-prob-grid">'+p.scenarios.map(function(s){return'<button type="button" data-scenario-code="'+esc(s.code)+'" class="scenario-prob-card '+(s.code===active?'active':'')+'"><small>'+s.code+'</small><b>'+esc(s.title)+'</b><strong>'+Math.round(s.prob*100)+'%</strong>'+horseBadgeList(s.horses)+'</button>'}).join('')+'</div><div class="scenario-main-note"><span>表示中シナリオ</span><b>'+esc(activeScenario.code)+' '+esc(activeScenario.title)+'　'+Math.round(activeScenario.prob*100)+'%</b>'+horseBadgeList(activeScenario.horses)+'</div><div class="scenario-diagnostics"><div class="scenario-diagnostic"><small>先行馬占有率</small><b>'+Math.round(occ.rate*100)+'%</b></div><div class="scenario-diagnostic"><small>最初から前</small>'+horseBadgeList(occ.early)+'</div><div class="scenario-diagnostic"><small>途中から上昇</small>'+horseBadgeList(occ.moved)+'</div><div class="scenario-diagnostic"><small>今回前候補</small>'+horseBadgeList(front)+'</div></div><div class="scenario-warning">'+(sand.length?'逃げハサミ警戒 '+horseBadgeList(sand):'')+(highFade.length>=2?'　高下がり率 '+horseBadgeList(highFade):'')+'</div></section>'}
function paceBoard(r,p){var hs=(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}),plan=activeScenarioPlan(p)||p.plan,stages=plan.stages||[],cp=courseProfile(r);return'<section class="card ai-flow-card"><div class="ai-flow-head"><span class="ai-flow-bars"><i></i><i></i><i></i></span><div class="ai-flow-copy"><div class="ai-flow-title">AI展開予想</div><div class="ai-flow-sub">過去走・脚質・枠順・テン・隣接圧力から局面ごとの隊列を表示</div></div><span class="ai-flow-scenario">'+esc(plan.scenario.code)+' '+esc(plan.scenario.title)+'</span></div><div class="ai-stage-tabs">'+stages.map(function(s,i){return'<button data-pace-stage="'+i+'" class="'+(i===0?'active':'')+'">'+esc(s.label)+'</button>'}).join('')+'</div><div class="ai-race-swipe-hint">図の左半分タップ＝前の局面　／　右半分タップ＝次の局面</div><div class="ai-race-topline"><div class="ai-race-meta-chip">'+esc(r.track)+'　'+esc(r.distance)+'m　'+esc(cp.turn)+(cp.shape==='straight'?'':'回り')+'</div><div class="ai-race-axis-strip"><span>← 後方</span><span>前方・先頭 →</span></div></div><div class="ai-race-board-wrap"><div id="pace-board" class="ai-race-visual">'+hs.map(function(h){return'<div class="ai-race-runner" data-horse="'+esc(h.horseNumber)+'" style="left:10%;top:50%">'+badge(h)+'</div>'}).join('')+'</div></div><div id="course-order" class="ai-race-order-panel">隊列を準備中</div><div id="pace-event" class="ai-stage-event">展開イベントを準備中</div><div class="ai-race-note">赤枠内は馬番のみ表示。説明文は下に分離し、右が先頭、左が後方です。</div></section>'}
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
function refreshPayoutsOnly(attempt){
  var r=state.race;
  if(!r||!r.id||state.payoutBusy)return;
  state.payoutBusy=true;
  fetchEdgeRace(r.id)
    .then(function(body){
      if(!body||!state.race||String(state.race.id)!==String(r.id))return;
      state.race=applySummaryEnvironment(body);
      saveDetailCache(r.id,state.race);
      render()
    })
    .catch(function(){})
    .finally(function(){state.payoutBusy=false})
}



function prepareRacePriority(id){return}
function idleTask(fn,delay){
  delay=n(delay,1200);
  if(window.requestIdleCallback){
    setTimeout(function(){requestIdleCallback(function(){try{fn()}catch(e){}},{timeout:1800})},delay)
  }else setTimeout(function(){try{fn()}catch(e){}},delay)
}

function diagnosisCurrent(r){
  var pm=r&&r.preparedMeta||{};
  return pm.diagnosisReady===true&&pm.diagnosisVersion==='kraiz-commercial-2026.09-v9'
}
function ensureAutoDiagnosis(id){scheduleVisibleRefresh()}
function checkSnapshotVersion(id,cached,seq){return refreshVisibleDetail()}

var pastPackJobs={};
function warmPastPack(r){return}

function openRace(id,keepStack,skipHistory){
  if(!id||state.raceLoading)return;
  if(state.oddsTimer){clearTimeout(state.oddsTimer);state.oddsTimer=null}
  state.oddsBusy=false;
  if(state.environmentTimer){clearTimeout(state.environmentTimer);state.environmentTimer=null}
  state.openPanel='entry';
  var seq=++state.detailSeq;
  if(!keepStack){state.raceStack=[];state.raceReturnPicker=state.picker}
  state.horseModalNo=null;
  if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
  state.error=null;
  state.picker=false;
  state.scenarioCode=null;
  state.paceStage=0;

  var cached=instantTrackDetails[String(id)]||loadDetailCache(id);
  var hasCached=!!(cached&&((cached.horses||[]).length||isFinal(cached)));

  if(hasCached){
    state.raceLoading=null;
    state.race=applySummaryEnvironment(cached);
    render();
    refreshVisibleDetail();
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
      state.error='Cloudflareにこのレース詳細がまだありません。次回同期後に更新してください。';
      if(state.raceStack.length)state.race=state.raceStack.pop();
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
function mergeOddsPayload(body){if(!state.race||!body)return false;var changed=false,hs=state.race.horses||[],rows=body.horses||[],map={},i,z,h;for(i=0;i<rows.length;i++){z=rows[i]||{};if(n(z.horseNumber)>0)map[n(z.horseNumber)]=z}for(i=0;i<hs.length;i++){h=hs[i];z=map[n(h.horseNumber)];if(!z)continue;if(z.winOdds!=null&&String(z.winOdds)!==''){h.winOdds=z.winOdds;changed=true}if(z.popularity!=null&&String(z.popularity)!==''){h.popularity=z.popularity;changed=true}if(z.bodyWeight!=null&&String(z.bodyWeight)!==''){h.bodyWeight=z.bodyWeight;changed=true}if(z.bodyWeightChange!=null&&String(z.bodyWeightChange)!==''){h.bodyWeightChange=z.bodyWeightChange;changed=true}if(z.oddsSource)h.oddsSource=z.oddsSource}if(body.oddsSource)state.race.oddsSource=body.oddsSource;if(body.oddsUpdatedAt)state.race.oddsUpdatedAt=body.oddsUpdatedAt;return changed}
function refreshRaceAfterCollect(id,attempt){reloadCurrent()}
function collectRaceInfo(no){reloadCurrent()}
function stopTimer(){if(state.timer){clearTimeout(state.timer);state.timer=null}if(state.anim){cancelAnimationFrame(state.anim);state.anim=null}state.simRunning=false}
function drawPaceStage(idx){if(!state.race||!state.pred)return;var plan=activeScenarioPlan(state.pred);if(!plan||!plan.stages)return;var stages=plan.stages,st=stages[clamp(idx,0,stages.length-1)],r=state.race,board=document.getElementById('pace-board');if(!st||!board)return;state.paceStage=clamp(idx,0,stages.length-1);var order=[],i,z,chip,left,top,rank,rowIdx;for(i=0;i<st.pack.length;i++){z=st.pack[i];rank=i;rowIdx=rank%4;chip=board.querySelector('[data-horse="'+z.no+'"]');if(!chip)continue;left=clamp(90-rank*5.9-n(z.gap)*58,8,92);top=clamp(16+rowIdx*20+n(z.lane)*2.4,12,88);chip.style.left=left+'%';chip.style.top=top+'%';order.push(z.no)}var ob=document.getElementById('course-order');if(ob)ob.innerHTML='<b>'+esc(st.label)+'</b><span>'+order.map(function(no){var h=horseByNo(r,no);return esc(no)+(h?' '+esc(h.name):'')}).join(' → ')+'</span>';var ev=document.getElementById('pace-event');if(ev)ev.innerHTML=stageNarrative(state.pred,idx);var bs=document.querySelectorAll('[data-pace-stage]');for(i=0;i<bs.length;i++)bs[i].className=n(bs[i].getAttribute('data-pace-stage'))===idx?'active':''}
function render(){var savedY=window.scrollY;stopTimer();try{syncLocation();if(state.raceLoading)app.innerHTML=renderRaceLoading();else if(state.race)app.innerHTML=renderRace();else if(state.picker)app.innerHTML=renderPicker();else if(state.track)app.innerHTML=renderVenue();else app.innerHTML=renderHome();bind();if(state.race){initPaceBoard()}scheduleVisibleRefresh();window.scrollTo(0,savedY)}catch(e){app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(e&&e.message||e)+'<br><button onclick="location.reload()">再読み込み</button></div>'}}
function goHome(){
  ++state.detailSeq;
  state.raceLoading=null;state.race=null;state.track=null;state.picker=false;state.horseModalNo=null;
  state.raceStack=[];state.pred=null;state.error=null;state.openPanel=null;
  clearTimeout(state.refreshTimer);clearTimeout(state.oddsTimer);clearTimeout(state.historyTimer);
  render();window.scrollTo(0,0)
}
function canGoBack(){return !!(state.horseModalNo||state.raceLoading||state.race||state.picker||state.track)}
function goBack(){
    if(window.history&&window.history.state&&window.history.state.keibaDepth>0){window.history.back();return}
    if(!canGoBack())return;
    if(state.horseModalNo){closeHorseModal();return}
    ++state.detailSeq;
    if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}
    if(state.collectTimer){clearTimeout(state.collectTimer);state.collectTimer=null}
    state.collectingHorse=null;state.error=null;state.pred=null;state.scenarioCode=null;state.paceStage=0;
    if(state.raceLoading||state.race){
        state.raceLoading=null;state.race=state.raceStack.length?state.raceStack.pop():null;
        if(!state.race)state.picker=state.raceReturnPicker;
    }else if(state.picker)state.picker=false;
    else state.track=null;
    render();

}
var navigationRestoring=false,routeKey=null;
function locationState(){return {tab:state.detailTab||'出走表',date:state.date,circuit:state.circuit,track:state.track,picker:state.picker,race_id:String(state.raceLoading||(state.race&&state.race.id)||''),horse:null,stack:state.raceStack.map(function(r){return r.id}),returnPicker:state.raceReturnPicker}}
function syncLocation(){try{if(navigationRestoring||!window.history)return;var view=locationState(),key=JSON.stringify(view);if(key===routeKey)return;var u=new URL(window.location.href);u.pathname=view.race_id?'/race':(view.track?'/venue':'/');['date','circuit','track','race_id','horse','tab'].forEach(function(k){if(view[k])u.searchParams.set(k,view[k]);else u.searchParams.delete(k)});if(view.picker)u.searchParams.set('picker','1');else u.searchParams.delete('picker');var prior=window.history.state||{},depth=n(prior.keibaDepth);if(routeKey===null)window.history.replaceState({keibaDepth:depth,view:view},'',u);else window.history.pushState({keibaDepth:depth+1,view:view},'',u);routeKey=key}catch(e){/* iOS may reject history changes during install; keep the screen usable. */}}
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
  state.diagnosisBusy=true;
  state.analysisSaved={};
  try{delete state.race._prediction}catch(e){}
  state.pred=null;
  render();
  refreshVisibleDetail().finally(function(){state.diagnosisBusy=false})
}
function pollDiagnosisRefresh(id,attempt){return}

function bind(){document.querySelectorAll('[data-action="home"]').forEach(function(el){el.onclick=goHome});document.querySelectorAll('[data-panel]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}var key=el.getAttribute('data-panel'),opening=state.openPanel!==key;state.openPanel=opening?key:null;render();if(opening&&key==='result'&&state.race&&isFinal(state.race)&&!(((state.race.result||{}).payouts||[]).length))setTimeout(function(){refreshPayoutsOnly(0)},0)}});document.querySelectorAll('[data-action="odds-update"]').forEach(function(el){el.onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}refreshOddsOnly(true)}});document.querySelectorAll('[data-dashboard-tab]').forEach(function(el){el.onclick=function(){state.detailTab=el.getAttribute('data-dashboard-tab');var id=el.getAttribute('data-tab-race');if(state.race&&String(state.race.id)===id)render();else openRace(id,false,false)}});document.querySelectorAll('.cinema-venue img').forEach(function(img){img.onerror=function(){this.style.display='none';var parent=this.parentElement;if(parent&&!parent.querySelector('.venue-photo-missing')){var label=document.createElement('span');label.className='venue-photo-missing';label.textContent='写真を読み込めません';parent.appendChild(label)}}});document.querySelectorAll('[data-date]').forEach(function(el){el.onclick=function(){++state.detailSeq;state.raceLoading=null;state.date=el.getAttribute('data-date');state.openPanel=null;state.race=null;state.track=null;state.picker=false;load()}});document.querySelectorAll('[data-detail-tab]').forEach(function(el){el.onclick=function(){state.detailTab=el.getAttribute('data-detail-tab');render()}});var els=document.querySelectorAll('[data-circuit]'),i;for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.circuit=this.getAttribute('data-circuit');state.openPanel=null;state.track=null;state.race=null;state.picker=false;load()};var d=document.getElementById('date');if(d)d.onchange=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.date=this.value;state.openPanel=null;state.track=null;state.race=null;state.picker=false;load()};els=document.querySelectorAll('[data-track]');for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];++state.detailSeq;state.raceLoading=null;state.race=null;state.pred=null;state.picker=false;state.track=this.getAttribute('data-track');var dc=this.getAttribute('data-circuit');if(dc)state.circuit=dc;state.openPanel=null;state.detailTab='出走表';mergeCachedVolatilityForTrack(state.track);window.scrollTo(0,0);render();warmTrackSnapshots(state.track,true)};els=document.querySelectorAll('[data-race]');for(i=0;i<els.length;i++)els[i].onclick=function(){var id=this.getAttribute('data-race'),row=state.races.find(function(x){return String(x.id)===String(id)});if(row)state.track=row.track;window.scrollTo(0,0);openRace(id,false,false)};els=document.querySelectorAll('[data-past-race]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openPastRace(this.getAttribute('data-past-race'))};var b=document.querySelectorAll('[data-action="back"]');for(i=0;i<b.length;i++)b[i].onclick=goBack;var rr=document.querySelectorAll('[data-action="reload"]');for(i=0;i<rr.length;i++)rr[i].onclick=reloadCurrent;var fi=document.querySelectorAll('[data-action="fetch-all-info"]');for(i=0;i<fi.length;i++)fi[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(null)};var rh=document.querySelectorAll('[data-action="retry-history"]');for(i=0;i<rh.length;i++)rh[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(null)};els=document.querySelectorAll('[data-horse-fetch]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}collectRaceInfo(this.getAttribute('data-horse-fetch'))};var ar=document.querySelectorAll('[data-action="all-races"]');for(i=0;i<ar.length;i++)ar[i].onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};var pn=document.querySelector('[data-action="pace-next"]');if(pn)pn.onclick=function(){var x=nextRace();if(x){openRace(x.id,false,false)}};var pp=document.querySelector('[data-action="pace-pick"]');if(pp)pp.onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};els=document.querySelectorAll('[data-horse-open]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openHorseModal(this.getAttribute('data-horse-open'))};els=document.querySelectorAll('[data-horse-close]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}closeHorseModal()};els=document.querySelectorAll('[data-horse-prev]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(-1)};els=document.querySelectorAll('[data-horse-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(1)};els=document.querySelectorAll('[data-scenario-code]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}state.scenarioCode=this.getAttribute('data-scenario-code');state.paceStage=0;render()};els=document.querySelectorAll('[data-pace-stage]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}drawPaceStage(n(this.getAttribute('data-pace-stage'),0))};var board=document.getElementById('pace-board');if(board){board.onclick=function(e){if(e&&e.target&&e.target.closest&&e.target.closest('button,a,input,select,textarea'))return;var rect=board.getBoundingClientRect(),plan=activeScenarioPlan(state.pred),len=(plan&&plan.stages?plan.stages.length:0);if(!len)return;var cur=n(state.paceStage,0),dir=(e.clientX-rect.left)<rect.width/2?-1:1,nx=(cur+dir+len)%len;drawPaceStage(nx)}}var panel=document.getElementById('horse-modal-panel');if(panel){panel.onclick=function(e){if(e&&e.target&&e.target.closest&&e.target.closest('button,a,input,select,textarea,summary'))return;var rect=panel.getBoundingClientRect();moveHorseModal((e.clientX-rect.left)<rect.width/2?-1:1)}}}
function initPaceBoard(){if(!state.pred)return;var plan=activeScenarioPlan(state.pred);if(!plan||!plan.stages)return;drawPaceStage(clamp(state.paceStage,0,plan.stages.length-1))}

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
  var d=state.date,seq=++state.requestSeq,
      embedded=(!force&&window.__KRAIZ_BOOTSTRAP__&&window.__KRAIZ_BOOTSTRAP__.date===d)?window.__KRAIZ_BOOTSTRAP__:null,
      full=force?null:loadFullBundle(d),
      listCache=force?null:loadRaceCache(d,'__ALL__');
  state.error=null;state.bootstrapReady=false;state.bootstrapProgress=null;

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

  // 2) Race summaries: Cloudflare/D1 first, Render only as fallback.
  function requestList(attempt){
    attempt=n(attempt,0);

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
              if((r[k]==null||r[k]===''||r[k]==='不明'||(k==='volatility'&&!r[k].ready))&&z[k]!=null&&z[k]!==''&&z[k]!=='不明')r[k]=z[k]
            })
        });

        state.races=rows;
        saveRaceCache(d,'__ALL__',rows);
        state.loading=false;
        render();
        if(state.track)warmTrackSnapshots(state.track,true)
      }else if(!state.races.length&&attempt<8){
        setTimeout(function(){requestList(attempt+1)},700)
      }
    })
    .catch(function(){
      if(seq!==state.requestSeq||state.date!==d)return;
      if(!state.races.length&&attempt<2){setTimeout(function(){requestList(attempt+1)},900)}else{state.loading=false;state.error='データを取得できません。通信状態を確認して更新してください。';render()}
    })
  }

  // 3) Details arrive separately and never block the home/venue list.
  function requestDetails(attempt){return}

  requestList(0)
}
window.onerror=function(msg){if(app)app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(msg)+'<br><button onclick="location.reload()">再読み込み</button></div>';return false};
document.addEventListener('visibilitychange',function(){if(!document.hidden){if(state.race)refreshVisibleDetail();else scheduleVisibleRefresh()}else clearTimeout(state.refreshTimer)});
installNavigation();installEdgeBack();installPwaCache();restoreLocation();setTimeout(load,0);
})();
