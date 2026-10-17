// Factual-history preservation at the D1 sync boundary.
// Incoming compact observations must not erase longer, previously verified run arrays.
const RICH_KEYS = Object.freeze(['recentRaces','allPastRuns']);
export function needsHistoryPreservation(detail) {
  return !!detail && Array.isArray(detail.horses) && detail.horses.some(h =>
    h && Number(h.horseNumber ?? h.horse_no) > 0);
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
      const incomingRuns=Array.isArray(h[key])?h[key]:[];
      const previousRuns=Array.isArray(before[key])?before[key]:[];
      if(previousRuns.length>incomingRuns.length) result[key]=previousRuns.map(run =>
        run && typeof run === 'object'?{...run}:run);
    }
    return result;
  })};
}
