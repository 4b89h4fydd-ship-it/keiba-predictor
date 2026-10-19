function lastCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[p.length-1],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
// Consistent pre-race window: deduplicate first, then take the newest five
// starts. A sixth (older) race cannot substitute for a missing first corner.
