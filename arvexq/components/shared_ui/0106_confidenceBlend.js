function confidenceBlend(score,count){var q=clamp(n(count)/3,0,1);return .5*(1-q)+score*q}
