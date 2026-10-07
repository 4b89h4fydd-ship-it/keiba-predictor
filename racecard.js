// Read only, compact roster. History/analysis/odds failures cannot block this route.
export const BASIC_SQL = `
  SELECT json_object(
    'id', race_id, 'date', race_date,
    'track', json_extract(payload, '$.track'),
    'circuit', json_extract(payload, '$.circuit'),
    'raceNumber', json_extract(payload, '$.raceNumber'),
    'title', json_extract(payload, '$.title'),
    'distance', json_extract(payload, '$.distance'),
    'surface', json_extract(payload, '$.surface'),
    'startTime', json_extract(payload, '$.startTime'),
    'fieldSize', json_extract(payload, '$.fieldSize'),
    'weather', json_extract(payload, '$.weather'),
    'condition', json_extract(payload, '$.condition'),
    'raceStatus', json_extract(payload, '$.raceStatus')
  ) AS basic FROM race_details
  WHERE race_id = ? AND json_valid(payload) = 1 LIMIT 1`;
export const HORSES_SQL = `
  SELECT json_object(
    'horseNumber', json_extract(h.value, '$.horseNumber'),
    'frameNumber', json_extract(h.value, '$.frameNumber'),
    'name', json_extract(h.value, '$.name'),
    'sex', json_extract(h.value, '$.sex'),
    'age', json_extract(h.value, '$.age'),
    'jockey', json_extract(h.value, '$.jockey'),
    'trainer', json_extract(h.value, '$.trainer'),
    'carriedWeight', json_extract(h.value, '$.carriedWeight'),
    'bodyWeight', json_extract(h.value, '$.bodyWeight'),
    'bodyWeightChange', json_extract(h.value, '$.bodyWeightChange'),
    'winOdds', json_extract(h.value, '$.winOdds'),
    'popularity', json_extract(h.value, '$.popularity'),
    'status', json_extract(h.value, '$.status'),
    'scratched', json_extract(h.value, '$.scratched'),
    'withdrawn', json_extract(h.value, '$.withdrawn')
  ) AS horse
  FROM race_details r, json_each(r.payload, '$.horses') h
  WHERE r.race_id = ? AND json_valid(r.payload) = 1
    AND CAST(json_extract(h.value, '$.horseNumber') AS INTEGER) > 0
  ORDER BY CAST(json_extract(h.value, '$.horseNumber') AS INTEGER)`;

export async function readRacecard(env, raceId) {
  const response = (body, status = 200) => new Response(JSON.stringify(body), {
    status, headers: {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'}
  });
  if (!raceId) return response({ok:false,error:'race_id is required'},400);
  try {
    const row = await env.DB.prepare(BASIC_SQL).bind(raceId).first();
    if (!row) return response({ok:false,error:'race not found',race_id:raceId},404);
    const basic = JSON.parse(row.basic);
    const result = await env.DB.prepare(HORSES_SQL).bind(raceId).all();
    const horses = (result.results || []).map(row => {
      const h = JSON.parse(row.horse);
      h.scratched = h.scratched === true || h.scratched === 1;
      h.withdrawn = h.withdrawn === true || h.withdrawn === 1;
      return h;
    });
    return response({ok:true,race_id:raceId,summary:basic,
      detail:{...basic,horses,_entryOnly:true},entry_state:horses.length?'loaded':
        (basic.fieldSize===0?'empty':'loading')});
  } catch {
    return response({ok:false,error:'racecard temporarily unavailable',race_id:raceId},503);
  }
}
