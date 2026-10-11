// LARGE: independent BOAT application. No horse app modules are loaded here.
import {todayJst,esc} from "./core/contract.js";
import {loadDay} from "./core/feed.js";
import {venueGrid,raceList,detail} from "./features/races.js";
import {selectedSection} from "./features/selected.js";
import {statsSection} from "./features/ai-stats.js";

const root=document.getElementById("boat-root");
const state={date:todayJst(),day:null,error:"",loading:false,view:"home",venue:"",raceId:"",request:0};
function emptyDay(){return {date:state.date,races:[],verifiedAt:""}}
function routeFromUrl(){
  const params=new URL(location.href).searchParams;
  state.date=/^\d{4}-\d{2}-\d{2}$/.test(params.get("date")||"")?params.get("date"):todayJst();
  state.view=["home","venues","selected","stats","races","race"].includes(params.get("view"))?params.get("view"):"home";
  state.venue=String(params.get("venue")||"");state.raceId=String(params.get("race")||"");
}
function route(view,venue="",raceId=""){
  const url=new URL(location.href);
  const next=new URLSearchParams();
  next.set("date",state.date);
  if(view!=="home")next.set("view",view);
  if(venue)next.set("venue",venue);
  if(raceId)next.set("race",raceId);
  url.search=next.toString();
  history.pushState({boat:true},"",url);
  state.view=view;state.venue=venue;state.raceId=raceId;
  draw();window.scrollTo(0,0);
}
function loadingNote(){return state.error?
  '<div class="boat-notice" role="status">'+esc(state.error)+'</div>':
  state.loading?'<div class="boat-notice" role="status">競艇データを確認しています…</div>':
  !(state.day&&state.day.verifiedAt)?'<div class="boat-notice" role="status">競艇データは現在未接続です。未確認の出走表・予想印・買い目は表示しません。</div>':"";
}
function navBar(){
  return '<div class="boat-page-head"><span class="boat-kicker">ARVEXQ / BOAT RACING</span><div class="boat-page-actions">'+
    '<label class="boat-date">開催日 <input type="date" id="boat-date" value="'+esc(state.date)+'"></label>'+
    '<button type="button" data-action="refresh" aria-label="競艇データを更新">↻</button></div></div>';
}
function home(){
  const races=(state.day||emptyDay()).races;
  const active=new Set(races.map(r=>r.venue));
  return '<section class="boat-home-hero"><span>ARVEXQ BOAT RACING</span><h1>競艇AI</h1>'+
    '<p>全国24場｜3連単 最大6点｜◎【単】・◎【軸】</p></section>'+
    '<div class="boat-home-actions">'+
      '<button type="button" data-view="selected"><strong>本日の厳選レース</strong><small>朝の確定予想のみ</small><b>›</b></button>'+
      '<button type="button" data-view="stats"><strong>AI成績</strong><small>保存済み買い目を照合</small><b>›</b></button>'+
      '<button type="button" data-view="venues"><strong>開催場一覧</strong><small>24場・レース詳細へ</small><b>›</b></button></div>'+
    '<section class="boat-panel"><h2>本日の厳選レース</h2>'+selectedSection(state.day||emptyDay())+
    '<button class="boat-secondary" type="button" data-view="selected">厳選レース一覧を見る ›</button></section>'+
    '<section class="boat-panel"><h2>AI成績</h2>'+statsSection(state.day||emptyDay())+
    '<button class="boat-secondary" type="button" data-view="stats">AI成績の詳細を見る ›</button></section>'+
    '<section class="boat-panel"><div class="boat-row"><h2>開催場一覧</h2><span class="boat-small">全国24場｜掲載データ '+active.size+'場</span></div>'+
    venueGrid(state.day||emptyDay(),"")+'</section>';
}
function subheader(title,back="home"){
  return '<div class="boat-subheader"><button type="button" data-back="'+back+'" aria-label="戻る">‹</button>'+
    '<h1>'+esc(title)+'</h1><button type="button" data-view="home" aria-label="トップへ戻る">×</button></div>';
}
function body(){
  const day=state.day||emptyDay(),venue=state.venue;
  if(state.view==="home")return home();
  if(state.view==="selected")return subheader("本日の厳選レース")+
    '<section class="boat-panel"><h2>朝確定・厳選予想</h2>'+selectedSection(day)+'</section>';
  if(state.view==="stats")return subheader("AI成績")+
    '<section class="boat-panel"><h2>3連単 AI成績</h2>'+statsSection(day.races)+'</section>';
  if(state.view==="venues")return subheader("開催場一覧")+
    '<section class="boat-panel"><h2>競艇場を選択</h2>'+venueGrid(day,"")+'</section>';
  if(state.view==="races")return subheader(venue+" 全レース","venues")+
    '<section class="boat-panel"><h2>'+esc(venue)+' 1R〜12R</h2>'+raceList(day,venue)+'</section>';
  if(state.view==="race"){
    const race=day.races.find(r=>r.id===state.raceId&&r.venue===venue);
    return subheader((venue||"")+(race?" "+race.raceNo+"R":""),"races")+
      (race?detail(race):'<section class="boat-panel"><p class="boat-muted">このレースの情報は確認できません。</p></section>');
  }
  return home();
}
function draw(){
  if(!root)return;
  root.innerHTML='<div class="boat-shell">'+navBar()+loadingNote()+
    '<main class="boat-main">'+body()+'</main><footer class="boat-footer">ARVEXQ | BOAT INTELLIGENCE</footer></div>';
}
async function refresh(){
  const request=++state.request;state.loading=true;state.error="";draw();
  try{
    const day=await loadDay(state.date);
    if(request!==state.request)return;
    state.day=day;state.error="";
  }catch(_error){
    if(request!==state.request)return;
    state.day=emptyDay();state.error="確認済みの競艇データがまだ公開されていません。データ接続完了までレース予想は表示できません。";
  }finally{if(request===state.request){state.loading=false;draw()}}
}
if(root){
  root.addEventListener("click",event=>{
    const b=event.target.closest("button");
    if(!b||!root.contains(b))return;
    if(b.dataset.action==="refresh"){refresh();return}
    if(b.dataset.view){route(b.dataset.view);return}
    if(b.dataset.venue){route("races",b.dataset.venue);return}
    if(b.dataset.race){
      const race=(state.day||emptyDay()).races.find(r=>r.id===b.dataset.race);
      if(race)route("race",race.venue,race.id);
      return;
    }
    if(b.dataset.back){
      if(b.dataset.back==="races")route("races",state.venue);
      else route(b.dataset.back);
    }
  });
  root.addEventListener("change",event=>{
    if(event.target.id==="boat-date"&&/^\d{4}-\d{2}-\d{2}$/.test(event.target.value)){
      state.date=event.target.value;route("home");refresh();
    }
  });
  window.addEventListener("popstate",()=>{routeFromUrl();refresh()});
  routeFromUrl();draw();refresh();
}
