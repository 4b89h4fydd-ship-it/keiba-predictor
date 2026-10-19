function raceIsGraded(r){
  if(!r)return false;
  if(r.isGraded===true||r.graded===true||r.isGradeRace===true||r.gradeRace===true)return true;
  var t=String(r.title||''),meta=[r.grade,r.gradeLabel,r.raceGrade,r.gradeCode,r.raceClass,r.className,r.category].map(function(v){return String(v||'')}).join(' '),s=t+' '+meta,grade='(?:[ⅠⅡⅢ]|I{1,3}|[123])';
  if(new RegExp('(?:Jpn\\s*)?G\\s*'+grade+'|(?:Jpn\\s*)'+grade+'|(?:^|[\\s（(\\[])(?:S|H|M|SP)\\s*'+grade+'(?:$|[\\s）)\\]])|重賞|賞\\s*[（(]重賞[）)]','i').test(s))return true;
  return /(?:ダービー|優駿|グランプリ)(?:$|[（(])/i.test(t)
}
