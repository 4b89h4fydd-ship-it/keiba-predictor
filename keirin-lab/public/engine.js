"use strict";
/* KEIRIN heuristic v2. These parameters are not empirically calibrated. */
const TRACKS={"函館":[400,51.3],"青森":[400,58.9],"いわき平":[400,62.7],"弥彦":[400,63.1],"前橋":[335,46.7],"取手":[400,54.8],"宇都宮":[500,63.3],"大宮":[500,66.7],"西武園":[400,47.6],"京王閣":[400,51.5],"立川":[400,58],"松戸":[333,38.2],"千葉":[500,60],"川崎":[400,58],"平塚":[400,54.2],"小田原":[333,36.1],"伊東":[333,46.6],"静岡":[400,56.4],"名古屋":[400,58.8],"岐阜":[400,59.3],"大垣":[400,56],"豊橋":[400,60.3],"富山":[333,43],"松阪":[400,61.5],"四日市":[400,62.4],"福井":[400,52.8],"奈良":[333,38],"向日町":[400,47.3],"和歌山":[400,59.9],"岸和田":[400,56.7],"玉野":[400,47.9],"広島":[400,57.9],"防府":[333,42.5],"高松":[400,54.8],"小松島":[400,55.5],"高知":[500,52],"松山":[400,58.6],"小倉":[400,56.9],"久留米":[400,50.7],"武雄":[400,64.4],"佐世保":[400,40.2],"別府":[400,59.9],"熊本":[400,60.3]};
function linesOf(entries){
 const riders=entries.map(e=>({n:+e.umaban,name:e.name||"",score:+e.score,win:+e.win_rate/100,place:+e.top3_rate/100,style:e.style||"",comment:e.comment||""}));
 const byName=new Map(riders.map(r=>[r.name.replace(/\s/g,""),r]));
 const ref=(comment)=>{const c=comment.replace(/\s/g,"");for(const r of riders){const last=r.name.replace(/\s/g,"");if(last.length>=2&&(c.includes(last+"君")||c.includes(last+"さん")||c.includes(last+"へ")||c.includes(last.slice(0,2)+"君")||c.includes(last.slice(0,2)+"さん")))return r.n}return null};
 const parent=new Map(riders.map(r=>[r.n,ref(r.comment)]));
 for(const r of riders){const c=r.comment; if(parent.get(r.n)===r.n)parent.set(r.n,null);
  if(!parent.get(r.n)&&/自力|単騎|決めず|自在|前々/.test(c))parent.set(r.n,null);
 }
 function root(n){const seen=new Set();while(parent.get(n)!=null&&!seen.has(n)){seen.add(n);n=parent.get(n)}return n}
 const groups=new Map();for(const r of riders){const rt=root(r.n);if(!groups.has(rt))groups.set(rt,[]);groups.get(rt).push(r.n)}
 const uncertain=riders.filter(r=>r.comment&&!/自力|単騎|決めず|自在|前々/.test(r.comment)&&parent.get(r.n)==null).map(r=>r.n);
 return {groups:[...groups.values()],uncertain};
}
function calculateKeirin(race){
 const data=race.entries||[], n=data.length;if(n<3||n>9)throw Error("対象車数が不正");
 const riders=data.map(e=>({n:+e.umaban,name:e.name||"",score:+e.score,win:+e.win_rate/100,place:+e.top3_rate/100,style:e.style||"",comment:e.comment||""}));
 if(riders.some(r=>!Number.isFinite(r.score)||!Number.isFinite(r.win)||!Number.isFinite(r.place)||r.win<0||r.win>r.place||r.place>1))throw Error("出走データ欠損");
 const avg=riders.reduce((v,r)=>v+r.score,0)/n,lines=linesOf(data),track=TRACKS[race.venue]||[400,55];
 const leaders=new Set(lines.groups.map(group=>group[0]));
 const leadCount=riders.filter(r=>leaders.has(r.n)&&r.style==="逃").length;
 const crowded=leadCount>=3;
 const scores=riders.map(r=>{
  const group=lines.groups.find(g=>g.includes(r.n))||[r.n],pos=group.indexOf(r.n);
  const straight=track[1];
  const startBonus=r.style==="逃"?(track[0]===333?.14:track[0]===500?-.06:.05):0;
  const sprintBonus=r.style==="追"?(straight>=57?.10:straight<45?-.05:0):0;
  const lineBonus=group.length>=2?(pos===0?.09:pos===1?.12:.02):0;
  const paceBonus=crowded?(r.style==="追"?.13:r.style==="逃"?-.17:.05):leadCount<=1&&r.style==="逃"?.12:0;
  return {...r,group,pos,weight:Math.exp(Math.max(-8,Math.min(8,(r.score-avg)/8+1.1*(r.win-.15)+.5*(r.place-.4)+(r.style==="逃"?.08:0)+startBonus+sprintBonus+lineBonus+paceBonus)))};
 });
 // Plackett-Luce ordering probability. Simple joint probability model only.
 const total=scores.reduce((s,r)=>s+r.weight,0),combos=[];
 for(const a of scores)for(const b of scores)for(const c of scores){
  if(a===b||b===c||a===c)continue;
  let p=a.weight/total*b.weight/(total-a.weight)*c.weight/(total-a.weight-b.weight);
  // Correlation adjustment to favor same-line cooperation. Renormalized later.
  if(a.group===b.group&&a.group.length>1)p*=1.12;
  if(b.group===c.group&&b.group.length>1)p*=1.08;
  combos.push({ticket:a.n+"-"+b.n+"-"+c.n,p});
 }
 const norm=combos.reduce((s,c)=>s+c.p,0);combos.forEach(c=>c.p/=norm);combos.sort((a,b)=>b.p-a.p);
 const byN=new Map(scores.map(r=>[r.n,{number:r.n,name:r.name,comment:r.comment,p1:0,p3:0,score:r.score}]));
 for(const c of combos){const [a,b,d]=c.ticket.split("-").map(Number);byN.get(a).p1+=c.p;for(const id of [a,b,d])byN.get(id).p3+=c.p}
 const ranked=[...byN.values()].sort((a,b)=>b.p1-a.p1);
 const marks=Object.fromEntries(["◎","○","▲","△","☆"].map((m,i)=>[m,ranked[i]?.number]).filter(x=>x[1]!=null));
 const scenario=crowded?"先行型が複数で踏み合う想定。差し・捲りの浮上に注意":leadCount===1?"主導権争いが少ない想定。先行ラインが残る展開に注意":"先行主導権が不明確。自在・番手の動きを重視";
 return {model:"keirin-line-track-v2-heuristic-uncalibrated",marks,riders:ranked,trifecta:combos,lines:lines.groups,uncertain_line_members:lines.uncertain,track:{length:track[0],straight:track[1],estimated:!TRACKS[race.venue]},scenario,limitations:"ラインは選手コメントによる暫定推定。風・実戦位置取り・オッズは未反映。確率校正未実施。"};
}
