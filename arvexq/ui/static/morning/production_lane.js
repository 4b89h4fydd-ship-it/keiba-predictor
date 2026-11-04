/* ARVEXQ morning 厳選 lane: adapters from the PRODUCTION stored
 * forecast + ticket plan (the server-published v9b payload) to the
 * morning selection contracts (classify / requireMorningTickets /
 * evidence capture). The lane never recomputes a forecast: every
 * value below is read off the stored detail exactly as published.
 *
 * Data-thinness gate: the legacy classify gate reads a per-runner
 * `threeFactorCoverage` — the count of the legacy engine's three
 * scored factors that carried measured evidence for that runner.
 * Production prediction rows carry a different field, `coverage`,
 * which is only a per-source flag (0 on unified rows, 1 on archived
 * server rows); it does NOT count evidence depth and is deliberately
 * NOT mapped onto the classify contract. The production engine's own
 * per-runner evidence lives on the stored diagnosis entry: whether
 * the ability layer could score the runner from its past-run
 * evidence (abilityScore), and whether the probability layers priced
 * it (winProbability / top3Probability). This adapter reports the
 * count of those three stored layers, on the same 0-3 scale and with
 * the same meaning for the gate: how much of the engine's evaluation
 * actually exists for this runner. Nothing is imputed; a layer is
 * counted only when the stored value is a finite number.
 *
 * Plan contract: the production ticket plan's stored decision is
 * 「参考候補・購入推奨なし」 everywhere outside this lane and stays
 * that way. Inside the lane, a plan object is built from the stored
 * ticketPlan.items only and is scoped by `source`, so the
 * purchase-style gates elsewhere can never be satisfied by it. The
 * 本線 (main) item is designated by the calibration generator's
 * fixed rule — the combo-kind group of the plan's
 * highest-probability ticket (the stored items[0]; api_shape sorts
 * probability-descending), with ALL of that kind's issued
 * combinations — so the morning judgement measures exactly the
 * object the calibration buckets grade. Point counts are recorded
 * faithfully: a 36-point Formation B 3連単 is a 36-point item here,
 * never truncated to the legacy 12-point cap.
 */
(function(global){
'use strict';
const SOURCE='arvexq-morning-production-lane-v1';
const MODEL_VERSION='arvexq-rewrite-v3-v9b';
const ABILITY_LANE='v9b-cal-market';
const WIDTHS={'ワイド':2,'馬連':2,'馬単':2,'3連複':3,'3連単':3};
function num(v){const n=Number(v);return Number.isInteger(n)&&n>0?n:0}
function present(v){return v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))}
function isProductionDetail(detail){
 if(!detail||!detail.id)return false;
 const uf=detail.unifiedForecast;
 if(!uf||uf.version!=='arvexq-unified-live-v1'||
    String(uf.modelVersion||'')!==MODEL_VERSION||
    String(uf.raceId||'')!==String(detail.id)||
    !Array.isArray(uf.marks)||!Array.isArray(uf.diagnosis)||
    !uf.ticketPlan||uf.ticketPlan.sameModelAndMarks!==true||
    !Array.isArray(uf.ticketPlan.items))return false;
 const lane=detail.preparedMeta&&detail.preparedMeta.rewritePublish&&
   detail.preparedMeta.rewritePublish.abilityLane;
 if(lane&&String(lane)!==ABILITY_LANE)return false;
 return true;
}
function forecast(detail){
 if(!isProductionDetail(detail))return null;
 const uf=detail.unifiedForecast;
 const marks={},attention=new Set();
 for(const m of uf.marks||[]){
   const no=num(m&&m.horseNumber);if(!no)continue;
   if(m.markSymbol)marks[no]=String(m.markSymbol);
   if(m.attention===true)attention.add(no);
 }
 for(const v of uf.ticketPlan.combinedPicks||[]){
   const no=num(v);if(no)attention.add(no);
 }
 const diag={};
 for(const d of uf.diagnosis||[]){
   const no=num(d&&d.horseNumber);if(no&&!diag[no])diag[no]=d;
 }
 const rows=[];
 for(const h of detail.horses||[]){
   const no=num(h&&h.horseNumber);if(!no)continue;
   const d=diag[no]||{};
   const coverage=[d.abilityScore,d.winProbability,d.top3Probability]
     .filter(present).length;
   rows.push({horse:h,predMark:marks[no]||(attention.has(no)?'注':''),
     threeFactorCoverage:coverage,singleWinSuitable:false});
 }
 return {rows:rows,source:SOURCE,modelVersion:MODEL_VERSION};
}
function plan(detail){
 if(!isProductionDetail(detail))return null;
 const items=detail.unifiedForecast.ticketPlan.items;
 if(!items.length)return null;
 const roster=new Set();
 for(const h of detail.horses||[]){const no=num(h&&h.horseNumber);if(no)roster.add(no)}
 const groups=[],byKind={};
 for(const raw of items){
   if(!raw||!Object.prototype.hasOwnProperty.call(WIDTHS,raw.kind)||
      !Array.isArray(raw.combo))return null;
   const combo=raw.combo.map(num);
   if(combo.length!==WIDTHS[raw.kind]||combo.some(n=>!n||!roster.has(n))||
      new Set(combo).size!==combo.length)return null;
   if(!byKind[raw.kind]){byKind[raw.kind]={kind:raw.kind,combos:[]};groups.push(byKind[raw.kind])}
   byKind[raw.kind].combos.push(combo);
 }
 if(!groups.length)return null;
 const mainKind=groups[0].kind;
 return {source:SOURCE,decision:'厳選判定',modelVersion:MODEL_VERSION,
   engineVersion:MODEL_VERSION,
   items:groups.map(g=>({level:g.kind===mainKind?'本線':'保険',kind:g.kind,
     combos:g.combos,points:g.combos.length}))};
}
global.ARVEXQMorningProductionLane=Object.freeze({SOURCE,MODEL_VERSION,
 isProductionDetail,forecast,plan});
})(window);
