function minetaStructureText(ctx){
  if(!ctx)return'';
  var bits=['先行占有 '+Math.round(ctx.rawOcc*100)+'%','距離補正後 '+Math.round(ctx.adjustedOcc*100)+'%','後方占有 '+Math.round(ctx.rearOcc*100)+'%'];
  if(ctx.band==='前少なめ')bits.push('前残りだけでなく強い先行馬を目標にする外の馬も重視');
  else if(ctx.band==='前多め')bits.push('競り合い消耗・内外・同脚質並び・差し巻き返しを重視');
  else bits.push('隊列・並び・逃げ挟み・同脚質の塊の隣を重視');
  return bits.join('｜')
}
