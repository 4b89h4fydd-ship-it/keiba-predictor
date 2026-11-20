/* Bets tab primary display (user rule 2026-11-21, third revision):
 * a strict selection across ALL ticket kinds from the payload's
 * ticketPlan, at most 5 points —
 *   1. 単勝: winExpectedValues with EV >= 1.25 AND win prob >= 5%,
 *      the maximum-EV horse (1 point).
 *   2. 複勝: placeExpectedValues with EV lower bound >= 1.0, the
 *      highest top-3 probability, excluding the 単勝 pick (1 point).
 *   3. Combinations: ticketPlan.items in joint-probability order,
 *      only probability >= 5%, filling up to 5 points total.
 * When a ticketPlan exists this selection is the ONLY main display
 * (nothing qualifying renders as 見送り); neither the marks
 * formation, the ticketPlan items alone, the integrated
 * recommendation (37-44 points) nor the mechanical recommendedBets
 * set is shown alongside. Payloads without a ticketPlan keep the
 * previous fallback chain (integrated recommendation, else the
 * mechanical set / legacy plan), and the EV sections are unchanged.
 * Display grouping (2026-11-21, display only — selection unchanged):
 * combination picks sharing an axis render as one formation line
 * (ワイド/馬連 shared horse, 馬単 shared 1st horse, 3連複 shared
 * pair, 3連単 shared 1st-2nd pair); group lines carry only the
 * point count, ungrouped picks keep their probability, and the
 * total still counts individual picks.
 * Run from the repository root: node scripts/arvexq_strict_primary_bets_smoke.js
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const W={};const ctx={window:W};vm.createContext(ctx);
function load(p){vm.runInContext(fs.readFileSync(p,'utf8'),ctx,{filename:p});}
load('arvexq/ui/static/forecast/integrated_osusume.js');
load('arvexq/ui/static/forecast/ticket_frame.js');
const frame=W.ARVEXQTicketFrame;
assert.ok(frame&&W.ARVEXQIntegratedOsusume,'frame + osusume loaded');

function diagnosis(n){
  const out=[];
  for(let i=1;i<=n;i++)out.push({horseNumber:i,winProbability:(n-i+1)/100,top3Probability:(n-i+1)/20,grade:'A'});
  return out;
}
const SYMS=['◎','○','▲','△','☆'];
const roster=Array.from({length:10},(_,i)=>({horseNumber:i+1,name:'馬'+(i+1)}));
function ufMarks(nos){
  return nos.map((no,i)=>({horseNumber:no,markSymbol:SYMS[i],
    winProbability:(11-no)/100,top3Probability:(11-no)/20}));
}
function predMarks(nos){
  return nos.map((no,i)=>({horseNumber:no,mark:SYMS[i]}));
}
function makeUf(ticketPlan,extra){
  return Object.assign({
    version:'arvexq-unified-live-v1',raceId:'r1',raceDate:'2026-11-21',
    diagnosis:diagnosis(10),
    marks:ufMarks([1,2,3,4,5]),
    roster:roster,
    ticketPlan:ticketPlan
  },extra||{});
}
const mech=[{kind:'ワイド',combos:[[7,8]],points:1,reason:'MECH-REASON-XYZ'}];

// A) Full selection: 単勝 = max EV among EV>=1.25 & win>=5%
//    (horse 6, EV 1.68; horse 3 fails EV, horse 4 fails win prob,
//    horse 5 passes but lower EV). 複勝 = highest top-3 prob among
//    EV-low>=1.0 excluding the 単勝 pick (horse 7; horse 6 excluded
//    as the win pick, horse 8 fails the EV-low bound despite the
//    highest top-3 prob). Combinations fill to 5 total in
//    probability order; the 5.1% item is cut by the cap and the
//    4.9% item by the probability floor.
const tpA={sameModelAndMarks:true,expectedValueStatus:'calibrated-estimate',
  combinedPicks:[],
  winExpectedValues:[
    {horseNumber:3,expectedValue:1.10,winProbability:0.20,odds:5.5},
    {horseNumber:4,expectedValue:2.10,winProbability:0.04,odds:52.0},
    {horseNumber:5,expectedValue:1.42,winProbability:0.12,odds:11.6},
    {horseNumber:6,expectedValue:1.68,winProbability:0.09,odds:18.2}],
  placeExpectedValues:[
    {horseNumber:6,top3Probability:0.55,placeOddsLow:2.0,placeOddsHigh:3.0,expectedValueLow:1.10,expectedValueHigh:1.65},
    {horseNumber:7,top3Probability:0.48,placeOddsLow:1.8,placeOddsHigh:2.6,expectedValueLow:1.02,expectedValueHigh:1.30},
    {horseNumber:8,top3Probability:0.60,placeOddsLow:1.5,placeOddsHigh:2.0,expectedValueLow:0.95,expectedValueHigh:1.20}],
  items:[
    {kind:'ワイド',combo:[6,7],probability:0.213},
    {kind:'馬連',combo:[6,5],probability:0.184},
    {kind:'3連複',combo:[6,7,5],probability:0.096},
    {kind:'3連単',combo:[6,7,5],probability:0.051},
    {kind:'ワイド',combo:[1,2],probability:0.049}]};
const raceA={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpA)};
const htmlA=frame.contents(raceA,{});
assert.match(htmlA,/arv-strict-picks/,'strict selection is the main display');
assert.match(htmlA,/単勝 6番 馬6/,'win pick: max EV passer');
assert.match(htmlA,/期待値 1\.68/,'win EV shown');
assert.doesNotMatch(htmlA,/単勝 5番|単勝 3番|単勝 4番/,'win rejects not picked');
assert.match(htmlA,/複勝 7番 馬7/,'place pick: best top-3 among EV-low passers, win pick excluded');
assert.match(htmlA,/期待値 1\.02〜1\.30/,'place EV range shown');
assert.doesNotMatch(htmlA,/複勝 8番|複勝 6番/,'place rejects not picked');
assert.match(htmlA,/推定確率 21\.3%/,'combo probability shown');
assert.ok(htmlA.indexOf('推定確率 21.3%')<htmlA.indexOf('推定確率 18.4%')&&
          htmlA.indexOf('推定確率 18.4%')<htmlA.indexOf('推定確率 9.6%'),
          'combos in probability order');
assert.match(htmlA,/合計 5点/,'total capped at 5');
assert.doesNotMatch(htmlA,/3連単/,'cap cut the 4th combo');
assert.doesNotMatch(htmlA,/1 - 2/,'probability floor cut the 4.9% combo');
assert.doesNotMatch(htmlA,/arv-formation-picks|arv-plan-picks/,'no formation / plan-picks primary');
assert.doesNotMatch(htmlA,/arv-osusume/,'integrated recommendation not shown');
assert.doesNotMatch(htmlA,/MECH-REASON-XYZ/,'mechanical set not shown');
assert.doesNotMatch(htmlA,/<details/,'no reference fold');
assert.match(htmlA,/期待値候補|単勝期待値/,'EV section kept');
assert.match(frame.render(raceA,{}),/おすすめ買い目/,'tab heading');

// B) No win/place qualifiers: combinations alone fill the 5 slots.
const tpB={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[1,2],probability:0.30},
    {kind:'馬連',combo:[1,3],probability:0.25},
    {kind:'3連複',combo:[1,2,3],probability:0.20},
    {kind:'馬単',combo:[1,2],probability:0.15},
    {kind:'ワイド',combo:[2,4],probability:0.10},
    {kind:'ワイド',combo:[8,9],probability:0.06}]};
const raceB={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpB)};
const htmlB=frame.contents(raceB,{});
assert.match(htmlB,/arv-strict-picks/);
assert.match(htmlB,/合計 5点/,'five combos fill the cap');
assert.doesNotMatch(htmlB,/8 - 9/,'sixth combo cut by the cap');
assert.doesNotMatch(htmlB,/単勝 \d+番|複勝 \d+番/,'no single picks');
// The two ワイド picks share horse 2, so they collapse into one
// formation line; the other kinds stay single lines with probabilities.
assert.match(htmlB,/2 − 1・4（2点）/,'wide picks grouped on shared horse 2');
assert.doesNotMatch(htmlB,/推定確率 30\.0%|推定確率 10\.0%/,'grouped picks lose individual probabilities');
assert.match(htmlB,/推定確率 25\.0%/,'ungrouped 馬連 keeps its probability');
assert.match(htmlB,/推定確率 15\.0%/,'ungrouped 馬単 keeps its probability');

// C) Partial selection: only the win pick and two combos qualify.
const tpC={sameModelAndMarks:true,combinedPicks:[],
  winExpectedValues:[{horseNumber:2,expectedValue:1.30,winProbability:0.10,odds:13.0}],
  placeExpectedValues:[{horseNumber:3,top3Probability:0.40,placeOddsLow:1.4,placeOddsHigh:1.9,expectedValueLow:0.80,expectedValueHigh:1.05}],
  items:[
    {kind:'ワイド',combo:[2,3],probability:0.22},
    {kind:'馬連',combo:[2,4],probability:0.11},
    {kind:'ワイド',combo:[5,6],probability:0.02}]};
const raceC={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpC)};
const htmlC=frame.contents(raceC,{});
assert.match(htmlC,/単勝 2番/);
assert.doesNotMatch(htmlC,/複勝 3番/,'place EV-low below 1.0 rejected');
assert.match(htmlC,/合計 3点/,'1 win + 2 combos');

// D) ticketPlan present but nothing qualifies: 見送り, and the
//    fallback chain is NOT used.
const tpD={sameModelAndMarks:true,combinedPicks:[],
  winExpectedValues:[{horseNumber:2,expectedValue:1.00,winProbability:0.30,odds:3.3}],
  placeExpectedValues:[{horseNumber:3,top3Probability:0.40,placeOddsLow:1.4,placeOddsHigh:1.9,expectedValueLow:0.90,expectedValueHigh:1.05}],
  items:[{kind:'ワイド',combo:[2,3],probability:0.03}]};
const raceD={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpD)};
const htmlD=frame.contents(raceD,{});
assert.match(htmlD,/arv-strict-picks/,'strict block still primary');
assert.match(htmlD,/見送り（条件を満たす買い目なし）/,'pass displayed');
assert.doesNotMatch(htmlD,/arv-osusume|MECH-REASON-XYZ/,'no fallback when ticketPlan exists');

// E) No ticketPlan on the unified payload: fallback chain applies
//    (integrated recommendation).
const ufE=makeUf(undefined);
delete ufE.ticketPlan;
const raceE={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,unifiedForecast:ufE};
const htmlE=frame.contents(raceE,{});
assert.doesNotMatch(htmlE,/arv-strict-picks/,'no ticketPlan, no strict block');
assert.match(htmlE,/arv-osusume/,'fallback: integrated recommendation');

// F) No unified payload at all: the mechanical set renders as before.
const raceF={id:'r5',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech};
const htmlF=frame.contents(raceF,{});
assert.match(htmlF,/MECH-REASON-XYZ/);
assert.doesNotMatch(htmlF,/arv-strict-picks|arv-osusume/);

// G) Plan branch: the strict selection outranks the projected plan
//    group; without a ticketPlan the plan group renders as before.
W.ARVEXQProductionTickets={build:()=>({fixedAt:'2026-11-21T08:00:00+09:00',
  items:[{kind:'馬連',combos:[[7,8]],reason:'PLAN-MECH-REASON'}]})};
const raceG={id:'r1',date:'2026-11-21',predictionMarks:predMarks([1,2,3,4,5]),
  recommendedBets:mech,unifiedForecast:makeUf(tpA)};
const htmlG=frame.contents(raceG,{});
assert.match(htmlG,/arv-strict-picks/,'plan branch: strict primary');
assert.doesNotMatch(htmlG,/PLAN-MECH-REASON/,'plan branch: projected plan not shown');
assert.doesNotMatch(htmlG,/arv-osusume/,'plan branch: integrated not shown');
const raceG2={id:'r7',date:'2026-11-21',predictionMarks:predMarks([1,2,3,4,5])};
const htmlG2=frame.contents(raceG2,{});
assert.match(htmlG2,/PLAN-MECH-REASON/,'plan fallback unchanged');
assert.doesNotMatch(htmlG2,/arv-strict-picks/);

// H) No legacy plan at all: the strict selection stands alone.
W.ARVEXQProductionTickets={build:()=>null};
const htmlH=frame.contents(raceG,{});
assert.match(htmlH,/arv-strict-picks/,'standalone strict selection');
assert.doesNotMatch(htmlH,/MECH-REASON-XYZ/);

// I) Formation grouping: ワイド sharing horse 4 (3 partners, in
//    probability order) and 馬連 sharing horse 4 collapse into
//    one line each. Group lines carry only the point count; the
//    total still counts the 5 individual picks.
const tpI={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[4,9],probability:0.30},
    {kind:'ワイド',combo:[4,8],probability:0.25},
    {kind:'ワイド',combo:[4,7],probability:0.20},
    {kind:'馬連',combo:[4,9],probability:0.15},
    {kind:'馬連',combo:[4,6],probability:0.12}]};
const raceI={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpI)};
const htmlI=frame.contents(raceI,{});
assert.match(htmlI,/4 − 9・8・7（3点）/,'wide formation: axis 4, partners in probability order');
assert.match(htmlI,/4 − 9・6（2点）/,'quinella formation: axis 4');
assert.doesNotMatch(htmlI,/推定確率/,'group lines carry no individual probabilities');
assert.match(htmlI,/合計 5点/,'total counts individual picks, not lines');

// J) 馬単 grouping on the shared 1st horse; an unrelated ワイド
//    stays a single line with its probability.
const tpJ={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'馬単',combo:[9,5],probability:0.30},
    {kind:'馬単',combo:[9,3],probability:0.25},
    {kind:'ワイド',combo:[1,2],probability:0.20}]};
const raceJ={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpJ)};
const htmlJ=frame.contents(raceJ,{});
assert.match(htmlJ,/9 → 5・3（2点）/,'exacta formation: shared 1st horse 9');
assert.match(htmlJ,/推定確率 20\.0%/,'ungrouped wide keeps its probability');
assert.match(htmlJ,/合計 3点/,'total counts individual picks');

// K) 3連複 grouping on the shared pair; a trio without the pair
//    stays a single line.
const tpK={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'3連複',combo:[4,9,7],probability:0.30},
    {kind:'3連複',combo:[4,9,8],probability:0.25},
    {kind:'3連複',combo:[1,2,3],probability:0.20}]};
const raceK={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpK)};
const htmlK=frame.contents(raceK,{});
assert.match(htmlK,/4・9 − 7・8（2点）/,'trio formation: shared pair 4・9');
assert.match(htmlK,/1 - 2 - 3/,'ungrouped trio stays a single line');
assert.match(htmlK,/推定確率 20\.0%/,'ungrouped trio keeps its probability');
assert.match(htmlK,/合計 3点/,'total counts individual picks');

// L) 3連単 grouping on the shared 1st-2nd pair; a trifecta with a
//    different 2nd horse stays a single line.
const tpL={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'3連単',combo:[9,5,3],probability:0.30},
    {kind:'3連単',combo:[9,5,7],probability:0.25},
    {kind:'3連単',combo:[9,3,5],probability:0.20}]};
const raceL={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpL)};
const htmlL=frame.contents(raceL,{});
assert.match(htmlL,/9-5 → 3・7（2点）/,'trifecta formation: shared 1st-2nd 9-5');
assert.match(htmlL,/9 - 3 - 5/,'ungrouped trifecta stays a single line');
assert.match(htmlL,/推定確率 20\.0%/,'ungrouped trifecta keeps its probability');
assert.match(htmlL,/合計 3点/,'total counts individual picks');

// M) Same kind but no shared axis: no grouping, both picks stay
//    single lines with their probabilities.
const tpM={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[1,2],probability:0.30},
    {kind:'ワイド',combo:[3,4],probability:0.25}]};
const raceM={id:'r1',date:'2026-11-21',predictionStatus:'ready',
  predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
  unifiedForecast:makeUf(tpM)};
const htmlM=frame.contents(raceM,{});
assert.match(htmlM,/推定確率 30\.0%/,'disjoint wide 1 keeps its probability');
assert.match(htmlM,/推定確率 25\.0%/,'disjoint wide 2 keeps its probability');
assert.doesNotMatch(htmlM,/（2点）/,'no formation line without a shared axis');
assert.match(htmlM,/合計 2点/,'total counts individual picks');

console.log('STRICT_PRIMARY_BETS_OK win-EV place-EVlow combos-to-5pt pass-display fallback-unchanged EV-kept formation-grouping');
