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
    var expectedPost=Date.parse(String(race.date)+'T'+String(race.scheduledStartTime||race.startTime||'').slice(0,5)+':00+09:00');
    var createdAt=Date.parse(String(rev.createdAt||''));
    var verifiedPreoff=rev.analysisType==='preoff-candidate'&&
      Number.isFinite(expectedPost)&&Number.isFinite(createdAt)&&createdAt<expectedPost;
    return {marks:marks,kind:verifiedPreoff?'preoff-candidate':'retrospective',scenarios:rev.scenarioSummaries||[],
            forecastText:String(rev.forecastText||''),modelVersion:rev.modelVersion||'',uncalibrated:rev.probabilityModelStatus!=='calibrated'};
  }

  function build(race){
    var server=race&&race.predictionStatus==='ready'&&race.prediction;
    if(server&&server.predictionStatus==='ready'&&Array.isArray(race.horses)){
      var stage=server.stages||{}, prob=(stage.probability&&stage.probability.value)||{}, marks=race.predictionMarks||[], by={};
      marks.forEach(function(x){by[String(Number(x.horseNumber))]=x});
      var rows=race.horses.filter(function(h){return h&&Number(h.horseNumber)>0}).map(function(h){
        var no=Number(h.horseNumber),m=by[String(no)]||{};
        return {horse:h,predMark:String(m.mark||''),serverPreoffMark:!!m.mark,
          originalPreoffMark:false,referencePostoffMark:false,revisionCandidateMark:false,
          predRank:marks.findIndex(function(x){return Number(x.horseNumber)===no})+1,
          winProbability:prob.win&&prob.win[no]!=null?prob.win[no]:null,
          p1Probability:prob.win&&prob.win[no]!=null?prob.win[no]:null,p2Probability:null,
          p3Probability:prob.top3&&prob.top3[no]!=null?prob.top3[no]:null,overallGrade:'',coverage:1};
      });
      // Stage64 pace is an array of scenarios, each keyed by actual horse number.
      // The array index is not a horse number and the correction is not a calibrated pace prediction.
      var pace=(stage.pace&&stage.pace.value)||[],paceRows=[];
      if(Array.isArray(pace))pace.forEach(function(deltas,index){
        if(!deltas||typeof deltas!=='object'||Array.isArray(deltas))return;
        Object.keys(deltas).forEach(function(key){
          var no=Number(key),delta=Number(deltas[key]);
          if(Number.isInteger(no)&&no>0&&Number.isFinite(delta))
            paceRows.push({scenarioIndex:index+1,horseNumber:no,delta:delta});
        });
      });
      last={active:marks.length>0,source:'stage64-preoff',scenarios:[],pace:paceRows,
        forecastText:String(server.forecastText||''),
        modelVersion:server.modelVersion||'',uncalibrated:!(stage.probability&&stage.probability.calibrationVerified===true),unavailable:!marks.length,
        marks:marks.map(function(x){var h=race.horses.find(function(y){return Number(y.horseNumber)===Number(x.horseNumber)})||{};return {horseNumber:Number(x.horseNumber),name:String(h.name||''),mark:String(x.mark||'')}})};
      return {rows:rows,legacyEngineDisabled:false,scenarios:[],plans:{},plan:null,suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:1};
    }
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
      scenarios:revision?revision.scenarios:[],forecastText:revision?revision.forecastText:'',modelVersion:revision?revision.modelVersion:'',
      uncalibrated:!!revision&&revision.uncalibrated,unavailable:!marks,
      marks:marks?rows.filter(function(r){return !!r.predMark}).map(function(r){
        return {horseNumber:Number(r.horse.horseNumber),name:String(r.horse.name||''),mark:r.predMark};
      }):[]};
    return {rows:rows,legacyEngineDisabled:true,scenarios:[],plans:{},plan:null,
      suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:0};
  }
  function current(){
    return {active:last.active,source:last.source||'',unavailable:!!last.unavailable,
      scenarios:(last.scenarios||[]).slice(),pace:(last.pace||[]).slice(),forecastText:last.forecastText||'',modelVersion:last.modelVersion||'',uncalibrated:!!last.uncalibrated,
      marks:last.marks.map(function(x){return Object.assign({},x)})};
  }
  root.ARVEXQProductionPrediction=Object.freeze({build:build,current:current});
})(typeof window!=='undefined'?window:globalThis);
