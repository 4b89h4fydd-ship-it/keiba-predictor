'use strict';
const assert=require('node:assert/strict');
module.exports=function verifyHonmeiRoles(rows,raceId){
  const wins=rows.filter(x=>x.win),axes=rows.filter(x=>x.axis),visible=rows.filter(x=>x.mark==='◎');
  assert(wins.length<=1,'duplicate win role '+raceId);
  assert(axes.length<=1,'duplicate podium-axis role '+raceId);
  assert(visible.length<=2,'too many visible honmei runners '+raceId);
  if(visible.length>1){
    assert.equal(wins.length,1,'multiple honmei without unique win role '+raceId);
    assert.equal(axes.length,1,'multiple honmei without unique axis role '+raceId);
    assert(visible.every(x=>x.win||x.axis),'untyped duplicate honmei '+raceId);
  }
};
