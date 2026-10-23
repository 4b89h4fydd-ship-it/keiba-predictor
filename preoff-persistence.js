import {authorizedStage64} from './public-race.js';

const KEYS = ['predictionStatus','predictionModelVersion','prediction','predictionMarks','recommendedBets'];

export function stage64Archive(detail) {
  if (!detail || !authorizedStage64(detail) ||
      !Array.isArray(detail.recommendedBets)) return null;
  const archive = {raceId:detail.id,raceDate:detail.date};
  for (const key of KEYS) archive[key] = structuredClone(detail[key]);
  return archive;
}

export function verifiedStage64Archive(archive, race) {
  if (!archive || !race || archive.raceId !== race.id ||
      archive.raceDate !== race.date) return null;
  const candidate = {...archive, id:race.id, date:race.date, horses:race.horses};
  return authorizedStage64(candidate) && Array.isArray(archive.recommendedBets) ? archive : null;
}

export function retainStage64Archive(incoming, older, newOriginal) {
  if (!incoming || typeof incoming !== 'object') return incoming;
  const chosen = verifiedStage64Archive(newOriginal, incoming) ||
    verifiedStage64Archive(incoming.preoffStage64Archive, incoming) ||
    verifiedStage64Archive(older?.preoffStage64Archive, incoming);
  return chosen ? {...incoming, preoffStage64Archive:structuredClone(chosen)} : incoming;
}

export function applyStage64Archive(restored, storedEnvelope) {
  const archive = verifiedStage64Archive(storedEnvelope?.preoffStage64Archive, restored);
  if (!archive || authorizedStage64(restored)) return restored;
  const result = {...restored};
  for (const key of KEYS) result[key] = structuredClone(archive[key]);
  return result;
}
