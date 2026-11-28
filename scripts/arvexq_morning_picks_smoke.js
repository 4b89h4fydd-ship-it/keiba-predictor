#!/usr/bin/env node
// Morning selection immutability after the 2026-11-28 app rebuild.
// The terminal no longer computes or reshuffles morning selections:
// the rich-UI readers (morningPickOf / selectedRaceCandidates / ...)
// were removed with the entry-table-only app, and the freeze producer
// no longer stamps anything without its retired engine. What must
// stay true:
//   - the evidence module that verifies frozen ticket receipts still
//     loads and exposes capture/verify;
//   - the terminal has no machinery that could recompute, reshuffle
//     or resurrect a morning selection (no predict, no candidate
//     builders, no localStorage state), so a late odds update, a
//     changed AI score or a result publication can never rewrite the
//     morning's selected/special list;
//   - the producer keeps its first-write-wins archive contract
//     (restore, corrupt-archive refusal, honest no-freeze).
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const win={};
new Function('window',fs.readFileSync('arvexq/ui/static/morning/ticket_lane_classifier.js','utf8'))(win);
new Function('window',fs.readFileSync('arvexq/ui/static/morning/frozen_ticket_evidence.js','utf8'))(win);
assert(win.ARVEXQMorningEvidence,'evidence module must load');
assert.equal(win.ARVEXQMorningEvidence.VERSION,'arvexq-morning-ticket-evidence-v1');
assert.equal(typeof win.ARVEXQMorningEvidence.capture,'function');
assert.equal(typeof win.ARVEXQMorningEvidence.verify,'function');
// The terminal reads only the static packs.
assert(src.includes('api-static/day/')&&src.includes('api-static/race/'),
  'terminal must read the static packs');
// None of the retired morning machinery may come back.
for(const gone of ['function predict(','selectedRaceCandidates',
  'specialForecastRaceCandidates','morningPickOf','legacyMorningPickOf',
  'localStorage','installNavigation();installEdgeBack();'])
  assert(!src.includes(gone),'retired morning machinery must stay removed: '+gone);
// The producer's archive contract stays in force.
const producer=fs.readFileSync('scripts/arvexq_morning_picks.js','utf8');
assert(producer.includes('invalid immutable morning archive'),
  'corrupt archives must stay fatal');
assert(producer.includes('MORNING_PICKS_REUSED_ALREADY_FIXED'),
  'first-write-wins restore must stay');
assert(producer.includes('ENGINE_UNAVAILABLE_NO_FREEZE'),
  'producer must stay honest about the retired engine');
console.log('MORNING_PICK_IMMUTABLE_AND_NO_LATE_ADDITION_PASS');
console.log('MORNING_TERMINAL_CANNOT_RECOMPUTE_PASS');
