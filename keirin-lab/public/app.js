const S={races:[],date:"",selected:null};
const el=id=>document.getElementById(id), fmt=x=>(x*100).toFixed(1)+"%";
const escape=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const today=()=>new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
function status(msg){el("status").textContent=msg}
async function load(){
 const date=el("date").value||today();S.date=date;status("出走表を読み込み中…");el("venues").innerHTML="";el("races").innerHTML="";el("detail").innerHTML="";
 try{
 const compact=date.replace(/-/g,"");
 const url="https://raw.githubusercontent.com/snarfnet/keirin-data/main/entries_"+compact+".json";
 const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw Error("出走表未公開（HTTP "+r.status+"）");
 const data=await r.json();
 let snapshots={};try{const sr=await fetch("/snapshots/"+date+".json",{cache:"no-store"});if(sr.ok){const saved=await sr.json();snapshots=saved.races||{}}}catch(_e){}
 for(const race of data.races||[]){const saved=snapshots[String(race.race_id)];if(saved){race.prediction=saved.prediction;race.prediction_snapshot_id=saved.prediction_snapshot_id;race.prediction_confirmed_at=saved.prediction_confirmed_at;race.prediction_status=saved.prediction?"confirmed":undefined;race.result_top3=saved.result_top3;race.payout_trifecta=saved.payout_trifecta}}
 if(!Array.isArray(data.races))throw Error("出走表形式が不正");
 S.races=data.races.filter(x=>Array.isArray(x.entries)&&x.entries.length>=3);
 const venues=[...new Set(S.races.map(x=>x.venue))];
 if(!venues.length)throw Error("表示できる開催情報なし");
 el("venues").innerHTML=venues.map(x=>'<option value="'+escape(x)+'">'+escape(x)+'</option>').join("");
 status(date+"｜"+S.races.length+"レース取得｜データ元：公開出走表（第三者提供）");
 showRaces();
  }catch(e){
 if(date==="2026-10-26"){
 const venues=[["青森",9],["川崎",9],["名古屋",11],["小松島",12],["京王閣",12],["小田原",12],["和歌山",12]];
 S.races=venues.flatMap(([venue,n])=>Array.from({length:n},(_,i)=>({race_id:venue+"-"+(i+1),venue,race_no:i+1,entries:[],provisional:true})));
 el("venues").innerHTML=venues.map(([venue])=>'<option value="'+escape(venue)+'">'+escape(venue)+'</option>').join("");
 status(date+"｜開催予定を表示。出走表の公開を待っています。");
 showRaces();
 }else status("取得失敗："+e.message+"。公開されていない日付の可能性があります。");
}
}
function raceStatus(r){
 if(r.provisional)return {code:"scheduled",label:"開催予定",detail:"出走表未取得"};
 if(r.cancelled||r.status==="cancelled")return {code:"cancelled",label:"中止",detail:"開催中止"};
 if(Array.isArray(r.result_top3)&&r.result_top3.length===3&&r.payout_trifecta!=null)return {code:"result",label:"結果確定",detail:"着順・払戻取得済み"};
 if(r.prediction&&r.prediction_status==="confirmed"&&r.prediction_snapshot_id&&r.prediction_confirmed_at)return {code:"confirmed",label:"予想確定",detail:"発走前保存済み予想"};
 if(Array.isArray(r.entries)&&r.entries.length>=3)return {code:"draft",label:"暫定予想",detail:"出走表取得済・予想未確定"};
 return {code:"scheduled",label:"開催予定",detail:"出走表未取得"};
}
function showRaces(){
 const venue=el("venues").value, races=S.races.filter(r=>r.venue===venue).sort((a,b)=>a.race_no-b.race_no);
 const filter=el("raceFilter")?.value||"all";
 const visible=races.filter(r=>filter==="all"||raceStatus(r).code===filter);
 el("races").innerHTML=visible.map(r=>{const st=raceStatus(r);return '<button type="button" class="race" data-id="'+escape(r.race_id)+'">'+r.race_no+'R <small>'+escape(r.start_time||"")+'</small><small>'+st.label+'</small></button>'}).join("");
 [...el("races").querySelectorAll("button")].forEach(b=>b.onclick=()=>choose(b.dataset.id));
 el("detail").innerHTML="<p class='sub'>レース番号を押すと予想を計算して表示します。</p>";
}
function choose(id){
 const r=S.races.find(x=>String(x.race_id)===String(id));if(!r)return;
 const st=raceStatus(r);
 if(r.provisional){el("detail").innerHTML="<h2>"+escape(r.venue)+" "+r.race_no+"R</h2><p class='notice'>開催予定のみ確認済み。出走表公開待ちのため予想はまだ表示できません。公開後に再読み込みしてください。</p>";return;}
 if(r.prediction && st.code==="confirmed"){
 const p=r.prediction;const marks=p.marks||{};
 const m=Object.entries(marks).map(([mark,n])=>mark+" "+n+" "+escape(r.entries.find(e=>Number(e.umaban)===Number(n))?.name||"")).join("　");
 const tt=(p.trifecta||[]).slice(0,12);
 el("detail").innerHTML="<h2>"+escape(r.venue)+" "+r.race_no+"R</h2><p class='notice'>予想確定（暫定モデル）｜保存日時："+escape(r.prediction_confirmed_at)+"｜保存ID："+escape(r.prediction_snapshot_id)+"</p><div class='summary'>"+m+"</div><h3>保存済み全選手確率</h3><div class='scroll'><table><thead><tr><th>車番</th><th>1着確率</th><th>3着内確率</th></tr></thead><tbody>"+(p.riders||[]).map(x=>"<tr><td>"+x.number+"</td><td>"+fmt(x.p1)+"</td><td>"+fmt(x.p3)+"</td></tr>").join("")+"</tbody></table></div><h3>確定時点の3連単候補</h3><div class='scroll'><table><tbody>"+tt.map(x=>"<tr><td>"+escape(x.ticket)+"</td><td>"+fmt(x.p)+"</td></tr>").join("")+"</tbody></table></div>"+(Array.isArray(r.result_top3)?"<h3>結果確定</h3><p>"+r.result_top3.join("-")+"</p>":"")+"<p class='notice'>予想は出走前の保存値を表示し、結果取得後も上書きしません。未校正モデルで収益性は未検証です。</p>";
 return;
}
 const riders=r.entries.map(e=>({n:Number(e.umaban),name:e.name,score:Number(e.score),style:e.style,win:Number(e.win_rate)/100,place:Number(e.top3_rate)/100,comment:e.comment||""}));
 if(riders.some(x=>!Number.isFinite(x.score)||!Number.isFinite(x.win)||!Number.isFinite(x.place))){el("detail").textContent="必要な成績に欠損があるため推定不能です。";return}
 const avg=riders.reduce((s,x)=>s+x.score,0)/riders.length;
 // コメントでの連係相手はユーザーに表示する。自動解釈の誤りを避け、計算には使用しない。
 riders.forEach(x=>{x.w=Math.exp(Math.max(-9,Math.min(9,(x.score-avg)/8 + 1.1*(x.win-.15)+.5*(x.place-.4)+(x.style==="逃"?.08:0))))});
 const combos=[];const sum=riders.reduce((s,x)=>s+x.w,0);
 for(const a of riders)for(const b of riders)for(const c of riders){if(a===b||b===c||a===c)continue;combos.push({key:a.n+"-"+b.n+"-"+c.n,p:a.w/sum*b.w/(sum-a.w)*c.w/(sum-a.w-b.w),a,b,c})}
 const total=combos.reduce((s,x)=>s+x.p,0);if(Math.abs(total-1)>1e-7){el("detail").textContent="計算エラー";return}
 riders.forEach(x=>{x.p1=combos.filter(c=>c.a===x).reduce((s,c)=>s+c.p,0);x.p3=combos.filter(c=>c.a===x||c.b===x||c.c===x).reduce((s,c)=>s+c.p,0)});
 riders.sort((a,b)=>b.p1-a.p1);combos.sort((a,b)=>b.p-a.p);
 const marks=["◎","○","▲","△","☆","","","",""];
 el("detail").innerHTML=
 '<h2>'+escape(r.venue)+' '+r.race_no+'R <span class="sub">'+escape(r.start_time||"")+'発走</span></h2><div class="notice">状態：'+st.label+'（'+st.detail+'）。「確定」は発走前に保存された予想か結果・払戻の記録がある場合のみ表示します。</div>'+
 '<div class="summary"><strong>'+marks[0]+' '+riders[0].n+' '+escape(riders[0].name)+'</strong><span>○ '+riders[1].n+' '+escape(riders[1].name)+'　▲ '+riders[2].n+' '+escape(riders[2].name)+'</span></div>'+
 '<h3>全選手の自動分析</h3><div class="scroll"><table><thead><tr><th>印・車番・選手</th><th>得点</th><th>直近1着率</th><th>直近3着内率</th><th>推定1着</th><th>推定3着内</th><th>コメント</th></tr></thead><tbody>'+
 riders.map((x,i)=>'<tr><td>'+marks[i]+' '+x.n+' '+escape(x.name)+'</td><td>'+x.score.toFixed(2)+'</td><td>'+fmt(x.win)+'</td><td>'+fmt(x.place)+'</td><td>'+fmt(x.p1)+'</td><td>'+fmt(x.p3)+'</td><td>'+escape(x.comment)+'</td></tr>').join("")+'</tbody></table></div>'+
 '<h3>3連単候補（全'+combos.length+'通り計算）</h3><div class="scroll"><table><thead><tr><th>買い目</th><th>モデル上の確率</th><th>損益分岐オッズ</th></tr></thead><tbody>'+
 combos.slice(0,12).map(x=>'<tr><td><b>'+x.key+'</b></td><td>'+fmt(x.p)+'</td><td>'+(1/x.p).toFixed(1)+'倍</td></tr>').join("")+'</tbody></table></div>'+
 '<p class="notice">未校正の暫定モデル。得点・直近率・脚質を使用。ライン・バンク・展開の学習済み統合、実オッズ自動取得、期待値購入判定は未実装。結果データを入力に使用していません。第三者の出走表は更新・欠損の可能性があります。</p>';
}
el("date").value=today();el("load").onclick=load;el("venues").onchange=showRaces;el("raceFilter").onchange=showRaces;
el("todayBtn").onclick=()=>{el("date").value=today();load()};
el("tomorrowBtn").onclick=()=>{const d=new Date(today()+"T12:00:00+09:00");d.setUTCDate(d.getUTCDate()+1);el("date").value=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit"}).format(d);load()};
load();
