function courseStageFrac(r,st){
  r=r||{};
  var p=courseProfile(r);
  if(p.shape==="straight")return st===0?.05:(st===1?.67:.92);
  var laps=Math.max(.1,n(r.distance,1200)/p.lap),start=normFrac(.965-p.dir*(laps%1)),prog=st===0?.015:(st===1?.81:.965);
  return normFrac(start+p.dir*laps*prog)
}
var app=document.getElementById("app");
var state={date:today(),circuit:"地方",races:[],track:null,race:null,raceLoading:null,picker:false,loading:false,error:null,timer:null,anim:null,simSpeed:5,simTarget:20,simRunning:false,simPaused:false,simStopped:false,simIndex:0,simDone:0,simCounts:null,simCurrentT:0,pred:null,requestSeq:0,detailSeq:0,raceReturnPicker:false,historyTimer:null,raceStack:[],historyPrefetch:{},paceStage:0,horseModalNo:null,detailHorseNo:null,subPage:null,subPageReturnPanel:null,collectingHorse:null,collectTimer:null,scenarioCode:null,analysisSaved:{},openPanel:null,oddsBusy:false,oddsRefreshAt:{},oddsTimer:null,environmentTimer:null,environmentBusy:false,bootstrapReady:false,bootstrapProgress:null,resultTimer:null,homePage:null,aiStatsTrack:null,pickCircuit:null,raceReturnHomePage:null,raceReturnPickCircuit:null};

// Race favorites are a user-only display preference. They never affect AI marks or bets.
var FAVORITE_RACES_KEY="arvexq:favorite-races:v1";
