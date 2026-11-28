#!/usr/bin/env node
'use strict';
// Result/payout display integrity under the 2026-11-28 shell migration
// (commit 827df37, user-confirmed entry-table-only app).
//
// The retired shell polled results inside app.js (scheduleResultRefresh,
// mergePublishedResult, hasResultData, resultPanel). Its contract was:
// polling runs even without a diagnosis, and a sparse or stale response
// can never erase or downgrade an already published result. The current
// shell renders no result panel and runs no result polling at all —
// results live in the static packs and the server-side ingest — so the
// client-side downgrade/erase vector itself is gone. This smoke pins
// that absence. The merge behaviour itself (a stale 速報 cannot
// downgrade a 確定, payout-only updates apply) is covered server-side by
// the Python regression tests (test_result_stalled_regressions,
// test_result_summary_real_finishers, test_result_partial_publish) and
// by the pipeline invariants step of this workflow.
const assert=require('node:assert/strict'),fs=require('node:fs');
const app=fs.readFileSync('arvexq/ui/static/app.js','utf8');
for(const retired of ['scheduleResultRefresh','function mergePublishedResult(',
  'function hasResultData(','resultPanel(','var resultPollBusy','function refreshPayoutsOnly(',
  'fetchEdgeRace(','mergeRaceReflection('])
  assert(!app.includes(retired),'retired in-app result handling must stay removed: '+retired);
assert(!app.includes('localStorage'),'shell keeps no client result state to overwrite');
// The shell's only data sources remain the static day/race packs.
assert(app.includes('function staticDayUrl(')&&app.includes('function staticRaceUrl('),
  'race display is pack-driven only');
console.log('RESULT_CONTINUOUS_SMOKE_OK app-renders-no-results stale-downgrade-vector-absent');
