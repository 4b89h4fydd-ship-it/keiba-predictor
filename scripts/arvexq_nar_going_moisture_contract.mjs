import assert from 'node:assert/strict';
import {parseNarGoingMoisture, overlayNarGoingMoisture} from '../workers/nar_going_moisture.mjs';

assert.equal(parseNarGoingMoisture('天候：晴 馬場：1.0'), '1.0');
assert.equal(parseNarGoingMoisture('馬場状態：稍重'), null);
const detail = await overlayNarGoingMoisture(
  {id: 'nar-2026-10-17-帯広ば-01', condition: '不明'},
  async () => new Response('天候：晴　馬場：1.0', {status: 200}),
);
assert.equal(detail.goingMoisture, '1.0');
console.log('NAR_GOING_MOISTURE_CONTRACT_PASS');
