/* Integrated おすすめ買い目 (user order 2026-11-04): ONE recommendation
   built deterministically from the stored payload's frozen fields —
   final win / top-3 probabilities, marks, win-EV presence, the
   combined gate's qualifiers (注) and diagnosis grades. The forecast
   is never recomputed here: the same payload always yields the same
   recommendation, and a payload upgraded later (place-ev-upgrade
   adding combinedPicks) yields the upgraded recommendation by design.
   Construction rules are documented in
   hidden_files/ui-rework-20261104/integrated-osusume-rules-20261104.md
   (kept with the goal's records). */
(function(root){
'use strict';
var TOTAL_CAP=44;
var FLOOR={'馬単':2,'馬連':3,'ワイド':4,'3連複':5,'3連単':12};
var KIND_ORDER=['ワイド','馬連','馬単','3連複','3連単'];

function num(x){var v=Number(x);return Number.isFinite(v)?v:null;}
function esc(x){
 return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;')
   .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function build(detail){
 var uf=detail&&detail.unifiedForecast;
 if(!uf)return null;
 /* Universe: every active runner with a frozen win probability.
    diagnosis carries all runners; marks are merged in as a fallback
    source. A horse without a win probability cannot be ranked and
    is left out (never imputed). */
 var rows=[],seen={};
 function add(no,win,top3){
   if(!Number.isInteger(no)||no<=0||seen[no]||win==null)return;
   seen[no]=1;rows.push({no:no,win:win,top3:top3});
 }
 if(Array.isArray(uf.diagnosis))uf.diagnosis.forEach(function(d){
   if(d)add(Number(d.horseNumber),num(d.winProbability),num(d.top3Probability));
 });
 if(Array.isArray(uf.marks))uf.marks.forEach(function(m){
   if(m)add(Number(m.horseNumber),num(m.winProbability),num(m.top3Probability));
 });
 if(rows.length<3)return null;
 var byNo={};rows.forEach(function(r){byNo[r.no]=r;});
 var grades={};
 if(Array.isArray(uf.diagnosis))uf.diagnosis.forEach(function(d){
   if(d&&d.grade)grades[Number(d.horseNumber)]=String(d.grade);
 });
 /* Marks: symbol + attention, and the mark order itself (the order
    the payload lists them: ◎○▲△☆). */
 var markOf={},markOrder=[];
 function noteMark(no,symbol,attention){
   if(!Number.isInteger(no)||no<=0||!byNo[no])return;
   if(symbol&&!markOf[no]){markOf[no]=symbol;markOrder.push(no);}
   if(attention===true)markOf[no+'#att']=true;
 }
 if(Array.isArray(detail.predictionMarks))detail.predictionMarks.forEach(function(m){
   if(m)noteMark(Number(m.horseNumber),String(m.mark||''),m.attention===true);
 });
 if(Array.isArray(uf.marks))uf.marks.forEach(function(m){
   if(m)noteMark(Number(m.horseNumber),String(m.markSymbol||''),m.attention===true);
 });
 /* 注 qualifiers (single source: ticketPlan.combinedPicks, plus any
    mark entry already flagged attention). */
 var tp=uf.ticketPlan||{};
 var Q=[],qSet={};
 function addQ(no){
   if(Number.isInteger(no)&&no>0&&byNo[no]&&!qSet[no]){qSet[no]=1;Q.push(no);}
 }
 if(Array.isArray(tp.combinedPicks))tp.combinedPicks.forEach(function(v){addQ(Number(v));});
 Object.keys(markOf).forEach(function(k){
   if(k.slice(-4)==='#att')addQ(Number(k.slice(0,-4)));
 });
 /* Rankings: probability desc, horse number asc on ties. A missing
    top-3 probability ranks below every measured one. */
 function rank(key){
   return rows.slice().sort(function(a,b){
     var av=a[key],bv=b[key];
     if(av==null&&bv==null)return a.no-b.no;
     if(av==null)return 1;
     if(bv==null)return -1;
     return bv-av||a.no-b.no;
   }).map(function(r){return r.no;});
 }
 var W=rank('win'),T=rank('top3');
 var wRank={};W.forEach(function(no,i){wRank[no]=i;});
 function pool(base,extra){
   var out=base.slice();
   (extra||[]).forEach(function(no){if(out.indexOf(no)<0)out.push(no);});
   return out;
 }
 var A=W.slice(0,Math.min(2,rows.length-1));
 var P=pool(T.slice(0,Math.min(5,rows.length)),Q);
 var W4=pool(W.slice(0,Math.min(4,rows.length)),Q);
 var W3=W.slice(0,Math.min(3,rows.length));
 /* --- ticket construction ------------------------------------- */
 function unorderedPairs(axes,partners){
   var out=[],done={};
   axes.forEach(function(a){
     partners.forEach(function(p){
       if(p===a)return;
       var key=Math.min(a,p)+'-'+Math.max(a,p);
       if(done[key])return;
       done[key]=1;out.push([a,p]);
     });
   });
   return out;
 }
 var wide=unorderedPairs(A,P);
 var umaren=unorderedPairs(A,W4);
 var umatan=[];
 A.forEach(function(a){
   W3.forEach(function(q){if(q!==a)umatan.push([a,q]);});
 });
 var trioPool=pool(A,P),trios=[];
 (function(){
   for(var i=0;i<trioPool.length;i++)for(var j=i+1;j<trioPool.length;j++)
     for(var k=j+1;k<trioPool.length;k++){
       var c=[trioPool[i],trioPool[j],trioPool[k]];
       if(!c.some(function(no){return A.indexOf(no)>=0;}))continue;
       c.sort(function(x,y){return (wRank[x]-wRank[y])||x-y;});
       trios.push(c);
     }
 })();
 /* 3連単: R24 skeleton (1st = mark ranks 1-2; the production
    recommendation since the user order of 2026-11-08) with the
    one documented deviation — the 2nd/3rd legs are the top-4 by
    top-3 probability plus every 注 qualifier, not mark ranks 1-5. */
 var firstLeg=markOrder.slice(0,2);
 if(firstLeg.length<2)firstLeg=W.slice(0,2);
 var placePool=pool(T.slice(0,Math.min(4,rows.length)),Q);
 var trifecta=[];
 if(rows.length>=3)firstLeg.forEach(function(f){
   placePool.forEach(function(s){
     if(s===f)return;
     placePool.forEach(function(t){
       if(t===f||t===s)return;
       trifecta.push([f,s,t]);
     });
   });
 });
 var groups=[
   {kind:'ワイド',combos:wide},
   {kind:'馬連',combos:umaren},
   {kind:'馬単',combos:umatan},
   {kind:'3連複',combos:trios},
   {kind:'3連単',combos:trifecta}
 ].filter(function(g){return g.combos.length>0;});
 /* --- point cap: trim weakest first, 注 combos protected ------- */
 function t3(no){var r=byNo[no];return r&&r.top3!=null?r.top3:0;}
 function wn(no){return byNo[no].win;}
 var total=groups.reduce(function(s,g){return s+g.combos.length;},0);
 var trimmed=0;
 function droppable(kind,combos){
   var scorer={
     '馬単':function(c){return wn(c[1]);},
     '馬連':function(c){return Math.min(wn(c[0]),wn(c[1]));},
     'ワイド':function(c){return t3(c[0])+t3(c[1]);},
     '3連複':function(c){
       var axes=c.filter(function(no){return A.indexOf(no)>=0;}).length;
       var hasQ=c.some(function(no){return qSet[no];});
       return (axes===1&&!hasQ?0:100)+(t3(c[0])+t3(c[1])+t3(c[2]));
     },
     '3連単':function(c){
       if(c[0]!==W[1])return null;
       return t3(c[1])+t3(c[2]);
     }
   }[kind];
   return combos.map(function(c,i){return {i:i,score:scorer(c),
     prot:c.some(function(no){return !!qSet[no];})};})
     .filter(function(x){return x.score!=null;})
     .sort(function(a,b){
       return (a.prot-b.prot)||(a.score-b.score)||(a.i-b.i);
     });
 }
 ['馬単','馬連','ワイド','3連複','3連単'].forEach(function(kind){
   if(total<=TOTAL_CAP)return;
   var g=groups.filter(function(x){return x.kind===kind;})[0];
   if(!g)return;
   var floor=FLOOR[kind]||0;
   var cand=droppable(kind,g.combos);
   while(total>TOTAL_CAP&&g.combos.length>floor&&cand.length){
     var drop=cand.shift();
     g.combos.splice(drop.i,1);
     cand.forEach(function(x){if(x.i>drop.i)x.i--;});
     total--;trimmed++;
   }
 });
 groups.forEach(function(g){g.points=g.combos.length;});
 /* --- reason text (plain, no performance claims) ---------------- */
 var names={};
 (uf.roster||[]).forEach(function(h){if(h)names[h.horseNumber]=h.name||'';});
 function label(no){
   var s=no+'番';
   if(markOf[no])s+=markOf[no];
   if(qSet[no])s+='（注）';
   if(grades[no])s+='・評価'+grades[no];
   return s;
 }
 var notes=[];
 var reason='軸は勝率上位の'+A.map(function(no){return no+'番';}).join('・')+'。';
 if(A.length>=2)reason+='軸を2頭に分けたので、1頭が崩れても買い目は残ります。';
 reason+='相手は3着内率の上位を中心に組みました。';
 if(Q.length)reason+='複合ゲート（単勝・3着内の両期待値）を通過した'+
   Q.map(function(no){return no+'番';}).join('・')+'（注）は、順位に関係なく相手に入れています。';
 var mechTri=null;
 (detail.recommendedBets||[]).forEach(function(x){
   if(x&&x.kind==='3連単')mechTri=Number(x.points)||null;
 });
 if(trifecta.length)reason+='3連単は印順位1・2位を1着脚（R24）に、2・3着の脚を3着内率上位4頭と注に絞りました'+
   (mechTri&&mechTri!==trifecta.length?'（従来セットの'+mechTri+'点から'+trifecta.length+'点）':'')+'。';
 var hasPlace=Array.isArray(tp.placeExpectedValues);
 var hasWinEv=Array.isArray(tp.winExpectedValues)&&tp.winExpectedValues.length>0;
 if(!hasPlace)notes.push('複勝オッズ未取得のため、注（複合ゲート）の判定材料はありません。確率と印のみで構成しています。');
 if(!hasWinEv)notes.push('単勝期待値の材料がないため、確率と印のみで構成しています。');
 if(trimmed>0)notes.push('点数上限（'+TOTAL_CAP+'点）に合わせ、根拠の弱い組み合わせから'+trimmed+'点を削りました。');
 return {
   groups:groups,totalPoints:total,
   axes:A.slice(),partners:P.slice(),winPartners:W4.slice(),
   qualifiers:Q.slice(),notes:notes,reason:reason,
   label:label,names:names,markOf:markOf,grades:grades,
   degraded:{noPlace:!hasPlace,noWinEv:!hasWinEv},trimmed:trimmed
 };
}

function fallbackCombos(item){
 return (item.combos||[]).map(function(c){
   return '<span class="arv-three-combo">'+esc((c||[]).join(' - '))+'</span>';
 }).join('');
}
function renderSection(detail,combosHtmlFn){
 var rec=build(detail);
 if(!rec)return '';
 var renderCombos=function(item){
   if(typeof combosHtmlFn==='function'){
     try{return combosHtmlFn(item);}catch(e){/* fall through */}
   }
   return fallbackCombos(item);
 };
 var head='<section class="arv-three-section arv-osusume"><h3>おすすめ買い目</h3>'
   +'<p class="arv-three-ticket-reason">'+esc(rec.reason)+'</p>'
   +'<p class="arv-three-ticket-reason arv-osusume-pools">軸：'
   +rec.axes.map(function(no){return esc(rec.label(no));}).join(' ／ ')
   +'｜相手：'
   +rec.partners.filter(function(no){return rec.axes.indexOf(no)<0;})
     .map(function(no){return esc(rec.label(no));}).join(' ／ ')
   +'</p>';
 var body=rec.groups.map(function(g){
   return '<div class="arv-three-ticket"><div class="arv-three-ticket-head"><b>'
     +esc(g.kind)+'</b><span class="arv-three-count">'+g.points+'点</span></div>'
     +'<strong class="arv-three-combos">'+renderCombos(g)+'</strong></div>';
 }).join('');
 var notes=rec.notes.map(function(n){
   return '<p class="arv-three-ticket-reason">'+esc(n)+'</p>';
 }).join('');
 return head+body
   +'<div class="arv-three-budget"><strong>合計 '+rec.totalPoints+'点</strong></div>'
   +notes+'</section>';
}
root.ARVEXQIntegratedOsusume=Object.freeze({
  build:build,renderSection:renderSection,TOTAL_CAP:TOTAL_CAP,KIND_ORDER:KIND_ORDER
});
})(typeof window!=='undefined'?window:globalThis);
