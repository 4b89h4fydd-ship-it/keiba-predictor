function runFinishQuality(rr){var f=n(rr.finish,0),fs=raceField(rr);if(!f)return.45;return clamp(1-(f-1)/Math.max(3,fs-1),0,1)}
