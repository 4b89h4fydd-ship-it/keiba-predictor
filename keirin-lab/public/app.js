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
 renderVenues();
  }catch(e){
 if(date==="2026-10-26"){
 const venues=[["青森",9],["川崎",9],["名古屋",11],["小松島",12],["京王閣",12],["小田原",12],["和歌山",12]];
 S.races=venues.flatMap(([venue,n])=>Array.from({length:n},(_,i)=>({race_id:venue+"-"+(i+1),venue,race_no:i+1,entries:[],provisional:true})));
 el("venues").innerHTML=venues.map(([venue])=>'<option value="'+escape(venue)+'">'+escape(venue)+'</option>').join("");
 status(date+"｜開催予定を表示。出走表の公開を待っています。");
 renderVenues();
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
function renderVenues(){
 el("listTitle").textContent="開催場一覧";
 el("raceTools").hidden=true;el("races").hidden=true;el("detail").hidden=true;el("venuesGrid").hidden=false;
 const names=[...new Set(S.races.map(r=>r.venue))];
 el("venuesGrid").innerHTML=names.map(name=>{const rr=S.races.filter(r=>r.venue===name);return '<button type="button" class="venueCard" data-venue="'+escape(name)+'"><span>'+escape(name)+'<small>'+rr.length+'レース</small></span><span aria-hidden="true">›</span></button>'}).join("");
 [...el("venuesGrid").querySelectorAll("button")].forEach(btn=>btn.onclick=()=>openVenue(btn.dataset.venue));
}
function openVenue(name){
 el("venues").value=name;el("listTitle").textContent=name+"・レース一覧";
 el("raceTools").hidden=false;el("venuesGrid").hidden=true;el("races").hidden=false;el("detail").hidden=true;
 showRaces();location.hash="venue="+encodeURIComponent(name);window.scrollTo(0,0);
}
function showRaces(){
 const venue=el("venues").value, races=S.races.filter(r=>r.venue===venue).sort((a,b)=>a.race_no-b.race_no);
 const filter=el("raceFilter")?.value||"all";
 const visible=races.filter(r=>filter==="all"||raceStatus(r).code===filter);
 el("races").innerHTML=visible.map(r=>{const st=raceStatus(r);return '<button type="button" class="race" data-id="'+escape(r.race_id)+'">'+r.race_no+'R <small>'+escape(r.start_time||"")+'</small><small>'+st.label+'</small></button>'}).join("");
 [...el("races").querySelectorAll("button")].forEach(b=>b.onclick=()=>choose(b.dataset.id));
 
}
function choose(id){
 el("detail").hidden=false;el("races").hidden=true;el("raceTools").hidden=true;el("venuesGrid").hidden=true;
 el("listTitle").textContent="レース予想詳細";
 location.hash="race="+encodeURIComponent(id);window.scrollTo(0,0);
 const r=S.races.find(x=>String(x.race_id)===String(id));if(!r)return;
 const st=raceStatus(r);
 if(r.provisional){el("detail").innerHTML="<button type='button' id='provisionalBack' class='back'>‹ レース一覧へ戻る</button><h2>"+escape(r.venue)+" "+r.race_no+"R</h2><p class='notice'>開催予定のみ確認済み。出走表公開待ちのため予想はまだ表示できません。公開後に再読み込みしてください。</p>";document.getElementById('provisionalBack').onclick=()=>openVenue(r.venue);return;}
 if(r.prediction && (st.code==="confirmed"||st.code==="result")){
 const p=r.prediction;const marks=p.marks||{};
 const m=Object.entries(marks).map(([mark,n])=>mark+" "+n+" "+escape(r.entries.find(e=>Number(e.umaban)===Number(n))?.name||"")).join("　");
 const tt=(p.trifecta||[]).slice(0,12);
 el("detail").innerHTML="<button type='button' id='savedBack' class='back'>‹ レース一覧へ戻る</button><h2>"+escape(r.venue)+" "+r.race_no+"R</h2><p class='notice'>予想確定（暫定モデル）｜保存日時："+escape(r.prediction_confirmed_at)+"｜保存ID："+escape(r.prediction_snapshot_id)+"</p><div class='summary'>"+m+"</div><h3>保存済み全選手確率</h3><div class='scroll'><table><thead><tr><th>車番</th><th>1着確率</th><th>3着内確率</th></tr></thead><tbody>"+(p.riders||[]).map(x=>"<tr><td>"+x.number+"</td><td>"+fmt(x.p1)+"</td><td>"+fmt(x.p3)+"</td></tr>").join("")+"</tbody></table></div><h3>確定時点の3連単候補</h3><div class='scroll'><table><tbody>"+tt.map(x=>"<tr><td>"+escape(x.ticket)+"</td><td>"+fmt(x.p)+"</td></tr>").join("")+"</tbody></table></div>"+(Array.isArray(r.result_top3)?"<h3>結果確定</h3><p>"+r.result_top3.join("-")+"</p>":"")+"<p class='notice'>予想は出走前の保存値を表示し、結果取得後も上書きしません。未校正モデルで収益性は未検証です。</p>";
 return;
}

 let p;try{p=calculateKeirin(r)}catch(e){el("detail").textContent="計算不可："+e.message;return}
 const markItems=Object.entries(p.marks).map(([m,n])=>m+n+" "+escape(r.entries.find(e=>+e.umaban===n)?.name||"")).join("　");
 const lines=p.lines.map(a=>a.join("－")).join(" ／ ");
 el("detail").innerHTML='<button type="button" class="back" id="detailBack">‹ レース一覧へ戻る</button>'+
 '<h2>'+escape(r.venue)+' '+r.race_no+'R <span class="sub">'+escape(r.start_time||"")+'発走</span></h2>'+
 '<div class="notice">状態：'+st.label+'｜自動計算は暫定予想。保存・確定済みの予想ではありません。</div>'+
 '<div class="summary"><strong>'+markItems+'</strong></div>'+
 '<h3>① 能力分析</h3><p>競走得点・近況・脚質を評価。</p><h3>② 映像分析</h3><p>'+(p.stages.video.used?'映像指標を反映':'映像未取得・補正なし')+'</p><h3>③ 展開分析</h3><p>スタート → 打鐘 → 最終バック → 最終コーナー → 直線</p><h3>想定ライン・展開</h3><p>想定ライン：'+escape(lines)+'</p><p>'+escape(p.scenario)+'</p>'+
 '<p class="sub">バンク '+p.track.length+'m／みなし直線 '+p.track.straight+'m。ラインはコメントから推定。未確認車番 '+(p.uncertain_line_members.join(",")||"なし")+'</p>'+
 '<h3>④ 確率計算・⑤ 印</h3><h3>全選手の能力・確率</h3><div class="scroll"><table><thead><tr><th>車番・選手</th><th>得点</th><th>1着推定</th><th>3着内推定</th><th>選手コメント</th></tr></thead><tbody>'+
 p.riders.map(x=>'<tr><td>'+x.number+' '+escape(x.name)+'</td><td>'+x.score.toFixed(2)+'</td><td>'+fmt(x.p1)+'</td><td>'+fmt(x.p3)+'</td><td>'+escape(x.comment)+'</td></tr>').join("")+'</tbody></table></div>'+
 '<h3>⑥ 買い目・3連単候補（'+p.trifecta.length+'通り計算）</h3><div class="scroll"><table><thead><tr><th>買い目</th><th>推定的中率</th><th>損益分岐オッズ</th></tr></thead><tbody>'+
 p.trifecta.slice(0,15).map(x=>'<tr><td>'+x.ticket+'</td><td>'+fmt(x.p)+'</td><td>'+(1/x.p).toFixed(1)+'倍</td></tr>').join("")+'</tbody></table></div>'+
 '<h3>期待値チェック</h3><div class="controls"><div><label>3連単候補</label><select id="evTicket">'+p.trifecta.slice(0,30).map(x=>'<option value="'+x.ticket+'">'+x.ticket+'</option>').join("")+'</select></div><div><label>実オッズ（倍）</label><input type="number" id="evOdds" inputmode="decimal" placeholder="オッズを入力" min="1" step="0.1"></div><button type="button" id="evCheck">期待値計算</button></div><p id="evAnswer" class="sub">実オッズ未取得のため、自動購入判定は行いません。</p>'+
 '<p class="notice">'+escape(p.limitations)+' このモデルは過去成績による校正前であり、的中率・回収率は未検証です。</p>';
 document.getElementById("detailBack").onclick=()=>openVenue(r.venue);
 document.getElementById("evCheck").onclick=()=>{const selected=p.trifecta.find(x=>x.ticket===el("evTicket").value);const odd=Number(el("evOdds").value);el("evAnswer").textContent=!el("evOdds").value||!Number.isFinite(odd)||odd<1?"実オッズを入力してください。":"期待回収率 "+(selected.p*odd*100).toFixed(1)+"%。理論上の損益分岐 "+(1/selected.p).toFixed(1)+"倍（モデル未校正・購入推奨ではありません）"};

}
el("date").value=today();el("load").onclick=load;el("venues").onchange=()=>openVenue(el("venues").value);el("raceFilter").onchange=showRaces;
el("backVenues").onclick=()=>{location.hash="";renderVenues();window.scrollTo(0,0)};
el("backRaces").onclick=()=>openVenue(el("venues").value);
el("todayBtn").onclick=()=>{el("date").value=today();load()};
el("tomorrowBtn").onclick=()=>{const d=new Date(today()+"T12:00:00+09:00");d.setUTCDate(d.getUTCDate()+1);el("date").value=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit"}).format(d);load()};
load();
