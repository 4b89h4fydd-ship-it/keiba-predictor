#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const lane=fs.readFileSync('arvexq/ui/static/morning/ticket_lane_classifier.js','utf8');
const cut=fs.readFileSync('arvexq/ui/static/morning/selection_cut.js','utf8');
const ctx={window:{},console,Math,Object,Number,String,Set,Array,RegExp};vm.createContext(ctx);
vm.runInContext(lane,ctx);
vm.runInContext(cut,ctx);
const lanes=ctx.window.ARVEXQMorningTicketLanes;
const selection=ctx.window.ARVEXQMorningSelection;
const rows=Array.from({length:7},(_,i)=>({horse:{horseNumber:i+1},predMark:i===0?'◎':'',threeFactorCoverage:3}));
const q=lanes.classify({circuit:'地方',raceNumber:1},{rows},{score:40});
assert.equal(q.selected,true,'ability score of 40 must NOT exclude empirically qualified bets');
const plan={decision:'購入候補',betInputGate:{ready:true},items:[{level:'本線',kind:'ワイド',combos:[[1,2]]}]};
assert(!lanes.requireMorningTickets(q,plan).selected,'no observed sample must not claim high hit probability');
ctx.window.ARVEXQTicketHitCalibration={version:'arvexq-empirical-ticket-hit-v1',modelVersion:'arvexq-true-run-pure-sectional-v2',
 asOfDate:'2026-10-13',buckets:{'ワイド|1':{kind:'ワイド',points:1,sample:32,wins:28,hitRate:.875,wilsonLower95:.72,qualified:true}}};
const good=lanes.requireMorningTickets(q,plan);
assert.equal(good.selected,true);
assert.equal(good.score,88);
assert.equal(good.hitRate,.875);
assert.equal(JSON.parse(JSON.stringify(selection.allStrictQualifiers([{race:{id:'r',raceNumber:1},selection:good}],{
 n:Number,chronological:()=>0}))).length,1);
const wrong={...plan,items:[{level:'本線',kind:'馬連',combos:[[1,2]]}]};
assert.equal(lanes.requireMorningTickets(q,wrong).selected,false,'do not use wide hit rate for exacta pair');
ctx.window.ARVEXQTicketHitCalibration.buckets['ワイド|1'].sample=2;
assert.equal(lanes.requireMorningTickets(q,plan).selected,false);
console.log('ARVEXQ_EMPIRICAL_TICKET_SELECTION_OK');
