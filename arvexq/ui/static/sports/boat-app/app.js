// LARGE: independent BOAT application. No horse app modules are loaded here.
import {todayJst,esc} from "./core/contract.js";
import {loadDay} from "./core/feed.js";
import {raceList,detail} from "./features/races.js";
import {allBoatRaces} from "./features/all-races.js";
import {selectedSection} from "./features/selected.js";
import {statsSection} from "./features/ai-stats.js";
import {specialSection} from "./features/special.js";

const root=document.getElementById("boat-root");
const state={date:todayJst(),day:null,error:"",loading:false,view:"home",venue:"",raceId:"",request:0,raceReturnView:"home"};
function emptyDay(){return {date:state.date,races:[],verifiedAt:""}}
function routeFromUrl(){
  const params=new URL(location.href).searchParams;
  state.date=/^\d{4}-\d{2}-\d{2}$/.test(params.get("date")||"")?params.get("date"):todayJst();
  state.view=["home","selected","special","stats","races","race"].includes(params.get("view"))?params.get("view"):"home";
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
// Subpages have one shared title/date/close row; the old kicker/refresh bar is removed.
function home(){
  const day=state.day||emptyDay(),shared=window.ARVEXQUnifiedHome;
  const hero=shared?shared.hero():'<div class="arv-unified-hero"></div>';
  const date=shared?shared.dateBar(state.date):'';
  const actions=shared?shared.buttons('boat'):'';
  return hero+'<div class="arv-unified-body">'+date+actions+
    (shared?shared.liveRaces('boat',day.races||[],state.date):'')+allBoatRaces(day)+'</div>';
}
function subheader(title,back="home"){
  const label=title.replace(/^本日の/,"").replace(/^当日の/,"");
  return '<div class="boat-subheader boat-subheader-dated"><button type="button" data-back="'+back+'" aria-label="戻る">‹</button>'+
    '<h1>'+esc(label)+'</h1><label class="boat-subdate" aria-label="表示日を選択"><span>'+esc(state.date.replace(/-/g,"/"))+
    '</span><input type="date" id="boat-date" value="'+esc(state.date)+'" aria-label="表示日を選択"></label>'+
    '<button type="button" data-view="home" aria-label="トップへ戻る">×</button></div>';
}
function body(){
  const day=state.day||emptyDay(),venue=state.venue;
  if(state.view==="home")return home();
  if(state.view==="selected")return subheader("本日の厳選レース")+
    '<section class="boat-panel"><h2>朝確定・厳選予想</h2>'+selectedSection(day)+'</section>';
  if(state.view==="special")return subheader("特別予想")+'<section class="boat-panel"><h2>特別予想</h2>'+specialSection(day)+'</section>';
  if(state.view==="stats")return subheader("AI成績")+
    '<section class="boat-panel"><h2>3連単 AI成績</h2>'+statsSection(day.races)+'</section>';
  if(state.view==="races")return subheader(venue+" 全レース","home")+
    '<section class="boat-panel"><h2>'+esc(venue)+' 1R〜12R</h2>'+raceList(day,venue)+'</section>';
  if(state.view==="race"){
    const race=day.races.find(r=>r.id===state.raceId&&r.venue===venue);
    return subheader((venue||"")+(race?" "+race.raceNo+"R":""),state.raceReturnView)+
      (race?detail(race):'<section class="boat-panel"><p class="boat-muted">このレースの情報は確認できません。</p></section>');
  }
  return home();
}
function draw(){
  if(!root)return;
  root.innerHTML='<div class="boat-shell"><main class="boat-main">'+loadingNote()+body()+
    '</main><footer class="boat-footer">ARVEXQ | BOAT INTELLIGENCE</footer></div>';
}
async function refresh(){
  const request=++state.request;state.loading=true;state.error="";draw();
  try{
    const day=await loadDay(state.date);
    if(request!==state.request)return;
    state.day=day;state.error="";
  }catch(_error){
    if(request!==state.request)return;
    // Preserve the last verified snapshot on transient errors for this date.
    if(!state.day||state.day.date!==state.date)state.day=emptyDay();
    state.error="この日の商用利用許諾済み競艇データは未配信です。実データが公開されるまで印・買い目は表示しません。";
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
      if(race){state.raceReturnView="races";route("race",race.venue,race.id);}
      return;
    }
    if(b.dataset.back){
      if(b.dataset.back==="races")route(state.raceReturnView==="home"?"home":"races",state.raceReturnView==="home"?"":state.venue);
      else route(b.dataset.back);
    }
  });
  root.addEventListener("change",event=>{
    if((event.target.id==="boat-date"||event.target.id==="date")&&/^\d{4}-\d{2}-\d{2}$/.test(event.target.value)){
      const keep=["selected","special","stats"].includes(state.view)?state.view:"home";
      state.date=event.target.value;route(keep);refresh();
    }
  });
  window.addEventListener("popstate",()=>{routeFromUrl();refresh()});
  routeFromUrl();draw();refresh();
  window.ARVEXQPullRefresh.mount({refresh});
  setInterval(function(){
    if(state.date===todayJst()&&!state.loading&&document.visibilityState!=="hidden")refresh();
  },60000);
  // Keep the next race moving even when no updated data file is published.
  setInterval(function(){
    if(state.view!=="home"||state.date!==todayJst()||document.visibilityState==="hidden")return;
    const shared=window.ARVEXQUnifiedHome;
    const panel=root.querySelector('.arv-realtime-section');
    if(!panel||!shared)return;
    const rows=(state.day||emptyDay()).races||[];
    const signature=shared.liveSignature('boat',rows,state.date);
    if(panel.getAttribute('data-live-signature')!==signature)
      panel.outerHTML=shared.liveRaces('boat',rows,state.date);
  },10000);
}
