var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// .arvexq-production-overlay/worker-entry.js
var __defProp2 = Object.defineProperty;
var __name2 = /* @__PURE__ */ __name((target, value) => __defProp2(target, "name", { value, configurable: true }), "__name");
var RETIRED_KEYS = /* @__PURE__ */ new Set([
  "aiEvaluation",
  "integratedEvaluation",
  "factorRanking",
  "honmeiDecision",
  "preRacePrediction",
  "preRaceBet",
  "predictionAudit",
  "frozenPredictionAudit",
  "winnerLearningProfile",
  "betRecommendations",
  "recommendedBets",
  "tickets",
  "buyList",
  "bets",
  "markMethod",
  "markEngineVersion",
  "predictionModelVersion",
  "mark",
  "predMark",
  "\u5370",
  "honmeiRole",
  "modelProbabilities",
  "forecastRevisions",
  "currentForecastRevisionId",
  "preoffStage64Archive",
  "morningMarkSnapshot",
  "officialMarkRevisions",
  "modelMarkRevisions",
  "savedForecastRevision",
  "_savedPreoffOriginal",
  "legacyPredictionAudit",
  "preRaceAudit",
  "observedModelCoverage"
]);
function authorizedStage64(race) {
  const p = race.prediction;
  if (race.predictionStatus !== "ready" || !p || p.predictionStatus !== "ready" || p.productionEligible !== true || !["arvexq-stage64-product-v1", "arvexq-rewrite-v1-uncalibrated-prior", "arvexq-rewrite-v2-elo-speed2"].includes(p.modelVersion) || p.raceId !== race.id || p.date !== race.date || !Array.isArray(race.horses) || !Array.isArray(race.predictionMarks) || race.predictionMarks.length !== 5) return null;
  const known = new Set(race.horses.map((h) => h?.horseNumber));
  const labels = ["\u25CE", "\u25CB", "\u25B2", "\u25B3", "\u2606"];
  const used = /* @__PURE__ */ new Set();
  const marks = [];
  for (let i = 0; i < 5; i++) {
    const row = race.predictionMarks[i];
    if (!row || row.mark !== labels[i] || !Number.isInteger(row.horseNumber) || !known.has(row.horseNumber) || used.has(row.horseNumber)) return null;
    used.add(row.horseNumber);
    marks.push({ ...row });
  }
  return marks;
}
__name(authorizedStage64, "authorizedStage64");
__name2(authorizedStage64, "authorizedStage64");
function publicRace(value) {
  if (Array.isArray(value)) return value.map(publicRace);
  if (!value || typeof value !== "object") return value;
  const result = {};
  for (const [key, entry] of Object.entries(value)) {
    if (!RETIRED_KEYS.has(key)) result[key] = publicRace(entry);
  }
  if (Array.isArray(value.horses)) {
    const live = authorizedStage64(value);
    if (live) {
      const byNo = new Map(live.map((row) => [row.horseNumber, row.mark]));
      result.predictionStatus = "ready";
      result.predictionModelVersion = value.prediction.modelVersion;
      result.predictionMarks = live;
      if (Array.isArray(value.recommendedBets)) result.recommendedBets = structuredClone(value.recommendedBets);
      result.horses = result.horses.map((h) => ({
        ...h,
        ...byNo.has(h.horseNumber) ? { predMark: byNo.get(h.horseNumber) } : {}
      }));
    } else {
      result.predictionStatus = "disabled";
      result.predictionModelVersion = "arvexq-prediction-removed";
      delete result.predictionMarks;
      delete result.prediction;
      delete result.recommendedBets;
    }
  }
  return result;
}
__name(publicRace, "publicRace");
__name2(publicRace, "publicRace");
async function publicRaceResponse(response2, request) {
  const path = new URL(request.url).pathname;
  if (request.method !== "GET" || !response2.ok || !(path === "/api/day" || path.startsWith("/api/race/") || path.startsWith("/api/racecard/"))) return response2;
  let body;
  try {
    body = await response2.clone().json();
  } catch {
    return response2;
  }
  const headers2 = new Headers(response2.headers);
  headers2.delete("content-length");
  headers2.delete("etag");
  headers2.set("content-type", "application/json; charset=utf-8");
  headers2.set("cache-control", "no-store");
  return new Response(JSON.stringify(publicRace(body)), { status: response2.status, statusText: response2.statusText, headers: headers2 });
}
__name(publicRaceResponse, "publicRaceResponse");
__name2(publicRaceResponse, "publicRaceResponse");
var VERSION = "arvexq-d1-preoff-evidence-v1";
var MAX_REQUEST_BYTES = 95e4;
var DELAY_SECONDS = 300;
var MAX_UNCOMPRESSED_BYTES = 12e6;
function stable(value) {
  if (Array.isArray(value)) return "[" + value.map(stable).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + stable(value[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}
__name(stable, "stable");
__name2(stable, "stable");
async function sha256(value, canonicalText) {
  const bytes = new TextEncoder().encode(canonicalText === void 0 ? stable(value) : canonicalText);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}
__name(sha256, "sha256");
__name2(sha256, "sha256");
function reply(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store"
  } });
}
__name(reply, "reply");
__name2(reply, "reply");
function authenticated(request, env) {
  const secret = typeof env.FORECAST_CAPTURE_TOKEN === "string" ? env.FORECAST_CAPTURE_TOKEN : "";
  return secret.length >= 24 && request.headers.get("authorization") === "Bearer " + secret;
}
__name(authenticated, "authenticated");
__name2(authenticated, "authenticated");
function validIsoDate(date) {
  return typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date) && !Number.isNaN(Date.parse(date + "T00:00:00Z"));
}
__name(validIsoDate, "validIsoDate");
__name2(validIsoDate, "validIsoDate");
function checkDocument(snapshot, receipt, now) {
  if (!snapshot || !receipt || typeof snapshot !== "object" || typeof receipt !== "object") {
    throw new Error("snapshot and acquisition receipt required");
  }
  if (!snapshot.raceId || receipt.raceId !== snapshot.raceId || receipt.featureHash !== snapshot.featureHash || receipt.version !== "arvexq-preoff-raw-evidence-v1" || receipt.source !== "preoff-acquisition-log" || receipt.attestedPreOff !== true) {
    throw new Error("invalid capture identity and provenance");
  }
  if (!validIsoDate(snapshot.date) || !["\u4E2D\u592E", "\u5730\u65B9"].includes(snapshot.circuit)) {
    throw new Error("invalid race date or circuit");
  }
  const captured = receipt.capturedAtEpoch, post = receipt.postAtEpoch;
  if (!Number.isSafeInteger(captured) || !Number.isSafeInteger(post) || !(captured > 0 && captured <= now && now < post && now - captured <= DELAY_SECONDS)) {
    throw new Error("not a timely pre-off capture");
  }
  const postJst = new Date((post + 9 * 3600) * 1e3).toISOString().slice(0, 10);
  if (postJst !== snapshot.date) throw new Error("post date mismatch");
  const numbers = receipt.activeHorseNumbers;
  if (!Array.isArray(numbers) || numbers.length < 3 || numbers.length > 30 || new Set(numbers).size !== numbers.length || numbers.some((n) => !Number.isSafeInteger(n) || n < 1 || n > 99)) {
    throw new Error("invalid official field claim");
  }
  const rows = snapshot.rows;
  if (!Array.isArray(rows) || rows.length !== numbers.length || snapshot.horseCount !== rows.length || new Set(rows.map((r) => r?.horseNumber)).size !== rows.length || rows.some((r) => !numbers.includes(r?.horseNumber) || !r.features || typeof r.features !== "object")) {
    throw new Error("frozen runners disagree with active field claim");
  }
  if (rows.some((r) => Object.keys(r.features).some((k) => /^(?:market::|result::|current::|payout::|label::)/.test(k)))) {
    throw new Error("future/result/market features prohibited");
  }
}
__name(checkDocument, "checkDocument");
__name2(checkDocument, "checkDocument");
async function decodeEvidence(raw) {
  const envelope = JSON.parse(raw);
  if (envelope?.encoding !== "arvexq-preoff-gzip-json-v1") return { body: envelope, compressed: null };
  if (typeof envelope.payload !== "string" || envelope.payload.length > MAX_REQUEST_BYTES) {
    throw new Error("compressed payload too large");
  }
  const binary = atob(envelope.payload);
  const input = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  if (!input.length || input.length > MAX_REQUEST_BYTES) throw new Error("compressed payload invalid");
  const decompressed = new Blob([input]).stream().pipeThrough(new DecompressionStream("gzip"));
  const reader = decompressed.getReader();
  const chunks = [];
  let total = 0;
  try {
    for (; ; ) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_UNCOMPRESSED_BYTES) {
        await reader.cancel();
        throw new Error("uncompressed payload too large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const buffer = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    buffer.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const body = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(buffer));
  return { body, compressed: envelope.payload };
}
__name(decodeEvidence, "decodeEvidence");
__name2(decodeEvidence, "decodeEvidence");
async function handlePreoffCapture(request, env, { now = /* @__PURE__ */ __name2(() => Math.floor(Date.now() / 1e3), "now") } = {}) {
  if (request.method !== "POST") return reply({ ok: false, error: "POST required" }, 405);
  if (!authenticated(request, env)) return reply({ ok: false, error: "unauthorized" }, 401);
  const size = Number(request.headers.get("content-length") || 0);
  if (size > MAX_REQUEST_BYTES) return reply({ ok: false, error: "payload too large" }, 413);
  let body;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).length > MAX_REQUEST_BYTES) return reply({ ok: false, error: "payload too large" }, 413);
    const decoded = await decodeEvidence(raw);
    body = decoded.body;
    checkDocument(body.snapshot, body.receipt, now());
    const snap = body.snapshot, rec = body.receipt;
    const { featureHash, ...snapshotWithoutHash } = snap;
    const snapshotCoreText = body.snapshotCoreCanonical;
    const receiptCoreText = body.receiptCoreCanonical;
    if (typeof snapshotCoreText !== "string" || typeof receiptCoreText !== "string") {
      throw new Error("canonical Python evidence strings required");
    }
    if (stable(JSON.parse(snapshotCoreText)) !== stable(snapshotWithoutHash)) {
      throw new Error("snapshot canonical payload inconsistent");
    }
    if (await sha256(snapshotWithoutHash, snapshotCoreText) !== featureHash) {
      throw new Error("snapshot hash mismatch");
    }
    const { receiptHash, ...receiptWithoutHash } = rec;
    if (stable(JSON.parse(receiptCoreText)) !== stable(receiptWithoutHash)) {
      throw new Error("receipt canonical payload inconsistent");
    }
    if (await sha256(receiptWithoutHash, receiptCoreText) !== receiptHash) {
      throw new Error("receipt hash mismatch");
    }
    const snapshotStorage = decoded.compressed ? "gzip-envelope:" + decoded.compressed : stable(snap);
    const receiptStorage = stable(rec);
    const identity = { raceId: rec.raceId, featureHash: rec.featureHash, capturedAtEpoch: rec.capturedAtEpoch };
    const captureId = await sha256(identity);
    const response2 = await env.DB.prepare(
      "INSERT OR IGNORE INTO forecast_preoff_evidence (capture_id,race_id,feature_hash,receipt_hash,snapshot_json,receipt_json,captured_at_epoch,stored_at_epoch,post_at_epoch) VALUES (?,?,?,?,?,?,?,?,?)"
    ).bind(
      captureId,
      rec.raceId,
      featureHash,
      receiptHash,
      snapshotStorage,
      receiptStorage,
      rec.capturedAtEpoch,
      now(),
      rec.postAtEpoch
    ).run();
    if (response2.meta?.changes === 0) {
      const old = await env.DB.prepare(
        "SELECT feature_hash,receipt_hash,snapshot_json,receipt_json FROM forecast_preoff_evidence WHERE capture_id=?"
      ).bind(captureId).first();
      if (!old || old.feature_hash !== featureHash || old.receipt_hash !== receiptHash || old.snapshot_json !== snapshotStorage || old.receipt_json !== receiptStorage) {
        return reply({ ok: false, error: "immutable identity collision" }, 409);
      }
    }
    return reply({
      ok: true,
      captureId,
      version: VERSION,
      researchOnly: true,
      duplicate: response2.meta?.changes === 0
    }, response2.meta?.changes === 0 ? 200 : 201);
  } catch (error) {
    const message = String(error?.message || "");
    if (/no such table|no such column/i.test(message)) return reply({ ok: false, error: "migration not applied" }, 503);
    if (/D1_|SQLITE_|database/i.test(message)) return reply({ ok: false, error: "storage unavailable" }, 503);
    return reply({ ok: false, error: message || "invalid capture" }, 422);
  }
}
__name(handlePreoffCapture, "handlePreoffCapture");
__name2(handlePreoffCapture, "handlePreoffCapture");
var KEYS = ["predictionStatus", "predictionModelVersion", "prediction", "predictionMarks", "recommendedBets"];
function stage64Archive(detail) {
  if (!detail || !authorizedStage64(detail) || !Array.isArray(detail.recommendedBets)) return null;
  const archive = { raceId: detail.id, raceDate: detail.date };
  for (const key of KEYS) archive[key] = structuredClone(detail[key]);
  return archive;
}
__name(stage64Archive, "stage64Archive");
__name2(stage64Archive, "stage64Archive");
function verifiedStage64Archive(archive, race) {
  if (!archive || !race || archive.raceId !== race.id || archive.raceDate !== race.date) return null;
  const candidate = { ...archive, id: race.id, date: race.date, horses: race.horses };
  return authorizedStage64(candidate) && Array.isArray(archive.recommendedBets) ? archive : null;
}
__name(verifiedStage64Archive, "verifiedStage64Archive");
__name2(verifiedStage64Archive, "verifiedStage64Archive");
function retainStage64Archive(incoming, older, newOriginal) {
  if (!incoming || typeof incoming !== "object") return incoming;
  const chosen = verifiedStage64Archive(newOriginal, incoming) || verifiedStage64Archive(incoming.preoffStage64Archive, incoming) || verifiedStage64Archive(older?.preoffStage64Archive, incoming);
  return chosen ? { ...incoming, preoffStage64Archive: structuredClone(chosen) } : incoming;
}
__name(retainStage64Archive, "retainStage64Archive");
__name2(retainStage64Archive, "retainStage64Archive");
function applyStage64Archive(restored, storedEnvelope) {
  const archive = verifiedStage64Archive(storedEnvelope?.preoffStage64Archive, restored);
  if (!archive || authorizedStage64(restored)) return restored;
  const result = { ...restored };
  for (const key of KEYS) result[key] = structuredClone(archive[key]);
  return result;
}
__name(applyStage64Archive, "applyStage64Archive");
__name2(applyStage64Archive, "applyStage64Archive");
var BASIC_SQL = `
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
var HORSES_SQL = `
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
async function readRacecard(env, raceId) {
  const response2 = /* @__PURE__ */ __name2((body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  }), "response");
  if (!raceId) return response2({ ok: false, error: "race_id is required" }, 400);
  try {
    const row = await env.DB.prepare(BASIC_SQL).bind(raceId).first();
    if (!row) return response2({ ok: false, error: "race not found", race_id: raceId }, 404);
    const basic = JSON.parse(row.basic);
    const result = await env.DB.prepare(HORSES_SQL).bind(raceId).all();
    const horses = (result.results || []).map((row2) => {
      const h = JSON.parse(row2.horse);
      h.scratched = h.scratched === true || h.scratched === 1;
      h.withdrawn = h.withdrawn === true || h.withdrawn === 1;
      return h;
    });
    return response2({
      ok: true,
      race_id: raceId,
      summary: basic,
      detail: { ...basic, horses, _entryOnly: true },
      entry_state: horses.length ? "loaded" : basic.fieldSize === 0 ? "empty" : "loading"
    });
  } catch {
    return response2({ ok: false, error: "racecard temporarily unavailable", race_id: raceId }, 503);
  }
}
__name(readRacecard, "readRacecard");
__name2(readRacecard, "readRacecard");
var DISPLAY_SQL = `SELECT
  json_remove(payload, '$.massFeatureSnapshot') AS payload,
  analysis_ready, updated_at
  FROM race_details WHERE race_id = ? AND json_valid(payload) = 1 LIMIT 1`;
