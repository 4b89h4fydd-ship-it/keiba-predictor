function validatedHonmeiMetadata(source){
  var q=source||{},role=String(q.honmeiRole||q.role||''),
      grade=String(q.honmeiGrade||q.confidenceGrade||'');
  return{honmeiRole:role==='win'||role==='axis'||role==='win-axis'?role:'',
    honmeiGrade:['A','B','C'].indexOf(grade)>=0?grade:''}
}
