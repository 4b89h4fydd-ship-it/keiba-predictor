#!/usr/bin/env node
'use strict';
// A retired NAR 60/40 engine must never seal a fresh prediction.
const assert=require('node:assert/strict'),cp=require('node:child_process');
const r=cp.spawnSync(process.execPath,['scripts/arvexq_capture_prerace_bet.js'],
 {input:JSON.stringify({id:'retired-capture-check',horses:[{horseNumber:1},{horseNumber:2}]}),encoding:'utf8',timeout:15000});
assert.notEqual(r.status,0,'Retired engine unexpectedly minted a betting receipt');
assert.match(String(r.stderr),/RETIRED_BET_ENGINE_DISABLED/);
assert.equal(String(r.stdout).trim(),'');
console.log('RETIRED_NAR_BET_ENGINE_REJECTED_PASS');
