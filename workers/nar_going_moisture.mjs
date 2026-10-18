const BANEI = new Set(['帯広ば', '帯広']);

function parseRaceId(raceId) {
  const m = /^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$/.exec(String(raceId || ''));
  return m ? {date: m[1], track: m[2], raceNo: Number(m[3])} : null;
}

export function parseNarGoingMoisture(text) {
  const m = /(?:^|[\s　])馬場(?!状態)\s*[：:]\s*(\d+(?:\.\d+)?)/.exec(String(text || ''));
  return m ? m[1] : null;
}

export async function overlayNarGoingMoisture(detail, fetchImpl = fetch) {
  if (!detail || typeof detail !== 'object') return detail;
  const id = parseRaceId(detail.id);
  if (!id || !BANEI.has(id.track) || detail.goingMoisture || detail.condition !== '不明') return detail;
  const q = new URLSearchParams({
    k_babaCode: '03',
    k_raceDate: id.date.replaceAll('-', '/'),
    k_raceNo: String(id.raceNo),
  });
  try {
    const response = await fetchImpl(`https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?${q}`,
      {headers: {'accept-language': 'ja-JP,ja;q=0.9'}});
    if (!response.ok) return detail;
    const moisture = parseNarGoingMoisture(await response.text());
    return moisture ? {...detail, goingMoisture: moisture, goingMoistureSource: 'NAR公式'} : detail;
  } catch {
    return detail;
  }
}

export async function enhanceNarGoingResponse(response, fetchImpl = fetch) {
  if (!response.ok) return response;
  let body;
  try { body = await response.clone().json(); } catch { return response; }
  if (!body || typeof body !== 'object') return response;
  if (body.detail) body.detail = await overlayNarGoingMoisture(body.detail, fetchImpl);
  if (Array.isArray(body.details)) {
    body.details = await Promise.all(body.details.map((d) => overlayNarGoingMoisture(d, fetchImpl)));
  }
  return new Response(JSON.stringify(body), {status: response.status, headers: response.headers});
}