async function restoreDisplaySnapshot(detail) {
  const envelope = detail?.arvexqFullPayload;
  if (!envelope) return detail;
  const expectedBytes = Number(envelope.bytes);
  if (envelope.version !== "arvexq-full-payload-v1" || !Number.isInteger(expectedBytes) || expectedBytes <= 0 || expectedBytes > 1e8 || !/^[0-9a-f]{64}$/.test(String(envelope.sha256 || "")) || typeof envelope.gzipBase64 !== "string" || !/^[A-Za-z0-9+/]*={0,2}$/.test(envelope.gzipBase64)) {
    throw new Error("invalid full snapshot envelope");
  }
  const compressed = Uint8Array.from(atob(envelope.gzipBase64), (c) => c.charCodeAt(0));
  const reader = new Blob([compressed]).stream().pipeThrough(new DecompressionStream("gzip")).getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > expectedBytes) throw new Error("full snapshot exceeds declared size");
      chunks.push(value);
    }
  } finally {
    await reader.cancel().catch(() => {
    });
  }
  if (total !== expectedBytes) throw new Error("full snapshot size mismatch");
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  const actualSha = Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join("");
  if (actualSha !== envelope.sha256) throw new Error("full snapshot digest mismatch");
  const restored = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  if (!restored || typeof restored !== "object" || Array.isArray(restored) || restored.id !== detail.id || !Array.isArray(restored.horses)) {
    throw new Error("full snapshot race identity mismatch");
  }
  delete restored.massFeatureSnapshot;
  return restored;
}
__name(restoreDisplaySnapshot, "restoreDisplaySnapshot");
__name2(restoreDisplaySnapshot, "restoreDisplaySnapshot");
async function readRaceDisplay(env, raceId) {
  const response2 = /* @__PURE__ */ __name2((body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  }), "response");
  if (!raceId) return response2({ ok: false, error: "race_id is required" }, 400);
  try {
    const row = await env.DB.prepare(DISPLAY_SQL).bind(raceId).first();
    if (!row) return response2({ ok: false, error: "race not found", race_id: raceId }, 404);
    const stored = JSON.parse(row.payload);
    const detail = applyStage64Archive(await restoreDisplaySnapshot(stored), stored);
    let odds = [];
    try {
      const result = await env.DB.prepare(`SELECT horse_no, win_odds, popularity,
        body_weight, body_weight_change, horse_status, updated_at
        FROM odds_current WHERE race_id = ? ORDER BY horse_no`).bind(raceId).all();
      odds = result.results || [];
    } catch {
    }
    return response2({
      ok: true,
      race_id: raceId,
      detail,
      summary: {
        id: raceId,
        date: detail.date,
        track: detail.track,
        raceNumber: detail.raceNumber
      },
      analysis_ready: !!row.analysis_ready,
      detail_updated_at: row.updated_at,
      odds
    });
  } catch {
    return response2({ ok: false, error: "race detail temporarily unavailable", race_id: raceId }, 503);
  }
}
__name(readRaceDisplay, "readRaceDisplay");
__name2(readRaceDisplay, "readRaceDisplay");
var RICH_KEYS = Object.freeze(["recentRaces", "allPastRuns"]);
var ARCHIVE_KEYS = Object.freeze(["careerArchive", "careerTransport", "_careerHistoryAudit", "careerStartEvidence"]);
function needsHistoryPreservation(detail) {
  return !!detail && Array.isArray(detail.horses) && detail.horses.some((h) => h && Number(h.horseNumber ?? h.horse_no) > 0);
}
__name(needsHistoryPreservation, "needsHistoryPreservation");
__name2(needsHistoryPreservation, "needsHistoryPreservation");
function runDate(run) {
  const value = String(run?.date ?? run?.raceDate ?? run?.\u65E5\u4ED8 ?? "").trim();
  if (/^\d{8}$/.test(value)) return value.slice(0, 4) + "-" + value.slice(4, 6) + "-" + value.slice(6, 8);
  const m = value.match(/^(\d{4})[./-](\d{1,2})[./-](\d{1,2})/);
  return m ? m[1] + "-" + m[2].padStart(2, "0") + "-" + m[3].padStart(2, "0") : "";
}
__name(runDate, "runDate");
__name2(runDate, "runDate");
function runKey(run) {
  if (!run || typeof run !== "object") return "raw:" + JSON.stringify(run);
  const date = runDate(run);
  if (date) return "date:" + date;
  const raceId = String(run.raceId ?? run.race_id ?? run.netkeibaRaceId ?? "").trim();
  if (raceId) return "race:" + raceId;
  return "raw:" + JSON.stringify(run, Object.keys(run).sort());
}
__name(runKey, "runKey");
__name2(runKey, "runKey");
function mergeRuns(previous, incoming) {
  const rows = /* @__PURE__ */ new Map();
  for (const run of [...Array.isArray(previous) ? previous : [], ...Array.isArray(incoming) ? incoming : []]) {
    const key = runKey(run);
    if (!rows.has(key)) {
      rows.set(key, run && typeof run === "object" ? { ...run } : run);
      continue;
    }
    const saved = rows.get(key);
    if (!saved || typeof saved !== "object" || !run || typeof run !== "object") continue;
    for (const [field, value] of Object.entries(run)) {
      if (saved[field] === void 0 || saved[field] === null || saved[field] === "" || Array.isArray(saved[field]) && saved[field].length === 0) {
        if (value !== void 0 && value !== null && value !== "") saved[field] = value;
      }
    }
  }
  const result = [...rows.values()];
  return result.sort((a, b) => {
    const da = runDate(a), db = runDate(b);
    return da && db ? db.localeCompare(da) : 0;
  });
}
__name(mergeRuns, "mergeRuns");
__name2(mergeRuns, "mergeRuns");
function archiveRunCount(archive) {
  const value = Number(archive?.storedRunCount ?? archive?.olderRunCount ?? NaN);
  return Number.isInteger(value) && value >= 0 ? value : null;
}
__name(archiveRunCount, "archiveRunCount");
__name2(archiveRunCount, "archiveRunCount");
function mergeStoredHorseHistory(incoming, previousHorses) {
  if (!incoming || !Array.isArray(incoming.horses) || !Array.isArray(previousHorses)) return incoming;
  const saved = new Map(previousHorses.filter(Boolean).map((h) => [Number(h.horseNumber ?? h.horse_no), h]).filter(([no]) => Number.isInteger(no) && no > 0));
  return { ...incoming, horses: incoming.horses.map((h) => {
    if (!h || typeof h !== "object") return h;
    const before = saved.get(Number(h.horseNumber ?? h.horse_no));
    if (!before) return h;
    const result = { ...h };
    for (const key of RICH_KEYS) {
      const previousRuns = Array.isArray(before[key]) ? before[key] : [];
      const incomingRuns = Array.isArray(h[key]) ? h[key] : [];
      if (previousRuns.length || incomingRuns.length) {
        const merged = mergeRuns(previousRuns, incomingRuns);
        result[key] = key === "recentRaces" ? merged.slice(0, 5) : merged;
      }
    }
    for (const key of ARCHIVE_KEYS) {
      if (before[key] !== void 0 && h[key] === void 0) result[key] = before[key];
    }
    const oldArchive = before.careerArchive, newArchive = h.careerArchive;
    if (oldArchive && newArchive && oldArchive.sha256 !== newArchive.sha256) {
      const oldCount = archiveRunCount(oldArchive), newCount = archiveRunCount(newArchive);
      if (newCount === null || oldCount === null || newCount <= oldCount) {
        result.careerArchive = oldArchive;
        for (const key of ["careerTransport", "_careerHistoryAudit"]) {
          if (before[key] !== void 0) result[key] = before[key];
        }
      }
    }
    return result;
  }) };
}
__name(mergeStoredHorseHistory, "mergeStoredHorseHistory");
__name2(mergeStoredHorseHistory, "mergeStoredHorseHistory");
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type, authorization, x-sync-token",
      "access-control-allow-methods": "GET,POST,OPTIONS"
    }
  });
}
__name(json, "json");
__name2(json, "json");
function safeJson(text) {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}
__name(safeJson, "safeJson");
__name2(safeJson, "safeJson");
function first(obj, ...keys) {
  for (const key of keys) {
    const value = obj?.[key];
    if (value !== void 0 && value !== null && value !== "") {
      return value;
    }
  }
  return null;
}
__name(first, "first");
__name2(first, "first");
function asInt(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : fallback;
}
__name(asInt, "asInt");
__name2(asInt, "asInt");
function asNum(value) {
  if (value === null || value === void 0 || value === "") {
    return null;
  }
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}
__name(asNum, "asNum");
__name2(asNum, "asNum");
function nowSec() {
  return Math.floor(Date.now() / 1e3);
}
__name(nowSec, "nowSec");
__name2(nowSec, "nowSec");
function authorized(request, env) {
  if (!env.SYNC_TOKEN) return false;
  const bearer = request.headers.get("authorization") || "";
  const headerToken = request.headers.get("x-sync-token") || "";
  return bearer === `Bearer ${env.SYNC_TOKEN}` || headerToken === env.SYNC_TOKEN;
}
__name(authorized, "authorized");
__name2(authorized, "authorized");
async function runBatches(db, statements, size = 75) {
  const results = [];
  for (let i = 0; i < statements.length; i += size) {
    const chunk = statements.slice(i, i + size);
    if (chunk.length) {
      results.push(...await db.batch(chunk));
    }
  }
  return results;
}
__name(runBatches, "runBatches");
__name2(runBatches, "runBatches");
var worker_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204
      });
    }
    try {
      if (path === "/api/health") {
        return json({
          ok: true,
          service: "KRAIZ API",
          version: "cloudflare-api-v3-sync"
        });
      }
      if (path === "/api/db-check") {
        const result = await env.DB.prepare(`
          SELECT name
          FROM sqlite_master
          WHERE type = 'table'
          ORDER BY name
        `).all();
        return json({
          ok: true,
          tables: result.results || []
        });
      }
      if (path === "/api/races") {
        const date = url.searchParams.get("date");
        if (!date) {
          return json({
            ok: false,
            error: "date is required"
          }, 400);
        }
        const result = await env.DB.prepare(`
          SELECT
            race_id,
            race_date,
            circuit,
            track,
            race_no,
            start_time,
            title,
            surface,
            distance,
            weather,
            condition,
            volatility_label,
            volatility_score,
            race_status,
            updated_at
          FROM race_summaries
          WHERE race_date = ?
          ORDER BY circuit, track, race_no
        `).bind(date).all();
        return json({
          ok: true,
          date,
          races: result.results || []
        });
      }
      if (path === "/api/day") {
        const date = url.searchParams.get("date");
        const includeDetails = url.searchParams.get("details") !== "0";
        if (!date) {
          return json({
            ok: false,
            error: "date is required"
          }, 400);
        }
        const summaryResult = await env.DB.prepare(`
    SELECT *
    FROM race_summaries
    WHERE race_date = ?
    ORDER BY circuit, track, race_no
  `).bind(date).all();
        const races = (summaryResult.results || []).map(
          (r) => ({
            id: r.race_id,
            date: r.race_date,
            circuit: r.circuit,
            track: r.track,
            raceNumber: r.race_no,
            startTime: r.start_time,
            scheduledStartTime: r.start_time,
            title: r.title,
            surface: r.surface,
            distance: r.distance,
            weather: r.weather,
            condition: r.condition,
            volatility: {
              label: r.volatility_label || "",
              score: r.volatility_score
            },
            raceStatus: r.race_status || "",
            updatedAtEpoch: r.updated_at
          })
        );
        if (!includeDetails) {
          return json({
            ok: true,
            date,
            races,
            details: [],
            raceCount: races.length,
            detailCount: 0,
            analysisCount: 0,
            missing: [],
            complete: races.length > 0,
            displayComplete: races.length > 0,
            source: "cloudflare-d1"
          });
        }
        const detailResult = await env.DB.prepare(`
    SELECT
      race_id,
      payload,
      analysis_ready,
      updated_at
    FROM race_details
    WHERE race_date = ?
    ORDER BY race_id
  `).bind(date).all();
        const detailRows = detailResult.results || [];
        const details = detailRows.map((r) => safeJson(r.payload)).filter(Boolean);
        const detailIds = new Set(
          details.map(
            (d) => String(d.id || d.race_id || d.raceId || "")
          )
        );
        const missing = races.map((r) => String(r.id || "")).filter((id) => id && !detailIds.has(id));
        const analysisCount = detailRows.filter(
          (r) => Number(r.analysis_ready || 0) === 1
        ).length;
        const complete = races.length > 0 && missing.length === 0;
        return json({
          ok: true,
          date,
          races,
          details,
          raceCount: races.length,
          detailCount: details.length,
          analysisCount,
          missing,
          complete,
          displayComplete: complete,
          analysisComplete: complete && analysisCount >= races.length,
          source: "cloudflare-d1"
        });
      }
      if (path.startsWith("/api/race/")) {
        const raceId = decodeURIComponent(
          path.substring("/api/race/".length)
        );
        if (!raceId) {
          return json({
            ok: false,
            error: "race_id is required"
          }, 400);
        }
        const detail = await env.DB.prepare(`
          SELECT
            race_id,
            race_date,
            payload,
            analysis_ready,
            updated_at
          FROM race_details
          WHERE race_id = ?
          LIMIT 1
        `).bind(raceId).first();
        if (!detail) {
          return json({
            ok: false,
            error: "race not found",
            race_id: raceId
          }, 404);
        }
        const summary = await env.DB.prepare(`
          SELECT *
          FROM race_summaries
          WHERE race_id = ?
          LIMIT 1
        `).bind(raceId).first();
        const odds = await env.DB.prepare(`
          SELECT
            horse_no,
            win_odds,
            popularity,
            body_weight,
            body_weight_change,
            horse_status,
            updated_at
          FROM odds_current
          WHERE race_id = ?
          ORDER BY horse_no
        `).bind(raceId).all();
        return json({
          ok: true,
          race_id: raceId,
          summary: summary || null,
          detail: safeJson(detail.payload),
          analysis_ready: !!detail.analysis_ready,
          detail_updated_at: detail.updated_at,
          odds: odds.results || []
        });
      }
      if (path.startsWith("/api/odds/")) {
        const raceId = decodeURIComponent(
          path.substring("/api/odds/".length)
        );
        const result = await env.DB.prepare(`
          SELECT
            horse_no,
            win_odds,
            popularity,
            body_weight,
            body_weight_change,
            horse_status,
            updated_at
          FROM odds_current
          WHERE race_id = ?
          ORDER BY horse_no
        `).bind(raceId).all();
        return json({
          ok: true,
          race_id: raceId,
          odds: result.results || []
        });
      }
      if (path === "/api/sync") {
        if (request.method !== "POST") {
          return json({
            ok: false,
            error: "POST required"
          }, 405);
        }
        if (!authorized(request, env)) {
          const expectedLength = String(env.SYNC_TOKEN || "").trim().length;
          const headerLength = String(
            request.headers.get("x-sync-token") || ""
          ).trim().length;
          return json({
            ok: false,
            error: "unauthorized",
            debug: {
              cloudflare_token_length: expectedLength,
              github_token_length: headerLength
            }
          }, 401);
        }
        const body = await request.json();
        const summaries = Array.isArray(body.summaries) ? body.summaries : Array.isArray(body.races) ? body.races : [];
        const details = Array.isArray(body.details) ? body.details : Array.isArray(body.raceDetails) ? body.raceDetails : [];
        const oddsCurrent = Array.isArray(body.odds_current) ? body.odds_current : Array.isArray(body.oddsCurrent) ? body.oddsCurrent : [];
        const oddsHistory = Array.isArray(body.odds_history) ? body.odds_history : Array.isArray(body.oddsHistory) ? body.oddsHistory : [];
        const meta = body.meta && typeof body.meta === "object" ? body.meta : {};
        const syncedAt = nowSec();
        const summaryStatements = [];
        for (const row of summaries) {
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId",
              "id"
            ) || ""
          );
          const raceDate = String(
            first(
              row,
              "race_date",
              "raceDate",
              "date"
            ) || ""
          );
          if (!raceId || !raceDate) {
            continue;
          }
          const volatility = row.volatility && typeof row.volatility === "object" ? row.volatility : {};
          const volatilityLabel = first(
            row,
            "volatility_label",
            "volatilityLabel"
          ) ?? first(volatility, "label");
          const volatilityScore = first(
            row,
            "volatility_score",
            "volatilityScore"
          ) ?? first(volatility, "score");
          summaryStatements.push(
            env.DB.prepare(`
              INSERT INTO race_summaries (
                race_id,
                race_date,
                circuit,
                track,
                race_no,
                start_time,
                title,
                surface,
                distance,
                weather,
                condition,
                volatility_label,
                volatility_score,
                race_status,
                updated_at
              )
              VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
              )

              ON CONFLICT(race_id)
              DO UPDATE SET
                race_date =
                  excluded.race_date,
                circuit =
                  excluded.circuit,
                track =
                  excluded.track,
                race_no =
                  excluded.race_no,
                start_time =
                  excluded.start_time,
                title =
                  excluded.title,
                surface =
                  excluded.surface,
                distance =
                  excluded.distance,
                weather =
                  excluded.weather,
                condition =
                  excluded.condition,
                volatility_label =
                  excluded.volatility_label,
                volatility_score =
                  excluded.volatility_score,
                race_status =
                  excluded.race_status,
                updated_at =
                  excluded.updated_at
            `).bind(
              raceId,
              raceDate,
              String(
                first(row, "circuit") || ""
              ),
              String(
                first(row, "track") || ""
              ),
              asInt(
                first(
                  row,
                  "race_no",
                  "raceNo",
                  "raceNumber"
                )
              ),
              String(
                first(
                  row,
                  "start_time",
                  "startTime",
                  "scheduledStartTime"
                ) || ""
              ),
              String(
                first(row, "title") || ""
              ),
              String(
                first(row, "surface") || ""
              ),
              asInt(
                first(row, "distance")
              ),
              String(
                first(row, "weather") || ""
              ),
              String(
                first(row, "condition") || ""
              ),
              volatilityLabel == null ? "" : String(volatilityLabel),
              volatilityScore == null ? null : asInt(volatilityScore),
              String(
                first(
                  row,
                  "race_status",
                  "raceStatus",
                  "status"
                ) || ""
              ),
              asInt(
                first(
                  row,
                  "updated_at",
                  "updatedAt",
                  "updatedAtEpoch"
                ),
                syncedAt
              )
            )
          );
        }
        const preserveIds = /* @__PURE__ */ new Set();
        for (const row of details) {
          const raw = row.payload ?? row.detail ?? row;
          const candidate = typeof raw === "string" ? safeJson(raw) : raw;
          if (!needsHistoryPreservation(candidate)) continue;
          const id = String(first(row, "race_id", "raceId", "id") || first(candidate, "race_id", "raceId", "id") || "");
          if (id) preserveIds.add(id);
        }
        const previousHorsesByRace = /* @__PURE__ */ new Map();
        const ids = [...preserveIds];
        for (let start = 0; start < ids.length; start += 25) {
          const batch = ids.slice(start, start + 25);
          const placeholders = batch.map(() => "?").join(",");
          const found = await env.DB.prepare(
            `SELECT race_id,json_extract(payload,'$.horses') AS horses
              FROM race_details WHERE race_id IN (${placeholders}) AND json_valid(payload)=1`
          ).bind(...batch).all();
          for (const saved of found.results || []) {
            const horses = safeJson(saved.horses);
            if (Array.isArray(horses)) previousHorsesByRace.set(String(saved.race_id), horses);
          }
        }
        const detailStatements = [];
        for (const row of details) {
          const rawPayload = row.payload ?? row.detail ?? row;
          let payloadObject = typeof rawPayload === "string" ? safeJson(rawPayload) : rawPayload;
          if (!payloadObject || typeof payloadObject !== "object") continue;
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId",
              "id"
            ) || first(
              payloadObject,
              "race_id",
              "raceId",
              "id"
            ) || ""
          );
          const raceDate = String(
            first(
              row,
              "race_date",
              "raceDate",
              "date"
            ) || first(
              payloadObject,
              "race_date",
              "raceDate",
              "date"
            ) || ""
          );
          if (!raceId || !raceDate) {
            continue;
          }
          const analysisReadyRaw = first(
            row,
            "analysis_ready",
            "analysisReady"
          ) ?? first(
            payloadObject?.preparedMeta || {},
            "diagnosisReady"
          );
          const analysisReady = analysisReadyRaw ? 1 : 0;
          const savedHorses = previousHorsesByRace.get(raceId);
          if (savedHorses) payloadObject = mergeStoredHorseHistory(payloadObject, savedHorses);
          const beforeRow = await env.DB.prepare(
            "SELECT payload FROM race_details WHERE race_id = ? LIMIT 1"
          ).bind(raceId).first();
          const before = safeJson(beforeRow?.payload);
          let newOriginal = null;
          try {
            newOriginal = stage64Archive(await restoreDisplaySnapshot(payloadObject));
          } catch {
          }
          if (!newOriginal && before) {
            try {
              newOriginal = stage64Archive(await restoreDisplaySnapshot(before));
            } catch {
            }
          }
          payloadObject = retainStage64Archive(payloadObject, before, newOriginal);
          const payloadText = JSON.stringify(payloadObject);
          detailStatements.push(
            env.DB.prepare(`
              INSERT INTO race_details (
                race_id,
                race_date,
                payload,
                analysis_ready,
                updated_at
              )
              VALUES (?, ?, ?, ?, ?)

              ON CONFLICT(race_id)
              DO UPDATE SET
                race_date =
                  excluded.race_date,
                payload =
                  excluded.payload,
                analysis_ready =
                  excluded.analysis_ready,
                updated_at =
                  excluded.updated_at
            `).bind(
              raceId,
              raceDate,
              payloadText,
              analysisReady,
              asInt(
                first(
                  row,
                  "updated_at",
                  "updatedAt",
                  "updatedAtEpoch"
                ),
                syncedAt
              )
            )
          );
        }
        const currentStatements = [];
        for (const row of oddsCurrent) {
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId"
            ) || ""
          );
          const horseNo = asInt(
            first(
              row,
              "horse_no",
              "horseNo",
              "horseNumber"
            )
          );
          if (!raceId || horseNo <= 0) {
            continue;
          }
          currentStatements.push(
            env.DB.prepare(`
              INSERT INTO odds_current (
                race_id,
                horse_no,
                win_odds,
                popularity,
                body_weight,
                body_weight_change,
                horse_status,
                updated_at
              )
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)

              ON CONFLICT(race_id, horse_no)
              DO UPDATE SET
                win_odds =
                  excluded.win_odds,
                popularity =
                  excluded.popularity,
                body_weight =
                  excluded.body_weight,
                body_weight_change =
                  excluded.body_weight_change,
                horse_status =
                  excluded.horse_status,
                updated_at =
                  excluded.updated_at
            `).bind(
              raceId,
              horseNo,
              asNum(
                first(
                  row,
                  "win_odds",
                  "winOdds"
                )
              ),
              first(
                row,
                "popularity"
              ) == null ? null : asInt(
                first(row, "popularity")
              ),
              first(
                row,
                "body_weight",
                "bodyWeight"
              ) == null ? null : asInt(
                first(
                  row,
                  "body_weight",
                  "bodyWeight"
                )
              ),
              first(
                row,
                "body_weight_change",
                "bodyWeightChange"
              ) == null ? null : asInt(
                first(
                  row,
                  "body_weight_change",
                  "bodyWeightChange"
                )
              ),
              String(
                first(
                  row,
                  "horse_status",
                  "horseStatus",
                  "status"
                ) || ""
              ),
              asInt(
                first(
                  row,
                  "updated_at",
                  "updatedAt"
                ),
                syncedAt
              )
            )
          );
        }
        const historyStatements = [];
        for (const row of oddsHistory) {
          const raceId = String(
            first(
              row,
              "race_id",
              "raceId"
            ) || ""
          );
          const horseNo = asInt(
            first(
              row,
              "horse_no",
              "horseNo",
              "horseNumber"
            )
          );
          const capturedAt = asInt(
            first(
              row,
              "captured_at",
              "capturedAt"
            ),
            syncedAt
          );
          if (!raceId || horseNo <= 0) {
            continue;
          }
          historyStatements.push(
            env.DB.prepare(`
              INSERT INTO odds_history (
                race_id,
                horse_no,
                win_odds,
                popularity,
                captured_at
              )

              SELECT ?, ?, ?, ?, ?

              WHERE NOT EXISTS (
                SELECT 1
                FROM odds_history
                WHERE race_id = ?
                  AND horse_no = ?
                  AND captured_at = ?
              )
            `).bind(
              raceId,
              horseNo,
              asNum(
                first(
                  row,
                  "win_odds",
                  "winOdds"
                )
              ),
              first(
                row,
                "popularity"
              ) == null ? null : asInt(
                first(row, "popularity")
              ),
              capturedAt,
              raceId,
              horseNo,
              capturedAt
            )
          );
        }
        const metaStatements = [];
        for (const [key, value] of Object.entries(meta)) {
          metaStatements.push(
            env.DB.prepare(`
              INSERT INTO meta (
                key,
                value,
                updated_at
              )
              VALUES (?, ?, ?)

              ON CONFLICT(key)
              DO UPDATE SET
                value =
                  excluded.value,
                updated_at =
                  excluded.updated_at
            `).bind(
              String(key),
              typeof value === "string" ? value : JSON.stringify(value),
              syncedAt
            )
          );
        }
        metaStatements.push(
          env.DB.prepare(`
            INSERT INTO meta (
              key,
              value,
              updated_at
            )
            VALUES (
              'last_sync_at',
              ?,
              ?
            )

            ON CONFLICT(key)
            DO UPDATE SET
              value =
                excluded.value,
              updated_at =
                excluded.updated_at
          `).bind(
            String(syncedAt),
            syncedAt
          )
        );
        await runBatches(
          env.DB,
          summaryStatements
        );
        await runBatches(
          env.DB,
          detailStatements
        );
        await runBatches(
          env.DB,
          currentStatements
        );
        await runBatches(
          env.DB,
          historyStatements
        );
        await runBatches(
          env.DB,
          metaStatements
        );
        return json({
          ok: true,
          synced_at: syncedAt,
          received: {
            summaries: summaries.length,
            details: details.length,
            odds_current: oddsCurrent.length,
            odds_history: oddsHistory.length,
            meta: Object.keys(meta).length
          },
          written: {
            summaries: summaryStatements.length,
            details: detailStatements.length,
            odds_current: currentStatements.length,
            odds_history: historyStatements.length,
            meta: metaStatements.length
          }
        });
      }
      return json({
        ok: true,
        service: "KRAIZ API",
        endpoints: [
          "/api/health",
          "/api/db-check",
          "/api/races?date=YYYY-MM-DD",
          "/api/race/<race_id>",
          "/api/odds/<race_id>",
          "POST /api/sync"
        ]
      });
    } catch (err) {
      return json({
        ok: false,
        error: String(
          err?.message || err
        )
      }, 500);
    }
  }
};
var SCRATCH_RE = /(?:出走取消|取消|競走除外|競走取消|除外|SCRATCHED)/i;
var CORS_ALLOW_HEADERS = "content-type, authorization, x-sync-token, cache-control, pragma, accept";
var CORS_ALLOW_METHODS = "GET,POST,OPTIONS";
function corsHeaders(request) {
  const requested = String(request?.headers?.get("access-control-request-headers") || "").trim();
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": CORS_ALLOW_METHODS,
    "access-control-allow-headers": requested || CORS_ALLOW_HEADERS,
    "access-control-max-age": "86400",
    "vary": "Origin, Access-Control-Request-Headers"
  };
}
__name(corsHeaders, "corsHeaders");
__name2(corsHeaders, "corsHeaders");
async function withCors(response2, request) {
  response2 = await publicRaceResponse(response2, request);
  const headers2 = new Headers(response2.headers);
  const cors = corsHeaders(request);
  for (const [key, value] of Object.entries(cors)) headers2.set(key, value);
  return new Response(response2.body, {
    status: response2.status,
    statusText: response2.statusText,
    headers: headers2
  });
}
__name(withCors, "withCors");
__name2(withCors, "withCors");
function overlayHorse(horse, live) {
  if (!horse || !live) return horse;
  const status = String(live.horse_status ?? live.status ?? "").trim();
  const next = { ...horse };
  if (live.win_odds != null) next.winOdds = live.win_odds;
  if (live.popularity != null) next.popularity = live.popularity;
  if (live.body_weight != null) next.bodyWeight = live.body_weight;
  if (live.body_weight_change != null) next.bodyWeightChange = live.body_weight_change;
  if (status) {
    next.status = status;
    next.scratched = SCRATCH_RE.test(status);
  }
  return next;
}
__name(overlayHorse, "overlayHorse");
__name2(overlayHorse, "overlayHorse");
function overlayDetail(detail, liveRows) {
  if (!detail || typeof detail !== "object" || !Array.isArray(detail.horses)) {
    return detail;
  }
  const byNo = /* @__PURE__ */ new Map();
  for (const row of liveRows || []) {
    const no = Number(row.horse_no ?? row.horseNumber ?? 0);
    if (no > 0) byNo.set(no, row);
  }
  return {
    ...detail,
    horses: detail.horses.map((h) => {
      const no = Number(h?.horseNumber ?? h?.horse_no ?? 0);
      return overlayHorse(h, byNo.get(no));
    })
  };
}
__name(overlayDetail, "overlayDetail");
__name2(overlayDetail, "overlayDetail");
function jsonResponse(body, original) {
  const headers2 = new Headers(original.headers);
  headers2.set("content-type", "application/json; charset=utf-8");
  headers2.set("cache-control", "no-store");
  return new Response(JSON.stringify(body), {
    status: original.status,
    statusText: original.statusText,
    headers: headers2
  });
}
__name(jsonResponse, "jsonResponse");
__name2(jsonResponse, "jsonResponse");
async function oddsForDay(env, date) {
  const result = await env.DB.prepare(`
    SELECT
      o.race_id,
      o.horse_no,
      o.win_odds,
      o.popularity,
      o.body_weight,
      o.body_weight_change,
      o.horse_status,
      o.updated_at
    FROM odds_current o
    INNER JOIN race_summaries r
      ON r.race_id = o.race_id
    WHERE r.race_date = ?
    ORDER BY o.race_id, o.horse_no
  `).bind(date).all();
  return result.results || [];
}
__name(oddsForDay, "oddsForDay");
__name2(oddsForDay, "oddsForDay");
async function enhanceRaceResponse(response2) {
  if (!response2.ok) return response2;
  let body;
  try {
    body = await response2.clone().json();
  } catch {
    return response2;
  }
  if (!body || typeof body !== "object") return response2;
  const odds = Array.isArray(body.odds) ? body.odds : [];
  body.detail = overlayDetail(body.detail, odds);
  return jsonResponse(body, response2);
}
__name(enhanceRaceResponse, "enhanceRaceResponse");
__name2(enhanceRaceResponse, "enhanceRaceResponse");
async function enhanceDayResponse(response2, env, url) {
  if (!response2.ok || url.searchParams.get("details") === "0") return response2;
  let body;
  try {
    body = await response2.clone().json();
  } catch {
    return response2;
  }
  if (!body || typeof body !== "object" || !Array.isArray(body.details)) return response2;
  const date = url.searchParams.get("date") || "";
  if (!date) return response2;
  let liveRows = [];
  try {
    liveRows = await oddsForDay(env, date);
  } catch {
    return response2;
  }
  const byRace = /* @__PURE__ */ new Map();
  for (const row of liveRows) {
    const rid = String(row.race_id || "");
    if (!rid) continue;
    if (!byRace.has(rid)) byRace.set(rid, []);
    byRace.get(rid).push(row);
  }
  body.details = body.details.map((detail) => {
    const rid = String(detail?.id ?? detail?.race_id ?? detail?.raceId ?? "");
    return overlayDetail(detail, byRace.get(rid) || []);
  });
  return jsonResponse(body, response2);
}
__name(enhanceDayResponse, "enhanceDayResponse");
__name2(enhanceDayResponse, "enhanceDayResponse");
var worker_entry_default = {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/research/preoff-evidence") {
      return handlePreoffCapture(request, env);
    }
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(request)
      });
    }
    if (request.method === "GET" && url.pathname.startsWith("/api/racecard/")) {
      let raceId;
      try {
        raceId = decodeURIComponent(url.pathname.slice("/api/racecard/".length));
      } catch {
        return withCors(new Response('{"ok":false,"error":"invalid race_id"}', { status: 400, headers: { "content-type": "application/json" } }), request);
      }
      return withCors(await readRacecard(env, raceId), request);
    }
    if (request.method === "GET" && url.pathname.startsWith("/api/race/") && url.searchParams.get("view") === "display") {
      let raceId;
      try {
        raceId = decodeURIComponent(url.pathname.slice("/api/race/".length));
      } catch {
        return withCors(new Response('{"ok":false,"error":"invalid race_id"}', { status: 400, headers: { "content-type": "application/json" } }), request);
      }
      return withCors(await readRaceDisplay(env, raceId), request);
    }
    let response2 = await worker_default.fetch(request, env, ctx);
    if (request.method === "GET") {
      if (url.pathname.startsWith("/api/race/")) {
        response2 = await enhanceRaceResponse(response2);
      } else if (url.pathname === "/api/day") {
        response2 = await enhanceDayResponse(response2, env, url);
      }
    }
    return withCors(response2, request);
  }
};

