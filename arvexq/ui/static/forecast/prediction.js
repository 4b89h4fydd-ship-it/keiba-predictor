/* Present server-produced pre-off provisional marks; NEVER derive predictions here. */
(function(root){
  'use strict';
  // Original receipts remain authoritative. The user-approved Stage64 trial
  // may supply separately labeled, provisional pre-off research roles only.
  var last={active:false,source:'',marks:[]};
  var latestTrialRace=null;

  function stage64Trial(race){
    if(!race||!race.id||!race.date||!Array.isArray(race.horses))return null;
    var f=race.researchShadow&&race.researchShadow.stage64;
    if(!f||f.raceId!==race.id||f.date!==race.date)return null;
    if((race.circuit==='中央'||race.circuit==='jra')?f.circuit!=='jra':
       (race.circuit==='地方'||race.circuit==='nar')?f.circuit!=='nar':true)return null;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(race.date)||
       !/^([01]\d|2[0-3]):[0-5]\d$/.test(String(race.startTime||'')))return null;
    var off=Date.parse(race.date+'T'+race.startTime+':00+09:00');
    if(!Number.isFinite(off)||Date.now()>=off||race.result&&race.result.status==='確定')return null;
    var stages=f.stages||{},marks=stages.marks&&stages.marks.value||null,
        ticket=stages.tickets&&stages.tickets.value||null;
    if(!marks||!ticket||!marks.winRole||!marks.axisRole||
       !Array.isArray(ticket.hypotheticalTrifectaTop10))return null;
    var known={},number;
    for(var i=0;i<race.horses.length;i++){
      number=Number(race.horses[i]&&race.horses[i].horseNumber);
      if(!Number.isInteger(number)||number<=0||known[number])return null;
      known[number]=true;
    }
    var win=Number(marks.winRole.horseNumber),axis=Number(marks.axisRole.horseNumber);
    if(!known[win]||!known[axis])return null;
    for(var j=0;j<ticket.hypotheticalTrifectaTop10.length;j++){
      var combo=ticket.hypotheticalTrifectaTop10[j];
      if(!Array.isArray(combo)||combo.length!==3||new Set(combo.map(Number)).size!==3||
         combo.some(function(n){return !known[Number(n)]}))return null;
    }
    return f;
  }


  function originalMarks(race){
    var tickets=root.ARVEXQProductionTickets;
    var receipt=tickets&&tickets.validatedReceipt&&tickets.validatedReceipt(race);
    if(!receipt||!Array.isArray(race.horses)||!Array.isArray(receipt.marks))return null;
    // Prevent a receipt for a partial/different field being displayed as today's marks.
    var known={},field=race.horses.filter(function(h){
      return h&&Number.isInteger(Number(h.horseNumber))&&Number(h.horseNumber)>0;
    });
    if(field.length<5||field.length!==receipt.marks.length)return null;
    for(var i=0;i<field.length;i++){
      var id=String(Number(field[i].horseNumber));
      if(known[id])return null;
      known[id]=true;
    }
    var marks={};
    for(var j=0;j<receipt.marks.length;j++){
      var row=receipt.marks[j],no=String(Number(row.horseNumber));
      if(!known[no]||Object.prototype.hasOwnProperty.call(marks,no))return null;
      // Historical records retain their original symbol, not a new ranking.
      var mark=String(row.mark||'');
      if(['','◎','○','▲','△','☆','☆+','注'].indexOf(mark)<0)return null;
      marks[no]=mark;
    }
    return marks;
  }

  function build(race){
    // Clear prior races before any validation to prevent stale ticket display.
    latestTrialRace=null;
    if(root.ARVEXQProductionTickets)root.ARVEXQProductionTickets.build(race);
    var marks=originalMarks(race),trial=marks?null:stage64Trial(race),
        roles=trial&&trial.stages.marks.value,win=roles&&Number(roles.winRole.horseNumber),
        axis=roles&&Number(roles.axisRole.horseNumber),
        rows=((race&&race.horses)||[])
      .filter(function(h){return h&&Number(h.horseNumber)>0})
      .map(function(h){
        var id=String(Number(h.horseNumber)),no=Number(id),
            mark=marks&&marks[id]||((trial&&(no===win||no===axis))?'◎':''),
            stage64Role=trial?(no===win&&no===axis?'win-axis':(no===win?'win':(no===axis?'axis':''))):'';
        return {horse:h,predMark:mark,serverPreoffMark:false,
          stage64Provisional:!!stage64Role,honmeiRole:stage64Role,
          originalPreoffMark:!!mark&&!!marks,referencePostoffMark:false,
          predRank:999,winProbability:null,p1Probability:null,p2Probability:null,
          p3Probability:null,overallGrade:'',coverage:0};
      });
    latestTrialRace=trial?race:null;
    last={active:!!(marks||trial),source:marks?'saved-preoff':(trial?'stage64-provisional':''),
      unavailable:!marks&&!trial,
      marks:(marks||trial)?rows.filter(function(r){return !!r.predMark}).map(function(r){
        return {horseNumber:Number(r.horse.horseNumber),
          name:String(r.horse.name||''),mark:r.predMark,
          role:r.stage64Provisional?r.honmeiRole:'',
          stage64Provisional:!!r.stage64Provisional};
      }):[]};
    return {rows:rows,legacyEngineDisabled:!trial,scenarios:[],plans:{},plan:null,
      suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:0};
  }
  function current(){
    return {active:last.active,source:last.source||'',unavailable:!!last.unavailable,marks:last.marks.map(function(x){return Object.assign({},x)})};
  }
  function currentTrialRace(){
    // The existing ticket frame is rendered without arguments by renderRace.
    // Only return the race whose six-stage preoff candidate passed validation.
    return latestTrialRace&&stage64Trial(latestTrialRace)?latestTrialRace:null;
  }
  root.ARVEXQProductionPrediction=Object.freeze({
    build:build,current:current,trial:stage64Trial,currentTrialRace:currentTrialRace
  });
})(typeof window!=='undefined'?window:globalThis);
