(function(){
"use strict";
/* Read-only ARVEXQ archived-race verifier. No network calls, writes or Stage64 imports.
   Only decompression, the frozen three-analysis feature schema and finish checking. */
function from64(s){
 const abc="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
 const lut=new Int16Array(128).fill(-1);for(let i=0;i<64;i++)lut[abc.charCodeAt(i)]=i;
 let out=new Uint8Array(Math.floor(s.length*3/4)),buf=0,bits=0,j=0;
 for(let i=0;i<s.length;i++){let c=s.charCodeAt(i);if(c===61)break;let v=c<128?lut[c]:-1;if(v<0)continue;buf=(buf<<6)|v;bits+=6;if(bits>=8){bits-=8;out[j++]=(buf>>>bits)&255}}
 return out.subarray(0,j);
}
function ungzip(b){
 if(b[0]!==31||b[1]!==139||b[2]!==8)throw Error("not gzip");
 let pos=10,flags=b[3];if(flags&4)pos+=2+b[pos]+256*b[pos+1];
 if(flags&8)while(b[pos++]){}if(flags&16)while(b[pos++]){}if(flags&2)pos+=2;
 let bit=pos*8;function rd(n){let v=0;for(let i=0;i<n;i++){v|=((b[bit>>3]>>(bit&7))&1)<<i;bit++}return v}
 function tree(ls){let count=Array(16).fill(0),next=Array(16).fill(0),maps=Array.from({length:16},()=>new Map()),max=0;
  for(let l of ls)if(l)count[l]++;
  let c=0;for(let i=1;i<=15;i++){c=(c+count[i-1])*2;next[i]=c;if(count[i])max=i}
  for(let i=0;i<ls.length;i++){let l=ls[i];if(l){let v=next[l]++,r=0;for(let j=0;j<l;j++){r=(r<<1)|(v&1);v>>=1}maps[l].set(r,i)}}return {maps,max}
 }
 function sym(h){let v=0;for(let i=1;i<=h.max;i++){v|=rd(1)<<(i-1);let out=h.maps[i].get(v);if(out!==undefined)return out}throw Error("deflate huffman")}
 const lb=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258],
 le=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0],
 db=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577],
 de=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
 let o=[],last=0;
 while(!last){last=rd(1);let typ=rd(2);
  if(typ===0){bit=(bit+7)&~7;const n=rd(16),inv=rd(16);if((n^inv)!==65535)throw Error("stored block");for(let i=0;i<n;i++)o.push(rd(8));continue}
  let lit,dist;
  if(typ===1){lit=tree(Array.from({length:288},(_,i)=>i<144?8:i<256?9:i<280?7:8));dist=tree(Array(32).fill(5))}
  else if(typ===2){let nl=rd(5)+257,nd=rd(5)+1,ncl=rd(4)+4,order=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15],cl=Array(19).fill(0);
   for(let i=0;i<ncl;i++)cl[order[i]]=rd(3);
   const ch=tree(cl),ls=[];while(ls.length<nl+nd){let x=sym(ch);if(x<=15)ls.push(x);else{let n=x===16?rd(2)+3:x===17?rd(3)+3:rd(7)+11,value=x===16?ls[ls.length-1]:0;if(value===undefined)throw Error("repeat");while(n--)ls.push(value)}}
   lit=tree(ls.slice(0,nl));dist=tree(ls.slice(nl,nl+nd));
  }else throw Error("deflate type");
  for(;;){let x=sym(lit);if(x<256){o.push(x);continue}if(x===256)break;let i=x-257;if(i<0||i>=lb.length)throw Error("length");
   let len=lb[i]+rd(le[i]),di=sym(dist),far=db[di]+rd(de[di]);if(far>o.length||di>=db.length)throw Error("distance");
   for(let k=0;k<len;k++)o.push(o[o.length-far]);
  }
 }
 let size=(b[b.length-4]+(b[b.length-3]<<8)+(b[b.length-2]<<16)+(b[b.length-1]*16777216))>>>0;
 if(o.length!==size)throw Error("gzip size");
 let s="",parts=[];for(let p=0;p<o.length;){let cp=o[p++];
  if(cp>=240){cp=((cp&7)<<18)|((o[p++]&63)<<12)|((o[p++]&63)<<6)|(o[p++]&63)}
  else if(cp>=224){cp=((cp&15)<<12)|((o[p++]&63)<<6)|(o[p++]&63)}
  else if(cp>=192){cp=((cp&31)<<6)|(o[p++]&63)}
  if(cp>65535){cp-=65536;s+=String.fromCharCode(55296+(cp>>10),56320+(cp&1023))}else s+=String.fromCharCode(cp);
  if(s.length>16000){parts.push(s);s=""}
 }return parts.join("")+s;
}
function number(x){if(x===null||x===undefined||x==="")return null;let z=Number(x);return Number.isFinite(z)?z:null}
function mean(v){let a=v.filter(x=>x!==null);return a.length?a.reduce((x,y)=>x+y,0)/a.length:null}
function quality(r){let n=number(r.fieldSize),f=number(r.finish);return n!==null&&n>1&&f!==null&&1<=f&&f<=n?(n-f)/(n-1):null}
function history(h,cutoff){
 let m=new Map();for(let field of ["recentRaces","allPastRuns"])for(let r of h[field]||[]){
  if(!r||typeof r!=="object"||Array.isArray(r))continue;
  let d=String(r._raceDate||r.date||"");if(d.length!==10||d>=cutoff||!/^\\d{4}-\\d{2}-\\d{2}$/.test(d)||["障害","ばんえい"].includes(r.surface))continue;
  let k=d+"|"+String(r.track||"")+"|"+String(r.raceNumber||""),old=m.get(k);
  if(old&&old.finish!==r.finish)throw Error("conflicting history");
  if(!old||Object.keys(r).length>Object.keys(old).length)m.set(k,r);
 }
 return [...m].sort((a,b)=>b[0].localeCompare(a[0])).map(x=>x[1]);
}
function evidence(race){
 let hs=(race.horses||[]).filter(h=>h&&Number.isInteger(h.horseNumber)&&!h.scratched&&!h.cancelled&&!h.withdrawn&&!["出走取消","競走除外","取消","除外"].includes(String(h.status||""))).sort((a,b)=>a.horseNumber-b.horseNumber);
 if(hs.length<3||new Set(hs.map(h=>h.horseNumber)).size!==hs.length)throw Error("runner identity");
 let early={},ability={},result={};
 for(let h of hs){let no=h.horseNumber,rows=history(h,race.date),valid=rows.map(quality).filter(x=>x!==null),ep=[];
  for(let r of rows){let positions=r.cornerPositions||r.passing||[],size=number(r.fieldSize),p=Array.isArray(positions)&&positions.length?number(positions[0]):null;
    if(p!==null&&size!==null&&size>1&&p>=1&&p<=size)ep.push((p-1)/(size-1))}
  early[no]=mean(ep.slice(0,5));
  let comparable=rows.filter(r=>r.surface===race.surface&&Math.abs((number(r.distance)||0)-(number(race.distance)||0))<=150);
  ability[no]={form:mean(valid.slice(0,5)),
   win_rate:rows.length?rows.filter(r=>number(r.finish)===1).length/rows.length:null,
   top3_rate:rows.length?rows.filter(r=>number(r.finish)!==null&&number(r.finish)<=3).length/rows.length:null,
   distance_form:mean(comparable.map(quality)),
   margin:mean(comparable.map(r=>number(r.marginSeconds!==undefined&&r.marginSeconds!==null?r.marginSeconds:r.timeBehindWinner)))};
 }
 let pressure=hs.filter(h=>early[h.horseNumber]!==null&&early[h.horseNumber]<=0.3).length/hs.length;
 for(let h of hs){let no=h.horseNumber;result[no]={...ability[no],early_position:early[no],
  frame:((h.frameNumber||no)-1)/Math.max(1,hs.length-1),pace_pressure:pressure,
  video_speed:null,video_start:null,video_extra_distance:null,video_slowdowns:null,video_missing:1}}
 return result;
}
function pick(race,model){
 if(!race||!race.result||race.result.status!=="確定")return null;
 let f=evidence(race),labels={},used=new Set();
 for(let h of race.result.finishers||[]){let z=number(h.finish);if(h.horseNumber!==null&&h.horseNumber!==undefined&&z!==null&&z>=1)labels[Number(h.horseNumber)]=Math.trunc(z)}
 let nums=Object.keys(f).map(Number).sort((a,b)=>a-b);
 if(nums.length!==Object.keys(labels).length||nums.some(n=>labels[n]===undefined)||new Set(Object.values(labels)).size!==nums.length||nums.some(n=>f[n].form===null))return null;
 let best=nums[0],hi=-Infinity;
 for(let n of nums){let score=0;for(let [k,w] of Object.entries(model.weights))score+=w*(f[n][k]===null?model.featureMeans[k]:f[n][k]);
   score/=model.temperature;if(score>hi){hi=score;best=n}}
 return {id:race.id,date:race.date,horseNumber:best,finish:labels[best],one:labels[best]===1,three:labels[best]<=3};
}
return Object.freeze({decodeRace:s=>JSON.parse(ungzip(from64(s))),pick:pick});
})()