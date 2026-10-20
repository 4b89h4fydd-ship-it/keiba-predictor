function trendResultReady(r){var d=resultDetailForTrend(r);return !!(d&&d.result&&(d.result.finishers||[]).some(function(x){return n(x&&x.finish)>0}))}
