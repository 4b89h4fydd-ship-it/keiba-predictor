#!/usr/bin/env node
'use strict';
/** Read-only production D1 AND production PWA real forecast smoke.
 * Real runner names, predictions, or user data are never printed to CI logs.
 */
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert/strict');
const target='jra-2026-10-25-京都-11', base='https://kraiz-api.4b89h4fydd.workers.dev';
async function json(url){
  const res=await fetch(url,{headers:{'cache-control':'no-cache'},signal:AbortSignal.timeout(25000)});
  if(!res.ok)throw Error('API_HTTP_'+res.status);
  return res.json();
}
async function main(){
  const body=await json(base+'/api/race/'+encodeURIComponent(target)+'?view=display&smoke='+Date.now());
  const detail=body&&body.detail;
  const candidate=detail&&detail.kikkaCandidate;
  const summary=body&&body.summary;
  console.log('KIKKA_LIVE_READBACK',JSON.stringify({
    httpOk:body&&body.ok,detail:!!detail,candidate:!!candidate,
    namedRunners:(detail?.horses||[]).filter(h=>h?.name).length,
    storedMarkCount:candidate?.marks?.length||0,
    savedPredictionStatus:detail?.predictionStatus||null,
    resultPresent:!!detail?.result,
    startTime:detail?.scheduledStartTime||detail?.startTime,
    frontendFields:{circuit:detail?.circuit,track:detail?.track,raceNumber:detail?.raceNumber,
      distance:detail?.distance,surface:detail?.surface,date:detail?.date},
    sourceFields:{date:summary?.race_date||summary?.date||null}
  }));
  if(!detail||!candidate)throw Error('CANDIDATE_MISSING_FROM_ACTUAL_LIVE_D1');
  // Diagnose the real live JSON through EXACT production PWA prediction adapter
  // and the mark visibility adapter. No fixtures.
  const context={ARVEXQProductionTickets:{build:()=>{throw Error('unexpected betting model fallback')},
          validatedReceipt:()=>{throw Error('unexpected historical receipt fallback')}}};
  vm.runInNewContext(fs.readFileSync('arvexq/ui/static/forecast/prediction.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('arvexq/ui/static/forecast/marks.js','utf8'),context);
  const local=context.ARVEXQProductionPrediction.build(detail);
  const displayed=local.rows.filter(row=>context.ARVEXQProductionMarks.visible(row));
  console.log('KIKKA_LIVE_PREDICTION_ADAPTER',JSON.stringify({
    markCount:displayed.length,bonmeiCount:displayed.filter(x=>x.predMark==='◎').length,
    source:context.ARVEXQProductionPrediction.current().source,
    confidenceUncalibrated:context.ARVEXQProductionPrediction.current().uncalibrated,
    recommendedPlan:local.plan!==null
  }));
  if(displayed.length===0){
    const names=['エムズビギン','コンジェスタス','アウダーシア','ショウナンガルフ',
      'ジャスティンシカゴ','バステール','ラージアンサンブル','ロブチェン','ゴーイントゥスカイ',
      'ダノンヒストリー','アスクエジンバラ','サノノグレーター','キンググローリー',
      'マジョレルブルー','シートゥサミット','ショウナンハヤナミ',
      'チャリングクロス','ナリタエスペランサ'];
    const rows=detail.horses||[],marks=candidate.marks||[];
    const mismatch=rows.filter(h=>names[Number(h.horseNumber)-1]!==String(h.name));
    const markSymbols=[...new Set(marks.map(x=>x.mark))];
    console.log('KIKKA_LIVE_REJECTION_REASONS',JSON.stringify({
      version:candidate.version,raceMatch:candidate.raceId===detail.id,
      dateMatch:candidate.raceDate===detail.date,
      modelVersion:candidate.modelVersion,
      provisional:candidate.provisional,productionEligible:candidate.productionEligible,
      bettingRecommended:candidate.bettingRecommended,probabilityCalibration:candidate.probabilityCalibration,
      trainedThrough:candidate.trainedThrough,trainedEarlier:candidate.trainedThrough<detail.date,
      capturedAt:candidate.capturedAt,capturedEpoch:Date.parse(candidate.capturedAt),
      sourceHashLen:String(candidate.sourceHash||'').length,modelHashLen:String(candidate.modelHash||'').length,
      horseNameMismatchCount:mismatch.length,horseNumberInvalid:rows.filter(h=>!Number.isInteger(Number(h.horseNumber))||Number(h.horseNumber)<1||Number(h.horseNumber)>18).length,
      markCount:marks.length,bonmeiCount:marks.filter(x=>x.mark==='◎').length,
      markSymbols:markSymbols,firstMarkType:typeof marks[0],firstMarkKeys:Object.keys(marks[0]||{}),
      firstMarkIsArray:Array.isArray(marks[0]), firstMarkNullCount:marks.filter(x=>x===null).length,
    }));
    throw Error('LIVE_D1_18_HORSES_STORED_BUT_PWA_BLANK_MARKS');
  }
  if(displayed.filter(x=>x.predMark==='◎').length!==1)throw Error('INVALID_REAL_LIVE_HONMEI');
  // Ensure the public JS has the new adapter before claiming deployed to iPhone.
  const js=await fetch('https://kraizweb1.4b89h4fydd.workers.dev/app-v330.js?smoke='+Date.now(),{
    headers:{'cache-control':'no-cache'},signal:AbortSignal.timeout(20000)});
  if(!js.ok)throw Error('PWA_BUNDLE_HTTP_'+js.status);
  const html=await js.text();
  const present=html.includes('kikka-2026-learned-preoff-candidate')&&
                html.includes('function kikkaCandidateMarks');
  console.log('KIKKA_PWA_DEPLOYED_BUNDLE',JSON.stringify({http:js.status,hasLiveNewPrediction:present,length:html.length}));
  if(!present)throw Error('LIVE_PWA_BUNDLE_MISSING_NEW_FORECAST');
}
main().catch(e=>{console.error('KIKKA_LIVE_VISIBLE_MARKS_FAILED',String(e.message));process.exitCode=1});
