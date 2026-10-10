/* An outage can return an actual old acquisition, with its original time. */
export function validateSavedOdds(body,source){
 if(!body||body.ok!==true||body.race_id!==source.id||!Array.isArray(body.odds)||!body.odds.length||
    body.sourceSnapshotSha256!==source.sourceSnapshotSha256||
    !/^[a-f0-9]{64}$/.test(body.sourceSnapshotSha256)||!Number.isFinite(Date.parse(body.oddsUpdatedAt)))return null;
 const known=new Map(source.horses.map(h=>[h.horseNumber,h.name])),seen=new Set();
 for(const row of body.odds){
  if(!known.has(row.horse_no)||known.get(row.horse_no)!==row.horse_name||seen.has(row.horse_no)||
     (!row.scratched&&!(row.win_odds>0))||!['netkeiba','netkeiba実オッズ','NAR公式','JRA公式','NAR公式出馬表'].includes(row.oddsSource))return null;
  seen.add(row.horse_no);
 }
 return {...body,oddsStatus:'saved',refreshFailed:true};
}
export async function savedOdds(env,origin,date,source){
 const response=await env.ASSETS.fetch(new Request(origin+'/odds-backups/'+date+'.json'));
 if(!response.ok)return null;
 const manifest=await response.json();
 if(manifest.version!=='arvexq-saved-actual-odds-v1'||manifest.date!==date)return null;
 return validateSavedOdds(manifest.races&&manifest.races[source.id],source);
}