// .arvexq-production-overlay/api_forecast_revisions.mjs
var TABLE_SQL = [
  `CREATE TABLE IF NOT EXISTS forecast_revisions (race_id TEXT NOT NULL,revision_id TEXT NOT NULL,race_date TEXT NOT NULL,model_version TEXT NOT NULL,created_at TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,PRIMARY KEY(race_id,revision_id))`,
  `CREATE TABLE IF NOT EXISTS forecast_revision_current (race_id TEXT PRIMARY KEY,revision_id TEXT NOT NULL,updated_at TEXT NOT NULL)`
];
var headers = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "access-control-allow-origin": "*", "access-control-allow-headers": "content-type,authorization,x-sync-token" };
var response = /* @__PURE__ */ __name((value, status = 200) => new Response(JSON.stringify(value), { status, headers }), "response");
var STORAGE = "arvexq-storage-gzip-v1";
var utf8 = new TextEncoder();
var sha = /* @__PURE__ */ __name(async (bytes) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (x) => x.toString(16).padStart(2, "0")).join(""), "sha");
async function restoreStoredJSON(stored) {
  const value = JSON.parse(stored);
  if (value?.storageEncoding !== STORAGE) return stored;
  if (!Number.isInteger(value.bytes) || value.bytes <= 0 || value.bytes > 1e6) throw Error("invalid storage length");
  const bytes = Uint8Array.from(atob(value.gzipBase64), (x) => x.charCodeAt(0));
  const reader = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")).getReader();
  const chunks = [];
  let size = 0;
  while (true) {
    const { done, value: chunk } = await reader.read();
    if (done) break;
    size += chunk.length;
    if (size > value.bytes) {
      await reader.cancel();
      throw Error("storage expansion limit");
    }
    ;
    chunks.push(chunk);
  }
  const raw = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    raw.set(chunk, offset);
    offset += chunk.length;
  }
  if (size !== value.bytes || await sha(raw) !== value.sha256) throw Error("storage checksum mismatch");
  return new TextDecoder("utf-8", { fatal: true }).decode(raw);
}
__name(restoreStoredJSON, "restoreStoredJSON");
async function compressStoredJSON(raw) {
  const bytes = utf8.encode(raw), compressed = new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new CompressionStream("gzip"))).arrayBuffer());
  let binary = "";
  for (let i = 0; i < compressed.length; i += 8192) binary += String.fromCharCode(...compressed.subarray(i, i + 8192));
  const stored = JSON.stringify({ storageEncoding: STORAGE, bytes: bytes.length, sha256: await sha(bytes), gzipBase64: btoa(binary) });
  return utf8.encode(stored).length < bytes.length ? stored : raw;
}
__name(compressStoredJSON, "compressStoredJSON");
function authorized2(request, env) {
  const token = String(env.SYNC_TOKEN || "");
  return token.length > 0 && (request.headers.get("x-sync-token") === token || request.headers.get("authorization") === "Bearer " + token);
}
__name(authorized2, "authorized");
async function forecastRevisions(request, env) {
  const url = new URL(request.url), path = url.pathname;
  if (request.method === "OPTIONS") return new Response("", { headers });
  if (path === "/api/admin/forecast-revisions/migrate") {
    if (request.method !== "POST") return response({ ok: false, error: "method not allowed" }, 405);
    if (!authorized2(request, env)) return response({ ok: false, error: "unauthorized" }, 401);
    await env.DB.batch(TABLE_SQL.map((sql) => env.DB.prepare(sql)));
    return response({ ok: true, version: "arvexq-forecast-revision-v1", original_tables_modified: false });
  }
  if (path.startsWith("/api/forecast-revisions/")) {
    if (request.method !== "GET") return response({ ok: false, error: "method not allowed" }, 405);
    const id = decodeURIComponent(path.slice("/api/forecast-revisions/".length));
    try {
      const current = await env.DB.prepare(`SELECT r.payload_json FROM forecast_revisions r JOIN forecast_revision_current c ON c.race_id=r.race_id AND c.revision_id=r.revision_id WHERE r.race_id=?`).bind(id).first();
      if (!current) return response({ ok: true, raceId: id, storageEncoding: STORAGE, currentForecastRevisionId: null, forecastRevisions: [] });
      const rows = await env.DB.prepare("SELECT payload_json FROM forecast_revisions WHERE race_id=? ORDER BY created_at,revision_id").bind(id).all();
      const selected = JSON.parse(await restoreStoredJSON(current.payload_json));
      const restored = await Promise.all((rows.results || []).map((r) => restoreStoredJSON(r.payload_json)));
      return new Response('{"ok":true,"storageEncoding":' + JSON.stringify(STORAGE) + ',"raceId":' + JSON.stringify(id) + ',"currentForecastRevisionId":' + JSON.stringify(selected.revisionId) + ',"forecastRevisions":[' + restored.join(",") + "]}", { headers });
    } catch (error) {
      if (/no such table.*forecast_revision/.test(String(error))) return response({ ok: true, raceId: id, storageEncoding: STORAGE, schemaReady: false, currentForecastRevisionId: null, forecastRevisions: [] });
      throw error;
    }
  }
  if (path === "/api/admin/forecast-revisions") {
    if (request.method !== "POST") return response({ ok: false, error: "method not allowed" }, 405);
    if (!authorized2(request, env)) return response({ ok: false, error: "unauthorized" }, 401);
    const body = await request.json();
    let raw = body.revisionRawJson;
    if (raw === void 0 && typeof body.revisionStorageJson === "string") {
      try {
        if (utf8.encode(body.revisionStorageJson).length > 1e6) throw Error("storage size");
        raw = await restoreStoredJSON(body.revisionStorageJson);
      } catch {
        return response({ ok: false, error: "invalid compressed revision" }, 400);
      }
    }
    if (typeof raw !== "string" || new TextEncoder().encode(raw).length > 1e6) return response({ ok: false, error: "invalid revision size" }, 400);
    let revision;
    try {
      revision = JSON.parse(raw);
    } catch {
      return response({ ok: false, error: "invalid revision JSON" }, 400);
    }
    const { raceId, revisionId, raceDate, modelVersion, createdAt } = revision || {};
    if (revision.version !== "arvexq-forecast-revision-v1" || !raceId || !/^\d{4}-\d{2}-\d{2}$/.test(raceDate || "") || !/^[a-f0-9]{64}$/.test(revisionId || "") || typeof modelVersion !== "string" || !Number.isFinite(Date.parse(createdAt || "")) || !["retrospective", "preoff-candidate"].includes(revision.analysisType) || !Array.isArray(revision.horses))
      return response({ ok: false, error: "invalid revision identity" }, 400);
    const seen = /* @__PURE__ */ new Set();
    let honmei = 0;
    for (const horse of revision.horses) {
      if (!Number.isInteger(horse.horseNumber) || horse.horseNumber <= 0 || seen.has(horse.horseNumber) || !["", "\u25CE", "\u25CB", "\u25B2", "\u25B3", "\u2606", "\u6CE8"].includes(horse.mark)) return response({ ok: false, error: "invalid horse marks" }, 400);
      const p = horse.probabilities || {}, keys = ["win", "top2", "top3"];
      if (keys.some((k) => p[k] !== void 0 && (!Number.isFinite(p[k]) || p[k] < 0 || p[k] > 1)) || keys.every((k) => p[k] !== void 0) && (p.win > p.top2 + 1e-9 || p.top2 > p.top3 + 1e-9))
        return response({ ok: false, error: "invalid horse probabilities" }, 400);
      seen.add(horse.horseNumber);
      if (horse.mark === "\u25CE") honmei++;
    }
    if (honmei > 1) return response({ ok: false, error: "multiple honmei" }, 400);
    if ((revision.betPlan?.items || []).reduce((n, item) => n + (item.combos || []).length, 0) > 10)
      return response({ ok: false, error: "ticket limit exceeded" }, 400);
    const source = await env.DB.prepare("SELECT race_date FROM race_details WHERE race_id=?").bind(raceId).first();
    if (!source || source.race_date !== raceDate) return response({ ok: false, error: "source race mismatch" }, 409);
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw)))).map((x) => x.toString(16).padStart(2, "0")).join("");
    if (body.payloadSha256 !== digest) return response({ ok: false, error: "revision checksum mismatch" }, 400);
    let stored;
    if (body.revisionStorageJson !== void 0) {
      try {
        if (typeof body.revisionStorageJson !== "string" || utf8.encode(body.revisionStorageJson).length > utf8.encode(raw).length || await restoreStoredJSON(body.revisionStorageJson) !== raw) throw Error("storage mismatch");
        stored = body.revisionStorageJson;
      } catch {
        return response({ ok: false, error: "invalid compressed revision" }, 400);
      }
    } else stored = await compressStoredJSON(raw);
    const previous = await env.DB.prepare("SELECT payload_sha256 FROM forecast_revisions WHERE race_id=? AND revision_id=?").bind(raceId, revisionId).first();
    if (previous && previous.payload_sha256 !== digest) return response({ ok: false, error: "immutable revision conflict" }, 409);
    await env.DB.batch([
      env.DB.prepare("INSERT INTO forecast_revisions(race_id,revision_id,race_date,model_version,created_at,payload_json,payload_sha256) VALUES(?,?,?,?,?,?,?) ON CONFLICT(race_id,revision_id) DO NOTHING").bind(raceId, revisionId, raceDate, modelVersion, createdAt, stored, digest),
      env.DB.prepare("INSERT INTO forecast_revision_current(race_id,revision_id,updated_at) VALUES(?,?,?) ON CONFLICT(race_id) DO UPDATE SET revision_id=excluded.revision_id,updated_at=excluded.updated_at").bind(raceId, revisionId, (/* @__PURE__ */ new Date()).toISOString())
    ]);
    return response({ ok: true, raceId, revisionId, original_tables_modified: false });
  }
  return response({ ok: false, error: "not found" }, 404);
}
__name(forecastRevisions, "forecastRevisions");

