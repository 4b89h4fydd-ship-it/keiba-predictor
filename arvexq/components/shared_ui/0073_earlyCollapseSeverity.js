function earlyCollapseSeverity(h,r){var rs=historicalWindow(h,r),w=recencyWeights(rs.length),vals=[],ws=[],i,p,a,fin,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||a>4||!fin)continue;vals.push(clamp((fin-a)/Math.max(3,fs-1),0,1));ws.push(w[i])}return weightedRate(vals,ws,.18)}
// v244: same-day live track bias.  Use ONLY races already run at the same venue/date.
// It is intentionally market-independent and shrunk hard toward neutral when sample size is small.
