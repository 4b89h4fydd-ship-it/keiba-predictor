#!/usr/bin/env node
// Evidence-only axis gate; tests no forced ◎ on noisy relative rankings.
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const win={};
new Function('window',fs.readFileSync('arvexq/ui/static/betting/podium_axis_guard.js','utf8'))(win);
const g=win.ARVEXQPodiumAxisGuard;
assert.equal(g.VERSION,'arvexq-axis-reliability-v1');
const horse={horse:{horseNumber:4},podiumAxisHistory:{starts:5,top3:4},
 podiumAxisScore:.71,axisRank:1,podiumRecallRank:2,winnerDecisionRank:2,
 edgeEvidence:.55,coverage:.65};
const runner={horse:{horseNumber:5},podiumAxisScore:.63};
assert(g.inspect(horse,runner).eligible,'stable history / model agreement earns ◎');
function reject(patch,code){
 const v=g.inspect({...horse,...patch},runner);
 assert.equal(v.eligible,false,code);
 assert(v.failures.includes(code),JSON.stringify(v));
}
reject({podiumAxisHistory:{starts:2,top3:1}},'historicalPodium');
reject({podiumAxisHistory:{starts:5,top3:2}},'historicalPodium');
reject({winnerDecisionRank:4},'winningChance');
reject({podiumAxisScore:.64},'clearSeparation');
reject({edgeEvidence:.20},'observedEvidence');
reject({axisRank:4},'broadConsensus');
reject({podiumAxisScore:.58},'axisStrength');
const missing=g.inspect(null,null);
assert.equal(missing.eligible,false,'missing candidates cannot be ◎');
console.log('PODIUM_AXIS_GUARD_OK strong=accepted short/noisy/low-evidence=withheld winner-agreement=required');
