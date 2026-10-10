/* Public, read-only source fetch. Does not access D1 or prediction storage. */
const NAR_CODES={'帯広ば':'03','帯広':'03','盛岡':'10','水沢':'11','浦和':'18','船橋':'19','大井':'20','川崎':'21','金沢':'22','笠松':'23','名古屋':'24','園田':'27','姫路':'28','高知':'31','佐賀':'32','門別':'36'};
const text=s=>String(s).replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;/g,' ').replace(/\s+/g,' ').trim();
const cleanName=s=>text(s).replace(/\s+/g,'');
export function narRows(html,source){
  const rows=[],known=new Map(source.horses.map(h=>[h.horseNumber,cleanName(h.name)]));
  for(const match of html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)){
    const cells=[...match[1].matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi)].map(m=>text(m[1]));
    if(cells.length<4||!/^\d{1,2}$/.test(cells[0])||!/^\d{1,2}$/.test(cells[1]))continue;
    const no=Number(cells[1]);if(!known.has(no))continue;
    if(known.get(no)!==cleanName(cells[2]))throw Error('official runner name mismatch');
    const scratch=/取消|除外|欠場/.test(cells[3]);
    const odds=/^\d+(?:\.\d+)?$/.test(cells[3])?Number(cells[3]):null;
    if(!scratch&&!(odds>0))continue;
    rows.push({horse_no:no,win_odds:scratch?null:odds,popularity:null,
      scratched:scratch,horse_status:scratch?'出走取消':'',oddsSource:'NAR公式'});
  }
  // Deterministic market rank from the very same official win odds, with ties.
  const ranked=rows.filter(r=>r.win_odds>0).sort((a,b)=>a.win_odds-b.win_odds||a.horse_no-b.horse_no);
  let rank=0,last=null;ranked.forEach((r,i)=>{if(r.win_odds!==last)rank=i+1;r.popularity=rank;last=r.win_odds});
  return rows;
}
export function centralRows(body,source){
  const values=body&&body.data&&body.data.odds&&body.data.odds['1'];
  if(!values||typeof values!=='object')throw Error('central win odds absent');
  const known=new Set(source.horses.map(h=>h.horseNumber)),rows=[];
  for(const [key,value] of Object.entries(values)){
    const no=Number(key);if(!known.has(no)||!Array.isArray(value))throw Error('central runner mismatch');
    const odds=/^\d+(?:\.\d+)?$/.test(String(value[0]))?Number(value[0]):null,pop=Number(value[2]);
    if(odds>0)rows.push({horse_no:no,win_odds:odds,popularity:Number.isInteger(pop)&&pop>0?pop:null,oddsSource:'netkeiba実オッズ'});
  }
  return rows;
}
export async function sourceOdds(source,fetcher=fetch){
  let url,sourceName;
  if(source.circuit==='地方'&&NAR_CODES[source.track]){
    const params=new URLSearchParams({k_babaCode:NAR_CODES[source.track],k_raceDate:source.date.replaceAll('-','/'),k_raceNo:String(source.raceNumber)});
    url='https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?'+params;sourceName='NAR公式';
  }else if(source.circuit==='中央'&&/^\d{12}$/.test(source.netkeibaRaceId||'')){
    url='https://race.netkeiba.com/api/api_get_jra_odds.html?'+new URLSearchParams({pid:'api_get_jra_odds',race_id:source.netkeibaRaceId,type:'1',sort:'odds',compress:'0',output:'json',action:'init'});
    sourceName='netkeiba実オッズ';
  }else throw Error('verified odds source absent');
  const res=await fetcher(url,{headers:{'User-Agent':'Mozilla/5.0','Accept-Language':'ja-JP','Referer':source.circuit==='地方'?'https://www.keiba.go.jp/':'https://race.netkeiba.com/'},signal:AbortSignal.timeout(4500)});
  if(!res.ok)throw Error('official odds fetch failed');
  let rows,publishedAt='',popularitySource='供給元の人気';
  if(source.circuit==='地方'){
    const html=await res.text();rows=narRows(html,source);popularitySource='NAR公式単勝オッズ順位';
    const time=/オッズ[\s\S]{0,60}?(\d{2}:\d{2})\s*現在/.exec(text(html));
    if(time)publishedAt=source.date+'T'+time[1]+':00+09:00';
  }else{
    const body=await res.json();rows=centralRows(body,source);
    const stamp=body.data&&body.data.official_datetime;
    if(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(stamp||'')&&stamp.slice(0,10)===source.date)publishedAt=stamp.replace(' ','T')+'+09:00';
  }
  if(!rows.length)throw Error('official odds not yet published');
  if(new Set(rows.map(r=>r.horse_no)).size!==rows.length)throw Error('duplicate official odds runner');
  const retrievedAt=new Date().toISOString();
  return {ok:true,race_id:source.id,odds:rows,oddsSource:sourceName,oddsUpdatedAt:retrievedAt,
    sourcePublishedAt:publishedAt,popularitySource,sourceUrl:url};
}
