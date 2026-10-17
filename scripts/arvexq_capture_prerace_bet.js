#!/usr/bin/env node
'use strict';
// The old 60/40 browser engine is retired. Refuse to mint new bet receipts.
// Previously sealed receipts are retained in their original store.
console.error('RETIRED_BET_ENGINE_DISABLED: learned forecasts only; no fabricated preoff bets');
process.exitCode=2;
