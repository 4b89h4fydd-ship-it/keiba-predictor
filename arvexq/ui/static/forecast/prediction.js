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

  // 2026 Kikuka Sho emergency route: display only verified source-bound
  // LEARNED research marks. No Stage64 fallback, no uncalibrated wagers.
  var KIKKA_NAMES=[
    'エムズビギン','コンジェスタス','アウダーシア',
    'ショウナンガルフ','ジャスティンシカゴ','バステール',
    'ラージアンサンブル','ロブチェン','ゴーイントゥスカイ',
    'ダノンヒストリー','アスクエジンバラ','サノノグレーター',
    'キンググローリー','マジョレルブルー','シートゥサミット',
    'ショウナンハヤナミ','チャリングクロス','ナリタエスペランサ'
  ];
  function kikkaCandidateMarks(race){
    var c=race&&race.kikkaCandidate;
    if(!race||race.id!=='jra-2026-10-25-京都-11'||
       race.date!=='2026-10-25'||race.track!=='京都'||
       Number(race.raceNumber)!==11||Number(race.distance)!==3000||
       String(race.surface||'').indexOf('芝')<0||
       String(race.scheduledStartTime||race.startTime||'').slice(0,5)!=='15:40'||
       !Array.isArray(race.horses)||race.horses.length!==18||
       !c||c.version!=='arvexq-kikka-urgent-learned-candidate-v1'||
       c.raceId!==race.id||c.raceDate!==race.date||
       c.modelVersion!=='arvexq-learned-whole-career-scenarios-v2'||
       c.provisional!==true||c.productionEligible!==false||
       c.bettingRecommended!==false||c.probabilityCalibration!=='unverified'||
       !/^20\d\d-\d\d-\d\d$/.test(String(c.trainedThrough||''))||
       c.trainedThrough>=race.date||
       !/^[a-f0-9]{64}$/i.test(String(c.sourceHash||''))||
       !/^[a-f0-9]{64}$/i.test(String(c.modelHash||''))||
       !Array.isArray(c.marks)||!c.marks.length)return null;
    var off=Date.parse('2026-10-25T15:40:00+09:00');
    var captured=Date.parse(String(c.capturedAt||''));
    if(!Number.isFinite(captured)||captured>=off||captured<Date.parse('2026-10-24T00:00:00+09:00'))return null;
    var names={},marks={},count=0,allowed={'◎':1,'○':1,'▲':1,'△':1,'☆':1,'注':1};
    for(var i=0;i<18;i++){
      var horse=race.horses[i],no=Number(horse&&horse.horseNumber);
      if(!Number.isInteger(no)||no<1||no>18||names[no]||String(horse.name||'')!==KIKKA_NAMES[no-1])
        return null;
      names[no]=true;
    }
    for(var j=0;j<c.marks.length;j++){
      var r=c.marks[j],n=Number(r&&r.horseNumber),m=String(r&&(r.markSymbol||r.mark)||'');
      if(!Number.isInteger(n)||!names[n]||marks[n]||!allowed[m])return null;
      marks[n]=m;
      if(m==='◎')count++;
    }
    if(count!==1||Object.keys(marks).length<5)return null;
    return {marks:marks,capturedAt:c.capturedAt,modelVersion:c.modelVersion};
  }

  function build(race){
    // Do not let the previous race's six-stage receipt leak into a race that
    // has no verified unified forecast.
    last={active:false,source:'',marks:[],scenarios:[],stages:[],pace:[],forecastText:'',modelVersion:'',uncalibrated:false,unavailable:true};
    if(race&&race.id==='jra-2026-10-25-京都-11'){
      var verified=kikkaCandidateMarks(race),marks=verified&&verified.marks||{};
      var rows=(race.horses||[]).filter(function(h){return h&&Number(h.horseNumber)>0;}).map(function(h){
        var no=Number(h.horseNumber),mark=marks[no]||'';
        return {horse:h,predMark:mark,serverPreoffMark:false,
          originalPreoffMark:false,referencePostoffMark:false,
          revisionCandidateMark:!!mark,predRank:999,winProbability:null,
          p1Probability:null,p2Probability:null,p3Probability:null,
          overallGrade:'',coverage:0};
      });
      last={active:!!verified,source:verified?'kikka-2026-learned-preoff-candidate':'',
        scenarios:[],pace:[],forecastText:verified?
          '菊花賞・発走前に保存した参考印。未使用レースでの勝率・3着内率の検証および確率校正は未完了。':
          '菊花賞の発走前予想は未保存です。',
        modelVersion:verified?verified.modelVersion:'',uncalibrated:true,
        unavailable:!verified,marks:rows.filter(function(row){return !!row.predMark}).map(function(row){
          return {horseNumber:Number(row.horse.horseNumber),name:String(row.horse.name||''),mark:row.predMark};
        })};
      return {rows:rows,legacyEngineDisabled:!verified,
        scenarios:[],plans:{},plan:null,suit:{},occ:[],pressure:0,
        arrangement:[],profile:{},coverage:0};
    }
    // Universal race forecast: one BEFORE-OFF receipt for all panels.
    // UI does not invent a ranking, second pace opinion, or ticket.
    var unified=race&&race.unifiedForecast;
    if(unified&&unified.version==='arvexq-unified-live-v1'&&
       unified.raceId===race.id&&unified.raceDate===race.date&&
       unified.circuit===race.circuit&&unified.researchOnly===true&&
       unified.probabilitiesCalibrated===false&&
       Array.isArray(unified.roster)&&Array.isArray(unified.marks)&&
       unified.roster.length>=3&&Array.isArray(race.horses)&&
       /^[a-f0-9]{64}$/i.test(unified.receiptSha256||'')&&
       /^[a-f0-9]{64}$/i.test(unified.modelHash||'')&&
       String(unified.trainedThrough||'')<String(race.date||'')&&
       Date.parse(String(unified.capturedAt||''))<
       Date.parse(String(race.date)+'T'+String(race.scheduledStartTime||race.startTime||'').slice(0,5)+':00+09:00')){
      var roster={},seen={},markMap={},accepted=true,best=0,allow={'◎':1,'○':1,'▲':1,'△':1,'☆':1,'注':1};
      unified.roster.forEach(function(x){
        var n=Number(x&&x.horseNumber);
        if(!Number.isInteger(n)||n<=0||roster[n])accepted=false;
        roster[n]=String(x.name||'');
      });
      (race.horses||[]).forEach(function(h){
        var n=Number(h&&h.horseNumber);
        if(!Number.isInteger(n)||n<=0)return;
        // Scratched/withdrawn entries may remain on the public racecard;
        // a verified receipt contains only the active pre-off roster.
        if(!Object.prototype.hasOwnProperty.call(roster,n)){
          if(!(h.scratched||h.withdrawn||h.cancelled||h.status==='取消'||h.status==='除外'))accepted=false;
        }else if(roster[n]!==String(h&&h.name||''))accepted=false;
      });
      unified.marks.forEach(function(x){
        var n=Number(x&&x.horseNumber),m=String(x&&x.markSymbol||'');
        if(!Number.isInteger(n)||!roster[n]||seen[n]||!allow[m])accepted=false;
        seen[n]=true;markMap[n]=x;if(m==='◎')best++;
      });
      if(accepted&&best===1){
        var unifiedStages=Array.isArray(unified.paceStages)?unified.paceStages:[],
            unifiedPlan=unifiedStages.length?{stages:unifiedStages}:null;
        var rowsU=race.horses.filter(function(h){return h&&Number(h.horseNumber)>0}).map(function(h){
          var no=Number(h.horseNumber),obj=markMap[no]||{},mark=String(obj.markSymbol||'');
          if(mark==='注')mark='';
          return {horse:h,predMark:mark,serverPreoffMark:false,
            originalPreoffMark:false,referencePostoffMark:false,revisionCandidateMark:!!mark,
            predRank:999,winProbability:null,p1Probability:null,p2Probability:null,
            p3Probability:null,overallGrade:'',coverage:0,
            forecastProbabilityRange:obj.winProbabilityRange||null,
            forecastTop3Range:obj.top3ProbabilityRange||null,forecastReason:obj.reason||''};
        });
        last={active:true,source:'arvexq-unified-preoff',scenarios:(unified.pace&&unified.pace.testedScenarios||[]),
          pace:[],forecastText:String(unified.pace&&unified.pace.text||''),
          modelVersion:unified.modelVersion,uncalibrated:true,unavailable:false,
          marks:rowsU.filter(function(x){return !!x.predMark}).map(function(x){
            return {horseNumber:Number(x.horse.horseNumber),name:String(x.horse.name||''),mark:x.predMark}
          })};
        return {rows:rowsU,legacyEngineDisabled:true,scenarios:[],plans:{},
          plan:unifiedPlan,suit:{},occ:[],pressure:0,arrangement:[],profile:{},coverage:1};
      }
    }
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
      // Historic models may contain a separate scenario array; fusion has direct observed evidence.
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
      last={active:marks.length>0,source:server.modelVersion==='arvexq-empirical-fusion-v1'?'empirical-fusion-preoff':'stage64-archived',scenarios:[],pace:paceRows,
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
