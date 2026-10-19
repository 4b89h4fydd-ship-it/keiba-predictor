function recentFinishScore(h){var rs=(h.allPastRuns||h.recentRaces||[]),w=recencyWeights(rs.length),v=[],i;for(i=0;i<rs.length;i++)v.push(runFinishQuality(rs[i]));return weightedRate(v,w,.45)}
