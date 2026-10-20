function firstCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[0],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
