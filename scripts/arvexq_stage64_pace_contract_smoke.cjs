'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const root = {window: null};
root.window = root;
vm.createContext(root);
for (const file of ['prediction.js', 'prediction_frame.js']) {
  vm.runInContext(fs.readFileSync('arvexq/ui/static/forecast/' + file, 'utf8'), root, {filename:file});
}
function race(circuit, scenarios) {
  return {
    id:(circuit === '中央' ? 'jra' : 'nar') + '-2026-10-23-test-01',
    date:'2026-10-23',circuit:circuit,predictionStatus:'ready',
    horses:[{horseNumber:1,name:'A'},{horseNumber:2,name:'B'}],
    predictionMarks:[{horseNumber:1,mark:'◎'},{horseNumber:2,mark:'○'}],
    prediction:{
      predictionStatus:'ready',modelVersion:'arvexq-stage64-product-v1',
      stages:{
        probability:{calibrationVerified:false,value:{win:{1:0.6,2:0.4},top3:{1:0.9,2:0.8}}},
        pace:{value:scenarios}
      }
    }
  };
}
for (const [circuit,scenarios] of [
  ['中央',[{'1':0,'2':0}]],
  ['地方',[{'1':0,'2':0},{'1':0.1,'2':-0.2},{'1':0.2,'2':-0.1},{'1':-0.1,'2':0.2}]]
]) {
  root.ARVEXQProductionPrediction.build(race(circuit,scenarios));
  const state=root.ARVEXQProductionPrediction.current();
  assert.equal(state.source,'stage64-preoff');
  assert.equal(state.pace.length,scenarios.length*2);
  assert.equal(state.pace[0].horseNumber,1);
  assert.equal(state.pace[0].scenarioIndex,1);
  assert.equal(state.uncalibrated,true);
  for (const row of state.pace) {
    assert([1,2].includes(row.horseNumber));
    assert.equal(row.delta,scenarios[row.scenarioIndex-1][row.horseNumber]);
  }
  const html=root.ARVEXQPredictionFrame.render();
  assert(html.includes('Stage64発走前の展開仮説'));
  assert(html.includes('仮説1 1番 補正0.000'));
  assert(!html.includes('このレースの学習済み予想印は未取得'));
  assert(!html.includes('仮説0'));
  if (circuit==='地方')assert(html.includes('仮説2 1番 補正+0.100'));
}
console.log('STAGE64_PACE_SCENARIO_IDS_AND_UNCALIBRATED_LABELS_OK');
