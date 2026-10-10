// Fixed-table authenticated logical backup. No SQL writes or arbitrary queries.
const TABLES=['race_details','race_summaries','odds_current','odds_history','meta'];
export async function snapshotExport(request,env){
  if(!env.SYNC_TOKEN||request.headers.get('authorization')!=='Bearer '+env.SYNC_TOKEN)
    return Response.json({ok:false,error:'unauthorized'},{status:401});
  if(request.method!=='GET')return Response.json({ok:false,error:'method not allowed'},{status:405});
  const url=new URL(request.url),table=url.searchParams.get('table');
  const respond=data=>Response.json(data,{headers:{'cache-control':'no-store'}});
  if(!table){
    const placeholders=TABLES.map(()=>'?').join(',');
    const schema=await env.DB.prepare(`SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL AND tbl_name IN (${placeholders}) AND type IN ('table','index') ORDER BY type DESC,name`).bind(...TABLES).all();
    const races=await env.DB.prepare('SELECT race_id,race_date,updated_at,length(CAST(payload AS BLOB)) AS bytes FROM race_details ORDER BY race_id').all();
    return respond({ok:true,version:'arvexq-logical-backup-v1',sql_writes:0,tables:TABLES,schema:schema.results,races:races.results});
  }
  if(!TABLES.includes(table))return respond({ok:false,error:'unsupported table'});
  const id=url.searchParams.get('race_id');
  if(table==='race_details'&&id){
    const row=await env.DB.prepare('SELECT * FROM race_details WHERE race_id=?').bind(id).first();
    return respond({ok:true,table,rows:row?[row]:[]});
  }
  const offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||1000);
  if(!Number.isInteger(offset)||offset<0||offset>10000000||!Number.isInteger(limit)||limit<1||limit>1000||table==='race_details')
    return Response.json({ok:false,error:'invalid pagination'},{status:400});
  const rows=await env.DB.prepare(`SELECT * FROM ${table} ORDER BY rowid LIMIT ? OFFSET ?`).bind(limit,offset).all();
  return respond({ok:true,table,rows:rows.results});
}
