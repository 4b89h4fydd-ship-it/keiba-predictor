function favoriteHomeSection(){
  var rows=favoriteRaces.filter(function(x){return x.date===state.date}).slice().sort(function(a,b){
    return String(a.startTime||'').localeCompare(String(b.startTime||''))||String(a.track||'').localeCompare(String(b.track||''),'ja')||n(a.raceNumber)-n(b.raceNumber)
  });
  if(!rows.length)return '';
  return '<section class="arv-favorites-home" aria-label="お気に入りレース">'+
    '<header class="arv-favorites-heading"><strong>★ お気に入りレース</strong><span>'+rows.length+'件</span></header>'+
    '<div class="arv-favorites-list">'+rows.map(function(saved){
      var r=state.races.find(function(x){return String(x.id)===String(saved.id)})||saved;
      var lifecycle=window.ARVEXQUnifiedHome&&window.ARVEXQUnifiedHome.raceStatus?
        window.ARVEXQUnifiedHome.raceStatus('horse',r,state.date,new Date()):'upcoming';
      return '<div class="arv-favorite-home-row"><button type="button" class="arv-favorite-home-open" data-race="'+esc(r.id)+'" data-race-state="'+esc(lifecycle)+'">'+
        '<span class="arv-favorite-race-label"><strong>'+esc(r.track||saved.track)+' '+esc(r.raceNumber||saved.raceNumber)+'R</strong><small>'+esc(r.title||saved.title||'')+'</small></span>'+
        '<span class="arv-favorite-home-meta"><time>'+esc(r.startTime||saved.startTime||'--:--')+'</time><em class="arv-race-state">'+esc(window.ARVEXQUnifiedHome?window.ARVEXQUnifiedHome.labelFor(lifecycle):'')+'</em></span><span aria-hidden="true">›</span></button>'+
        favoriteStarHtml({id:saved.id,date:saved.date},'arv-home-favorite-star')+'</div>'
    }).join('')+'</div></section>'
}

var dailyAiStats={date:"",loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,centralPodiumHits:0,centralPodiumTotal:0,localPodiumHits:0,localPodiumTotal:0,markedPodiumSum:0,holePlaceHits:0,top2Hits:0,top3Hits:0,candidateOrderMisses:0,candidateMisses:0,highConfHits:0,highConfTotal:0,brierSum:0,logLossSum:0,reasons:{},rows:[],error:""},dailyAiStatsJob=0;
var previousAiStats={date:"",loading:false,done:false,total:0,finalCount:0,winHits:0,markHits:0,fullPodiumHits:0,markedPodiumSum:0,rows:[],error:""},previousAiStatsJob=0;
var liveCenterOpen=false,liveCenterTrack="",liveCenterCircuit="";

var ARVEXQ_RACE_CACHE_SCHEMA="horse-race-source-v362";