// .arvexq-production-overlay/api_storage_audit.mjs
async function storageAudit(request, env) {
  if (!env.SYNC_TOKEN || request.headers.get("authorization") !== "Bearer " + env.SYNC_TOKEN)
    return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
  const statements = {
    page_count: "PRAGMA page_count",
    page_size: "PRAGMA page_size",
    details: "SELECT COUNT(*) AS rows, SUM(length(CAST(payload AS BLOB))) AS payload_bytes, MIN(race_date) AS first_date, MAX(race_date) AS last_date FROM race_details",
    summaries: "SELECT COUNT(*) AS rows FROM race_summaries",
    odds_current: "SELECT COUNT(*) AS rows FROM odds_current",
    odds_history: "SELECT COUNT(*) AS rows FROM odds_history"
  };
  const queries = {};
  for (const [name, sql] of Object.entries(statements)) {
    try {
      const result = await env.DB.prepare(sql).all();
      queries[name] = { results: result.results, meta: result.meta };
    } catch (e) {
      queries[name] = { error: String(e.message || e) };
    }
  }
  return Response.json(
    { ok: true, version: "arvexq-readonly-storage-v1", sql_writes: 0, queries },
    { headers: { "cache-control": "no-store" } }
  );
}
__name(storageAudit, "storageAudit");

