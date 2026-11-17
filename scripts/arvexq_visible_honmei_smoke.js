#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const src=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const start=src.indexOf('function markRoleLabel(');
const end=src.indexOf('\nfunction honmeiA11yText(',start);
assert(start>0&&end>start);
const label=new Function(src.slice(start,end)+';return markRoleLabel;')();
assert.equal(label({predMark:'◎',preOffAxisCandidate:false,markFrozen:false}),'◎ 本命');
assert.equal(label({predMark:'◎',preOffAxisCandidate:true,markFrozen:false}),'◎ 本命');
assert.equal(label({predMark:'▲',preOffAxisCandidate:true,markFrozen:false}),'');
assert.equal(label({predMark:'◎',markFrozen:true,honmeiRole:'axis'}),'保存印：◎（旧軸）');
assert.equal(label({predMark:'◎',markFrozen:true,honmeiRole:'win'}),'保存印：◎（旧単勝）');
assert.equal(label({predMark:'◎',markFrozen:true,honmeiRole:''}),'保存印：◎');
assert.equal(label({predMark:'',preOffAxisCandidate:true,markFrozen:false}),'');
assert.equal(label(null),'');
const card=src.slice(src.indexOf('function racecardEntryRow('),src.indexOf('function morningSavedMarkRows('));
// v348 (user direction 2026-11-17): role badges no longer render on
// the racecard at all — ARVEXQ marks live on the 予想 tab table, and
// the racecard check column carries only the user's own-mark toggle.
// markRoleLabel itself is unchanged (unit assertions above).
assert(!card.includes('rc-honmei-role'),'role badge must not render on the racecard');
assert(!card.includes('rc-mark-box'),'AI mark box must not render on the racecard');
assert(card.includes('data-user-mark'),'own-mark check stays on the racecard');
const panel=src.slice(src.indexOf('function aiMarksPanel('),src.indexOf('function betPanel('));
assert(panel.includes('ARVEXQMarkFrame.render(r)'),'dedicated empty frame');
require('./test_support/production_ui.cjs').assertNoForecast({horses:[{horseNumber:1,mark:'◎',honmeiRole:'win-axis'}]});
assert(!src.includes('axisScore:.45*stable'),'independent fixed-weight axis must be removed');
console.log('VISIBLE_HONMEI_ROLES_OK');
