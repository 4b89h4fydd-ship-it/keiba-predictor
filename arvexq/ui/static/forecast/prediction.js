/* Present server-produced pre-off provisional marks; NEVER derive predictions here. */
(function(root){
  'use strict';
  // Original sealed marks take priority. An existing model revision is clearly labelled provisional/retrospective.
  // All assistant-introduced probabilistic/provisional and post-off models are retired.
  var last={active:false,source:'',marks:[]};

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

  function revisionMarks(race){
    var rev=race&&race._forecastRevisionView;
    if(!rev||rev.version!=='arvexq-forecast-revision-v1'||
       rev.raceId!==race.id||rev.raceDate!==race.date||
       !['candidate-analysis'].includes(rev.predictionStatus)||
       !['retrospective','preoff-candidate'].includes(rev.analysisType)||
       !Array.isArray(rev.horses)||!Array.isArray(race.horses))return null;
    var active=race.horses.filter(function(h){return h&&Number(h.horseNumber)>0&&!h.scratched&&!h.withdrawn;});
    if(active.length<3||active.length!==rev.horses.length)return null;
    var allowed={'':1,'◎':1,'○':1,'▲':1,'△':1,'☆':1,'注':1};
    var known={},marks={},count=0;
    for(var i=0;i<active.length;i++){
      var n=Number(active[i].horseNumber);
      if(!Number.isInteger(n)||n<=0||known[n])return null;
      known[n]=true;
    }
    for(var j=0;j<rev.horses.length;j++){
      var row=rev.horses[j],no=Number(row&&row.horseNumber),mark=String(row&&row.mark||'');
      if(!known[no]||Object.prototype.hasOwnProperty.call(marks,no)||
         !Object.prototype.hasOwnProperty.call(allowed,mark))return null;
      marks[no]=mark;
      if(mark==='◎')count++;
    }
    if(count!==1)return null;
    // Revision models are research-only; a preoff-candidate is NOT a saved original.
    return {marks:marks,kind:rev.analysisType,scenarios:rev.scenarioSummaries||[],
            modelVersion:rev.modelVersion||'',uncalibrated:rev.probabilityModelStatus!=='calibrated'};
  }

  function build(race){
    if(root.ARVEXQProductionTickets)root.ARVEXQProductionTickets.build(race);
    var originals=originalMarks(race),revision=originals?null:revisionMarks(race),
        marks=originals||(revision&&revision.marks),rows=((race&&race.horses)||[])
      .filter(function(h){return h&&Number(h.horseNumber)>0})
      .map(function(h){
        var id=String(Number(h.horseNumber)),mark=marks&&marks[id]||'';
        return {horse:h,predMark:mark,serverPreoffMark:false,
          originalPreoffMark:!!mark&&!!originals,referencePostoffMark:!!mark&&!!revision&&revision.kind==='retrospective',
          revisionCandidateMark:!!mark&&!!revision&&revision.kind==='preoff-candidate',
          predRank:999,winProbability:null,p1Probability:null,p2Probability:null,
          p3Probability:null,overallGrade:'',coverage:0};
      });
    last={active:!!marks,source:originals?'saved-preoff':(revision?'learned-revision-'+revision.kind:''),
      scenarios:revision?revision.scenarios:[],modelVersion:revision?revision.modelVersion:'',
      uncalibrated:!!revision&&revision.uncalibrated,unavailable:!marks,
      marks:marks?rows.filter(function(r){return !!r.predMark}).map(function(r){
        return {horseNumber:Number(r.horse.horseNumber),name:String(r.horse.name||''),mark:r.predMark};
      }):[]};
    return {rows:rows,legacyEngineDisabled:true,scenarios:[],plans:{},plan:null,
      suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:0};
  }
  function current(){
    return {active:last.active,source:last.source||'',unavailable:!!last.unavailable,
      scenarios:(last.scenarios||[]).slice(),modelVersion:last.modelVersion||'',uncalibrated:!!last.uncalibrated,
      marks:last.marks.map(function(x){return Object.assign({},x)})};
  }
  root.ARVEXQProductionPrediction=Object.freeze({build:build,current:current});
})(typeof window!=='undefined'?window:globalThis);