// .arvexq-production-overlay/api_snapshot_export.mjs
var TABLES = ["race_details", "race_summaries", "odds_current", "odds_history", "meta", "forecast_revisions", "forecast_revision_current"];
async function snapshotExport(request, env) {
  if (!env.SYNC_TOKEN || request.headers.get("authorization") !== "Bearer " + env.SYNC_TOKEN)
    return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
  if (request.method !== "GET") return Response.json({ ok: false, error: "method not allowed" }, { status: 405 });
  const url = new URL(request.url), table = url.searchParams.get("table");
  const respond = /* @__PURE__ */ __name((data) => Response.json(data, { headers: { "cache-control": "no-store" } }), "respond");
  if (!table) {
    const placeholders = TABLES.map(() => "?").join(",");
    const schema = await env.DB.prepare(`SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL AND tbl_name IN (${placeholders}) AND type IN ('table','index') ORDER BY type DESC,name`).bind(...TABLES).all();
    const races = await env.DB.prepare("SELECT race_id,race_date,updated_at FROM race_details ORDER BY race_id").all();
    return respond({ ok: true, version: "arvexq-logical-backup-v1", sql_writes: 0, tables: TABLES.filter((name) => (schema.results || []).some((row) => row.type === "table" && row.name === name)), schema: schema.results, races: races.results });
  }
  if (!TABLES.includes(table)) return respond({ ok: false, error: "unsupported table" });
  const id = url.searchParams.get("race_id");
  if (table === "race_details" && id) {
    if (url.searchParams.has("chunk")) {
      const chunk = Number(url.searchParams.get("chunk")), size = 65536;
      if (!Number.isInteger(chunk) || chunk < 0 || chunk > 2e3) return Response.json({ ok: false, error: "invalid chunk" }, { status: 400 });
      const row2 = await env.DB.prepare("SELECT race_id,race_date,analysis_ready,updated_at,length(CAST(payload AS BLOB)) AS payload_bytes,hex(substr(CAST(payload AS BLOB),?,?)) AS payload_hex FROM race_details WHERE race_id=?").bind(chunk * size + 1, size, id).first();
      return respond({ ok: true, table, chunk, chunk_bytes: size, rows: row2 ? [row2] : [] });
    }
    const row = await env.DB.prepare("SELECT * FROM race_details WHERE race_id=?").bind(id).first();
    return respond({ ok: true, table, rows: row ? [row] : [] });
  }
  const offset = Number(url.searchParams.get("offset") || 0), limit = Number(url.searchParams.get("limit") || 1e3);
  if (!Number.isInteger(offset) || offset < 0 || offset > 1e7 || !Number.isInteger(limit) || limit < 1 || limit > 1e3 || table === "race_details")
    return Response.json({ ok: false, error: "invalid pagination" }, { status: 400 });
  const rows = await env.DB.prepare(`SELECT * FROM ${table} ORDER BY rowid LIMIT ? OFFSET ?`).bind(limit, offset).all();
  return respond({ ok: true, table, rows: rows.results });
}
__name(snapshotExport, "snapshotExport");

