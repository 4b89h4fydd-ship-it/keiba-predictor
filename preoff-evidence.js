/* Research-only, append-only D1 endpoint. Never publishes predictions or marks.
 * The Worker clock governs admission. A request-supplied attestation is not
 * independent proof of acquisition time or of an official runner roster.
 */
const VERSION = "arvexq-d1-preoff-evidence-v1";
const MAX_REQUEST_BYTES = 950000;
const DELAY_SECONDS = 300;

function stable(value) {
  if (Array.isArray(value)) return "[" + value.map(stable).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + stable(value[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}

async function sha256(value, canonicalText) {
  const bytes = new TextEncoder().encode(canonicalText === undefined ? stable(value) : canonicalText);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
}

function reply(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: {
    "content-type": "application/json; charset=utf-8", "cache-control": "no-store"
  }});
}

function authenticated(request, env) {
  const secret = typeof env.FORECAST_CAPTURE_TOKEN === "string" ? env.FORECAST_CAPTURE_TOKEN : "";
  return secret.length >= 24 && request.headers.get("authorization") === "Bearer " + secret;
}

function validIsoDate(date) {
  return typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date)
    && !Number.isNaN(Date.parse(date + "T00:00:00Z"));
}

function checkDocument(snapshot, receipt, now) {
  if (!snapshot || !receipt || typeof snapshot !== "object" || typeof receipt !== "object") {
    throw new Error("snapshot and acquisition receipt required");
  }
  if (!snapshot.raceId || receipt.raceId !== snapshot.raceId ||
      receipt.featureHash !== snapshot.featureHash ||
      receipt.version !== "arvexq-preoff-raw-evidence-v1" ||
      receipt.source !== "preoff-acquisition-log" || receipt.attestedPreOff !== true) {
    throw new Error("invalid capture identity and provenance");
  }
  if (!validIsoDate(snapshot.date) || !["中央", "地方"].includes(snapshot.circuit)) {
    throw new Error("invalid race date or circuit");
  }
  const captured = receipt.capturedAtEpoch, post = receipt.postAtEpoch;
  if (!Number.isSafeInteger(captured) || !Number.isSafeInteger(post) ||
      !(captured > 0 && captured <= now && now < post && now - captured <= DELAY_SECONDS)) {
    throw new Error("not a timely pre-off capture");
  }
  const postJst = new Date((post + 9 * 3600) * 1000).toISOString().slice(0, 10);
  if (postJst !== snapshot.date) throw new Error("post date mismatch");
  const numbers = receipt.activeHorseNumbers;
  if (!Array.isArray(numbers) || numbers.length < 3 || numbers.length > 30 ||
      new Set(numbers).size !== numbers.length ||
      numbers.some(n => !Number.isSafeInteger(n) || n < 1 || n > 99)) {
    throw new Error("invalid official field claim");
  }
  const rows = snapshot.rows;
  if (!Array.isArray(rows) || rows.length !== numbers.length ||
      snapshot.horseCount !== rows.length ||
      new Set(rows.map(r => r?.horseNumber)).size !== rows.length ||
      rows.some(r => !numbers.includes(r?.horseNumber) || !r.features || typeof r.features !== "object")) {
    throw new Error("frozen runners disagree with active field claim");
  }
  if (rows.some(r => Object.keys(r.features).some(k => /^(?:market::|result::|current::|payout::|label::)/.test(k)))) {
    throw new Error("future/result/market features prohibited");
  }
}

export async function handlePreoffCapture(request, env, { now = () => Math.floor(Date.now() / 1000) } = {}) {
  if (request.method !== "POST") return reply({ok:false,error:"POST required"},405);
  if (!authenticated(request, env)) return reply({ok:false,error:"unauthorized"},401);
  const size = Number(request.headers.get("content-length") || 0);
  if (size > MAX_REQUEST_BYTES) return reply({ok:false,error:"payload too large"},413);
  let body;
  try {
    const encoding = request.headers.get('content-encoding');
    if (encoding !== 'gzip') throw new Error('gzip encoding required');
    if (typeof DecompressionStream !== 'function') throw new Error('gzip decompression unavailable');
    const stream = request.body.pipeThrough(new DecompressionStream('gzip'));
    const reader = stream.getReader();
    const chunks = [];
    let total = 0;
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > 6000000) { await reader.cancel(); return reply({ok:false,error:'expanded payload too large'},413); }
      chunks.push(value);
    }
    const expanded = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { expanded.set(chunk, offset); offset += chunk.byteLength; }
    const raw = new TextDecoder('utf-8', {fatal:true}).decode(expanded);

    body = JSON.parse(raw);
    checkDocument(body.snapshot, body.receipt, now());
    const snap = body.snapshot, rec = body.receipt;
    const {featureHash, ...snapshotWithoutHash} = snap;
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
    const {receiptHash, ...receiptWithoutHash} = rec;
    if (stable(JSON.parse(receiptCoreText)) !== stable(receiptWithoutHash)) {
      throw new Error("receipt canonical payload inconsistent");
    }
    if (await sha256(receiptWithoutHash, receiptCoreText) !== receiptHash) {
      throw new Error("receipt hash mismatch");
    }
    const identity = {raceId:rec.raceId,featureHash:rec.featureHash,capturedAtEpoch:rec.capturedAtEpoch};
    const captureId = await sha256(identity);
    // Only insert; conflicting identities or changed bytes never overwrite stored evidence.
    const response = await env.DB.prepare(
      "INSERT OR IGNORE INTO forecast_preoff_evidence " +
      "(capture_id,race_id,feature_hash,receipt_hash,snapshot_json,receipt_json,captured_at_epoch,stored_at_epoch,post_at_epoch) " +
      "VALUES (?,?,?,?,?,?,?,?,?)"
    ).bind(captureId,rec.raceId,featureHash,receiptHash,stable(snap),stable(rec),
           rec.capturedAtEpoch,now(),rec.postAtEpoch).run();
    if (response.meta?.changes === 0) {
      const old = await env.DB.prepare(
        "SELECT feature_hash,receipt_hash,snapshot_json,receipt_json FROM forecast_preoff_evidence WHERE capture_id=?"
      ).bind(captureId).first();
      if (!old || old.feature_hash !== featureHash || old.receipt_hash !== receiptHash ||
          old.snapshot_json !== stable(snap) || old.receipt_json !== stable(rec)) {
        return reply({ok:false,error:"immutable identity collision"},409);
      }
    }
    return reply({ok:true, captureId, version:VERSION, researchOnly:true,
      duplicate:response.meta?.changes === 0},response.meta?.changes === 0 ? 200 : 201);
  } catch (error) {
    const message = String(error?.message || "");
    // Missing migration fails closed; no table is created at request time.
    if (/no such table|no such column/i.test(message)) return reply({ok:false,error:"migration not applied"},503);
    if (/D1_|SQLITE_|database/i.test(message)) return reply({ok:false,error:"storage unavailable"},503);
    return reply({ok:false,error:message || "invalid capture"},422);
  }
}
