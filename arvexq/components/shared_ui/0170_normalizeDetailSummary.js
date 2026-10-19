function normalizeDetailSummary(row,id){
  row=row||{};
  var out=Object.assign({},row),aliases={id:'race_id',date:'race_date',raceNumber:'race_no',startTime:'start_time',fieldSize:'field_size',raceStatus:'race_status'};
  Object.keys(aliases).forEach(function(k){if(out[k]==null&&row[aliases[k]]!=null)out[k]=row[aliases[k]]});
  if(!out.id)out.id=String(id);return out
}
