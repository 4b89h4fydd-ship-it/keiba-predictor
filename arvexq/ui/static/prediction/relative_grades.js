/* Pure ARVEXQRelativeGrades calculations. Dependencies are explicit; no storage or UI state. */
(function(global){
'use strict';
function create(deps){
var clamp=deps.clamp;
var mean=deps.mean;
var n=deps.n;
var raceMode=deps.raceMode;
var recentFinishScore=deps.recentFinishScore;
function gradeClass(g){return g==='S'?'grade-s':(g==='A'?'grade-a':(g==='B'?'grade-b':'grade-c'))}

function predictionProfile(r){
  var mode=raceMode(r);
  if(mode==='障害')return{code:'JUMP',label:'障害専用モデル',version:'ARVEXQ-JUMP-v3'};
  if(mode==='新馬')return{code:'DEBUT',label:'新馬専用モデル',version:'ARVEXQ-DEBUT-v3'};
  if(r.circuit==='地方')return{code:'NAR',label:'地方専用モデル',version:'ARVEXQ-NAR-v3'};
  return{code:'JRA',label:'中央専用モデル',version:'ARVEXQ-JRA-v3'}
}

function gradeRowsRelative(rows){
  if(!rows.length)return;
  var lo=Math.min.apply(null,rows.map(function(z){return z.overallRaw})),
      hi=Math.max.apply(null,rows.map(function(z){return z.overallRaw}));
  rows.forEach(function(z){
    var rel=hi===lo?.5:(z.overallRaw-lo)/(hi-lo), exact=clamp(z.overallRaw*.80+(.44+.56*rel)*.20,0,1)*100;
    z.overallScoreExact=Math.round(exact*10)/10;
    z.overallScore=Math.round(exact)
  });
  // v155: rank by the unrounded model value first. The UI and marks reuse this rank,
  // so horses tied at e.g. 76 points can no longer show the S horse in 3rd place.
  rows.sort(function(a,b){return n(b.overallRaw)-n(a.overallRaw)||n(b.overallScore)-n(a.overallScore)||n(b.ability)-n(a.ability)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});
  var m=rows.length;
  rows.forEach(function(z,rank){
    var pct=(rank+1)/m,score=z.overallScore;
    z.overallRank=rank+1;
    if((score>=83)||(pct<=.12&&score>=72))z.overallGrade='S';
    else if((score>=73)||(pct<=.35&&score>=65))z.overallGrade='A';
    else if((score>=60)||(pct<=.70))z.overallGrade='B';
    else z.overallGrade='C';
    if(!z.overallReasons.length)z.overallReasons.push('総合バランス型')
  })
}

function baseGradeReasons(x,su,fitScore){
  x.overallReasons=[];
  if(x.ability>=.62)x.overallReasons.push('能力評価高め');
  if(n(su.overall)>=.62)x.overallReasons.push('展開適性高め');
  if(x.frontStay>=.64)x.overallReasons.push('前残り力');
  if(x.comeFromBehind>=.64)x.overallReasons.push('差し込み力');
  if(x.fade<=.25)x.overallReasons.push('下がり率低め');
  if(fitScore>=.58)x.overallReasons.push('今回条件に実績');
  if(x.bodyWeightKnown&&x.bodyWeightSuit>=.58)x.overallReasons.push('馬体重変動は安定圏');
  if(x.bodyWeightKnown&&x.bodyWeightSuit<=.45)x.overallReasons.push('馬体重変動注意');
  if(x.frontCost>=.12)x.overallReasons.push('隣接圧力注意');
  if(x.fade>=.50)x.overallReasons.push('下がり率注意');
  if(x.coverage<.45)x.overallReasons.push('データ補完中・複数ソース確認');
  if((x.horse.recentRaces||[]).length<2||x.styleSamples<2)x.overallReasons.push('限定データ評価')
}

function assignOverallGradesCentral(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,fitScore,representative,resultsScore,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    fitScore=clamp(n(x.distFit,.5)*.43+n(x.trackFit,.5)*.34+n(x.condFit,.5)*.23,0,1);
    resultsScore=clamp(recentFinishScore(x.horse)*.38+n(x.speedScore,.5)*.22+n(x.levelFit,.5)*.25+n(x.prizeScore,.5)*.15,0,1);
    representative=clamp(n(x.speedScore,.5)*.30+n(x.levelFit,.5)*.28+recentFinishScore(x.horse)*.24+x.posCons*.10+x.latePower*.08,0,1);
    raw=
      resultsScore*.30+
      x.ability*.25+
      fitScore*.22+
      representative*.13+
      n(su.overall,.5)*.05+
      n(x.jockeyScore,.5)*.02+
      n(x.bodyWeightSuit,.5)*.01+
      x.coverage*.02;
    x.resultsScore=resultsScore;x.fitComposite=fitScore;x.representativeScore=representative;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(resultsScore>=.62)x.overallReasons.push('近走実績評価高め');
    if(fitScore>=.62)x.overallReasons.push('適性評価高め');
    if(representative>=.64)x.overallReasons.push('代表走評価高め');
    if(n(x.levelFit)>=.60)x.overallReasons.push('相手レベル適性');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}

function assignOverallGradesNar(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,q,fitScore,resultsScore,representative,positionEdge,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};q=pressure[no]||{};
    fitScore=clamp(n(x.trackFit,.5)*.41+n(x.distFit,.5)*.37+n(x.condFit,.5)*.22,0,1);
    // Local racing: class/opponent level and repeatable course-distance performance matter more
    // than a single tactical projection. Pace/position remains a modifier, not the core rank.
    resultsScore=clamp(recentFinishScore(x.horse)*.38+n(x.speedScore,.5)*.22+n(x.levelFit,.5)*.25+n(x.prizeScore,.5)*.15,0,1);
    representative=clamp(n(x.speedScore,.5)*.28+n(x.levelFit,.5)*.30+recentFinishScore(x.horse)*.25+x.posCons*.10+x.latePower*.07,0,1);
    positionEdge=clamp(x.goProb*.28+x.frontStay*.24+x.holdFront*.15+x.breakSkill*.10+n(x.jockeyFront,.0)*.08+(1-clamp(n(q.conflict),0,1))*.08+n(q.freeOuter,0)*.07,0,1);
    raw=
      resultsScore*.30+
      x.ability*.24+
      fitScore*.22+
      representative*.12+
      n(su.overall,.5)*.05+
      positionEdge*.03+
      n(x.jockeyScore,.5)*.015+
      x.posCons*.01+
      n(x.bodyWeightSuit,.5)*.005+
      x.coverage*.01-
      x.frontCost*.015-
      x.outerStress*.005;
    x.resultsScore=resultsScore;x.fitComposite=fitScore;x.representativeScore=representative;x.positionEdge=positionEdge;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(resultsScore>=.62)x.overallReasons.push('近走実績評価高め');
    if(fitScore>=.62)x.overallReasons.push('適性評価高め');
    if(representative>=.64)x.overallReasons.push('代表走評価高め');
    if(n(x.levelFit)>=.60)x.overallReasons.push('相手レベル適性');
    if(positionEdge>=.68)x.overallReasons.push('隊列は加点材料');
    if(n(x.trackFit)>=.60)x.overallReasons.push('同場適性');
    if(q.sandwich)x.overallReasons.push('逃げハサミ警戒');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}

function assignOverallGradesJump(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,fitScore,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    fitScore=mean([n(x.distFit,.5),n(x.trackFit,.5),n(x.condFit,.5)]);
    raw=
      x.ability*.25+
      x.stamina*.18+
      n(su.overall,.5)*.17+
      fitScore*.13+
      x.posCons*.08+
      x.hold*.06+
      x.latePower*.05+
      n(x.jockeyScore,.5)*.04+
      (1-x.fade)*.025+
      x.coverage*.025;
    x.overallRaw=clamp(raw,0,1);
    baseGradeReasons(x,su,fitScore);
    if(x.stamina>=.62)x.overallReasons.push('障害スタミナ');
    if(x.posCons>=.62)x.overallReasons.push('位置取り安定');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}

function assignOverallGradesDebut(r,rows,suit,pressure){
  var eligible=[],i,x,no,su,raw;
  for(i=0;i<rows.length;i++){
    x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};
    raw=
      x.ability*.20+
      n(x.jockeyScore,.5)*.18+
      n(x.trainerScore,.5)*.15+
      n(x.prizeScore,.5)*.10+
      n(x.distFit,.5)*.08+
      n(x.trackFit,.5)*.07+
      n(x.weightSuit,.5)*.06+
      n(x.ageSexSuit,.5)*.05+
      n(su.overall,.5)*.05+
      x.breakSkill*.04+
      x.coverage*.02;
    x.overallRaw=clamp(raw,0,1);x.overallReasons=['新馬専用評価'];
    if(n(x.jockeyScore)>=.60)x.overallReasons.push('騎手評価');
    if(n(x.trainerScore)>=.60)x.overallReasons.push('厩舎評価');
    if(x.coverage<.35)x.overallReasons.push('実戦データ限定');
    eligible.push(x)
  }
  gradeRowsRelative(eligible)
}

function assignOverallGrades(r,rows,suit,sc,pressure){
  var p=predictionProfile(r);
  if(p.code==='NAR')return assignOverallGradesNar(r,rows,suit,pressure);
  if(p.code==='JUMP')return assignOverallGradesJump(r,rows,suit,pressure);
  if(p.code==='DEBUT')return assignOverallGradesDebut(r,rows,suit,pressure);
  return assignOverallGradesCentral(r,rows,suit,pressure)
}
return Object.freeze({gradeClass:gradeClass,predictionProfile:predictionProfile,gradeRowsRelative:gradeRowsRelative,baseGradeReasons:baseGradeReasons,assignOverallGradesCentral:assignOverallGradesCentral,assignOverallGradesNar:assignOverallGradesNar,assignOverallGradesJump:assignOverallGradesJump,assignOverallGradesDebut:assignOverallGradesDebut,assignOverallGrades:assignOverallGrades});
}
global.ARVEXQRelativeGrades=Object.freeze({create:create});
})(window);
