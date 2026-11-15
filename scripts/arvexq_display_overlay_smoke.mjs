// Smoke test for the display overlay (weather/condition + oddsUpdatedAt).
// Pure-function checks only; no network or D1 access.
import assert from 'node:assert/strict';
import {overlayDisplayFields, overlayRaceResponse, overlayDayResponse} from '../workers/api_display_overlay.mjs';

// 1) Summary with known weather/condition overrides a stale snapshot detail.
{
  const detail = {id: 'r1', weather: '不明', condition: '不明', oddsUpdatedAt: '00:02:45'};
  overlayDisplayFields(detail, {weather: '晴', condition: '良'}, null);
  assert.equal(detail.weather, '晴');
  assert.equal(detail.condition, '良');
  assert.equal(detail.oddsUpdatedAt, '00:02:45', 'no live odds rows -> snapshot stamp kept');
}

// 2) Unknown summary values never erase a known detail value.
{
  const detail = {id: 'r2', weather: '雨', condition: '重', oddsUpdatedAt: '09:00:00'};
  overlayDisplayFields(detail, {weather: '不明', condition: ''}, null);
  assert.equal(detail.weather, '雨');
  assert.equal(detail.condition, '重');
}

// 3) oddsUpdatedAt follows the newest odds_current capture (epoch -> JST clock).
{
  const detail = {id: 'r3', weather: '不明', condition: '不明', oddsUpdatedAt: '15:35:45'};
  // 2026-11-13 10:21:30 JST == 1794532890 epoch seconds.
  overlayDisplayFields(detail, null, 1794532890);
  assert.equal(detail.oddsUpdatedAt, '10:21:30');
}

// 4) Race response overlay uses the summary + odds rows travelling with it.
{
  const body = {
    ok: true,
    race_id: 'r4',
    summary: {weather: '晴', condition: '良'},
    detail: {id: 'r4', weather: '不明', condition: '不明', oddsUpdatedAt: '00:02:45', prediction: {sealed: true}},
    odds: [{horse_no: 1, updated_at: 1794495773}, {horse_no: 2, updated_at: 1794532890}],
  };
  const res = new Response(JSON.stringify(body), {headers: {'content-type': 'application/json'}});
  const out = await overlayRaceResponse(res);
  const patched = await out.json();
  assert.equal(patched.detail.weather, '晴');
  assert.equal(patched.detail.condition, '良');
  assert.equal(patched.detail.oddsUpdatedAt, '10:21:30');
  assert.deepEqual(patched.detail.prediction, {sealed: true}, 'sealed forecast untouched');
}

// 5) Day response overlay: per-race summary wins; odds max comes from D1 aggregate.
{
  const body = {
    ok: true,
    date: '2026-11-13',
    races: [{id: 'r5', weather: '晴', condition: '良'}, {id: 'r6', weather: '不明', condition: '不明'}],
    details: [
      {id: 'r5', weather: '不明', condition: '不明', oddsUpdatedAt: '00:03:00'},
      {id: 'r6', weather: '不明', condition: '不明', oddsUpdatedAt: '00:03:00'},
    ],
  };
  const env = {DB: {prepare(sql) {
    assert.match(sql, /MAX\(o\.updated_at\)/);
    return {bind(date) {
      assert.equal(date, '2026-11-13');
      return {all: async () => ({results: [{race_id: 'r5', max_at: 1794532890}]})};
    }};
  }}};
  const res = new Response(JSON.stringify(body), {headers: {'content-type': 'application/json'}});
  const out = await overlayDayResponse(res, env, new URL('https://example.invalid/api/day?date=2026-11-13'));
  const patched = await out.json();
  assert.equal(patched.details[0].weather, '晴');
  assert.equal(patched.details[0].oddsUpdatedAt, '10:21:30');
  assert.equal(patched.details[1].weather, '不明', 'summary unknown -> detail kept');
  assert.equal(patched.details[1].oddsUpdatedAt, '00:03:00', 'no live rows -> snapshot stamp kept');
}

// 6) details=0 day responses pass through untouched.
{
  const res = new Response(JSON.stringify({ok: true, details: []}), {headers: {'content-type': 'application/json'}});
  const out = await overlayDayResponse(res, {DB: {prepare() { throw new Error('must not query'); }}}, new URL('https://example.invalid/api/day?date=2026-11-13&details=0'));
  assert.equal(out, res);
}

console.log('DISPLAY_OVERLAY_SMOKE_PASS');
