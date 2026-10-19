function winOddsText(h){var v=h&&h.winOdds;if(v==null||v===''||Number(v)<=0)return'—';var x=Number(v);return isFinite(x)?(Math.round(x*10)/10).toFixed(1):String(v)}
// A rank saved at a different market timestamp must never be paired with new
// displayed odds. Derive popularity only from a complete, homogeneous visible
// win-odds field; otherwise show 未取得 rather than an incorrect old rank.
