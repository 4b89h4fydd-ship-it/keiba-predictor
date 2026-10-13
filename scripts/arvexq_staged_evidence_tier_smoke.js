'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('arvexq/ui/static/app.js', 'utf8');
const start = source.indexOf('function integratedGrades(');
const end = source.indexOf('\n// v345:', start);
assert.ok(start >= 0 && end > start, 'integratedGrades source was not found');
const context = { n: (value, fallback = 0) => Number.isFinite(Number(value)) && value != null ? Number(value) : fallback };
const integratedGrades = vm.runInNewContext('(' + source.slice(start, end) + ')', context);

for (const [observed, expected] of [
  [0, '実測データ不足'],
  [1, '1指標実測評価'],
  [2, '2指標実測評価'],
]) {
  const row = { overallScore: 70, threeFactorCoverage: observed, overallGrade: 'B' };
  integratedGrades({}, [row]);
  assert.equal(row.evaluation.tier, expected, 'coverage ' + observed);
  assert.notEqual(row.evaluation.tier, '3指標実測評価');
}
console.log('staged evidence-tier regression: PASS (0/1/2 observed)');

// Recent form must not be represented as independently measured ability.
assert.match(source, /researchFactors=\{ability:null,form:f\.recentForm,/);
assert.doesNotMatch(source, /researchFactors=\{ability:f\.recentForm,form:f\.recentForm,/);

assert.doesNotMatch(source, /3要素|TRUE RUN45%|SECTIONAL20%/);
