// Private, fixed SQL metrics only. Existing data and predictions are read-only.
export async function storageAudit(request,env){
  if(!env.SYNC_TOKEN||request.headers.get('authorization')!=='Bearer '+env.SYNC_TOKEN)
    return Response.json({ok:false,error:'unauthorized'},{status:401});
  const statements={page_count:'PRAGMA page_count',page_size:'PRAGMA page_size',
    details:'SELECT COUNT(*) AS rows, SUM(length(CAST(payload AS BLOB))) AS payload_bytes, MIN(race_date) AS first_date, MAX(race_date) AS last_date FROM race_details',
    summaries:'SELECT COUNT(*) AS rows FROM race_summaries',
    odds_current:'SELECT COUNT(*) AS rows FROM odds_current',
    odds_history:'SELECT COUNT(*) AS rows FROM odds_history'};
  const queries={};
  for(const [name,sql] of Object.entries(statements)){
    try{const result=await env.DB.prepare(sql).all();queries[name]={results:result.results,meta:result.meta}}
    catch(e){queries[name]={error:String(e.message||e)}}
  }
  return Response.json({ok:true,version:'arvexq-readonly-storage-v1',sql_writes:0,queries},
    {headers:{'cache-control':'no-store'}});
}
