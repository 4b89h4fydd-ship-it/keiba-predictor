/* Own the existing, unchanged D1 SQL rewrite and environment binding. */
export function rewriteDetailSQL(sql,compactDay=false){
  if(compactDay&&/FROM\s+race_details\s+WHERE\s+race_date\s*=/.test(sql))
    return sql.replace(/\bpayload\b/,"CASE WHEN json_valid(payload) THEN json_remove(payload,'$.arvexqFullPayload','$.massFeatureArchive','$.massFeatureSnapshot') ELSE payload END AS payload");
  if(/INSERT\s+INTO\s+race_details\s*\(/i.test(sql)&&/ON CONFLICT\(race_id\)/i.test(sql)&&!/\bWHERE\b/i.test(sql))
    return sql.trim().replace(/;$/,'')+' WHERE race_details.payload IS NOT excluded.payload OR race_details.analysis_ready IS NOT excluded.analysis_ready OR race_details.race_date IS NOT excluded.race_date';
  return sql;
}
export function storageEnvironment(env,compactDay=false){
  const db=env.DB;
  return {...env,DB:new Proxy(db,{get(target,key){if(key==='prepare')return sql=>db.prepare(rewriteDetailSQL(sql,compactDay));const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value}})};
}
