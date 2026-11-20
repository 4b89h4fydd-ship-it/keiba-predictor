/* Bets tab primary display (user rule 2026-11-21, final revision):
 * a strict selection across ALL ticket kinds from the payload's
 * ticketPlan, at most 5 points, built ONLY from the marked horses
 * (◎○▲△☆) — a pick naming an unmarked horse is never shown. This
 * mirrors the posting-side selection (generate_posts.py):
 *   1. 単勝: winExpectedValues with EV >= 1.25 AND win prob >= 5%,
 *      marked horses only, the maximum-EV horse (1 point).
 *   2. 複勝: placeExpectedValues with EV lower bound >= 1.0,
 *      marked horses only, the highest top-3 probability,
 *      excluding the 単勝 pick (1 point).
 *   3. Combinations: ticketPlan.items in payload order whose
 *      horses are ALL marked, only probability >= 5% (an item
 *      carrying no probability passes), filling up to 5 points.
 *   4. Coverage: a marked horse still in no pick is covered by a
 *      marked-only combination — 3+ uncovered: the 3連複 of the
 *      three with the highest top-3 probabilities (diagnosis);
 *      2 uncovered: their ワイド; 1 uncovered: a ワイド with the
 *      strongest mark (◎, or ○ when the horse itself is ◎). At
 *      the 5-point cap the coverage bet replaces the lowest-
 *      probability combination （単勝/複勝 are never replaced).
 * No probability percentages are displayed: combination rows carry
 * no 推定確率, and the 単勝/複勝 rows show only their EV.
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
 * point count, and the total still counts individual picks.
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
function raceOf(uf){
  return {id:'r1',date:'2026-11-21',predictionStatus:'ready',
    predictionMarks:predMarks([1,2,3,4,5]),recommendedBets:mech,
    unifiedForecast:uf};
}
const mech=[{kind:'ワイド',combos:[[7,8]],points:1,reason:'MECH-REASON-XYZ'}];

// A) Full selection, marked horses only. 単勝 = max EV among marked
//    EV>=1.25 & win>=5% passers (horse 5, EV 1.68): horse 6 has a
//    higher EV but is unmarked and excluded; horse 3 fails EV,
//    horse 4 fails win prob, horse 2 passes with a lower EV.
//    複勝 = highest top-3 prob among marked EV-low>=1.0 passers
//    excluding the win pick (horse 1): horse 6 is unmarked, horse 5
//    is the win pick, horse 2 fails the EV-low bound. Combinations
//    fill to 5 in payload order (the [5,6] item names an unmarked
//    horse and is excluded; [1,2] is cut by the cap). Coverage then
//    replaces the lowest-probability combination (3連複 9.6%) with
//    the ワイド of the two uncovered marks 3 and 4.
const tpA={sameModelAndMarks:true,expectedValueStatus:'calibrated-estimate',
  combinedPicks:[],
  winExpectedValues:[
    {horseNumber:6,expectedValue:3.00,winProbability:0.30,odds:9.0},
    {horseNumber:5,expectedValue:1.68,winProbability:0.09,odds:18.2},
    {horseNumber:2,expectedValue:1.42,winProbability:0.12,odds:11.6},
    {horseNumber:3,expectedValue:1.10,winProbability:0.20,odds:5.5},
    {horseNumber:4,expectedValue:2.10,winProbability:0.04,odds:52.0}],
  placeExpectedValues:[
    {horseNumber:6,top3Probability:0.60,placeOddsLow:3.0,placeOddsHigh:4.5,expectedValueLow:2.00,expectedValueHigh:3.00},
    {horseNumber:5,top3Probability:0.55,placeOddsLow:2.0,placeOddsHigh:3.0,expectedValueLow:1.10,expectedValueHigh:1.65},
    {horseNumber:1,top3Probability:0.48,placeOddsLow:1.8,placeOddsHigh:2.6,expectedValueLow:1.02,expectedValueHigh:1.30},
    {horseNumber:2,top3Probability:0.50,placeOddsLow:1.5,placeOddsHigh:2.0,expectedValueLow:0.95,expectedValueHigh:1.20}],
  items:[
    {kind:'ワイド',combo:[5,6],probability:0.300},
    {kind:'ワイド',combo:[5,1],probability:0.213},
    {kind:'馬連',combo:[5,2],probability:0.184},
    {kind:'3連複',combo:[5,1,2],probability:0.096},
    {kind:'ワイド',combo:[1,2],probability:0.060},
    {kind:'ワイド',combo:[1,3],probability:0.049}]};
const raceA=raceOf(makeUf(tpA));
const htmlA=frame.contents(raceA,{});
assert.match(htmlA,/arv-strict-picks/,'strict selection is the main display');
assert.match(htmlA,/単勝 5番 馬5/,'win pick: max EV marked passer');
assert.match(htmlA,/期待値 1\.68/,'win EV shown');
assert.doesNotMatch(htmlA,/単勝 6番|単勝 2番|単勝 3番|単勝 4番/,'win rejects not picked (6 is unmarked)');
assert.match(htmlA,/複勝 1番 馬1/,'place pick: best top-3 among marked EV-low passers');
assert.match(htmlA,/期待値 1\.02〜1\.30/,'place EV range shown');
assert.doesNotMatch(htmlA,/複勝 6番|複勝 5番|複勝 2番/,'place rejects not picked');
assert.doesNotMatch(htmlA,/5 - 6/,'combo naming an unmarked horse excluded');
assert.match(htmlA,/5 - 1/,'wide combo kept');
assert.match(htmlA,/5 - 2/,'quinella combo kept');
assert.match(htmlA,/3 - 4/,'coverage wide for the uncovered marks 3 and 4');
assert.doesNotMatch(htmlA,/3連複/,'lowest-probability combo replaced by the coverage bet');
assert.doesNotMatch(htmlA,/1 - 2/,'cap cut the remaining item');
assert.match(htmlA,/合計 5点/,'total capped at 5');
assert.doesNotMatch(htmlA,/推定確率/,'no probability percentages anywhere');
assert.doesNotMatch(htmlA,/× 単勝 18\.2/,'win row shows no win-rate detail line');
assert.doesNotMatch(htmlA,/arv-formation-picks|arv-plan-picks/,'no formation / plan-picks primary');
assert.doesNotMatch(htmlA,/arv-osusume/,'integrated recommendation not shown');
assert.doesNotMatch(htmlA,/MECH-REASON-XYZ/,'mechanical set not shown');
assert.doesNotMatch(htmlA,/<details/,'no reference fold');
assert.match(htmlA,/期待値候補|単勝期待値/,'EV section kept');
assert.match(frame.render(raceA,{}),/おすすめ買い目/,'tab heading');

// B) Coverage branches with no qualifying picks at all: the items
//    are unusable (one names unmarked horses, one is below the
//    probability floor), so coverage alone builds the selection —
//    first the 3連複 of the three uncovered marks with the highest
//    diagnosis top-3 probabilities (3, 4, 1), then the ワイド of
//    the two remaining marks (2, 5).
const diagB=[1,2,3,4,5,6,7,8,9,10].map(function(no){
  const t3={1:0.30,2:0.10,3:0.50,4:0.40,5:0.20}[no]||0.05;
  return {horseNumber:no,winProbability:0.05,top3Probability:t3,grade:'A'};
});
const tpB={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[6,7],probability:0.30},
    {kind:'ワイド',combo:[1,2],probability:0.04}]};
const raceB=raceOf(makeUf(tpB,{diagnosis:diagB}));
const htmlB=frame.contents(raceB,{});
assert.match(htmlB,/arv-strict-picks/);
assert.doesNotMatch(htmlB,/単勝 \d+番|複勝 \d+番/,'no single picks');
assert.doesNotMatch(htmlB,/6 - 7/,'unmarked combo excluded');
assert.match(htmlB,/1 - 3 - 4/,'coverage trio: top-3 by diagnosis top-3 probability');
assert.match(htmlB,/2 - 5/,'coverage wide for the last two uncovered marks');
assert.match(htmlB,/合計 2点/,'two coverage bets');
assert.doesNotMatch(htmlB,/推定確率/,'coverage bets carry no probability display');

// C) Coverage of a single uncovered mark: the partner is the
//    strongest mark (◎ = horse 1). Selection: win pick 1, place
//    pick 3 (horse 2 fails the EV-low bound), one wide item
//    covering marks 2 and 4 — mark 5 is left over and covered by
//    ワイド [1,5].
const tpC={sameModelAndMarks:true,combinedPicks:[],
  winExpectedValues:[{horseNumber:1,expectedValue:1.30,winProbability:0.10,odds:13.0}],
  placeExpectedValues:[
    {horseNumber:3,top3Probability:0.45,placeOddsLow:1.6,placeOddsHigh:2.2,expectedValueLow:1.05,expectedValueHigh:1.40},
    {horseNumber:2,top3Probability:0.50,placeOddsLow:1.4,placeOddsHigh:1.9,expectedValueLow:0.80,expectedValueHigh:1.05}],
  items:[{kind:'ワイド',combo:[2,4],probability:0.20}]};
const raceC=raceOf(makeUf(tpC));
const htmlC=frame.contents(raceC,{});
assert.match(htmlC,/単勝 1番/);
assert.match(htmlC,/複勝 3番/,'place pick: EV-low passer');
assert.doesNotMatch(htmlC,/複勝 2番/,'place EV-low below 1.0 rejected');
assert.match(htmlC,/2 - 4/,'item kept');
assert.match(htmlC,/1 - 5/,'single uncovered mark covered with the ◎ horse');
assert.match(htmlC,/合計 4点/,'win + place + item + coverage');
assert.doesNotMatch(htmlC,/推定確率/,'no probability percentages');
assert.doesNotMatch(htmlC,/3着内 45/,'place row shows no top-3 detail line');

// C2) The single uncovered mark is ◎ itself: the partner is ○.
const tpC2={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'3連複',combo:[2,3,4],probability:0.20},
    {kind:'ワイド',combo:[4,5],probability:0.15}]};
const raceC2=raceOf(makeUf(tpC2));
const htmlC2=frame.contents(raceC2,{});
assert.match(htmlC2,/2 - 3 - 4/,'trio item kept');
assert.match(htmlC2,/4 - 5/,'wide item kept');
assert.match(htmlC2,/1 - 2/,'uncovered ◎ covered with the ○ horse');
assert.match(htmlC2,/合計 3点/,'two items + coverage');

// D) ticketPlan present but no marks at all: nothing can be built
//    (every candidate names an unmarked horse, and there is no
//    marked horse to cover) — 見送り, and the fallback chain is
//    NOT used.
const tpD={sameModelAndMarks:true,combinedPicks:[],
  winExpectedValues:[{horseNumber:2,expectedValue:1.80,winProbability:0.30,odds:5.8}],
  placeExpectedValues:[{horseNumber:3,top3Probability:0.40,placeOddsLow:1.4,placeOddsHigh:1.9,expectedValueLow:1.10,expectedValueHigh:1.30}],
  items:[{kind:'ワイド',combo:[2,3],probability:0.30}]};
const raceD=raceOf(makeUf(tpD,{marks:[]}));
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

// I) Formation grouping: ワイド sharing horse 1 (3 partners, in
//    selection order) and 馬連 sharing horse 1 collapse into one
//    line each. All five marks are covered by the items, so no
//    coverage bet appears. Group lines carry only the point
//    count; the total still counts the 5 individual picks.
const tpI={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[1,4],probability:0.30},
    {kind:'ワイド',combo:[1,3],probability:0.25},
    {kind:'ワイド',combo:[1,2],probability:0.20},
    {kind:'馬連',combo:[1,4],probability:0.15},
    {kind:'馬連',combo:[1,5],probability:0.12}]};
const raceI=raceOf(makeUf(tpI));
const htmlI=frame.contents(raceI,{});
assert.match(htmlI,/1 − 4・3・2（3点）/,'wide formation: axis 1, partners in selection order');
assert.match(htmlI,/1 − 4・5（2点）/,'quinella formation: axis 1');
assert.doesNotMatch(htmlI,/推定確率/,'group lines carry no probabilities');
assert.match(htmlI,/合計 5点/,'total counts individual picks, not lines');

// J) 馬単 grouping on the shared 1st horse; an unrelated ワイド
//    stays a single line. All marks are covered by the items.
const tpJ={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'馬単',combo:[2,5],probability:0.30},
    {kind:'馬単',combo:[2,3],probability:0.25},
    {kind:'ワイド',combo:[1,4],probability:0.20}]};
const raceJ=raceOf(makeUf(tpJ));
const htmlJ=frame.contents(raceJ,{});
assert.match(htmlJ,/2 → 5・3（2点）/,'exacta formation: shared 1st horse 2');
assert.match(htmlJ,/1 - 4/,'ungrouped wide stays a single line');
assert.doesNotMatch(htmlJ,/推定確率/,'ungrouped pick shows no probability either');
assert.match(htmlJ,/合計 3点/,'total counts individual picks');

// K) 3連複 grouping on the shared pair; a trio without the pair
//    stays a single line. All marks are covered by the items.
const tpK={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'3連複',combo:[1,2,4],probability:0.30},
    {kind:'3連複',combo:[1,2,5],probability:0.25},
    {kind:'3連複',combo:[3,4,5],probability:0.20}]};
const raceK=raceOf(makeUf(tpK));
const htmlK=frame.contents(raceK,{});
assert.match(htmlK,/1・2 − 4・5（2点）/,'trio formation: shared pair 1・2');
assert.match(htmlK,/3 - 4 - 5/,'ungrouped trio stays a single line');
assert.match(htmlK,/合計 3点/,'total counts individual picks');

// L) 3連単 grouping on the shared 1st-2nd pair; a trifecta with a
//    different 2nd horse stays a single line. Mark 5 is in no
//    item, so coverage appends ワイド [1,5] (total 3 -> 4).
const tpL={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'3連単',combo:[2,1,3],probability:0.30},
    {kind:'3連単',combo:[2,1,4],probability:0.25},
    {kind:'3連単',combo:[2,3,1],probability:0.20}]};
const raceL=raceOf(makeUf(tpL));
const htmlL=frame.contents(raceL,{});
assert.match(htmlL,/2-1 → 3・4（2点）/,'trifecta formation: shared 1st-2nd 2-1');
assert.match(htmlL,/2 - 3 - 1/,'ungrouped trifecta stays a single line');
assert.match(htmlL,/1 - 5/,'coverage wide for the uncovered mark 5');
assert.match(htmlL,/合計 4点/,'total counts individual picks incl. coverage');

// M) Same kind but no shared axis: no grouping, both ワイド picks
//    stay single lines; the 馬連 covers the last mark so no
//    coverage bet is needed.
const tpM={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[1,2],probability:0.30},
    {kind:'ワイド',combo:[3,4],probability:0.25},
    {kind:'馬連',combo:[3,5],probability:0.20}]};
const raceM=raceOf(makeUf(tpM));
const htmlM=frame.contents(raceM,{});
assert.match(htmlM,/1 - 2/,'disjoint wide 1 stays a single line');
assert.match(htmlM,/3 - 4/,'disjoint wide 2 stays a single line');
assert.match(htmlM,/3 - 5/,'quinella stays a single line');
assert.doesNotMatch(htmlM,/（2点）/,'no formation line without a shared axis');
assert.doesNotMatch(htmlM,/推定確率/,'no probability percentages');
assert.match(htmlM,/合計 3点/,'total counts individual picks');

// N) Coverage replacement never touches the 単勝/複勝 picks: with
//    the cap full (win + place + 3 combos) and marks 4, 5
//    uncovered, the coverage ワイド [4,5] replaces the lowest-
//    probability combination (3連複 20%) only.
const tpN={sameModelAndMarks:true,combinedPicks:[],
  winExpectedValues:[{horseNumber:1,expectedValue:1.30,winProbability:0.10,odds:13.0}],
  placeExpectedValues:[
    {horseNumber:2,top3Probability:0.50,placeOddsLow:1.8,placeOddsHigh:2.4,expectedValueLow:1.05,expectedValueHigh:1.30}],
  items:[
    {kind:'ワイド',combo:[1,2],probability:0.30},
    {kind:'馬連',combo:[1,2],probability:0.25},
    {kind:'3連複',combo:[1,2,3],probability:0.20}]};
const raceN=raceOf(makeUf(tpN));
const htmlN=frame.contents(raceN,{});
assert.match(htmlN,/単勝 1番/,'win pick survives the replacement');
assert.match(htmlN,/複勝 2番/,'place pick survives the replacement');
assert.match(htmlN,/4 - 5/,'coverage wide present');
assert.doesNotMatch(htmlN,/3連複/,'lowest-probability combo replaced');
assert.match(htmlN,/合計 5点/,'total stays at the cap');

// O) An item carrying no probability passes the floor (posting
//    side parity); an item at exactly 5% passes and one below is
//    cut. Mark 5 is left uncovered and covered by ワイド [1,5],
//    which shares the axis horse 1 with the first item and so
//    renders inside its formation line.
const tpO={sameModelAndMarks:true,winExpectedValues:[],placeExpectedValues:[],
  combinedPicks:[],
  items:[
    {kind:'ワイド',combo:[1,2]},
    {kind:'馬連',combo:[3,4],probability:0.049},
    {kind:'馬連',combo:[3,4],probability:0.05}]};
const raceO=raceOf(makeUf(tpO));
const htmlO=frame.contents(raceO,{});
assert.match(htmlO,/1 − 2・5（2点）/,'probability-less item + coverage wide grouped on axis 1');
assert.match(htmlO,/3 - 4/,'boundary 5% item passes');
assert.match(htmlO,/合計 3点/,'two items + coverage');

console.log('STRICT_PRIMARY_BETS_OK marks-only win-EV place-EVlow combos-to-5pt coverage(trio/wide-single/replace) no-percent pass-display fallback-unchanged EV-kept formation-grouping');
