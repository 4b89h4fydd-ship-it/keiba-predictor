import assert from 'node:assert/strict';
import {narRows,centralRows,sourceOdds} from '../workers/live_odds.mjs';
const source={id:'nar-2026-10-10-高知-11',date:'2026-10-10',circuit:'地方',track:'高知',raceNumber:11,
  horses:[{horseNumber:1,name:'甲'},{horseNumber:2,name:'乙'},{horseNumber:3,name:'丙'}]};
const html='<h4>単勝・複勝 オッズ（17:45 現在）</h4><table>'+[
  ['1','1','甲','6.2'],['2','2','乙','2.1'],['3','3','丙','取消']
].map(c=>'<tr>'+c.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</table>';
const rows=narRows(html,source);
assert.equal(rows.length,3);assert.equal(rows[0].popularity,2);assert.equal(rows[1].popularity,1);
assert.equal(rows[2].scratched,true);assert.equal(rows[2].win_odds,null);
assert.throws(()=>narRows(html.replace('甲','別馬'),source),/name mismatch/);
const payload={data:{official_datetime:'2026-10-10 14:45:27',odds:{'1':{'01':['4.2','0','2'],'02':['1.8','0','1']}}}};
assert.equal(centralRows(payload,source)[0].popularity,2);
assert.throws(()=>centralRows({data:{odds:{'1':{'99':['1','0','1']}}}},source),/runner mismatch/);
let count=0;
const result=await sourceOdds(source,async url=>{count++;assert.ok(url.startsWith('https://www.keiba.go.jp/'));return new Response(html)});
assert.equal(count,1);assert.equal(result.oddsSource,'NAR公式');
assert.equal(result.sourcePublishedAt,'2026-10-10T17:45:00+09:00');
assert.ok(Date.parse(result.oddsUpdatedAt)>0);
const central={...source,circuit:'中央',netkeibaRaceId:'202605040309'};
const result2=await sourceOdds(central,async url=>{assert.ok(url.startsWith('https://race.netkeiba.com/'));return Response.json(payload)});
assert.equal(result2.sourcePublishedAt,'2026-10-10T14:45:27+09:00');
assert.equal(result2.oddsSource,'netkeiba実オッズ');
await assert.rejects(sourceOdds(source,async()=>new Response('missing')),/not yet published/);
console.log('OFFICIAL_ODDS_IDENTITY_SOURCE_TIME_SCRATCH_RANK_PASS');
