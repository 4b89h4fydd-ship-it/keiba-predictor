function reflectUseful(v){
  if(v===false||v===0)return true;
  if(v==null||v==='')return false;
  if(Array.isArray(v))return v.length>0;
  if(typeof v==='object')return Object.keys(v).length>0;
  if(typeof v==='string'&&(v==='不明'||v==='—'))return false;
  return true
}
