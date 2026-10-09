#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const root=fs.readFileSync('arvexq/ui/static/app.js','utf8');
const i=root.indexOf('function latestUserApprovedModelMarkRevision(r){'),
      j=root.indexOf('function immutableArchivedPrediction(r){',i);
assert(i>=0&&j>i,'model mark reader has a distinct explicit approval branch');
const source=root.slice(i,j);
const n=(v,d=0)=>v==null||v===''||!Number.isFinite(Number(v))?d:Number(v);
const validMorningMarkSnapshot=r=>r.morningMarkSnapshot;
const api=new Function('n','validMorningMarkSnapshot','serverFrozenPrediction',
 source+'\nreturn {latestUserApprovedModelMarkRevision,latestAuthorizedMarkRevision,authorizedPreOffMarks};')(
   n,validMorningMarkSnapshot,()=>null);
const original=[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'},{horseNumber:3,mark:'▲'}];
const r={id:'nar-2026-10-09-園田-12',date:'2026-10-09',startTime:'23:40',
 morningMarkSnapshot:{version:'arvexq-morning-marks-v1',
 raceId:'nar-2026-10-09-園田-12',raceDate:'2026-10-09',
 fixedAt:'2026-10-09T09:08:00+09:00',horses:original}};
function model(at='22:12:00'){
 return {version:'arvexq-user-model-mark-revision-v1',
 approvalId:'user-approved-past-five-from-2026-10-09-20-10-jst',
 modelVersion:'arvexq-axis-reliability-v2-past-context',
 raceId:r.id,raceDate:r.date,revisedAt:'2026-10-09T'+at+'+09:00',
 reason:'explicit user model update',horses:[
   {horseNumber:1,mark:'○'},{horseNumber:2,mark:'◎'},{horseNumber:3,mark:'▲'}]};
}
assert.equal(api.authorizedPreOffMarks(r).horses[0].mark,'◎','original used without revision');
r.modelMarkRevisions=[model()];
assert.equal(api.authorizedPreOffMarks(r).horses[1].mark,'◎','valid approved pre-off revision used');
assert.equal(r.morningMarkSnapshot.horses[0].mark,'◎','original immutable');
r.modelMarkRevisions=[{...model(),revisedAt:'2026-10-09T23:41:00+09:00'}];
assert.equal(api.authorizedPreOffMarks(r).horses[0].mark,'◎','post-off model update rejected');
r.modelMarkRevisions=[{...model(),approvalId:'unapproved'}];
assert.equal(api.authorizedPreOffMarks(r).horses[0].mark,'◎','unapproved model revision rejected');
r.modelMarkRevisions=[model()];
r.officialMarkRevisions=[{version:'arvexq-official-mark-revision-v1',
 raceId:r.id,raceDate:r.date,revisedAt:'2026-10-09T22:25:00+09:00',
 officialCourseCondition:{publishedAt:'2026-10-09T22:20:00+09:00',sourceUrl:'https://www.keiba.go.jp/'},
 horses:original}];
assert.equal(api.authorizedPreOffMarks(r).version,'arvexq-official-mark-revision-v1',
 'later official revision wins');
r.modelMarkRevisions=[model('22:30:00')];
assert.equal(api.authorizedPreOffMarks(r).version,'arvexq-user-model-mark-revision-v1',
 'later approved model revision wins');
console.log('MODEL_MARK_REVISION_OK original_preserved approval_window_post_off_rejection_source_precedence');
