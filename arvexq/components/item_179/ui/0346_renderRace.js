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
    if(isFinal(r))content+=savedRevisionOriginalHtml(r)
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
      '<div class="smart-race-content">'+content+window.ARVEXQPredictionFrame.render()+window.ARVEXQMarkFrame.render()+window.ARVEXQTicketFrame.render()+'</div>'+ 
    '</main>'+ 
    cinematicFooter()+
  '</div>'
}

