// Only the existing saved D1 race-detail path can supply this v3 factual DTO.
// No alternate collectors, DB writes, background fetches, models or bet code.
const RACE = ['id','date','circuit','track','raceNumber','title','surface',
  'distance','condition','weather','startTime','fieldSize','racePrize1'];
const HORSE = ['horseNumber','frameNumber','name','sex','age','jockey','trainer',
  'affiliation','carriedWeight','bodyWeight','bodyWeightChange','status',
  'scratched','withdrawn'];
const PAST = ['date','track','surface','distance','condition','weather','finish',
  'rank','timeSeconds','time','margin','last3f','cornerPositions','passing',
  'jockey','carriedWeight','fieldSize','className','grade','raceId'];
const ODDS = ['winOdds','placeOdds','popularity'];

function pick(row,fields) {
  const result = {};
  for (const field of fields) if (Object.hasOwn(row,field))
    result[field] = structuredClone(row[field]);
  return result;
}
function circuitOf(value) {
  const name = String(value || '').toLowerCase().trim();
  if (['jra','中央','central'].includes(name)) return 'jra';
  if (['nar','地方','local'].includes(name)) return 'nar';
  return null;
}
function dateKey(raw) {
  if (typeof raw !== 'string') return null;
  let day = raw.trim().replaceAll('/', '-').replaceAll('.', '-');
  if (day.length > 10 && !/^\d{8}$/.test(day)) day = day.slice(0, 10);
  if (/^\d{8}$/.test(day)) day = day.slice(0,4)+'-'+day.slice(4,6)+'-'+day.slice(6);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const iso = new Date(day+'T00:00:00.000Z');
  return Number.isNaN(iso.valueOf()) || iso.toISOString().slice(0,10)!==day ? null : day;
}
function observed(value) {
  return value !== undefined && value !== null &&
    !(typeof value==='string' && ['', '-', '--','不明'].includes(value.trim()));
}
function pastRows(horse,targetDate) {
  const byDate = new Map();
  for (const collection of ['allPastRuns','recentRaces']) {
    if (!Array.isArray(horse[collection])) continue;
    for (const row of horse[collection]) {
      if (!row || typeof row !== 'object' || Array.isArray(row)) continue;
      const date = dateKey(row.date ?? row.raceDate ?? row['日付']);
      if (!date || date >= targetDate) continue;
      const sample = pick(row,PAST);
      sample.date = date;
      // At most one prior start per calendar date, matching Python's saved
      // career merge. Only copied, observed fields may fill a duplicate.
      const existing = byDate.get(date);
      if (existing) {
        for (const key of PAST)
          if ((existing[key]===undefined || existing[key]===null ||
               existing[key]==='' || Array.isArray(existing[key]) && !existing[key].length) &&
              observed(sample[key])) existing[key]=structuredClone(sample[key]);
      } else byDate.set(date,sample);
    }
  }
  return [...byDate.values()].sort((a,b)=>b.date.localeCompare(a.date));
}
function classify(raw) {
  if (!observed(raw)) return {status:'missing',value:null};
  if (typeof raw === 'boolean' ||
      (typeof raw === 'number' && !Number.isFinite(raw))) return {status:'invalid',value:null};
  return {status:'observed',value:structuredClone(raw)};
}
function priceFact(raw,field) {
  const base=classify(raw);
  if (base.status!=='observed') return base;
  const invalid={status:'invalid',value:null};
  if (field==='placeOdds' && typeof raw==='string' && raw.includes('-')) {
    const split=raw.trim().split('-').map(x=>Number(x.trim()));
    return split.length===2 && split.every(x=>Number.isFinite(x)&&x>0) && split[0]<=split[1]
      ? base : invalid;
  }
  const numeric=Number(raw);
  if (!Number.isFinite(numeric)||numeric<=0) return invalid;
  if (field==='popularity' &&
      !(typeof raw==='number' && Number.isInteger(raw) ||
        typeof raw==='string' && /^[1-9][0-9]*$/.test(raw.trim()))) return invalid;
  return base;
}
function projection(original,requestedId) {
  if (!original || typeof original!=='object' || Array.isArray(original))
    throw Error('invalid saved race');
  const circuit = circuitOf(original.circuit);
  const raceDate = dateKey(original.date);
  if (!circuit || !requestedId.startsWith(circuit+'-') ||
      original.id!==requestedId || !raceDate ||
      !requestedId.startsWith(circuit+'-'+raceDate+'-'))
    throw Error('stored race identity/circuit/date conflict');
  if (!Array.isArray(original.horses) || original.horses.length===0)
    throw Error('no saved runner rows');
  const seen = new Set();
  let historyCount=0, runnersWithPrior=0, missingCells=0;
  const rows=[], win=[],place=[],popularity=[],quoteTime=[];
  for (const horse of original.horses) {
    if (!horse || typeof horse!=='object' || Array.isArray(horse))
      throw Error('invalid runner row');
    const number=horse.horseNumber;
    if (!Number.isInteger(number) || number<=0 || seen.has(number))
      throw Error('ambiguous saved runner identity');
    seen.add(number);
    const runs=pastRows(horse,raceDate);
    historyCount+=runs.length;
    runnersWithPrior+=Number(runs.length>0);
    for (const key of ['name','jockey','trainer','carriedWeight'])
      if (!observed(horse[key])) missingCells++;
    const quote=pick(horse,ODDS);
    rows.push({horseNumber:number,horse:pick(horse,HORSE),odds:quote,
      recentRaces:runs.slice(0,5),observedPriorRunCount:runs.length,
      careerCompleteness:'unverified'});
    for (const [out,key] of [[win,'winOdds'],[place,'placeOdds'],[popularity,'popularity']]) {
      const q=priceFact(horse[key],key);
      out.push({horseNumber:number,state:q.status,value:q.value});
    }
    const w=win.at(-1).state, p=place.at(-1).state, rank=popularity.at(-1).state;
    const basicFields={};
    for (const key of ['name','jockey','trainer','carriedWeight']) {
      const raw=horse[key];
      basicFields[key]=!observed(raw)?'missing':
        typeof raw==='boolean'||typeof raw==='number'&&!Number.isFinite(raw)
          ?'invalid':'observed';
    }
    rows.at(-1).readiness={
      basicFields,
      schema:'arvexq-v3-runner-readiness-1',horseNumber:number,
      history:runs.length?'partial-unverified':'missing',
      observedPriorRunCount:runs.length,allCareerRunsVerified:false,
      odds:w==='observed'&&p==='observed'?'observed-unverified':'incomplete',
      win:w,place:p,popularity:rank,marketFreshnessVerified:false,
      canClaimFullyRetrieved:false
    };
    // Timestamp is accepted only from the explicit horse quote field, never
    // the race start time, worker clock or live odds_current overlay.
    const quoteAt=horse.oddsUpdatedAt ?? horse.oddsTimestamp;
    const t=classify(quoteAt);
    quoteTime.push({horseNumber:number,status:t.status,value:t.value,
      sourceKey:observed(horse.oddsUpdatedAt)?'oddsUpdatedAt':
        observed(horse.oddsTimestamp)?'oddsTimestamp':null});
  }
  rows.sort((a,b)=>a.horseNumber-b.horseNumber);
  const count=(values,state)=>values.filter(x=>x.state===state).length;
  const cellSummary=(v)=>({
    observed:count(v,'observed'),missing:count(v,'missing'),invalid:count(v,'invalid')
  });
  const markets={win,place,popularity};
  const oddsFields={
    schema:'arvexq-v3-observed-odds-fields-1',circuit,
    runnerRows:rows.length,win,place,popularity,
    counts:Object.fromEntries(Object.entries(markets).map(([key,v])=>[key,cellSummary(v)])),
    marketDateAndPreOffVerified:false,liveMarketFreshnessVerified:false,
    predictionsCalculated:false
  };
  const quoteFields={
    schema:'arvexq-v3-observed-quote-fields-1',circuit,
    fields:{
      quote_time:{rows:quoteTime,observed:quoteTime.filter(x=>x.status==='observed').length,
        missing:quoteTime.filter(x=>x.status==='missing').length},
    },
    quoteFreshness:'unknown',quoteTimeIndependentVerified:false,
    notModelProbabilities:true
  };
  return {
    schema:'arvexq-v3-factual-screen-1',
    race:pick(original,RACE),
    rows,
    results:null,
    resultFields:null,
    coverage:{
      schema:'arvexq-v3-worker-d1-coverage-1',source:'existing-D1-saved-race-detail',
      circuit,runnerRows:rows.length,observedPriorRuns:historyCount,
      runnersWithPriorRuns:runnersWithPrior,missingBasicRunnerCells:missingCells,
      careerCompleteness:'unverified',officialRosterVerified:false,
      liveD1FreshnessVerified:false,resultState:'withheld-until-postrace',
      completeness:{
        roster:{
          state:Number.isInteger(original.fieldSize)&&original.fieldSize>0&&
            original.fieldSize!==rows.length?'count-mismatch':'unverified',
          expected: Number.isInteger(original.fieldSize)&&original.fieldSize>0?original.fieldSize:null,
          observed:rows.length,officialVerified:false
        },
        history:{
          state:historyCount===0?'missing':'partial-unverified',
          observedPriorRuns:historyCount,runnersWithPriorRuns:runnersWithPrior,
          totalRunners:rows.length,allCareerRunsVerified:false
        },
        odds:{
          state:count(win,'observed')===rows.length&&
            count(place,'observed')===rows.length?'observed-unverified':'incomplete',
          winObserved:count(win,'observed'),placeObserved:count(place,'observed'),
          winInvalid:count(win,'invalid'),placeInvalid:count(place,'invalid'),
          expectedRunners:rows.length,marketFreshnessVerified:false
        }
      }
    },
    oddsFields,quoteFields,
    displayReadiness:{
      schema:'arvexq-v3-display-readiness-1',
      complete:false,
      roster: Number.isInteger(original.fieldSize)&&original.fieldSize>0&&
        original.fieldSize!==rows.length?'count-mismatch':'unverified',
      history:historyCount===0?'missing':'partial-unverified',
      odds:count(win,'observed')===rows.length&&count(place,'observed')===rows.length
        ?'observed-unverified':'incomplete',
      message:'保存済み観測データのみ。全項目の取得完了は未確認',
      canClaimFullyRetrieved:false,
      predictionsEnabled:false
    },
    predictionStatus:'not-implemented',marks:null,tickets:null
  };
}

function json(value,status=200) {
  return Response.json(value,{status,headers:{
    'cache-control':'no-store',
    'access-control-allow-origin':'*',
    'access-control-allow-headers':'content-type,authorization,cache-control,pragma,x-sync-token'
  }});
}
export function factualProjection(detail,raceId) {return projection(detail,raceId)}
export async function readV3Facts(request,getExistingResponse) {
  if (request.method!=='GET') return json({ok:false,error:'method not allowed'},405);
  const url=new URL(request.url);
  let id;
  try {id=decodeURIComponent(url.pathname.slice('/api/race/'.length))}
  catch{return json({ok:false,error:'invalid race ID'},400)}
  if (!/^(jra|nar)-\d{4}-\d{2}-\d{2}-.+-\d{2}$/.test(id))
    return json({ok:false,error:'invalid canonical race ID'},422);
  try {
    const received=await getExistingResponse(id);
    if (!received.ok) return json({ok:false,error:'saved race unavailable',
      raceId:id},received.status===404?404:received.status===429?429:503);
    const body=await received.json();
    const detail=body?.detail;
    return json({ok:true,race_id:id,detail:projection(detail,id)});
  } catch {
    return json({ok:false,error:'invalid saved factual race'},422);
  }
}
