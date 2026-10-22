/* Present server-produced pre-off provisional marks; NEVER derive predictions here. */
(function(root){
  'use strict';
  // Only an immutable user-owned pre-off receipt can supply forecast marks.
  // All assistant-introduced probabilistic/provisional and post-off models are retired.
  var last={active:false,source:'',marks:[],status:'not-generated'};

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
    if(root.ARVEXQProductionTickets)root.ARVEXQProductionTickets.build(race);
    var model=root.ARVEXQProductionTickets&&root.ARVEXQProductionTickets.approvedForecast&&
      root.ARVEXQProductionTickets.approvedForecast(race);
    // Preserve immutable user-owned historical receipt ahead of a new model.
    var stored=originalMarks(race);
    if(model&&!stored){
      var byNo={};
      model.probabilities.forEach(function(x){byNo[x.horseNumber]=x});
      var modelRows=(race.horses||[]).filter(function(h){return h&&Number(h.horseNumber)>0})
        .map(function(h){
          var x=byNo[Number(h.horseNumber)];
          return {horse:h,predMark:x.mark,serverPreoffMark:true,
            originalPreoffMark:!!x.mark,referencePostoffMark:false,
            predRank:999,winProbability:x.win,p1Probability:x.win,
            p2Probability:x.top2,p3Probability:x.top3,
            overallGrade:'',coverage:1};
        });
      last={active:true,source:'approved-model',status:'model-approved',
        unavailable:false,marks:modelRows.filter(function(x){return !!x.predMark})
          .map(function(x){return {horseNumber:Number(x.horse.horseNumber),
            name:String(x.horse.name||''),mark:x.predMark};})};
      return {rows:modelRows,legacyEngineDisabled:true,approvedForecast:model,
        scenarios:model.scenarios.map(function(x,i){return {code:'trained-'+i,
          prob:x.probability,order:x.horses};}),
        plans:{verified:model.pace},plan:model.pace,
        suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:1};
    }
    var marks=stored,rows=((race&&race.horses)||[])
      .filter(function(h){return h&&Number(h.horseNumber)>0})
      .map(function(h){
        var id=String(Number(h.horseNumber)),mark=marks&&marks[id]||'';
        return {horse:h,predMark:mark,serverPreoffMark:false,
          originalPreoffMark:!!mark&&!!marks,referencePostoffMark:false,
          predRank:999,winProbability:null,p1Probability:null,p2Probability:null,
          p3Probability:null,overallGrade:'',coverage:0};
      });
    last={active:!!marks,source:marks?'saved-preoff':'',unavailable:!marks,
      status:marks?'saved-preoff':(race&&race.predictionStatus==='disabled'?'model-disabled':'no-verified-preoff-receipt'),
      marks:marks?rows.filter(function(r){return !!r.predMark}).map(function(r){
        return {horseNumber:Number(r.horse.horseNumber),name:String(r.horse.name||''),mark:r.predMark};
      }):[]};
    return {rows:rows,legacyEngineDisabled:true,scenarios:[],plans:{},plan:null,
      suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:0};
  }
  function current(){
    return {active:last.active,source:last.source||'',status:last.status,
      unavailable:!!last.unavailable,marks:last.marks.map(function(x){return Object.assign({},x)})};
  }
  root.ARVEXQProductionPrediction=Object.freeze({build:build,current:current});
})(typeof window!=='undefined'?window:globalThis);
