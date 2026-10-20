function smartVal(v){if(v==null||v==='')return'—';var x=Number(v);if(isFinite(x))return (Math.round(x*10)/10).toString();return String(v)}
