import {applyStage64Archive} from './preoff-persistence.js';
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

// Opt-in UI view. Keep the legacy response and stored prediction snapshot intact.
export const DISPLAY_SQL = `SELECT
  json_remove(payload, '$.massFeatureSnapshot') AS payload,
  analysis_ready, updated_at
  FROM race_details WHERE race_id = ? AND json_valid(payload) = 1 LIMIT 1`;
// Restore the existing lossless full-snapshot envelope for the display-only read.
// The D1 original and the legacy/raw API retain their existing packed shape.
export async function restoreDisplaySnapshot(detail) {
  const envelope = detail?.arvexqFullPayload;
  if (!envelope) return detail;
  const expectedBytes = Number(envelope.bytes);
  if (envelope.version !== 'arvexq-full-payload-v1' ||
      !Number.isInteger(expectedBytes) || expectedBytes <= 0 ||
      expectedBytes > 100_000_000 ||
      !/^[0-9a-f]{64}$/.test(String(envelope.sha256 || '')) ||
      typeof envelope.gzipBase64 !== 'string' ||
      !/^[A-Za-z0-9+/]*={0,2}$/.test(envelope.gzipBase64)) {
    throw new Error('invalid full snapshot envelope');
  }
  const compressed = Uint8Array.from(atob(envelope.gzipBase64), c => c.charCodeAt(0));
  const reader = new Blob([compressed]).stream()
    .pipeThrough(new DecompressionStream('gzip')).getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > expectedBytes) throw new Error('full snapshot exceeds declared size');
      chunks.push(value);
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
  if (total !== expectedBytes) throw new Error('full snapshot size mismatch');
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  const actualSha = Array.from(digest, b => b.toString(16).padStart(2, '0')).join('');
  if (actualSha !== envelope.sha256) throw new Error('full snapshot digest mismatch');
  const restored = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
  if (!restored || typeof restored !== 'object' || Array.isArray(restored) ||
      restored.id !== detail.id || !Array.isArray(restored.horses)) {
    throw new Error('full snapshot race identity mismatch');
  }
  // Match the prior display projection; the large frozen feature archive stays in D1.
  delete restored.massFeatureSnapshot;
  return restored;
}

export async function readRaceDisplay(env, raceId) {
  const response = (body, status = 200) => new Response(JSON.stringify(body), {
    status, headers: {'content-type':'application/json; charset=utf-8','cache-control':'no-store'}
  });
  if (!raceId) return response({ok:false,error:'race_id is required'},400);
  try {
    const row = await env.DB.prepare(DISPLAY_SQL).bind(raceId).first();
    if (!row) return response({ok:false,error:'race not found',race_id:raceId},404);
    const stored = JSON.parse(row.payload);
    const detail = applyStage64Archive(await restoreDisplaySnapshot(stored), stored);
    let odds = [];
    try {
      const result = await env.DB.prepare(`SELECT horse_no, win_odds, popularity,
        body_weight, body_weight_change, horse_status, updated_at
        FROM odds_current WHERE race_id = ? ORDER BY horse_no`).bind(raceId).all();
      odds = result.results || [];
    } catch { /* The roster/history response does not depend on odds availability. */ }
    return response({ok:true,race_id:raceId,detail,summary:{id:raceId,date:detail.date,
      track:detail.track,raceNumber:detail.raceNumber},analysis_ready:!!row.analysis_ready,
      detail_updated_at:row.updated_at,odds});
  } catch {
    return response({ok:false,error:'race detail temporarily unavailable',race_id:raceId},503);
  }
}
