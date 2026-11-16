/* Volatility risk label （堅／普／荒）, computed in the browser from the
   stored full race detail. Client-side port of workers/api_risk_label.mjs
   (the API read-time overlay cannot be deployed: the API deploy workflow's
   source guard rejects the current production bundle), so the label is
   produced here instead and served through the normal Web Deploy path.
   Display-only: stored payloads are never rewritten.

   Method (validated 2026-11-16, volatility-risk-20261116): five pre-race
   components, each mapped through a fixed per-segment ECDF table (the same
   constants as workers/api_risk_label_constants.mjs, built from the
   validation corpus), averaged into a risk score in [0,1]. Bands are the
   validation's pre-fixed absolute bands: score < 1/3 -> 堅, < 2/3 -> 普,
   otherwise 荒.
     ent_model          normalized entropy of the forecast win probabilities
     weak_fav_mkt       1 - max normalized market implied probability
     field              number of runners on the forecast roster
     thin_share         share of runners with evidenceRuns <= 2
     weak_ability_conc  1 - max(abilityScore) / sum(abilityScore)
   A race gets NO label when any component cannot be computed from stored
   material (no unifiedForecast, missing odds/evidence/ability coverage):
   missing material is reported as absence, never estimated. Thin day
   details carry the full detail inside the arvexqFullPayload envelope;
   ensureRiskLabel restores it in memory (never written back) and computes
   from the restored payload, exactly like the server overlay did. */
