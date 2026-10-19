function aiStatsDayTitle(){
  if(state.date===today())return '本日のAI成績';
  var p=String(state.date||'').split('-'),m=n(p[1]),d=n(p[2]);
  return (m&&d)?(m+'月'+d+'日のAI成績'):'当日のAI成績'
}

var selectedRacePreload={date:'',busy:{},done:{},timer:null,fullLoaded:false,fullLoading:false,loadedCount:0,expectedCount:0,lastError:''},fastTopRefresh=null,selectedSectionsOpen={selected:false},selectedCircuitSectionsOpen={selected:{'中央':false,'地方':false}};