// .arvexq-production-overlay/api_full_snapshot.mjs
var KEY = "arvexqFullPayload";
var VERSION2 = "arvexq-full-payload-v1";
async function restoreBytes(envelope) {
  const ref = envelope && envelope[KEY];
  if (!ref || ref.version !== VERSION2 || !(ref.bytes > 0 && ref.bytes <= 1e8)) throw Error("invalid full snapshot envelope");
  const zipped = Uint8Array.from(atob(ref.gzipBase64), (c) => c.charCodeAt(0));
  const raw = await new Response(new Blob([zipped]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", raw)), (x) => x.toString(16).padStart(2, "0")).join("");
  if (raw.byteLength !== ref.bytes || hash !== ref.sha256) throw Error("full snapshot restore mismatch");
  return new Uint8Array(raw);
}
__name(restoreBytes, "restoreBytes");
async function readCompressedRace(env, id) {
  const record = await env.DB.prepare(`SELECT payload,analysis_ready,updated_at FROM race_details WHERE race_id=? AND json_valid(payload) AND json_extract(payload,'$.arvexqFullPayload.version')=?`).bind(id, VERSION2).first();
  if (!record) return null;
  const envelope = JSON.parse(record.payload), raw = await restoreBytes(envelope);
  const summary = await env.DB.prepare("SELECT * FROM race_summaries WHERE race_id=?").bind(id).first();
  const odds = await env.DB.prepare("SELECT horse_no,win_odds,popularity,body_weight,body_weight_change,horse_status,updated_at FROM odds_current WHERE race_id=? ORDER BY horse_no").bind(id).all();
  const prefix = JSON.stringify({
    ok: true,
    race_id: id,
    summary: summary || null,
    analysis_ready: !!record.analysis_ready,
    detail_updated_at: record.updated_at,
    odds: odds.results || []
  }).slice(0, -1) + ',"detail":';
  const encode = new TextEncoder();
  const stream = new ReadableStream({ start(controller) {
    controller.enqueue(encode.encode(prefix));
    controller.enqueue(raw);
    controller.enqueue(encode.encode("}"));
    controller.close();
  } });
  return new Response(stream, { headers: {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "content-type,authorization,cache-control,pragma,x-sync-token"
  } });
}
__name(readCompressedRace, "readCompressedRace");
async function compressStoredSnapshot(request, env) {
  if (!env.SYNC_TOKEN || request.headers.get("authorization") !== "Bearer " + env.SYNC_TOKEN)
    return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
  if (request.method !== "POST") return Response.json({ ok: false, error: "method not allowed" }, { status: 405 });
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ ok: false, error: "invalid JSON" }, { status: 400 });
  }
  const id = String(body.race_id || "");
  if (!id || !/^[a-f0-9]{64}$/.test(body.expected_sha256 || "") || !body.payload)
    return Response.json({ ok: false, error: "invalid backup proof" }, { status: 400 });
  const row = await env.DB.prepare(`SELECT payload,CASE WHEN json_valid(payload) THEN json_extract(payload,'$.arvexqFullPayload.version') ELSE NULL END AS codec FROM race_details WHERE race_id=?`).bind(id).first();
  if (!row) return Response.json({ ok: false, error: "missing original" }, { status: 404 });
  if (row.codec === VERSION2) return Response.json({ ok: true, already_compressed: true });
  const old = new TextEncoder().encode(row.payload);
  const oldHash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", old)), (x) => x.toString(16).padStart(2, "0")).join("");
  if (oldHash !== body.expected_sha256) return Response.json({ ok: false, error: "original changed since backup" }, { status: 409 });
  let raw;
  try {
    raw = await restoreBytes(body.payload);
  } catch {
    return Response.json({ ok: false, error: "compression restore failed" }, { status: 400 });
  }
  if (body.payload[KEY].sha256 !== oldHash || raw.byteLength !== old.byteLength)
    return Response.json({ ok: false, error: "compression does not restore original" }, { status: 400 });
  const original = JSON.parse(new TextDecoder().decode(raw)), thin = {};
  const keep = /* @__PURE__ */ new Set(["preRacePrediction", "preRaceBet", "preRaceBetPlan", "morningTicketEvidence", "morningPicks", "environmentMeta", "volatility", "preparedMeta", "result", "modelRevisions", "authorizedRevisions", "massFeatureArchive", "dataReadiness"]);
  for (const [key, value] of Object.entries(original)) if (key !== KEY && (keep.has(key) || value === null || typeof value !== "object")) thin[key] = value;
  if (Array.isArray(original.horses)) thin.horses = original.horses.filter((h) => h && typeof h === "object").map((h) => Object.fromEntries(Object.entries(h).filter(([key, value]) => key === "careerTransport" || value === null || typeof value !== "object")));
  thin[KEY] = body.payload[KEY];
  const packed = JSON.stringify(thin);
  if (new TextEncoder().encode(packed).byteLength >= old.byteLength) return Response.json({ ok: true, skipped_no_saving: true });
  const result = await env.DB.prepare("UPDATE race_details SET payload=? WHERE race_id=? AND payload=?").bind(packed, id, row.payload).run();
  if (!result.meta || result.meta.changes !== 1) return Response.json({ ok: false, error: "concurrent original update" }, { status: 409 });
  return Response.json({ ok: true, restored_sha256: oldHash, original_bytes: old.byteLength, stored_bytes: new TextEncoder().encode(packed).byteLength, meta: result.meta });
}
__name(compressStoredSnapshot, "compressStoredSnapshot");

// .arvexq-production-overlay/worker-entry-overlay.mjs
var worker_entry_overlay_default = { async fetch(request, env, ctx) {
  const path = new URL(request.url).pathname;
  if (path.startsWith("/api/forecast-revisions/") || path.startsWith("/api/admin/forecast-revisions")) return forecastRevisions(request, env);
  if (path === "/api/admin/storage-audit") return storageAudit(request, env);
  if (path === "/api/admin/snapshot-export") return snapshotExport(request, env);
  if (path === "/api/admin/snapshot-compress") return compressStoredSnapshot(request, env);
  if (request.method === "GET" && path.startsWith("/api/race/")) {
    const id = decodeURIComponent(path.slice("/api/race/".length));
    const full = await readCompressedRace(env, id);
    if (full) return full;
  }
  return worker_entry_default.fetch(request, env, ctx);
} };
export {
  worker_entry_overlay_default as default
};
//# sourceMappingURL=worker-entry-overlay.js.map