// Lossless factual-history preservation at the D1 sync boundary.
// Compact observations cannot erase previously verified starts or their sidecar archive.
const RICH_KEYS = Object.freeze(['recentRaces','allPastRuns']);
const ARCHIVE_KEYS = Object.freeze(['careerArchive','careerTransport','_careerHistoryAudit','careerStartEvidence']);

export function needsHistoryPreservation(detail) {
  return !!detail && Array.isArray(detail.horses) && detail.horses.some(h =>
    h && Number(h.horseNumber ?? h.horse_no) > 0);
}

function runDate(run) {
  const value = String(run?.date ?? run?.raceDate ?? run?.日付 ?? '').trim();
  if (/^\\d{8}$/.test(value)) return value.slice(0,4)+'-'+value.slice(4,6)+'-'+value.slice(6,8);
  const m = value.match(/^(\\d{4})[./-](\\d{1,2})[./-](\\d{1,2})/);
  return m ? m[1]+'-'+m[2].padStart(2,'0')+'-'+m[3].padStart(2,'0') : '';
}

function runKey(run) {
  if (!run || typeof run !== 'object') return 'raw:'+JSON.stringify(run);
  const date = runDate(run);
  if (date) return 'date:'+date;
  const raceId = String(run.raceId ?? run.race_id ?? run.netkeibaRaceId ?? '').trim();
  if (raceId) return 'race:'+raceId;
  return 'raw:'+JSON.stringify(run,Object.keys(run).sort());
}

function mergeRuns(previous, incoming) {
  const rows = new Map();
  for (const run of [...(Array.isArray(previous)?previous:[]),...(Array.isArray(incoming)?incoming:[])]) {
    const key = runKey(run);
    if (!rows.has(key)) {
      rows.set(key, run && typeof run === 'object' ? {...run} : run);
      continue;
    }
    const saved = rows.get(key);
    if (!saved || typeof saved !== 'object' || !run || typeof run !== 'object') continue;
    // Keep the already stored observation on conflicts; only add incoming fields
    // where the stored record did not contain an observation.
    for (const [field,value] of Object.entries(run)) {
      if (saved[field] === undefined || saved[field] === null || saved[field] === '' ||
          (Array.isArray(saved[field]) && saved[field].length === 0)) {
        if (value !== undefined && value !== null && value !== '') saved[field] = value;
      }
    }
  }
  const result = [...rows.values()];
  return result.sort((a,b) => {
    const da=runDate(a), db=runDate(b);
    return da && db ? db.localeCompare(da) : 0;
  });
}

function archiveRunCount(archive) {
  const value=Number(archive?.storedRunCount ?? archive?.olderRunCount ?? NaN);
  return Number.isInteger(value) && value >= 0 ? value : null;
}

export function mergeStoredHorseHistory(incoming, previousHorses) {
  if (!incoming || !Array.isArray(incoming.horses) || !Array.isArray(previousHorses)) return incoming;
  const saved = new Map(previousHorses.filter(Boolean).map(h =>
    [Number(h.horseNumber ?? h.horse_no), h]).filter(([no]) => Number.isInteger(no) && no > 0));
  return {...incoming, horses:incoming.horses.map(h => {
    if (!h || typeof h !== 'object') return h;
    const before=saved.get(Number(h.horseNumber ?? h.horse_no));
    if (!before) return h;
    const result={...h};
    for(const key of RICH_KEYS) {
      const previousRuns=Array.isArray(before[key])?before[key]:[];
      const incomingRuns=Array.isArray(h[key])?h[key]:[];
      if (previousRuns.length || incomingRuns.length) {
        const merged=mergeRuns(previousRuns,incomingRuns);
        result[key]=key==='recentRaces'?merged.slice(0,5):merged;
      }
    }
    for (const key of ARCHIVE_KEYS) {
      if (before[key] !== undefined && h[key] === undefined) result[key]=before[key];
    }
    const oldArchive=before.careerArchive, newArchive=h.careerArchive;
    if (oldArchive && newArchive && oldArchive.sha256 !== newArchive.sha256) {
      const oldCount=archiveRunCount(oldArchive), newCount=archiveRunCount(newArchive);
      // An equal-sized or smaller changed sidecar cannot prove that it retained
      // the prior observations. Keep the stored copy; the merged run arrays above
      // still retain complementary incoming facts.
      if (newCount === null || oldCount === null || newCount <= oldCount) {
        result.careerArchive=oldArchive;
        for (const key of ['careerTransport','_careerHistoryAudit']) {
          if (before[key] !== undefined) result[key]=before[key];
        }
      }
    }
    return result;
  })};
}