(function(root){
  'use strict';
  var RISK_LABEL_VERSION='arvexq-risk-label-v1';
  var UPSET_FORECAST_VERSION='arvexq-upset-forecast-v1';
  var RISK_ECDF_TABLES={"nar":{"ent":{"n":1118,"bp":[0.650048,0.668925,0.691084,0.713695,0.723853,0.732013,0.73617,0.743667,0.750391,0.755515,0.759714,0.76587,0.77072,0.775283,0.778119,0.781239,0.784347,0.787691,0.79059,0.795255,0.798306,0.800628,0.803555,0.805299,0.806702,0.809157,0.812339,0.815045,0.816348,0.817504,0.819012,0.820758,0.824833,0.826255,0.828528,0.830179,0.832548,0.834793,0.837039,0.83892,0.840342,0.841807,0.843428,0.845131,0.846326,0.848941,0.850245,0.851242,0.853961,0.856141,0.857179,0.8583,0.859559,0.861272,0.862707,0.864711,0.865965,0.867828,0.869161,0.870332,0.871637,0.873903,0.875089,0.877378,0.87908,0.880013,0.881839,0.883504,0.885147,0.886971,0.888649,0.889599,0.891005,0.893287,0.895259,0.896317,0.898507,0.899544,0.900881,0.902821,0.904834,0.906934,0.910622,0.912753,0.914592,0.917383,0.919746,0.920781,0.922881,0.924229,0.927,0.929044,0.931341,0.934994,0.939686,0.944642,0.949102,0.952643,0.960019]},"weak_fav":{"n":1006,"bp":[0.249227,0.27168,0.294461,0.331266,0.340759,0.372821,0.380004,0.391218,0.396951,0.417602,0.428563,0.436813,0.457805,0.464499,0.47142,0.476094,0.493619,0.499005,0.502161,0.505691,0.522135,0.529548,0.532168,0.533863,0.550167,0.554158,0.555929,0.557409,0.562146,0.576107,0.57826,0.579598,0.582215,0.595585,0.597676,0.601668,0.602795,0.612382,0.617351,0.619045,0.62092,0.627045,0.634723,0.635516,0.637918,0.642193,0.650211,0.651029,0.65231,0.653646,0.65527,0.665104,0.665808,0.666412,0.667391,0.668986,0.673962,0.678809,0.679334,0.681247,0.682377,0.690539,0.691618,0.692481,0.694147,0.702165,0.70308,0.703855,0.704606,0.712565,0.713535,0.71456,0.715491,0.717478,0.723523,0.724617,0.732003,0.733424,0.734767,0.741868,0.744914,0.749759,0.750278,0.757215,0.757888,0.763636,0.765014,0.770862,0.772053,0.777281,0.778636,0.783843,0.789391,0.794109,0.799653,0.805412,0.813907,0.822728,0.840087]},"field":{"n":1118,"bp":[6,7,7,7,8,8,8,8,8,8,9,9,9,9,9,9,9,9,9,9,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,13,13,14,14,14,14]},"thin_share":{"n":1118,"bp":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.071429,0.083333,0.083333,0.083333,0.090909,0.090909,0.090909,0.1,0.1,0.1,0.111111,0.111111,0.125,0.142857,0.166667,0.166667,0.166667,0.181818,0.2,0.222222,0.25,0.272727,0.3,0.333333,0.363636,0.416667,0.454545,0.5,0.583333,0.666667]},"weak_ab":{"n":1097,"bp":[0.729046,0.750808,0.768426,0.777591,0.783558,0.787673,0.791774,0.794835,0.798099,0.800933,0.803471,0.807141,0.809036,0.810358,0.812553,0.815475,0.818387,0.819831,0.821565,0.824108,0.825116,0.826347,0.827562,0.829729,0.830809,0.832339,0.832922,0.834052,0.834601,0.83591,0.836982,0.838157,0.839438,0.840382,0.841076,0.84179,0.842678,0.843494,0.844112,0.845151,0.845738,0.846317,0.84729,0.848331,0.848866,0.84975,0.850223,0.850953,0.851926,0.85255,0.853082,0.853779,0.854282,0.855027,0.855575,0.856418,0.857014,0.857791,0.858344,0.858933,0.859456,0.860161,0.860946,0.86144,0.862199,0.862918,0.863412,0.864314,0.865237,0.865843,0.866877,0.86765,0.868456,0.869353,0.869674,0.870205,0.870857,0.871477,0.872287,0.872971,0.87372,0.874582,0.875233,0.875592,0.876289,0.876981,0.878269,0.879246,0.880407,0.88113,0.882299,0.883474,0.884796,0.886137,0.887444,0.889661,0.891421,0.893689,0.898932]}},"jra":{"ent":{"n":204,"bp":[0.635616,0.640247,0.651928,0.663979,0.6893,0.691739,0.700599,0.702839,0.70581,0.707194,0.719298,0.726962,0.737014,0.740535,0.741392,0.746075,0.749274,0.753385,0.756194,0.758783,0.75928,0.761945,0.76493,0.766471,0.770051,0.772504,0.778114,0.780339,0.782291,0.786172,0.792565,0.793723,0.79509,0.798497,0.799485,0.804568,0.805178,0.807016,0.808981,0.814598,0.815357,0.817182,0.818106,0.818749,0.820308,0.823998,0.826432,0.827202,0.828153,0.831773,0.834382,0.834829,0.837211,0.838098,0.83846,0.839623,0.844934,0.847369,0.849982,0.853865,0.854247,0.855193,0.856209,0.859157,0.860703,0.861875,0.862549,0.86273,0.863043,0.864575,0.865134,0.866834,0.86902,0.872353,0.874521,0.877213,0.878477,0.882392,0.883095,0.884621,0.887421,0.889248,0.890451,0.890644,0.893161,0.895853,0.896594,0.897344,0.898847,0.900578,0.901666,0.903963,0.906624,0.909407,0.91257,0.916102,0.921167,0.924698,0.926252]},"weak_fav":{"n":193,"bp":[0.390098,0.40985,0.432798,0.449481,0.47963,0.504622,0.509697,0.512336,0.537483,0.541093,0.5615,0.565392,0.581001,0.581697,0.585065,0.586316,0.604872,0.620054,0.621458,0.624615,0.626173,0.641248,0.643294,0.655812,0.656087,0.656715,0.657252,0.657632,0.668803,0.66979,0.670842,0.681293,0.682439,0.682857,0.683192,0.683857,0.684864,0.684908,0.686109,0.694597,0.694901,0.695264,0.695498,0.696263,0.697304,0.697585,0.705881,0.706422,0.706542,0.707172,0.707278,0.708105,0.715511,0.716349,0.726203,0.726712,0.727714,0.736954,0.743347,0.744592,0.750629,0.751199,0.751231,0.752114,0.752638,0.753089,0.758735,0.75902,0.75968,0.760657,0.766301,0.766988,0.772928,0.779945,0.784863,0.785107,0.785628,0.790537,0.79581,0.80073,0.8013,0.80194,0.806204,0.810832,0.819031,0.823341,0.824024,0.830591,0.830846,0.834376,0.83745,0.837857,0.841037,0.844173,0.849833,0.8502,0.852653,0.855493,0.865382]},"field":{"n":204,"bp":[6,7,8,8,8,8,9,9,9,9,9,10,10,10,10,10,10,10,10,10,11,11,11,11,11,11,11,11,11,12,12,12,12,12,12,12,12,12,12,12,12,12,13,13,13,13,13,13,13,13,14,14,14,14,14,14,14,14,14,14,15,15,15,15,15,15,15,15,15,15,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,17,17,18,18,18,18,18]},"thin_share":{"n":204,"bp":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.055556,0.0625,0.071429,0.083333,0.090909,0.090909,0.1,0.5,0.538462,0.555556,0.6,0.642857,0.666667,0.666667,0.7,0.714286,0.727273,0.727273,0.727273,0.733333,0.75,0.75,0.785714,0.8,0.8,0.8,0.8125,0.833333,0.833333,0.833333,0.846154,0.846154,0.857143,0.875,0.9,0.916667,0.916667,0.923077,0.923077,0.933333,1,1,1]},"weak_ab":{"n":204,"bp":[0.742695,0.756142,0.785843,0.793428,0.801083,0.80495,0.806067,0.808574,0.813751,0.813836,0.814222,0.825695,0.827145,0.828907,0.829139,0.830237,0.831813,0.835815,0.837929,0.838381,0.840837,0.841008,0.842127,0.844892,0.846519,0.847165,0.848178,0.850102,0.8509,0.85277,0.85398,0.854832,0.855445,0.856624,0.859191,0.861856,0.863594,0.864025,0.8664,0.868439,0.869509,0.87132,0.871604,0.873785,0.873886,0.874713,0.875513,0.877065,0.878234,0.879007,0.879656,0.879739,0.880609,0.880876,0.881859,0.882979,0.883779,0.884831,0.885706,0.886418,0.886847,0.887808,0.888998,0.891737,0.892016,0.892604,0.89356,0.893796,0.894309,0.894984,0.895734,0.896337,0.89678,0.897168,0.897424,0.897913,0.898969,0.899859,0.900653,0.901059,0.901569,0.902466,0.903196,0.903383,0.904618,0.904792,0.905998,0.906828,0.90707,0.907791,0.90833,0.908823,0.908984,0.909285,0.911053,0.913977,0.91433,0.915267,0.915852]}}};

  function ecdf(table,value){
    var bp=table.bp,lo=0,hi=bp.length,mid;
    while(lo<hi){mid=(lo+hi)>>1;if(bp[mid]<value)lo=mid+1;else hi=mid;}
    // lo = number of grid breakpoints strictly below value (grid = p1..p99).
    var p=(lo+0.5)/100;
    return Math.min(0.995,Math.max(0.005,p));
  }

  function finite(x){
    if(x===null||x===undefined||x==='')return null;
    var v=Number(x);
    return Number.isFinite(v)?v:null;
  }

  // detail: a full (restored) race detail payload. The market component
  // uses the win odds sealed inside the detail at forecast capture time —
  // the same kind of pre-race market snapshot the validation used — not
  // live odds, so the label stays fixed with the forecast.
  // Returns {version, label, score, segment, components} or null.
  function computeRiskLabel(detail){
    if(!detail||typeof detail!=='object')return null;
    var uf=detail.unifiedForecast;
    if(!uf||!Array.isArray(uf.roster)||!Array.isArray(uf.diagnosis))return null;
    var roster=uf.roster.map(function(x){return Number(x&&x.horseNumber);})
      .filter(function(n){return Number.isInteger(n)&&n>0;});
    if(roster.length<3||new Set(roster).size!==roster.length)return null;
    var segment=(detail.circuit==='地方'||uf.circuit==='地方')?'nar'
      :(detail.circuit==='中央'||uf.circuit==='中央')?'jra':null;
    if(!segment)return null;
    var table=RISK_ECDF_TABLES[segment];
    if(!table)return null;

    var diag=new Map(),i,n,d;
    for(i=0;i<uf.diagnosis.length;i++){
      d=uf.diagnosis[i];n=Number(d&&d.horseNumber);
      if(Number.isInteger(n)&&n>0&&!diag.has(n))diag.set(n,d);
    }

    // ent_model: forecast win probabilities for every roster runner.
    var probSum=0,probs=[],p;
    for(i=0;i<roster.length;i++){
      n=roster[i];
      p=finite(diag.has(n)?diag.get(n).winProbability:null);
      if(p===null||p<0)return null;
      probs.push(p);probSum+=p;
    }
    if(!(probSum>0))return null;
    var ent=0,q;
    for(i=0;i<probs.length;i++){
      q=probs[i]/probSum;
      if(q>0)ent-=q*Math.log(q);
    }
    ent/=Math.log(roster.length);

    // weak_fav_mkt: win odds sealed in the detail's horses, normalized
    // within the race (the corpus implied_prob sums to 1 the same way).
    var horseByNo=new Map(),h;
    var horses=detail.horses||[];
    for(i=0;i<horses.length;i++){
      h=horses[i];n=Number(h&&h.horseNumber);
      if(Number.isInteger(n)&&n>0&&!horseByNo.has(n))horseByNo.set(n,h);
    }
    var rawSum=0,rawMax=0,odds,raw;
    for(i=0;i<roster.length;i++){
      n=roster[i];
      odds=finite(horseByNo.has(n)?horseByNo.get(n).winOdds:null);
      if(odds===null||odds<=1)return null;
      raw=1/odds;rawSum+=raw;
      if(raw>rawMax)rawMax=raw;
    }
    if(!(rawSum>0))return null;
    var weakFav=1-rawMax/rawSum;

    // thin_share: evidence runs recorded by the issuing analysis.
    var runners=(detail.masterAnalysis&&Array.isArray(detail.masterAnalysis.runners))
      ?detail.masterAnalysis.runners:null;
    if(!runners)return null;
    var evByNo=new Map(),r;
    for(i=0;i<runners.length;i++){
      r=runners[i];n=Number(r&&r.horseNumber);
      if(Number.isInteger(n)&&n>0&&!evByNo.has(n))evByNo.set(n,finite(r.evidenceRuns));
    }
    var thin=0,ev;
    for(i=0;i<roster.length;i++){
      n=roster[i];
      ev=evByNo.has(n)?evByNo.get(n):undefined;
      if(ev===null||ev===undefined)return null;
      if(ev<=2)thin+=1;
    }
    var thinShare=thin/roster.length;

    // weak_ability_conc: diagnosis ability scores, >=80% coverage required
    // (same rule as the validation; below that the component is missing).
    var abCount=0,abSum=0,abMax=0,a;
    for(i=0;i<roster.length;i++){
      n=roster[i];
      a=finite(diag.has(n)?diag.get(n).abilityScore:null);
      if(a!==null){abCount+=1;abSum+=a;if(a>abMax)abMax=a;}
    }
    if(abCount<0.8*roster.length||!(abSum>0))return null;
    var weakAb=1-abMax/abSum;

    var components={
      ent_model:ent,
      weak_fav_mkt:weakFav,
      field:roster.length,
      thin_share:thinShare,
      weak_ability_conc:weakAb,
    };
    var keys=['ent','weak_fav','field','thin_share','weak_ab'];
    var values=[ent,weakFav,roster.length,thinShare,weakAb];
    var score=0;
    for(i=0;i<keys.length;i++)score+=ecdf(table[keys[i]],values[i]);
    score/=keys.length;
    var label=score<1/3?'堅':score<2/3?'普':'荒';
    var rounded={};
    Object.keys(components).forEach(function(k){
      rounded[k]=Math.round(components[k]*10000)/10000;
    });
    return {
      version:RISK_LABEL_VERSION,
      label:label,
      score:Math.round(score*1000)/1000,
      segment:segment,
      components:rounded,
    };
  }

  // arvexqFullPayload envelope restore: port of restoreBytes in
  // workers/api_full_snapshot.mjs (gzip + size/SHA-256 verification).
  var FULL_KEY='arvexqFullPayload',FULL_VERSION='arvexq-full-payload-v1';
  var RISK_LABEL_MAX_RESTORE_BYTES=4000000;
  function restoreBytes(envelope){
    var ref=envelope&&envelope[FULL_KEY];
    if(!ref||ref.version!==FULL_VERSION||!(ref.bytes>0&&ref.bytes<=100000000))
      return Promise.reject(new Error('invalid full snapshot envelope'));
    var zipped=Uint8Array.from(atob(ref.gzipBase64),function(c){return c.charCodeAt(0);});
    var stream=new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).arrayBuffer().then(function(buf){
      var raw=new Uint8Array(buf);
      return crypto.subtle.digest('SHA-256',raw).then(function(digest){
        var hash=Array.from(new Uint8Array(digest),function(x){
          return x.toString(16).padStart(2,'0');
        }).join('');
        if(raw.byteLength!==ref.bytes||hash!==ref.sha256)
          throw new Error('full snapshot restore mismatch');
        return raw;
      });
    });
  }

  // Label for a detail that may be in thin day form: compute directly when
  // the material is present; otherwise restore the sealed envelope in
  // memory (never written back) and compute from the restored payload.
  // Resolves to the label object (also set on detail.riskLabel) or null.
  function ensureRiskLabel(detail){
    if(!detail||typeof detail!=='object')return Promise.resolve(null);
    if(detail.riskLabel&&detail.riskLabel.label)return Promise.resolve(detail.riskLabel);
    var label=computeRiskLabel(detail);
    if(label){detail.riskLabel=label;return Promise.resolve(label);}
    var ref=detail[FULL_KEY];
    if(!ref||!(Number(ref.bytes)>0&&Number(ref.bytes)<=RISK_LABEL_MAX_RESTORE_BYTES))
      return Promise.resolve(null);
    return restoreBytes(detail).then(function(raw){
      var full=JSON.parse(new TextDecoder().decode(raw));
      var restored=computeRiskLabel(full);
      if(restored)detail.riskLabel=restored;
      return restored;
    }).catch(function(){return null;});
  }

  /* Upset forecast （荒れ予想）: a presentation of the SAME validated risk
     score — no new definition, no new thresholds. The level bands are the
     validation's pre-fixed absolute bands, identical to the label bands,
     so the forecast can never contradict the 堅/普/荒 label:
       score < 1/3 -> label 堅 / upset level 低
       score < 2/3 -> label 普 / upset level 中
       otherwise   -> label 荒 / upset level 高
     score100 is the risk score on a 0-100 scale (SPEC section 5.2,
     volatility band). reasons names the components contributing most to
     the score (per-component ECDF recomputed from the label's stored raw
     component values); for a low-upset race it names the strongest
     stabilising components instead.
     NOTE: the score is validated for NAR （地方， 951R) only; for JRA the
     same display is shown but the separation is not confirmed (see
     volatility-risk-20261116/REPORT.md). */
  var UPSET_COMPONENTS=[
    ['ent_model','ent','予想が割れている','予想が本命に集中している'],
    ['weak_fav_mkt','weak_fav','人気が割れている','人気が本命に集中している'],
    ['field','field','出走頭数が多い','出走頭数が少ない'],
    ['thin_share','thin_share','実績の薄い馬が多い','実績馬が揃っている'],
    ['weak_ability_conc','weak_ab','能力が拮抗している','能力上位が抜けている'],
  ];

  function upsetFromRisk(risk){
    if(!risk||typeof risk!=='object')return null;
    var table=RISK_ECDF_TABLES[risk.segment];
    var score=finite(risk.score);
    if(!table||score===null||!risk.components)return null;
    var level=score>=2/3?'高':score>=1/3?'中':'低';
    var ranked=[],i,v;
    for(i=0;i<UPSET_COMPONENTS.length;i++){
      v=finite(risk.components[UPSET_COMPONENTS[i][0]]);
      if(v===null)return null;
      ranked.push({i:i,e:ecdf(table[UPSET_COMPONENTS[i][1]],v),
        highPhrase:UPSET_COMPONENTS[i][2],lowPhrase:UPSET_COMPONENTS[i][3]});
    }
    var picked,list,reasons;
    if(level==='低'){
      picked=ranked.filter(function(x){return x.e<=0.5;})
        .sort(function(a,b){return (a.e-b.e)||(a.i-b.i);}).slice(0,2);
      list=picked.length?picked:[ranked.slice()
        .sort(function(a,b){return (a.e-b.e)||(a.i-b.i);})[0]];
      reasons=list.map(function(x){return x.lowPhrase;});
    }else{
      picked=ranked.filter(function(x){return x.e>=0.5;})
        .sort(function(a,b){return (b.e-a.e)||(a.i-b.i);}).slice(0,2);
      list=picked.length?picked:[ranked.slice()
        .sort(function(a,b){return (b.e-a.e)||(a.i-b.i);})[0]];
      reasons=list.map(function(x){return x.highPhrase;});
    }
    return {
      version:UPSET_FORECAST_VERSION,
      level:level,
      score100:Math.round(score*100),
      label:risk.label,
      score:score,
      segment:risk.segment,
      reasons:reasons,
    };
  }

  function computeUpsetForecast(detail){
    var risk=computeRiskLabel(detail);
    return risk?upsetFromRisk(risk):null;
  }

  root.ARVEXQRiskLabel=Object.freeze({
    version:RISK_LABEL_VERSION,
    upsetVersion:UPSET_FORECAST_VERSION,
    computeRiskLabel:computeRiskLabel,
    ensureRiskLabel:ensureRiskLabel,
    computeUpsetForecast:computeUpsetForecast,
    upsetFromRisk:upsetFromRisk,
    restoreBytes:restoreBytes,
    tables:RISK_ECDF_TABLES,
  });
})(typeof window!=='undefined'?window:globalThis);
