'use strict';
const assert=require('node:assert/strict');
module.exports=function verifyHonmeiRoles(rows,raceId,options={}){
  const wins=rows.filter(x=>x.win),axes=rows.filter(x=>x.axis),visible=rows.filter(x=>x.mark==='◎');
  assert(wins.length<=1,'duplicate win role '+raceId);
  assert(axes.length<=1,'duplicate podium-axis role '+raceId);
  if(options.legacyPolicy===true){
    assert(visible.length<=2,'too many visible honmei runners '+raceId);
    if(visible.length>1){
      assert.equal(wins.length,1,'multiple honmei without unique win role '+raceId);
      assert.equal(axes.length,1,'multiple honmei without unique axis role '+raceId);
      assert(visible.every(x=>x.win||x.axis),'untyped duplicate honmei '+raceId);
    }
    return;
  }
  const original=options.originalHonmeiHorseNumbers||[];
  if(visible.length>1&&original.length>1){
    assert.deepEqual(visible.map(x=>x.horseNumber).sort((a,b)=>a-b),[...original].sort((a,b)=>a-b),
      'historical honmei differ from immutable original '+raceId);
    return;
  }
  assert(visible.length<=1,'multiple unified honmei '+raceId);
  if(wins.length&&axes.length)assert.equal(wins[0],axes[0],'winning and axis roles must share the same horse '+raceId);
};
