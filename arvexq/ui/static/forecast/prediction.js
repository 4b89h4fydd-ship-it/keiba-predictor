/* Present server-produced pre-off provisional marks; NEVER derive predictions here. */
(function(root){
  'use strict';
  var VERSION='arvexq-observed-history-baseline-v1';
  var MARKS={'◎':1,'○':1,'▲':1,'△':1,'☆':1};
  var last={active:false,marks:[]};

  function authorized(race){
    if(!race||race.predictionStatus!=='provisional'||
       race.predictionModelVersion!==VERSION||
       !Array.isArray(race.predictionMarks)||!Array.isArray(race.horses)||
       (race.result&&race.result.status==='確定'))return null;
    var date=String(race.date||''),time=String(race.startTime||'').slice(0,5);
    if(!/^20\d\d-\d\d-\d\d$/.test(date)||!/^\d\d:\d\d$/.test(time))return null;
    var off=Date.parse(date+'T'+time+':00+09:00');
    if(!Number.isFinite(off)||Date.now()>=off)return null;
    var starters=race.horses.filter(function(h){
      return h&&!h.scratched&&!h.withdrawn&&!/^(?:取消|除外|競走除外)$/.test(String(h.status||''))&&
        Number.isInteger(Number(h.horseNumber))&&Number(h.horseNumber)>0;
    });
    if(starters.length<3||Number(race.predictionRunnerCount)!==starters.length)return null;
    var allowed={};
    for(var i=0;i<starters.length;i++){
      var no=String(Number(starters[i].horseNumber));
      if(allowed[no])return null;
      allowed[no]=1;
    }
    var marks={},count={'◎':0,'○':0,'▲':0};
    for(var j=0;j<race.predictionMarks.length;j++){
      var row=race.predictionMarks[j]||{},id=String(Number(row.horseNumber));
      var mark=String(row.mark||'');
      if(!allowed[id]||marks[id]||!MARKS[mark])return null;
      marks[id]=mark;
      if(Object.prototype.hasOwnProperty.call(count,mark))count[mark]++;
    }
    if(count['◎']!==1||count['○']!==1||count['▲']!==1)return null;
    return marks;
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
    // No model or bets are inferred in-browser, before or after the race.
    if(root.ARVEXQProductionTickets)root.ARVEXQProductionTickets.build(race);
    var live=authorized(race),stored=live?null:originalMarks(race),
        marks=live||stored,rows=((race&&race.horses)||[])
      .filter(function(h){return h&&Number(h.horseNumber)>0})
      .map(function(h){
        var id=String(Number(h.horseNumber)),mark=marks&&marks[id]||'';
        return {horse:h,predMark:mark,serverPreoffMark:!!mark&&!!live,originalPreoffMark:!!mark&&!!stored,
          predRank:999,winProbability:null,p1Probability:null,p2Probability:null,
          p3Probability:null,overallGrade:'',coverage:0};
      });
    last={active:!!marks,source:live?'live-preoff':(stored?'saved-preoff':''),marks:marks?rows.filter(function(r){return !!r.predMark}).map(function(r){
      return {horseNumber:Number(r.horse.horseNumber),name:String(r.horse.name||''),mark:r.predMark};
    }):[]};
    return {rows:rows,legacyEngineDisabled:true,scenarios:[],plans:{},plan:null,
      suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:0};
  }
  function current(){
    return {active:last.active,source:last.source||'',marks:last.marks.map(function(x){return Object.assign({},x)})};
  }
  root.ARVEXQProductionPrediction=Object.freeze({build:build,current:current});
})(typeof window!=='undefined'?window:globalThis);
