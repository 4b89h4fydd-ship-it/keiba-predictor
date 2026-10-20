function expectedValueRaceProfile(r,p){
  var rows=(p&&p.rows||[]).slice(),field=rows.length,cov=n(p&&p.coverage,0),uniform=1/Math.max(1,field),ready=dataReadinessProfile(r,p),strict=strictSelectedRaceProfile(r,p),method=arvexqRacePolicy(r),vg=method.value;
  if(!strict.selected)return{selected:false,score:0,reason:'厳選品質ゲート未通過',readiness:ready,selection:strict,model:method.id};
  if(field<5||cov<vg.cov||ready.prediction<vg.ready)return{selected:false,score:0,reason:'予想データ不足',readiness:ready,selection:strict,model:method.id};
  var actual=rows.filter(function(x){var h=x.horse||{};return n(h.winOdds)>1&&!h.oddsForecast&&!/予想|forecast/i.test(String(h.oddsSource||''))}),need=Math.max(4,Math.ceil(field*vg.oddsCoverage));
  if(actual.length<need)return{selected:false,score:0,reason:'実オッズ待ち',mode:'actual',readiness:ready,selection:strict,model:method.id};
  var candidates=rows.map(function(x){
    var h=x.horse||{},odds=n(h.winOdds,0),forecast=!!h.oddsForecast||/予想|forecast/i.test(String(h.oddsSource||'')),pwin=n(x.evWinProbability,n(x.winnerDecisionProbability,n(x.p1Probability,0))),ev=odds>1?pwin*odds:0,
        kelly=(odds>1&&ev>1)?(ev-1)/(odds-1):0,edge=n(x.edgeScore,0),evidence=n(x.edgeEvidence,0),rank=n(x.winnerDecisionRank,n(x.winnerConsensusRank,n(x.winRank,999)));
    return{x:x,odds:odds,pwin:pwin,ev:ev,kelly:kelly,edge:edge,evidence:evidence,rank:rank,forecast:forecast}
  }).filter(function(z){return !z.forecast&&z.odds>1&&z.ev>=vg.ev&&z.edge>=vg.edge&&z.evidence>=vg.evidence&&z.kelly>=vg.kelly&&z.pwin>=Math.max(.055,uniform*.72)&&z.rank<=2}).sort(function(a,b){return b.ev-a.ev||b.kelly-a.kelly||b.edge-a.edge||b.pwin-a.pwin});
  if(!candidates.length)return{selected:false,score:0,reason:'実オッズ期待値基準未達',mode:'actual',readiness:ready,selection:strict,model:method.id};
  var best=candidates[0],evEdge=best.ev-1,score=Math.round(clamp(clamp(evEdge/.65,0,1)*.40+clamp((best.edge-60)/32,0,1)*.21+best.evidence*.15+ready.market*.12+clamp(best.kelly/.10,0,1)*.08+clamp(best.pwin/Math.max(uniform*2,.12),0,1)*.04,0,1)*100),selected=score>=vg.score;
  return{selected:selected,score:score,horse:best.x.horse,horseNo:n(best.x.horse&&best.x.horse.horseNumber),horseName:String(best.x.horse&&best.x.horse.name||''),odds:best.odds,pwin:best.pwin,ev:best.ev,kelly:best.kelly,riskFraction:Math.min(.02,best.kelly*.20),edge:best.edge,evidence:best.evidence,coverage:cov,mode:'actual',readiness:ready,selection:strict,reason:selected?'買い目品質ゲート通過':'買い目品質スコア不足',model:method.id+'-actual-odds'}
}
