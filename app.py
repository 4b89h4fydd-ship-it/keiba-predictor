from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
import json
import csv
import hashlib
import io
import os
import re
import sqlite3
import threading
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date as dt_date, datetime
from pathlib import Path
from typing import Iterable, Iterator

app = FastAPI(title="競馬展開AI", version="3.1-production-v11")

INDEX = '<!doctype html>\n<html lang="ja">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n  <meta name="theme-color" content="#0f172a">\n  <meta name="apple-mobile-web-app-capable" content="yes">\n  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n  <meta name="apple-mobile-web-app-title" content="競馬展開AI">\n  <link rel="manifest" href="/manifest.webmanifest?v=11">\n  <link rel="stylesheet" href="/styles.css?v=11">\n  <title>競馬展開AI</title>\n</head>\n<body>\n  <div id="app"><div class="boot">競馬展開AIを起動中…</div></div>\n  <script defer src="/app.js?v=11"></script>\n</body>\n</html>'
CSS = '\n:root{--bg:#f4f5f8;--card:#fff;--text:#111827;--muted:#667085;--line:#e5e7eb;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Hiragino Sans",sans-serif;color:var(--text);background:var(--bg);font-weight:400}\n*{box-sizing:border-box}body{margin:0;background:var(--bg);font-weight:400;-webkit-text-size-adjust:100%}button,input,textarea{font:inherit;font-weight:400}.boot{padding:32px;text-align:center;color:#64748b}.shell{max-width:760px;margin:auto;padding-bottom:calc(24px + env(safe-area-inset-bottom))}.header{position:sticky;top:0;z-index:50;background:rgba(15,23,42,.98);color:#fff;padding:calc(7px + env(safe-area-inset-top)) 10px 8px;box-shadow:0 2px 8px rgba(0,0,0,.14)}.header-row{display:flex;align-items:center;gap:8px}.header-title{min-width:0;flex:1}.header h1{margin:0;font-size:18px;font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.header small{display:block;color:#cbd5e1;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.back,.reload{border:0;background:rgba(255,255,255,.12);color:#fff;border-radius:10px;padding:7px 10px}.main{padding:8px;display:grid;gap:8px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:11px}.card h2,.section-title{margin:0 0 8px;font-size:18px;font-weight:400}.muted{color:var(--muted)}.setup{display:grid;grid-template-columns:1fr;gap:10px}.label{font-size:11px;color:var(--muted);margin-bottom:4px}.date{display:block;width:100%;height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 9px;background:#fff;font-size:15px}.segment{display:grid;grid-template-columns:1fr 1fr;gap:6px}.segment button{border:1px solid var(--line);background:#fff;border-radius:10px;padding:9px 4px}.segment button.active{background:#111827;color:#fff}.row{display:flex;align-items:center;gap:8px}.between{justify-content:space-between}.pill{background:#eef2f7;border-radius:999px;padding:4px 8px;font-size:10px}.venue-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.venue{border:1px solid var(--line);background:#fff;border-radius:11px;padding:10px;text-align:left}.venue .name{font-size:17px}.venue .count{font-size:11px;color:var(--muted)}.race-list{display:grid;gap:7px}.race{width:100%;border:1px solid var(--line);background:#fff;border-radius:11px;padding:10px;text-align:left;display:flex;justify-content:space-between;align-items:center;gap:8px}.race.disabled{opacity:.42}.race-result{font-size:11px;color:#2563eb}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}.metric{background:#f8fafc;border-radius:9px;padding:8px 2px;text-align:center}.metric b{display:block;font-size:13px;font-weight:400}.metric span{font-size:9px;color:var(--muted)}.big-number{font-size:31px}.style-list{display:grid;gap:6px}.style-row{border:1px solid var(--line);border-radius:11px;padding:8px;background:#fff}.style-top{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto;align-items:center;gap:6px}.horse-name,.result-name{font-weight:700!important;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.score{font-size:13px;font-variant-numeric:tabular-nums}.expected{font-size:10px;color:#475569;background:#f1f5f9;border-radius:999px;padding:3px 6px;white-space:nowrap}.rates{display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin-top:6px}.rate{background:#f8fafc;border-radius:7px;text-align:center;padding:5px 2px;font-size:11px}.rate small{display:block;color:var(--muted);font-size:8px}.stage{padding:11px 0;border-bottom:1px solid var(--line)}.stage:last-child{border-bottom:0}.stage-title{font-size:12px;color:var(--muted);margin-bottom:7px}.stage-line{display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:20px;line-height:1.65}.queue-group{display:inline-flex;align-items:center;gap:4px}.arrow{color:#94a3b8;font-size:20px}.scenario-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.scenario{background:#f8fafc;border-radius:11px;padding:10px 5px;min-height:116px;text-align:center}.scenario-title{font-size:13px}.prob{font-size:28px;margin:5px 0}.scenario-horses{display:flex;gap:4px;flex-wrap:wrap;justify-content:center}.marks{display:grid;grid-template-columns:1fr 1fr;gap:5px}.mark{display:grid;grid-template-columns:auto auto minmax(0,1fr);align-items:center;gap:5px;background:#f8fafc;border-radius:10px;padding:9px}.mark-symbol{font-size:19px}.horse-card{border:1px solid var(--line);border-radius:11px;padding:10px;margin-top:7px}.horse-card summary{display:flex;align-items:center;gap:7px;font-size:16px;list-style:none}.horse-detail{padding-top:9px;display:grid;gap:8px;font-size:15px;line-height:1.45}.recent{border-top:1px dashed var(--line);padding-top:8px}.notice{background:#fff7ed;color:#9a3412;border-radius:10px;padding:10px;font-size:12px}.empty{text-align:center;color:var(--muted);padding:18px 8px;font-size:12px}.frame-badge{display:inline-flex;align-items:center;justify-content:center;width:29px;height:29px;border-radius:6px;border:1px solid rgba(0,0,0,.18);font-size:14px;font-weight:400;flex:0 0 auto}.frame1{background:#fff;color:#111}.frame2{background:#222;color:#fff}.frame3{background:#e53935;color:#fff}.frame4{background:#1e66d0;color:#fff}.frame5{background:#f5d547;color:#111}.frame6{background:#3a9b56;color:#fff}.frame7{background:#f28c28;color:#111}.frame8{background:#e894b7;color:#111}.queue-badge{width:35px;height:35px;font-size:17px}.source-tag{font-size:9px;color:#64748b;margin-top:3px}.result-list{display:grid;gap:7px}.result-row{display:grid;grid-template-columns:30px auto minmax(0,1fr) auto;align-items:center;gap:7px;padding:7px 0;border-bottom:1px solid var(--line)}.result-row:last-child{border-bottom:0}.finish-pos{font-size:19px}.result-time{font-size:13px;color:#475569}.review-box{margin-top:10px;background:#f8fafc;border-radius:11px;padding:9px}.review-title{font-size:14px;margin-bottom:6px}.diff-list{display:grid;gap:5px;font-size:13px}.diff-item{padding:6px 7px;background:#fff;border-radius:8px}.review-meta{font-size:10px;color:#64748b;margin-top:6px}.review-text{width:100%;min-height:78px;resize:vertical;border:1px solid var(--line);border-radius:9px;padding:8px;margin-top:8px;background:#fff;font-size:14px}.save-review{margin-top:6px;border:0;background:#111827;color:#fff;border-radius:9px;padding:8px 12px}.save-status{font-size:11px;color:#16a34a;margin-left:8px}\n@media(max-width:390px){.main{padding:6px}.card{padding:9px}.style-top{grid-template-columns:auto minmax(0,1fr) auto}.expected{grid-column:2/4;justify-self:start}.scenario-grid{gap:3px}.scenario{padding:8px 3px}.frame-badge{width:27px;height:27px}.queue-badge{width:34px;height:34px}}\n'
JS = '\n(function(){\n"use strict";\nvar CENTRAL=["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"];\nvar LOCAL=["帯広","門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"];\nvar app=document.getElementById("app");\nvar state={circuit:"地方",date:todayJst(),races:[],selectedTrack:null,selectedRace:null,loading:false,error:null,retries:0};\nfunction todayJst(){var d=new Date(Date.now()+9*3600000);return d.toISOString().slice(0,10)}\nfunction esc(v){return String(v==null?"":v).replace(/[&<>\\"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",\'\\"\':"&quot;"}[c]})}\nfunction circled(n){n=Number(n);return n>=1&&n<=20?String.fromCodePoint(0x245f+n):String(n)}\nfunction pct(v){v=Number(v);return isFinite(v)?Math.round(v*100)+"%":"0%"}\nfunction money(n){try{return new Intl.NumberFormat("ja-JP").format(Number(n)||0)}catch(e){return String(n||0)}}\nfunction season(iso){var m=Number(String(iso||"").split("-")[1]);if(m>=3&&m<=5)return"春";if(m>=6&&m<=8)return"夏";if(m>=9&&m<=11)return"秋";return"冬"}\nfunction fmtTime(s){s=Number(s);if(!isFinite(s)||s<=0)return"—";if(s<60)return s.toFixed(1);var m=Math.floor(s/60),r=(s-m*60).toFixed(1);if(Number(r)<10)r="0"+r;return m+":"+r}\nfunction badge(h,extra){var f=Math.max(1,Math.min(8,Number(h&&h.frameNumber)||Number(h&&h.horseNumber)||1));return \'<span class="frame-badge frame\'+f+(extra?\' \'+extra:\'\')+\'">\'+esc(h&&h.horseNumber)+\'</span>\'}\nfunction horseByNo(r,n){var hs=r.horses||[];for(var i=0;i<hs.length;i++)if(Number(hs[i].horseNumber)===Number(n))return hs[i];return null}\nfunction styleRates(h){var c={front:0,stalk:0,mid:0,close:0},t=0,rs=(h&&h.recentRaces)||[];for(var i=0;i<rs.length;i++){var p=rs[i].cornerPositions||[],x=Number(p[0]);if(!isFinite(x))continue;t++;if(x===1)c.front++;else if(x<=4)c.stalk++;else if(x<=7)c.mid++;else c.close++}var d=t||1;return{front:c.front/d,stalk:c.stalk/d,mid:c.mid/d,close:c.close/d}}\nfunction fadeRate(h){var rs=(h&&h.recentRaces)||[],eligible=[],i;for(i=0;i<rs.length;i++){var p=rs[i].cornerPositions||[];if(Number(p[0])<=4)eligible.push(rs[i])}if(!eligible.length)return 0;var faded=0;for(i=0;i<eligible.length;i++){var r=eligible[i],cp=r.cornerPositions||[],first=Number(cp[0]),last=Number(cp[cp.length-1]),fin=Number(r.finish);if((isFinite(last)&&last>=first+2)||(isFinite(fin)&&fin>=first+3))faded++}return faded/eligible.length}\nfunction styleScore(h){var r=styleRates(h);return r.front+2*r.stalk+3*r.mid+4*r.close}\nfunction expected(s){if(s<1.6)return"逃げ";if(s<2.35)return"先行";if(s<3.1)return"好位〜差し";return"後方"}\nfunction styleMap(horses){var out=[];for(var i=0;i<horses.length;i++){var h=horses[i],r=styleRates(h),s=styleScore(h);out.push({horse:h,score:s,front:r.front,stalk:r.stalk,mid:r.mid,close:r.close,fade:fadeRate(h),expected:expected(s)})}out.sort(function(a,b){return Number(a.horse.horseNumber)-Number(b.horse.horseNumber)});return out}\nfunction paceRows(rows){return rows.slice().sort(function(a,b){return a.score-b.score||Number(a.horse.horseNumber)-Number(b.horse.horseNumber)})}\nfunction occupancy(horses){var early=[],moved=[];for(var i=0;i<horses.length;i++){var rr=(horses[i].recentRaces||[])[0],p=rr&&rr.cornerPositions||[];if(!p.length)continue;var any=false;for(var j=0;j<p.length;j++)if(Number(p[j])<=3)any=true;if(!any)continue;if(Number(p[0])<=3)early.push(horses[i].horseNumber);else moved.push(horses[i].horseNumber)}var nums=early.concat(moved).sort(function(a,b){return a-b});return{rate:horses.length?nums.length/horses.length:0,nums:nums,early:early,moved:moved}}\nfunction groupsFor(rows,late){var o=paceRows(rows),n=o.length,f=Math.max(1,Math.ceil(n*.25)),s=Math.max(f+1,Math.ceil(n*.55)),a=o.slice(0,f),b=o.slice(f,s),c=o.slice(s);if(late&&c.length){var mv=c.slice(0,2).reverse();return[a,b,mv.concat(c.slice(2))]}return[a,b,c]}\nfunction buildStages(rows){return[["スタート〜100m",groupsFor(rows,false)],["最初のコーナー",groupsFor(rows,false)],["向正面",groupsFor(rows,true)],["3〜4角",groupsFor(rows,true)],["直線",groupsFor(rows,true)]]}\nfunction scenarios(rows,occ){var ordered=paceRows(rows),front=ordered.filter(function(r){return r.score<2.35}),high=front.filter(function(r){return r.fade>=.5}).length,a=40,c=20;if(front.length<=2){a+=10;c-=5}if(high>=2){c+=10;a-=5}if(occ.rate>=.6){c+=5;a-=5}a=Math.max(15,Math.min(60,a));c=Math.max(10,Math.min(45,c));var b=100-a-c;return[{code:"A",title:"前残り",prob:a,horses:ordered.filter(function(r){return r.score<2.8}).slice(0,4).map(function(r){return r.horse})},{code:"B",title:"平均",prob:b,horses:ordered.slice(0,5).map(function(r){return r.horse})},{code:"C",title:"前崩れ",prob:c,horses:ordered.slice().sort(function(x,y){return y.score-x.score}).slice(0,4).map(function(r){return r.horse})}]}\nfunction clamp01(v){return Math.max(0,Math.min(1,Number(v)||0))}\nfunction winRate(s){if(!s||!s.starts)return 0;return (s.wins||0)/s.starts}\nfunction placeRate(s){if(!s||!s.starts)return 0;return ((s.wins||0)+(s.seconds||0)+(s.thirds||0))/s.starts}\nfunction statsStrength(s){return clamp01(placeRate(s)*.7+winRate(s)*.3)}\nfunction finishQuality(f){f=Number(f);if(!isFinite(f)||f<=0)return .35;return clamp01(1-(f-1)/11)}\nfunction wetGroup(c){c=String(c||"");if(c.indexOf("不良")>=0||c.indexOf("重")>=0)return 2;if(c.indexOf("稍")>=0)return 1;return 0}\nfunction conditionSimilarity(a,b){if(!a&&!b)return .5;if(String(a||"")===String(b||""))return 1;return wetGroup(a)===wetGroup(b)?.65:.15}\nfunction recentFormScore(h){var rs=(h.recentRaces||[]).slice(0,5),weights=[1,.88,.76,.66,.56],sum=0,w=0;for(var i=0;i<rs.length;i++){sum+=finishQuality(rs[i].finish)*weights[i];w+=weights[i]}return w?sum/w:.4}\nfunction eligibleSpeedRuns(h,race){var rs=h.recentRaces||[],out=[],target=Number(race.distance)||0;for(var i=0;i<rs.length;i++){var d=Number(rs[i].distance)||0,t=Number(rs[i].timeSeconds)||0;if(!d||!t)continue;var diff=target?Math.abs(d-target)/target:0;if(diff<=.25)out.push(d/t)}return out}\nfunction speedScores(race){var hs=race.horses||[],raw={},vals=[];for(var i=0;i<hs.length;i++){var a=eligibleSpeedRuns(hs[i],race);if(a.length){var best=Math.max.apply(null,a);raw[String(hs[i].horseNumber)]=best;vals.push(best)}}if(vals.length<2){var neutral={};for(i=0;i<hs.length;i++)neutral[String(hs[i].horseNumber)]=.5;return neutral}var lo=Math.min.apply(null,vals),hi=Math.max.apply(null,vals),out={};for(i=0;i<hs.length;i++){var k=String(hs[i].horseNumber),v=raw[k];out[k]=isFinite(v)&&hi>lo?clamp01((v-lo)/(hi-lo)):.45}return out}\nfunction conditionFit(h,race){var rs=(h.recentRaces||[]).slice(0,5),target=Number(race.distance)||0,sum=0,w=0;for(var i=0;i<rs.length;i++){var rr=rs[i],d=Number(rr.distance)||0,dist=target&&d?clamp01(1-Math.abs(d-target)/Math.max(300,target*.3)):.35,tr=String(rr.track||"")===String(race.track||"")?1:.2,cond=conditionSimilarity(rr.condition,race.condition),wea=String(rr.weather||"")===String(race.weather||"")?1:.35,sea=season(rr.date)===season(race.date)?1:.45,match=.36*dist+.24*tr+.20*cond+.10*wea+.10*sea,rec=.95-i*.1;sum+=finishQuality(rr.finish)*match*rec;w+=match*rec}return w?clamp01(sum/w):.4}\nfunction prizeScores(hs){var logs=[],i;for(i=0;i<hs.length;i++)logs.push(Math.log1p(Math.max(0,Number(hs[i].prizeMoneyAtRace)||0)));var lo=Math.min.apply(null,logs),hi=Math.max.apply(null,logs),out={};for(i=0;i<hs.length;i++)out[String(hs[i].horseNumber)]=hi>lo?clamp01((logs[i]-lo)/(hi-lo)):.5;return out}\nfunction profileWeightScores(hs){var all=[],groups={},i;for(i=0;i<hs.length;i++){var w=Number(hs[i].carriedWeight);if(isFinite(w))all.push(w);var g=String(hs[i].sex||"")+"/"+String(hs[i].age||"");if(!groups[g])groups[g]=[];if(isFinite(w))groups[g].push(w)}var avg=all.length?all.reduce(function(a,b){return a+b},0)/all.length:55,out={};for(i=0;i<hs.length;i++){var h=hs[i],ww=Number(h.carriedWeight),gg=String(h.sex||"")+"/"+String(h.age||""),ga=groups[gg]&&groups[gg].length?groups[gg].reduce(function(a,b){return a+b},0)/groups[gg].length:avg;if(!isFinite(ww)){out[String(h.horseNumber)]=.5;continue}out[String(h.horseNumber)]=.65*clamp01(.5+(avg-ww)/8)+.35*clamp01(.5+(ga-ww)/6)}return out}\nfunction scenarioFitFor(row,scs){var s=row.score,fade=row.fade,front=clamp01((3.15-s)/2.15)*(1-.45*fade),balanced=clamp01(1-Math.abs(s-2.45)/1.7)*(1-.18*fade),close=clamp01((s-1.65)/2.35)*(.75+.25*(1-fade)),a=0,b=0,c=0;for(var i=0;i<scs.length;i++){if(scs[i].code==="A")a=scs[i].prob/100;else if(scs[i].code==="B")b=scs[i].prob/100;else if(scs[i].code==="C")c=scs[i].prob/100}return clamp01(front*a+balanced*b+close*c)}\nfunction marks(race,rows,scs){var hs=race.horses||[],pScores=prizeScores(hs),wScores=profileWeightScores(hs),spd=speedScores(race),rowBy={},i;for(i=0;i<rows.length;i++)rowBy[String(rows[i].horse.horseNumber)]=rows[i];var arr=[];for(i=0;i<hs.length;i++){var h=hs[i],k=String(h.horseNumber),row=rowBy[k]||{score:styleScore(h),fade:fadeRate(h)},scenario=scenarioFitFor(row,scs),form=recentFormScore(h),speed=spd[k]==null?.45:spd[k],cond=conditionFit(h,race),prize=pScores[k]==null?.5:pScores[k],jockey=statsStrength(h.jockeyStats),trainer=statsStrength(h.trainerStats),survive=clamp01(1-fadeRate(h)),profile=wScores[k]==null?.5:wScores[k];var total=30*scenario+12*form+8*speed+12*cond+10*prize+8*jockey+6*trainer+8*survive+6*profile;arr.push({h:h,score:total})}arr.sort(function(a,b){return b.score-a.score||Number(a.h.horseNumber)-Number(b.h.horseNumber)});var sy=["◎","○","▲","☆","△","注"],out=[];for(i=0;i<sy.length&&i<arr.length;i++)out.push([sy[i],arr[i].h]);return out}\nfunction predict(r){var rows=styleMap(r.horses||[]),occ=occupancy(r.horses||[]),scs=scenarios(rows,occ);return{rows:rows,occ:occ,stages:buildStages(rows),scenarios:scs,marks:marks(r,rows,scs)}}\nfunction isFinal(r){return !!(r&&r.result&&r.result.status==="確定"&&(r.result.finishers||[]).length)}\nfunction snapshotKey(r){return "keiba-prediction:"+r.id}\nfunction reviewKey(r){return "keiba-review:"+r.id}\nfunction makeSnapshot(r,p){var ordered=paceRows(p.rows),markRows=p.marks.map(function(m){return{symbol:m[0],horseNumber:Number(m[1].horseNumber),name:m[1].name}}),scenarioRows=p.scenarios.map(function(s){return{code:s.code,title:s.title,prob:s.prob}}),exp={};for(var i=0;i<p.rows.length;i++)exp[String(p.rows[i].horse.horseNumber)]=p.rows[i].expected;return{savedAt:new Date().toISOString(),marks:markRows,scenarios:scenarioRows,predictedLead:ordered.length?Number(ordered[0].horse.horseNumber):null,expected:exp}}\nfunction storedJSON(k){try{var v=localStorage.getItem(k);return v?JSON.parse(v):null}catch(e){return null}}\nfunction setStored(k,v){try{localStorage.setItem(k,JSON.stringify(v));return true}catch(e){return false}}\nfunction predictionForReview(r,p){var k=snapshotKey(r),old=storedJSON(k);if(!isFinal(r)){var cur=makeSnapshot(r,p);setStored(k,cur);return{snapshot:cur,source:"事前保存"}}if(old)return{snapshot:old,source:"事前保存"};return{snapshot:makeSnapshot(r,p),source:"結果後の再計算"}}\nfunction actualScenario(r){var fs=(r.result&&r.result.finishers)||[],top=fs.slice(0,3),field=Math.max(1,(r.horses||[]).length),line=Math.max(3,Math.ceil(field*.35)),front=0,wpos=null;for(var i=0;i<top.length;i++){var cp=top[i].cornerPositions||[],x=Number(cp[0]);if(isFinite(x)&&x<=line)front++;if(i===0)wpos=x}if(front>=2&&isFinite(wpos)&&wpos<=line)return"A";if(front<=1)return"C";return"B"}\nfunction actualLeader(r){var fs=(r.result&&r.result.finishers)||[],best=null,bp=999;for(var i=0;i<fs.length;i++){var cp=fs[i].cornerPositions||[],x=Number(cp[0]);if(isFinite(x)&&x<bp){bp=x;best=Number(fs[i].horseNumber)}}return best}\nfunction resultDiff(r,p,info){var fs=(r.result&&r.result.finishers)||[],top=fs.slice(0,3),snap=info.snapshot||{},map={},issues=[];for(var i=0;i<(snap.marks||[]).length;i++)map[String(snap.marks[i].horseNumber)]=snap.marks[i].symbol;var winner=top[0],second=top[1],third=top[2],predWin=snap.marks&&snap.marks[0];if(winner&&(!predWin||Number(predWin.horseNumber)!==Number(winner.horseNumber)))issues.push("1着適性：◎"+(predWin?circled(predWin.horseNumber)+predWin.name:"—")+" → 実1着 "+circled(winner.horseNumber)+winner.name+"（"+(map[String(winner.horseNumber)]||"無印")+"）");var ps=(snap.scenarios||[]).slice().sort(function(a,b){return b.prob-a.prob})[0],as=actualScenario(r);if(ps&&ps.code!==as)issues.push("展開：予測 "+ps.code+" → 実際 "+as);var pl=snap.predictedLead,al=actualLeader(r);if(pl&&al&&Number(pl)!==Number(al))issues.push("ハナ：予測 "+circled(pl)+" → 実際 "+circled(al));if(second){var sm=map[String(second.horseNumber)];if(!sm||["○","▲","☆"].indexOf(sm)<0)issues.push("2着適性：実2着 "+circled(second.horseNumber)+second.name+"（"+(sm||"無印")+"）を上位2着候補に置けず")}if(third&&!map[String(third.horseNumber)])issues.push("3着取りこぼし："+circled(third.horseNumber)+third.name+"が無印");if(!issues.length)issues.push("大きなズレなし");return issues}\nfunction header(title,back,sub){return \'<header class="header"><div class="header-row">\'+(back?\'<button class="back" data-action="back">‹</button>\':\'\')+\'<div class="header-title"><h1>\'+esc(title)+\'</h1><small>\'+esc(sub||"競馬展開AI")+\'</small></div><button class="reload" data-action="reload">↻</button></div></header>\'}\nfunction renderHome(){var all=state.circuit==="中央"?CENTRAL:LOCAL,venues=[];for(var i=0;i<all.length;i++){var t=all[i],n=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===t}).length;if(n)venues.push([t,n])}var empty=state.circuit==="中央"?\'中央本番データ源が未接続、またはこの日の開催データがありません\':\'この日の取得データはありません\';return \'<div class="shell">\'+header("レース選択",false)+\'<main class="main"><section class="card"><div class="setup"><div><div class="label">日付</div><input id="date" class="date" type="date" value="\'+esc(state.date)+\'"></div><div><div class="label">区分</div><div class="segment"><button data-circuit="中央" class="\'+(state.circuit===\'中央\'?\'active\':\'\')+\'">中央</button><button data-circuit="地方" class="\'+(state.circuit===\'地方\'?\'active\':\'\')+\'">地方</button></div></div></div></section><section class="card"><div class="row between"><h2>開催場</h2><span class="pill">\'+state.races.filter(function(r){return r.circuit===state.circuit}).length+\'R</span></div>\'+(state.loading?\'<div class="empty">読込中…</div>\':state.error?\'<div class="notice">\'+esc(state.error)+\'</div>\':venues.length?\'<div class="venue-grid">\'+venues.map(function(v){return \'<button class="venue" data-track="\'+esc(v[0])+\'"><div class="name">\'+esc(v[0])+\'</div><div class="count">\'+v[1]+\'レース</div></button>\'}).join(\'\')+\'</div>\':\'<div class="empty">\'+empty+\'</div>\')+\'</section></main></div>\'}\nfunction resultShort(r){if(!isFinal(r))return\'\';var f=(r.result.finishers||[]).slice(0,3);return \'<span class="race-result">確定 \'+f.map(function(x){return x.horseNumber}).join(\'-\')+\'</span>\'}\nfunction renderVenue(){var rs=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===state.selectedTrack}).sort(function(a,b){return a.raceNumber-b.raceNumber}),by={};for(var i=0;i<rs.length;i++)by[rs[i].raceNumber]=rs[i];var list=\'\';for(i=1;i<=12;i++){var r=by[i];list+=r?\'<button class="race" data-race="\'+esc(r.id)+\'"><span>\'+i+\'R \'+esc(r.title)+\'</span><span>\'+(resultShort(r)||\'›\')+\'</span></button>\':\'<button class="race disabled" disabled>\'+i+\'R\u3000未取得</button>\'}return \'<div class="shell">\'+header(state.selectedTrack,true,state.date+\'・\'+state.circuit)+\'<main class="main"><section class="card"><div class="race-list">\'+list+\'</div></section></main></div>\'}\nfunction queueHtml(groups){var html=[];for(var i=0;i<groups.length;i++){var g=groups[i];if(!g.length)continue;html.push(\'<span class="queue-group">\'+g.map(function(x){return badge(x.horse,\'queue-badge\')}).join(\'\')+\'</span>\')}return html.join(\'<span class="arrow">→</span>\')}\nfunction renderResult(r,p){if(!isFinal(r))return\'\';var fs=(r.result.finishers||[]).slice(0,3),info=predictionForReview(r,p),diff=resultDiff(r,p,info),memo=\'\';try{memo=localStorage.getItem(reviewKey(r))||\'\'}catch(e){}var rows=fs.map(function(x){var h=horseByNo(r,x.horseNumber)||x;return \'<div class="result-row"><span class="finish-pos">\'+x.finish+\'着</span>\'+badge(h)+\'<span class="result-name">\'+esc(x.name||h.name||\'\')+\'</span><span class="result-time">\'+fmtTime(x.timeSeconds)+\'</span></div>\'}).join(\'\');return \'<section class="card"><div class="section-title">結果</div><div class="result-list">\'+rows+\'</div><div class="review-box"><div class="review-title">結果とのズレ</div><div class="diff-list">\'+diff.map(function(x){return \'<div class="diff-item">\'+esc(x)+\'</div>\'}).join(\'\')+\'</div><div class="review-meta">比較元：\'+esc(info.source)+\'</div><textarea id="review-memo" class="review-text" placeholder="回顧メモを残す">\'+esc(memo)+\'</textarea><button id="review-save" class="save-review">メモ保存</button><span id="review-status" class="save-status"></span></div></section>\'}\nfunction renderRace(){var r=state.selectedRace,p=predict(r);predictionForReview(r,p);var rows=p.rows.slice().sort(function(a,b){return Number(a.horse.horseNumber)-Number(b.horse.horseNumber)}),early=p.occ.early.map(circled).join(\' \'),moved=p.occ.moved.map(circled).join(\' \');var style=rows.map(function(x){var h=x.horse;return \'<div class="style-row"><div class="style-top">\'+badge(h)+\'<span class="horse-name">\'+esc(h.name)+\'</span><span class="score">点 \'+x.score.toFixed(2)+\'</span><span class="expected">\'+esc(x.expected)+\'</span></div><div class="rates"><span class="rate"><small>逃</small>\'+pct(x.front)+\'</span><span class="rate"><small>先</small>\'+pct(x.stalk)+\'</span><span class="rate"><small>差</small>\'+pct(x.mid)+\'</span><span class="rate"><small>追</small>\'+pct(x.close)+\'</span><span class="rate"><small>下</small>\'+pct(x.fade)+\'</span></div></div>\'}).join(\'\');var stages=p.stages.map(function(s){return \'<div class="stage"><div class="stage-title">\'+esc(s[0])+\'</div><div class="stage-line">\'+queueHtml(s[1])+\'</div></div>\'}).join(\'\');var sc=p.scenarios.map(function(s){return \'<div class="scenario"><div class="scenario-title">\'+s.code+\' \'+esc(s.title)+\'</div><div class="prob">\'+s.prob+\'%</div><div class="scenario-horses">\'+s.horses.map(function(h){return badge(h)}).join(\'\')+\'</div></div>\'}).join(\'\');var mk=p.marks.map(function(m){return \'<div class="mark"><span class="mark-symbol">\'+m[0]+\'</span>\'+badge(m[1])+\'<span class="horse-name">\'+esc(m[1].name)+\'</span></div>\'}).join(\'\');var data=(r.horses||[]).slice().sort(function(a,b){return a.horseNumber-b.horseNumber}).map(function(h){var rec=(h.recentRaces||[]).map(function(rr){return \'<div class="recent">\'+esc(rr.date)+\' \'+esc(rr.track)+\' \'+esc(rr.distance)+\'m\u3000\'+esc(rr.finish)+\'着 / \'+fmtTime(rr.timeSeconds)+\'<br><span class="muted">\'+esc(rr.condition)+\'・\'+esc(rr.weather||\'不明\')+\'・\'+season(rr.date)+\'・通過 \'+esc((rr.cornerPositions||[]).join(\'-\')||\'—\')+\'</span></div>\'}).join(\'\');return \'<details class="horse-card"><summary>\'+badge(h)+\'<span class="horse-name">\'+esc(h.name)+\'</span><span>\'+esc(h.sex)+esc(h.age)+\' \'+esc(h.carriedWeight)+\'kg</span></summary><div class="horse-detail"><div>騎手：\'+esc(h.jockey)+\'\u3000\'+(h.jockeyStats&&h.jockeyStats.starts?h.jockeyStats.starts+\'戦 \'+h.jockeyStats.wins+\'勝 / 複勝率 \'+pct(placeRate(h.jockeyStats)):\'成績データなし\')+\'</div><div>調教師：\'+esc(h.trainer)+\'\u3000\'+(h.trainerStats&&h.trainerStats.starts?h.trainerStats.starts+\'戦 \'+h.trainerStats.wins+\'勝 / 複勝率 \'+pct(placeRate(h.trainerStats)):\'成績データなし\')+\'</div><div>このレース時点の獲得賞金：\'+money(h.prizeMoneyAtRace)+\'円</div>\'+rec+\'</div></details>\'}).join(\'\');return \'<div class="shell">\'+header(r.track+\' \'+r.raceNumber+\'R\',true,r.title+\'｜\'+r.distance+\'m・\'+r.condition+\'・\'+(r.weather||\'不明\'))+\'<main class="main"><section class="card"><div class="metrics"><div class="metric"><b>\'+r.distance+\'m</b><span>距離</span></div><div class="metric"><b>\'+esc(r.condition)+\'</b><span>馬場</span></div><div class="metric"><b>\'+esc(r.weather||\'不明\')+\'</b><span>天候</span></div><div class="metric"><b>\'+season(r.date)+\'</b><span>季節</span></div><div class="metric"><b>\'+r.horses.length+\'頭</b><span>頭数</span></div></div><div class="source-tag">\'+esc(r.source||\'\')+\'</div></section><section class="card"><div class="section-title">1\u3000先行馬占有率</div><div class="big-number">\'+pct(p.occ.rate)+\'</div><div class="muted">対象：\'+(p.occ.nums.map(circled).join(\' \')||\'—\')+\'</div><div class="muted">最初から前：\'+(early||\'—\')+\'\u3000途中進出：\'+(moved||\'—\')+\'</div></section><section class="card"><div class="section-title">2\u3000脚質マップ</div><div class="style-list">\'+style+\'</div></section><section class="card"><div class="section-title">3\u3000隊列</div>\'+stages+\'</section><section class="card"><div class="section-title">4\u3000ABC</div><div class="scenario-grid">\'+sc+\'</div></section><section class="card"><div class="section-title">5\u3000印</div><div class="marks">\'+mk+\'</div></section>\'+renderResult(r,p)+\'<section class="card"><h2>出馬データ</h2>\'+data+\'</section></main></div>\'}\nfunction render(){try{if(state.selectedRace)app.innerHTML=renderRace();else if(state.selectedTrack)app.innerHTML=renderVenue();else app.innerHTML=renderHome();bind()}catch(e){app.innerHTML=\'<div class="notice" style="margin:20px">表示エラー：\'+esc(e&&e.message||e)+\'<br><button onclick="location.reload()">再読み込み</button></div>\'}}\nfunction bind(){var els=document.querySelectorAll(\'[data-circuit]\'),i;for(i=0;i<els.length;i++)els[i].onclick=function(){state.circuit=this.getAttribute(\'data-circuit\');state.selectedTrack=null;state.selectedRace=null;render()};var d=document.getElementById(\'date\');if(d)d.onchange=function(){state.date=this.value;state.selectedTrack=null;state.selectedRace=null;loadRaces()};els=document.querySelectorAll(\'[data-track]\');for(i=0;i<els.length;i++)els[i].onclick=function(){state.selectedTrack=this.getAttribute(\'data-track\');render()};els=document.querySelectorAll(\'[data-race]\');for(i=0;i<els.length;i++)els[i].onclick=function(){var id=this.getAttribute(\'data-race\');state.selectedRace=state.races.find(function(r){return String(r.id)===String(id)});render()};els=document.querySelectorAll(\'[data-action="back"]\');for(i=0;i<els.length;i++)els[i].onclick=function(){if(state.selectedRace)state.selectedRace=null;else state.selectedTrack=null;render()};els=document.querySelectorAll(\'[data-action="reload"]\');for(i=0;i<els.length;i++)els[i].onclick=loadRaces;var save=document.getElementById(\'review-save\');if(save)save.onclick=function(){var ta=document.getElementById(\'review-memo\'),st=document.getElementById(\'review-status\');try{localStorage.setItem(reviewKey(state.selectedRace),ta?ta.value:\'\');if(st)st.textContent=\'保存した\'}catch(e){if(st)st.textContent=\'保存できませんでした\'}}}\nfunction loadRaces(){state.loading=true;state.error=null;render();var ctrl=window.AbortController?new AbortController():null,timer=ctrl?setTimeout(function(){ctrl.abort()},14000):null;fetch(\'/api/v1/races?date=\'+encodeURIComponent(state.date),{cache:\'no-store\',signal:ctrl?ctrl.signal:undefined}).then(function(res){if(timer)clearTimeout(timer);if(!res.ok)throw new Error(\'API \'+res.status);return res.json()}).then(function(body){state.races=Array.isArray(body)?body:(body.races||[]);state.loading=false;state.error=null;state.retries=0;render();if(state.circuit===\'地方\'&&!state.races.some(function(r){return r.circuit===\'地方\'})&&state.retries<3){state.retries++;setTimeout(loadRaces,5000)}}).catch(function(e){if(timer)clearTimeout(timer);state.loading=false;state.error=\'データ取得待機中。↻で再読込できます\';render()})}\nwindow.onerror=function(msg){if(app)app.innerHTML=\'<div class="notice" style="margin:20px">表示エラー：\'+esc(msg)+\'<br><button onclick="location.reload()">再読み込み</button></div>\';return false};\nrender();setTimeout(loadRaces,0);\n})();\n'

CSS += r'''
/* UI v5 — thin typography; only horse names are bold */
.prediction-shell,
.prediction-shell button,
.prediction-shell input,
.prediction-shell select,
.prediction-shell h1,
.prediction-shell h2,
.prediction-shell h3,
.prediction-shell b,
.prediction-shell strong,
.prediction-shell .section-title,
.prediction-shell .pill,
.prediction-shell .metric b,
.prediction-shell .metric span,
.prediction-shell .stage b,
.prediction-shell .stage div,
.prediction-shell .scenario b,
.prediction-shell .scenario .scenario-name,
.prediction-shell .scenario .prob,
.prediction-shell .scenario .horses,
.prediction-shell .mark-symbol,
.prediction-shell .style-rank,
.prediction-shell .style-score,
.prediction-shell .style-expected,
.prediction-shell .style-rate b,
.prediction-shell .style-rate span,
.prediction-shell .horse-no,
.prediction-shell .horse-summary-meta,
.prediction-shell .statline,
.prediction-shell .recent,
.prediction-shell .back-btn {
  font-weight: 400 !important;
}

/* Horse names alone get emphasis. */
.prediction-shell .style-horse,
.prediction-shell .horse-summary-name,
.prediction-shell .mark-row strong {
  font-weight: 700 !important;
}

/* Keep 10・11・12 the same visual weight and width as single-digit numbers. */
.prediction-shell .horse-no {
  width: 32px;
  min-width: 32px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
}
'''

# --- UI v4: horse-number map + larger race analysis + frame colors -----
CSS += r'''
/* UI v4 - frame colors, readable iPhone prediction */
.waku-0 { --waku-color:#94a3b8; --waku-bg:#e2e8f0; --waku-text:#0f172a; }
.waku-1 { --waku-color:#a3a3a3; --waku-bg:#ffffff; --waku-text:#111827; }
.waku-2 { --waku-color:#111827; --waku-bg:#111827; --waku-text:#ffffff; }
.waku-3 { --waku-color:#dc2626; --waku-bg:#dc2626; --waku-text:#ffffff; }
.waku-4 { --waku-color:#2563eb; --waku-bg:#2563eb; --waku-text:#ffffff; }
.waku-5 { --waku-color:#eab308; --waku-bg:#facc15; --waku-text:#111827; }
.waku-6 { --waku-color:#16a34a; --waku-bg:#16a34a; --waku-text:#ffffff; }
.waku-7 { --waku-color:#f97316; --waku-bg:#f97316; --waku-text:#111827; }
.waku-8 { --waku-color:#ec4899; --waku-bg:#ec4899; --waku-text:#ffffff; }
.horse-no { display:inline-grid; place-items:center; flex:0 0 auto; width:30px; height:30px; border-radius:7px; background:var(--waku-bg); color:var(--waku-text); border:1px solid var(--waku-color); font-size:15px; font-weight:950; line-height:1; box-shadow:0 1px 2px rgba(15,23,42,.12); }
.horse-accent { border-left:5px solid var(--waku-color) !important; }
.style-map-top { grid-template-columns:auto minmax(0,1fr) auto auto; }
.style-map-row .style-horse { font-size:14px; }
.style-map-row .style-score { font-size:14px; white-space:nowrap; }
.queue-line { font-size:19px; font-weight:900; line-height:1.8; letter-spacing:.01em; }
.queue-line .horse-no { width:29px; height:29px; font-size:14px; margin:0 1px; vertical-align:middle; }
.scenario { border:1px solid var(--line); }
.scenario .scenario-name { font-weight:900; font-size:16px; }
.scenario .prob { font-size:30px; }
.scenario .horses { font-size:17px; line-height:1.6; }
.scenario .horses .horse-no { width:28px; height:28px; font-size:14px; margin-right:2px; }
.mark-row .horse-no { width:27px; height:27px; font-size:13px; }
.horse-card summary { list-style:none; }
.horse-card summary::-webkit-details-marker { display:none; }
.horse-summary { display:flex; align-items:center; gap:8px; min-width:0; }
.horse-summary-name { min-width:0; font-weight:900; }
.horse-summary-meta { color:var(--muted); font-weight:700; margin-left:auto; white-space:nowrap; }
@media (max-width:620px) {
  .prediction-shell .style-map-row { padding:9px 9px; }
  .prediction-shell .style-map-top { grid-template-columns:auto minmax(0,1fr) auto; gap:7px; }
  .prediction-shell .style-expected { grid-column:2 / 4; justify-self:start; font-size:11px; padding:4px 7px; }
  .prediction-shell .style-rate { padding:6px 2px; }
  .prediction-shell .style-rate b { font-size:10px; }
  .prediction-shell .style-rate span { font-size:12px; }
  .prediction-shell .stage { padding:9px 0; }
  .prediction-shell .stage b { font-size:11px; margin-bottom:3px; }
  .prediction-shell .stage div, .prediction-shell .queue-line { font-size:18px; line-height:1.75; }
  .prediction-shell .scenario-grid { grid-template-columns:1fr !important; gap:8px; }
  .prediction-shell .scenario { min-height:0; padding:10px 12px; border-radius:12px; display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:4px 10px; }
  .prediction-shell .scenario .scenario-name { font-size:16px; }
  .prediction-shell .scenario .prob { font-size:28px; line-height:1; }
  .prediction-shell .scenario .horses { grid-column:1 / -1; margin-top:3px; font-size:17px; }
  .prediction-shell .mark-row { padding:8px 8px; }
  .prediction-shell .mark-row strong { font-size:13px; }
  .prediction-shell .horse-card { padding:10px; margin-top:7px; }
  .prediction-shell .horse-card summary { font-size:15px; line-height:1.45; }
  .prediction-shell .horse-summary-meta { font-size:12px; }
  .prediction-shell .horse-detail { gap:10px; padding-top:11px; }
  .prediction-shell .statline { font-size:14px; line-height:1.5; }
  .prediction-shell .recent { font-size:13px; line-height:1.55; padding-top:9px; }
  .prediction-shell .recent .muted { font-size:12px; }
}
'''

JS += r'''
// UI v4 overrides
function wakuNo(h) { const n=Number(h?.frameNumber||0); return n>=1&&n<=8?n:0; }
function wakuClass(h) { return `waku-${wakuNo(h)}`; }
function horseBadge(h) { return `<span class="horse-no ${wakuClass(h)}">${h.horseNumber}</span>`; }
function horseByNo(race,no) { return (race.horses||[]).find(h=>Number(h.horseNumber)===Number(no)); }
function badgeByNo(race,no) { const h=horseByNo(race,no); return h?horseBadge(h):`<span class="horse-no waku-0">${no}</span>`; }
function colorizeQueue(race,text) { let html=String(text||"—"); const horses=[...(race.horses||[])].sort((a,b)=>b.horseNumber-a.horseNumber); for(const h of horses) html=html.split(circled(h.horseNumber)).join(horseBadge(h)); return html; }
function scenarioHorseBadges(race,nums) { return (nums||[]).map(n=>badgeByNo(race,n)).join(" ")||"—"; }

function renderRace(){
  const r=state.selectedRace, p=predict(r);
  const early=p.occ.early.map(circled).join(' '), moved=p.occ.moved.map(circled).join(' ');
  const mapRows=[...p.rows].sort((a,b)=>a.horse.horseNumber-b.horse.horseNumber);
  const horseRows=[...r.horses].sort((a,b)=>a.horseNumber-b.horseNumber);
  return `<div class="shell prediction-shell">${header(`${r.track} ${r.raceNumber}R`,true, `${r.title}｜${r.distance}m・${r.condition}・${r.weather||'不明'}`)}<main class="main">
    <section class="card"><div class="row between"><div><h2>${r.title}</h2><div class="muted">${r.date} ${r.startTime}</div></div><span class="pill">${r.circuit}</span></div><div class="metrics" style="margin-top:10px"><div class="metric"><b>${r.distance}m</b><span>距離</span></div><div class="metric"><b>${r.condition}</b><span>馬場</span></div><div class="metric"><b>${r.weather||'不明'}</b><span>天候</span></div><div class="metric"><b>${seasonOf(r.date)}</b><span>季節</span></div><div class="metric"><b>${r.horses.length}頭</b><span>頭数</span></div></div></section>
    <section class="card"><div class="section-title">1　先行馬占有率</div><div style="font-size:32px;font-weight:900">${pct(p.occ.rate)}</div><div class="muted">対象：${p.occ.nums.map(circled).join(' ')||'—'}</div><div class="muted" style="font-size:12px;margin-top:4px">最初から前：${early||'—'}　途中進出：${moved||'—'}</div></section>
    <section class="card"><div class="section-title">2　脚質マップ</div><div class="muted" style="font-size:11px;margin-bottom:7px">馬番順｜脚質点は低いほど前</div><div class="style-map-list">${mapRows.map(x=>`<div class="style-map-row horse-accent ${wakuClass(x.horse)}"><div class="style-map-top">${horseBadge(x.horse)}<span class="style-horse">${x.horse.name}</span><span class="style-score">点 ${x.score.toFixed(2)}</span><span class="style-expected">${x.expected}</span></div><div class="style-rate-grid"><span class="style-rate"><b>逃</b><span>${pct(x.front)}</span></span><span class="style-rate"><b>先</b><span>${pct(x.stalk)}</span></span><span class="style-rate"><b>差</b><span>${pct(x.mid)}</span></span><span class="style-rate"><b>追</b><span>${pct(x.close)}</span></span><span class="style-rate"><b>下</b><span>${pct(x.fade)}</span></span></div></div>`).join('')}</div></section>
    <section class="card"><div class="section-title">3　隊列</div>${p.stages.map(([n,v])=>`<div class="stage"><b>${n}</b><div class="queue-line">${colorizeQueue(r,v)}</div></div>`).join('')}</section>
    <section class="card"><div class="section-title">4　ABC</div><div class="scenario-grid">${p.scenarios.map(s=>`<div class="scenario"><div class="scenario-name">${s.code} ${s.title}</div><div class="prob">${s.prob}%</div><div class="horses">${scenarioHorseBadges(r,s.horses)}</div></div>`).join('')}</div></section>
    <section class="card"><div class="section-title">5　印</div><div class="marks">${p.marks.map(([s,h])=>`<div class="mark-row horse-accent ${wakuClass(h)}"><div class="mark-symbol">${s}</div>${horseBadge(h)}<div><strong>${h.name}</strong><div class="muted" style="font-size:12px">${h.sex}${h.age}・${h.carriedWeight}kg・${h.jockey}</div></div></div>`).join('')}</div></section>
    <section class="card"><h2 style="font-size:18px">出馬データ</h2>${horseRows.map(h=>`<details class="horse-card horse-accent ${wakuClass(h)}"><summary><span class="horse-summary">${horseBadge(h)}<span class="horse-summary-name">${h.name}</span><span class="horse-summary-meta">${h.sex}${h.age} ${h.carriedWeight}kg</span></span></summary><div class="horse-detail"><div class="statline">騎手：${h.jockey}（${h.jockeyStats?.starts||0}戦 ${h.jockeyStats?.wins||0}勝 / 複勝率${pct(placeRate(h.jockeyStats))}）</div><div class="statline">調教師：${h.trainer}（${h.trainerStats?.starts||0}戦 ${h.trainerStats?.wins||0}勝 / 複勝率${pct(placeRate(h.trainerStats))}）</div><div class="statline">このレース時点の獲得賞金：${fmtMoney(h.prizeMoneyAtRace)}円</div>${(h.recentRaces||[]).map(rr=>`<div class="recent"><b>${rr.date} ${rr.track} ${rr.distance}m</b>　${rr.finish}着 / ${rr.timeSeconds.toFixed(1)}秒<br><span class="muted">${rr.condition}・${rr.weather||'不明'}・${seasonOf(rr.date)}　通過 ${rr.cornerPositions?.join('-')||'—'}</span></div>`).join('')}</div></details>`).join('')}</section>
  </main></div>`;
}
'''


CSS += '/* v11: list time/status and result-first */\n.race{position:relative;overflow:hidden}\n.race.final{background:#f0fdf4;border-color:#86efac}\n.race.final:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#16a34a}\n.race-main{min-width:0;display:grid;gap:3px}\n.race-topline{display:flex;align-items:baseline;gap:7px;min-width:0}\n.race-no{font-size:17px;white-space:nowrap}\n.race-title{font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n.race-time{font-size:13px;color:#475569;white-space:nowrap}\n.time-old{text-decoration:line-through;color:#94a3b8;margin-right:5px}\n.time-changed{color:#dc2626;font-weight:500}\n.final-badge{display:inline-flex;align-items:center;justify-content:center;border:1.5px solid #16a34a;color:#15803d;background:#fff;border-radius:5px;padding:3px 7px;font-size:12px;line-height:1;white-space:nowrap}\n.race-arrow{font-size:20px;color:#94a3b8}\n.result-card{border-color:#93c5fd;background:#f8fbff}\n.result-card .section-title{font-size:20px;margin-bottom:9px}\n.result-card .review-box{background:#fff}\n.prediction-shell .result-row{padding:8px 0}\n.prediction-shell .result-name{font-size:16px}\n.prediction-shell .finish-pos{font-size:20px}\n.prediction-shell .result-time{font-size:14px}\n'
JS += '// v11 overrides: time in race list, final badge only, result first\nfunction raceTimeHtml(r){\n  const now=String(r.startTime||\'—\');\n  const original=String(r.scheduledStartTime||now||\'—\');\n  const changed=!!r.startTimeChanged || (!!original && !!now && original!==now);\n  return changed ? `<span class="race-time"><span class="time-old">${esc(original)}</span><span class="time-changed">${esc(now)} 修正</span></span>` : `<span class="race-time">${esc(now)}</span>`;\n}\nfunction renderVenue(){\n  const rs=state.races.filter(r=>r.circuit===state.circuit&&r.track===state.selectedTrack).sort((a,b)=>a.raceNumber-b.raceNumber), by={};\n  for(const r of rs) by[r.raceNumber]=r;\n  let list=\'\';\n  for(let i=1;i<=12;i++){\n    const r=by[i];\n    if(r){\n      const final=isFinal(r);\n      list+=`<button class="race ${final?\'final\':\'\'}" data-race="${esc(r.id)}"><span class="race-main"><span class="race-topline"><span class="race-no">${i}R</span><span class="race-title">${esc(r.title)}</span></span>${raceTimeHtml(r)}</span><span>${final?\'<span class="final-badge">確定</span>\':\'<span class="race-arrow">›</span>\'}</span></button>`;\n    }else{\n      list+=`<button class="race disabled" disabled><span class="race-main"><span class="race-topline"><span class="race-no">${i}R</span><span class="race-title">未取得</span></span></span></button>`;\n    }\n  }\n  return `<div class="shell">${header(state.selectedTrack,true,state.date+\'・\'+state.circuit)}<main class="main"><section class="card"><div class="race-list">${list}</div></section></main></div>`;\n}\nfunction renderRace(){\n  const r=state.selectedRace, p=predict(r);\n  const early=p.occ.early.map(circled).join(\' \'), moved=p.occ.moved.map(circled).join(\' \');\n  const mapRows=[...p.rows].sort((a,b)=>a.horse.horseNumber-b.horse.horseNumber);\n  const horseRows=[...r.horses].sort((a,b)=>a.horseNumber-b.horseNumber);\n  const resultTop=isFinal(r)?renderResult(r,p).replace(\'<section class="card">\',\'<section class="card result-card">\'):\'\';\n  return `<div class="shell prediction-shell">${header(`${r.track} ${r.raceNumber}R`,true, `${r.title}｜${r.distance}m・${r.condition}・${r.weather||\'不明\'}`)}<main class="main">\n    ${resultTop}\n    <section class="card"><div class="row between"><div><h2>${r.title}</h2><div class="muted">${r.date} ${raceTimeHtml(r)}</div></div><span class="pill">${r.circuit}</span></div><div class="metrics" style="margin-top:10px"><div class="metric"><b>${r.distance}m</b><span>距離</span></div><div class="metric"><b>${r.condition}</b><span>馬場</span></div><div class="metric"><b>${r.weather||\'不明\'}</b><span>天候</span></div><div class="metric"><b>${seasonOf(r.date)}</b><span>季節</span></div><div class="metric"><b>${r.horses.length}頭</b><span>頭数</span></div></div></section>\n    <section class="card"><div class="section-title">1\u3000先行馬占有率</div><div style="font-size:32px">${pct(p.occ.rate)}</div><div class="muted">対象：${p.occ.nums.map(circled).join(\' \')||\'—\'}</div><div class="muted" style="font-size:12px;margin-top:4px">最初から前：${early||\'—\'}\u3000途中進出：${moved||\'—\'}</div></section>\n    <section class="card"><div class="section-title">2\u3000脚質マップ</div><div class="muted" style="font-size:11px;margin-bottom:7px">馬番順｜脚質点は低いほど前</div><div class="style-map-list">${mapRows.map(x=>`<div class="style-map-row horse-accent ${wakuClass(x.horse)}"><div class="style-map-top">${horseBadge(x.horse)}<span class="style-horse">${x.horse.name}</span><span class="style-score">点 ${x.score.toFixed(2)}</span><span class="style-expected">${x.expected}</span></div><div class="style-rate-grid"><span class="style-rate"><b>逃</b><span>${pct(x.front)}</span></span><span class="style-rate"><b>先</b><span>${pct(x.stalk)}</span></span><span class="style-rate"><b>差</b><span>${pct(x.mid)}</span></span><span class="style-rate"><b>追</b><span>${pct(x.close)}</span></span><span class="style-rate"><b>下</b><span>${pct(x.fade)}</span></span></div></div>`).join(\'\')}</div></section>\n    <section class="card"><div class="section-title">3\u3000隊列</div>${p.stages.map(([n,v])=>`<div class="stage"><b>${n}</b><div class="queue-line">${colorizeQueue(r,v)}</div></div>`).join(\'\')}</section>\n    <section class="card"><div class="section-title">4\u3000ABC</div><div class="scenario-grid">${p.scenarios.map(s=>`<div class="scenario"><div class="scenario-name">${s.code} ${s.title}</div><div class="prob">${s.prob}%</div><div class="horses">${scenarioHorseBadges(r,s.horses)}</div></div>`).join(\'\')}</div></section>\n    <section class="card"><div class="section-title">5\u3000印</div><div class="marks">${p.marks.map(([s,h])=>`<div class="mark-row horse-accent ${wakuClass(h)}"><div class="mark-symbol">${s}</div>${horseBadge(h)}<div><strong>${h.name}</strong><div class="muted" style="font-size:12px">${h.sex}${h.age}・${h.carriedWeight}kg・${h.jockey}</div></div></div>`).join(\'\')}</div></section>\n    <section class="card"><h2 style="font-size:18px">出馬データ</h2>${horseRows.map(h=>`<details class="horse-card horse-accent ${wakuClass(h)}"><summary><span class="horse-summary">${horseBadge(h)}<span class="horse-summary-name">${h.name}</span><span class="horse-summary-meta">${h.sex}${h.age} ${h.carriedWeight}kg</span></span></summary><div class="horse-detail"><div class="statline">騎手：${h.jockey}（${h.jockeyStats?.starts||0}戦 ${h.jockeyStats?.wins||0}勝 / 複勝率${pct(placeRate(h.jockeyStats))}）</div><div class="statline">調教師：${h.trainer}（${h.trainerStats?.starts||0}戦 ${h.trainerStats?.wins||0}勝 / 複勝率${pct(placeRate(h.trainerStats))}）</div><div class="statline">このレース時点の獲得賞金：${fmtMoney(h.prizeMoneyAtRace)}円</div>${(h.recentRaces||[]).map(rr=>`<div class="recent"><b>${rr.date} ${rr.track} ${rr.distance}m</b>\u3000${rr.finish}着 / ${rr.timeSeconds.toFixed(1)}秒<br><span class="muted">${rr.condition}・${rr.weather||\'不明\'}・${seasonOf(rr.date)}\u3000通過 ${rr.cornerPositions?.join(\'-\')||\'—\'}</span></div>`).join(\'\')}</div></details>`).join(\'\')}</section>\n  </main></div>`;\n}\n'

MANIFEST = '{\n  "name": "競馬展開AI",\n  "short_name": "競馬展開AI",\n  "description": "中央・地方競馬の脚質マップ、隊列、ABC展開、印を確認するPWA",\n  "start_url": "./",\n  "scope": "./",\n  "display": "standalone",\n  "background_color": "#f6f7fb",\n  "theme_color": "#0f172a",\n  "lang": "ja",\n  "icons": [\n    {"src": "./assets/icon-192.png", "sizes": "192x192", "type": "image/png"},\n    {"src": "./assets/icon-512.png", "sizes": "512x512", "type": "image/png"}\n  ]\n}\n'
SW = 'self.addEventListener("install",function(){self.skipWaiting()});self.addEventListener("activate",function(e){e.waitUntil(self.registration.unregister().then(function(){return self.clients.matchAll()}).then(function(cs){cs.forEach(function(c){c.navigate(c.url)})}))});'
JS += r"""
// v12 race selection: date/circuit -> realtime -> venues
function minuteOfDay(s){var m=String(s||"").match(/^(\d{1,2}):(\d{2})/);return m?Number(m[1])*60+Number(m[2]):9999}
function jstMinuteNow(){var d=new Date(Date.now()+9*3600000);return d.getUTCHours()*60+d.getUTCMinutes()}
function liveRaceLabel(r){var diff=minuteOfDay(r.startTime)-jstMinuteNow();if(state.date!==todayJst())return "";if(diff>=0&&diff<=10)return '<span class="live-now">まもなく</span>';if(diff>10&&diff<=60)return '<span class="live-next">次走</span>';if(diff<0&&diff>=-30)return '<span class="live-running">進行中</span>';return ""}
function liveRacesForHome(){
  var rs=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime});
  rs.sort(function(a,b){return minuteOfDay(a.startTime)-minuteOfDay(b.startTime)});
  if(state.date!==todayJst()) return [];
  var now=jstMinuteNow(), near=rs.filter(function(r){var d=minuteOfDay(r.startTime)-now;return d>=-30&&d<=180});
  if(!near.length) near=rs.filter(function(r){return minuteOfDay(r.startTime)>=now}).slice(0,4);
  return near.slice(0,4);
}
function renderHome(){
  var all=state.circuit==="中央"?CENTRAL:LOCAL,venues=[];
  for(var i=0;i<all.length;i++){
    var t=all[i],n=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===t}).length;
    if(n)venues.push([t,n]);
  }
  var empty=state.circuit==="中央"?'中央本番データ源が未接続、またはこの日の開催データがありません':'この日の取得データはありません';
  var live=liveRacesForHome();
  var liveHtml='';
  if(state.loading){liveHtml='<div class="empty">読込中…</div>'}
  else if(state.date!==todayJst()){liveHtml='<div class="live-empty">当日を選ぶとリアルタイム表示します</div>'}
  else if(live.length){
    liveHtml='<div class="live-grid">'+live.map(function(r){
      return '<button class="live-race" data-race="'+esc(r.id)+'"><div class="live-top"><span class="live-track">'+esc(r.track)+' '+esc(r.raceNumber)+'R</span>'+liveRaceLabel(r)+'</div><div class="live-title">'+esc(r.title||'')+'</div><div class="live-time">'+raceTimeHtml(r)+'</div></button>';
    }).join('')+'</div>';
  }else{liveHtml='<div class="live-empty">この区分で直近の未確定レースはありません</div>'}
  return '<div class="shell">'+header("レース選択",false)+
    '<main class="main">'+
      '<section class="card home-setup"><div class="home-heading">日付・区分</div><div class="setup-grid"><div><div class="label">日付</div><input id="date" class="date" type="date" value="'+esc(state.date)+'"></div><div><div class="label">区分</div><div class="segment"><button data-circuit="中央" class="'+(state.circuit==='中央'?'active':'')+'">中央</button><button data-circuit="地方" class="'+(state.circuit==='地方'?'active':'')+'">地方</button></div></div></div></section>'+
      '<section class="card live-section"><div class="row between"><h2>リアルタイムのレース</h2><span class="live-dot">LIVE</span></div>'+liveHtml+'</section>'+
      '<section class="card"><div class="row between"><h2>開催場</h2><span class="pill">'+state.races.filter(function(r){return r.circuit===state.circuit}).length+'R</span></div>'+
        (state.loading?'<div class="empty">読込中…</div>':state.error?'<div class="notice">'+esc(state.error)+'</div>':venues.length?'<div class="venue-grid">'+venues.map(function(v){return '<button class="venue" data-track="'+esc(v[0])+'"><div class="name">'+esc(v[0])+'</div><div class="count">'+v[1]+'レース</div></button>'}).join('')+'</div>':'<div class="empty">'+empty+'</div>')+
      '</section>'+
    '</main></div>';
}
"""
CSS += r"""
/* v12 race selection layout */
.home-setup{padding:10px 11px}.home-heading{font-size:17px;margin-bottom:8px}.setup-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:9px;align-items:end}.setup-grid .date{height:42px}.setup-grid .segment button{height:42px;padding:6px 3px}.live-section h2{margin:0;font-size:18px}.live-dot{font-size:10px;line-height:1;background:#ef4444;color:white;border-radius:5px;padding:3px 6px;letter-spacing:.04em}.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.live-race{min-width:0;border:1px solid #dbe3ef;background:#fff;border-radius:11px;padding:9px;text-align:left}.live-top{display:flex;align-items:center;justify-content:space-between;gap:5px}.live-track{font-size:15px;color:#2563eb;white-space:nowrap}.live-title{font-size:11px;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:4px}.live-time{margin-top:6px;font-size:16px}.live-time .race-time{display:inline-flex;gap:5px;align-items:center}.live-now,.live-next,.live-running{font-size:9px;border-radius:999px;padding:2px 5px;white-space:nowrap}.live-now{background:#fee2e2;color:#b91c1c}.live-next{background:#dbeafe;color:#1d4ed8}.live-running{background:#dcfce7;color:#15803d}.live-empty{padding:12px 4px 4px;color:#64748b;font-size:12px;text-align:center}
@media(max-width:360px){.setup-grid{grid-template-columns:1fr}.live-grid{grid-template-columns:1fr 1fr}.live-track{font-size:14px}.live-time{font-size:15px}}
"""

SAMPLES = json.loads('[\n  {\n    "id": "demo-local-sonoda-20260925-01",\n    "date": "2026-09-25",\n    "track": "園田",\n    "raceNumber": 1,\n    "title": "C3三 デモレース",\n    "distance": 1400,\n    "condition": "良",\n    "startTime": "10:45",\n    "horses": [\n      {\n        "id": 1,\n        "horseNumber": 1,\n        "frameNumber": 1,\n        "name": "アオゾラロード",\n        "age": 4,\n        "sex": "牡",\n        "carriedWeight": 52.5,\n        "jockey": "田中騎手",\n        "trainer": "青木厩舎",\n        "jockeyStats": {\n          "starts": 43,\n          "wins": 4,\n          "seconds": 6,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 75,\n          "wins": 7,\n          "seconds": 8,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 1270000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 90.6,\n            "cornerPositions": [\n              1,\n              1,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 3,\n            "timeSeconds": 91.3,\n            "cornerPositions": [\n              1,\n              1,\n              3\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 92.0,\n            "cornerPositions": [\n              2,\n              2,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 1,\n            "timeSeconds": 92.7,\n            "cornerPositions": [\n              1,\n              1,\n              1\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              3,\n              3,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 2,\n        "horseNumber": 2,\n        "frameNumber": 2,\n        "name": "ミナミノスター",\n        "age": 5,\n        "sex": "牝",\n        "carriedWeight": 53.0,\n        "jockey": "山本騎手",\n        "trainer": "森厩舎",\n        "jockeyStats": {\n          "starts": 46,\n          "wins": 5,\n          "seconds": 8,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 80,\n          "wins": 8,\n          "seconds": 9,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 1740000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 91.2,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 91.9,\n            "cornerPositions": [\n              3,\n              3,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 92.6,\n            "cornerPositions": [\n              2,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 93.3,\n            "cornerPositions": [\n              4,\n              4,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 94.0,\n            "cornerPositions": [\n              3,\n              2,\n              3\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 3,\n        "horseNumber": 3,\n        "frameNumber": 3,\n        "name": "リベルタスノー",\n        "age": 6,\n        "sex": "牡",\n        "carriedWeight": 53.5,\n        "jockey": "佐藤騎手",\n        "trainer": "中島厩舎",\n        "jockeyStats": {\n          "starts": 49,\n          "wins": 6,\n          "seconds": 4,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 85,\n          "wins": 9,\n          "seconds": 10,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 2210000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 91.8,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 92.5,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 93.2,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 4,\n            "timeSeconds": 93.8,\n            "cornerPositions": [\n              5,\n              4,\n              4\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              7,\n              7,\n              6\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 4,\n        "horseNumber": 4,\n        "frameNumber": 4,\n        "name": "カゼノシルシ",\n        "age": 7,\n        "sex": "セ",\n        "carriedWeight": 54.0,\n        "jockey": "中村騎手",\n        "trainer": "田村厩舎",\n        "jockeyStats": {\n          "starts": 52,\n          "wins": 7,\n          "seconds": 6,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 90,\n          "wins": 10,\n          "seconds": 11,\n          "thirds": 13\n        },\n        "prizeMoneyAtRace": 2680000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 92.3,\n            "cornerPositions": [\n              8,\n              7,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 93.0,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 93.7,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 7,\n            "timeSeconds": 94.4,\n            "cornerPositions": [\n              8,\n              8,\n              7\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 95.1,\n            "cornerPositions": [\n              7,\n              7,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 5,\n        "horseNumber": 5,\n        "frameNumber": 5,\n        "name": "オオゾラキング",\n        "age": 3,\n        "sex": "牡",\n        "carriedWeight": 52.0,\n        "jockey": "鈴木騎手",\n        "trainer": "石川厩舎",\n        "jockeyStats": {\n          "starts": 55,\n          "wins": 3,\n          "seconds": 8,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 95,\n          "wins": 11,\n          "seconds": 12,\n          "thirds": 9\n        },\n        "prizeMoneyAtRace": 3150000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 92.8,\n            "cornerPositions": [\n              2,\n              2,\n              5\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 93.5,\n            "cornerPositions": [\n              1,\n              1,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 7,\n            "timeSeconds": 94.2,\n            "cornerPositions": [\n              3,\n              3,\n              6\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 94.9,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 95.6,\n            "cornerPositions": [\n              4,\n              4,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 6,\n        "horseNumber": 6,\n        "frameNumber": 6,\n        "name": "ライトニングベル",\n        "age": 4,\n        "sex": "牝",\n        "carriedWeight": 52.5,\n        "jockey": "渡辺騎手",\n        "trainer": "藤原厩舎",\n        "jockeyStats": {\n          "starts": 58,\n          "wins": 4,\n          "seconds": 4,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 100,\n          "wins": 12,\n          "seconds": 7,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 3620000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 94.1,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 94.8,\n            "cornerPositions": [\n              3,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 95.5,\n            "cornerPositions": [\n              4,\n              3,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 96.2,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 7,\n        "horseNumber": 7,\n        "frameNumber": 7,\n        "name": "サクラブレイブ",\n        "age": 5,\n        "sex": "牡",\n        "carriedWeight": 53.0,\n        "jockey": "高橋騎手",\n        "trainer": "小林厩舎",\n        "jockeyStats": {\n          "starts": 61,\n          "wins": 5,\n          "seconds": 6,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 105,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 4090000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 93.9,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 94.6,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 95.3,\n            "cornerPositions": [\n              5,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 96.0,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 96.7,\n            "cornerPositions": [\n              5,\n              5,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 8,\n        "horseNumber": 8,\n        "frameNumber": 8,\n        "name": "クロノフェザー",\n        "age": 6,\n        "sex": "牝",\n        "carriedWeight": 53.5,\n        "jockey": "伊藤騎手",\n        "trainer": "松本厩舎",\n        "jockeyStats": {\n          "starts": 64,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 110,\n          "wins": 7,\n          "seconds": 9,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 4560000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              8,\n              8,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 95.2,\n            "cornerPositions": [\n              8,\n              7,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 95.9,\n            "cornerPositions": [\n              7,\n              6,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 8,\n            "timeSeconds": 96.6,\n            "cornerPositions": [\n              8,\n              8,\n              8\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 97.3,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      }\n    ],\n    "weather": "晴",\n    "circuit": "地方"\n  },\n  {\n    "id": "demo-local-kasamatsu-20260925-07",\n    "date": "2026-09-25",\n    "track": "笠松",\n    "raceNumber": 7,\n    "title": "3歳条件 デモレース",\n    "distance": 1400,\n    "condition": "良",\n    "startTime": "14:10",\n    "horses": [\n      {\n        "id": 1,\n        "horseNumber": 1,\n        "frameNumber": 1,\n        "name": "アオゾラロード",\n        "age": 4,\n        "sex": "牡",\n        "carriedWeight": 52.5,\n        "jockey": "田中騎手",\n        "trainer": "青木厩舎",\n        "jockeyStats": {\n          "starts": 43,\n          "wins": 4,\n          "seconds": 6,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 75,\n          "wins": 7,\n          "seconds": 8,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 1270000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 90.6,\n            "cornerPositions": [\n              1,\n              1,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 3,\n            "timeSeconds": 91.3,\n            "cornerPositions": [\n              1,\n              1,\n              3\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 92.0,\n            "cornerPositions": [\n              2,\n              2,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 1,\n            "timeSeconds": 92.7,\n            "cornerPositions": [\n              1,\n              1,\n              1\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              3,\n              3,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 2,\n        "horseNumber": 2,\n        "frameNumber": 2,\n        "name": "ミナミノスター",\n        "age": 5,\n        "sex": "牝",\n        "carriedWeight": 53.0,\n        "jockey": "山本騎手",\n        "trainer": "森厩舎",\n        "jockeyStats": {\n          "starts": 46,\n          "wins": 5,\n          "seconds": 8,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 80,\n          "wins": 8,\n          "seconds": 9,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 1740000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 91.2,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 91.9,\n            "cornerPositions": [\n              3,\n              3,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 92.6,\n            "cornerPositions": [\n              2,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 93.3,\n            "cornerPositions": [\n              4,\n              4,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 94.0,\n            "cornerPositions": [\n              3,\n              2,\n              3\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 3,\n        "horseNumber": 3,\n        "frameNumber": 3,\n        "name": "リベルタスノー",\n        "age": 6,\n        "sex": "牡",\n        "carriedWeight": 53.5,\n        "jockey": "佐藤騎手",\n        "trainer": "中島厩舎",\n        "jockeyStats": {\n          "starts": 49,\n          "wins": 6,\n          "seconds": 4,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 85,\n          "wins": 9,\n          "seconds": 10,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 2210000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 91.8,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 92.5,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 93.2,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 4,\n            "timeSeconds": 93.8,\n            "cornerPositions": [\n              5,\n              4,\n              4\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              7,\n              7,\n              6\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 4,\n        "horseNumber": 4,\n        "frameNumber": 4,\n        "name": "カゼノシルシ",\n        "age": 7,\n        "sex": "セ",\n        "carriedWeight": 54.0,\n        "jockey": "中村騎手",\n        "trainer": "田村厩舎",\n        "jockeyStats": {\n          "starts": 52,\n          "wins": 7,\n          "seconds": 6,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 90,\n          "wins": 10,\n          "seconds": 11,\n          "thirds": 13\n        },\n        "prizeMoneyAtRace": 2680000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 92.3,\n            "cornerPositions": [\n              8,\n              7,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 93.0,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 93.7,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 7,\n            "timeSeconds": 94.4,\n            "cornerPositions": [\n              8,\n              8,\n              7\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 95.1,\n            "cornerPositions": [\n              7,\n              7,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 5,\n        "horseNumber": 5,\n        "frameNumber": 5,\n        "name": "オオゾラキング",\n        "age": 3,\n        "sex": "牡",\n        "carriedWeight": 52.0,\n        "jockey": "鈴木騎手",\n        "trainer": "石川厩舎",\n        "jockeyStats": {\n          "starts": 55,\n          "wins": 3,\n          "seconds": 8,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 95,\n          "wins": 11,\n          "seconds": 12,\n          "thirds": 9\n        },\n        "prizeMoneyAtRace": 3150000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 92.8,\n            "cornerPositions": [\n              2,\n              2,\n              5\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 93.5,\n            "cornerPositions": [\n              1,\n              1,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 7,\n            "timeSeconds": 94.2,\n            "cornerPositions": [\n              3,\n              3,\n              6\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 94.9,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 95.6,\n            "cornerPositions": [\n              4,\n              4,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 6,\n        "horseNumber": 6,\n        "frameNumber": 6,\n        "name": "ライトニングベル",\n        "age": 4,\n        "sex": "牝",\n        "carriedWeight": 52.5,\n        "jockey": "渡辺騎手",\n        "trainer": "藤原厩舎",\n        "jockeyStats": {\n          "starts": 58,\n          "wins": 4,\n          "seconds": 4,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 100,\n          "wins": 12,\n          "seconds": 7,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 3620000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 94.1,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 94.8,\n            "cornerPositions": [\n              3,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 95.5,\n            "cornerPositions": [\n              4,\n              3,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 96.2,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 7,\n        "horseNumber": 7,\n        "frameNumber": 7,\n        "name": "サクラブレイブ",\n        "age": 5,\n        "sex": "牡",\n        "carriedWeight": 53.0,\n        "jockey": "高橋騎手",\n        "trainer": "小林厩舎",\n        "jockeyStats": {\n          "starts": 61,\n          "wins": 5,\n          "seconds": 6,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 105,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 4090000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 93.9,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 94.6,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 95.3,\n            "cornerPositions": [\n              5,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 96.0,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 96.7,\n            "cornerPositions": [\n              5,\n              5,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 8,\n        "horseNumber": 8,\n        "frameNumber": 8,\n        "name": "クロノフェザー",\n        "age": 6,\n        "sex": "牝",\n        "carriedWeight": 53.5,\n        "jockey": "伊藤騎手",\n        "trainer": "松本厩舎",\n        "jockeyStats": {\n          "starts": 64,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 110,\n          "wins": 7,\n          "seconds": 9,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 4560000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              8,\n              8,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 95.2,\n            "cornerPositions": [\n              8,\n              7,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 95.9,\n            "cornerPositions": [\n              7,\n              6,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "笠松",\n            "distance": 1400,\n            "condition": "不良",\n            "finish": 8,\n            "timeSeconds": 96.6,\n            "cornerPositions": [\n              8,\n              8,\n              8\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "園田",\n            "distance": 1400,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 97.3,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      }\n    ],\n    "weather": "晴",\n    "circuit": "地方"\n  },\n  {\n    "id": "demo-central-tokyo-20260926-09",\n    "date": "2026-09-26",\n    "track": "東京",\n    "raceNumber": 9,\n    "title": "1勝クラス デモレース",\n    "distance": 1600,\n    "condition": "良",\n    "startTime": "14:35",\n    "horses": [\n      {\n        "id": 1,\n        "horseNumber": 1,\n        "frameNumber": 1,\n        "name": "アオゾラロード",\n        "age": 4,\n        "sex": "牡",\n        "carriedWeight": 52.5,\n        "jockey": "田中騎手",\n        "trainer": "青木厩舎",\n        "jockeyStats": {\n          "starts": 43,\n          "wins": 4,\n          "seconds": 6,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 75,\n          "wins": 7,\n          "seconds": 8,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 1270000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 90.6,\n            "cornerPositions": [\n              1,\n              1,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 3,\n            "timeSeconds": 91.3,\n            "cornerPositions": [\n              1,\n              1,\n              3\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 92.0,\n            "cornerPositions": [\n              2,\n              2,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 1,\n            "timeSeconds": 92.7,\n            "cornerPositions": [\n              1,\n              1,\n              1\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              3,\n              3,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 2,\n        "horseNumber": 2,\n        "frameNumber": 2,\n        "name": "ミナミノスター",\n        "age": 5,\n        "sex": "牝",\n        "carriedWeight": 53.0,\n        "jockey": "山本騎手",\n        "trainer": "森厩舎",\n        "jockeyStats": {\n          "starts": 46,\n          "wins": 5,\n          "seconds": 8,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 80,\n          "wins": 8,\n          "seconds": 9,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 1740000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 91.2,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 91.9,\n            "cornerPositions": [\n              3,\n              3,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 92.6,\n            "cornerPositions": [\n              2,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 93.3,\n            "cornerPositions": [\n              4,\n              4,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 94.0,\n            "cornerPositions": [\n              3,\n              2,\n              3\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 3,\n        "horseNumber": 3,\n        "frameNumber": 3,\n        "name": "リベルタスノー",\n        "age": 6,\n        "sex": "牡",\n        "carriedWeight": 53.5,\n        "jockey": "佐藤騎手",\n        "trainer": "中島厩舎",\n        "jockeyStats": {\n          "starts": 49,\n          "wins": 6,\n          "seconds": 4,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 85,\n          "wins": 9,\n          "seconds": 10,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 2210000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 91.8,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 92.5,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 93.2,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 4,\n            "timeSeconds": 93.8,\n            "cornerPositions": [\n              5,\n              4,\n              4\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              7,\n              7,\n              6\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 4,\n        "horseNumber": 4,\n        "frameNumber": 4,\n        "name": "カゼノシルシ",\n        "age": 7,\n        "sex": "セ",\n        "carriedWeight": 54.0,\n        "jockey": "中村騎手",\n        "trainer": "田村厩舎",\n        "jockeyStats": {\n          "starts": 52,\n          "wins": 7,\n          "seconds": 6,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 90,\n          "wins": 10,\n          "seconds": 11,\n          "thirds": 13\n        },\n        "prizeMoneyAtRace": 2680000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 92.3,\n            "cornerPositions": [\n              8,\n              7,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 93.0,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 93.7,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 7,\n            "timeSeconds": 94.4,\n            "cornerPositions": [\n              8,\n              8,\n              7\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 95.1,\n            "cornerPositions": [\n              7,\n              7,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 5,\n        "horseNumber": 5,\n        "frameNumber": 5,\n        "name": "オオゾラキング",\n        "age": 3,\n        "sex": "牡",\n        "carriedWeight": 52.0,\n        "jockey": "鈴木騎手",\n        "trainer": "石川厩舎",\n        "jockeyStats": {\n          "starts": 55,\n          "wins": 3,\n          "seconds": 8,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 95,\n          "wins": 11,\n          "seconds": 12,\n          "thirds": 9\n        },\n        "prizeMoneyAtRace": 3150000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 92.8,\n            "cornerPositions": [\n              2,\n              2,\n              5\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 93.5,\n            "cornerPositions": [\n              1,\n              1,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 7,\n            "timeSeconds": 94.2,\n            "cornerPositions": [\n              3,\n              3,\n              6\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 94.9,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 95.6,\n            "cornerPositions": [\n              4,\n              4,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 6,\n        "horseNumber": 6,\n        "frameNumber": 6,\n        "name": "ライトニングベル",\n        "age": 4,\n        "sex": "牝",\n        "carriedWeight": 52.5,\n        "jockey": "渡辺騎手",\n        "trainer": "藤原厩舎",\n        "jockeyStats": {\n          "starts": 58,\n          "wins": 4,\n          "seconds": 4,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 100,\n          "wins": 12,\n          "seconds": 7,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 3620000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 94.1,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 94.8,\n            "cornerPositions": [\n              3,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 95.5,\n            "cornerPositions": [\n              4,\n              3,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 96.2,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 7,\n        "horseNumber": 7,\n        "frameNumber": 7,\n        "name": "サクラブレイブ",\n        "age": 5,\n        "sex": "牡",\n        "carriedWeight": 53.0,\n        "jockey": "高橋騎手",\n        "trainer": "小林厩舎",\n        "jockeyStats": {\n          "starts": 61,\n          "wins": 5,\n          "seconds": 6,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 105,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 4090000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 93.9,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 94.6,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 95.3,\n            "cornerPositions": [\n              5,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 96.0,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 96.7,\n            "cornerPositions": [\n              5,\n              5,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 8,\n        "horseNumber": 8,\n        "frameNumber": 8,\n        "name": "クロノフェザー",\n        "age": 6,\n        "sex": "牝",\n        "carriedWeight": 53.5,\n        "jockey": "伊藤騎手",\n        "trainer": "松本厩舎",\n        "jockeyStats": {\n          "starts": 64,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 110,\n          "wins": 7,\n          "seconds": 9,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 4560000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              8,\n              8,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 95.2,\n            "cornerPositions": [\n              8,\n              7,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 95.9,\n            "cornerPositions": [\n              7,\n              6,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 8,\n            "timeSeconds": 96.6,\n            "cornerPositions": [\n              8,\n              8,\n              8\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 97.3,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      }\n    ],\n    "weather": "曇",\n    "circuit": "中央"\n  },\n  {\n    "id": "demo-central-hanshin-20260926-10",\n    "date": "2026-09-26",\n    "track": "阪神",\n    "raceNumber": 10,\n    "title": "2勝クラス デモレース",\n    "distance": 1600,\n    "condition": "良",\n    "startTime": "15:05",\n    "horses": [\n      {\n        "id": 1,\n        "horseNumber": 1,\n        "frameNumber": 1,\n        "name": "アオゾラロード",\n        "age": 4,\n        "sex": "牡",\n        "carriedWeight": 52.5,\n        "jockey": "田中騎手",\n        "trainer": "青木厩舎",\n        "jockeyStats": {\n          "starts": 43,\n          "wins": 4,\n          "seconds": 6,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 75,\n          "wins": 7,\n          "seconds": 8,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 1270000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 90.6,\n            "cornerPositions": [\n              1,\n              1,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 3,\n            "timeSeconds": 91.3,\n            "cornerPositions": [\n              1,\n              1,\n              3\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 92.0,\n            "cornerPositions": [\n              2,\n              2,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 1,\n            "timeSeconds": 92.7,\n            "cornerPositions": [\n              1,\n              1,\n              1\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              3,\n              3,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 2,\n        "horseNumber": 2,\n        "frameNumber": 2,\n        "name": "ミナミノスター",\n        "age": 5,\n        "sex": "牝",\n        "carriedWeight": 53.0,\n        "jockey": "山本騎手",\n        "trainer": "森厩舎",\n        "jockeyStats": {\n          "starts": 46,\n          "wins": 5,\n          "seconds": 8,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 80,\n          "wins": 8,\n          "seconds": 9,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 1740000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 3,\n            "timeSeconds": 91.2,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 91.9,\n            "cornerPositions": [\n              3,\n              3,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 92.6,\n            "cornerPositions": [\n              2,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 93.3,\n            "cornerPositions": [\n              4,\n              4,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 94.0,\n            "cornerPositions": [\n              3,\n              2,\n              3\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 3,\n        "horseNumber": 3,\n        "frameNumber": 3,\n        "name": "リベルタスノー",\n        "age": 6,\n        "sex": "牡",\n        "carriedWeight": 53.5,\n        "jockey": "佐藤騎手",\n        "trainer": "中島厩舎",\n        "jockeyStats": {\n          "starts": 49,\n          "wins": 6,\n          "seconds": 4,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 85,\n          "wins": 9,\n          "seconds": 10,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 2210000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 91.8,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 92.5,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 93.2,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 4,\n            "timeSeconds": 93.8,\n            "cornerPositions": [\n              5,\n              4,\n              4\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              7,\n              7,\n              6\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 4,\n        "horseNumber": 4,\n        "frameNumber": 4,\n        "name": "カゼノシルシ",\n        "age": 7,\n        "sex": "セ",\n        "carriedWeight": 54.0,\n        "jockey": "中村騎手",\n        "trainer": "田村厩舎",\n        "jockeyStats": {\n          "starts": 52,\n          "wins": 7,\n          "seconds": 6,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 90,\n          "wins": 10,\n          "seconds": 11,\n          "thirds": 13\n        },\n        "prizeMoneyAtRace": 2680000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 92.3,\n            "cornerPositions": [\n              8,\n              7,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 93.0,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 93.7,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 7,\n            "timeSeconds": 94.4,\n            "cornerPositions": [\n              8,\n              8,\n              7\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "中京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 95.1,\n            "cornerPositions": [\n              7,\n              7,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 5,\n        "horseNumber": 5,\n        "frameNumber": 5,\n        "name": "オオゾラキング",\n        "age": 3,\n        "sex": "牡",\n        "carriedWeight": 52.0,\n        "jockey": "鈴木騎手",\n        "trainer": "石川厩舎",\n        "jockeyStats": {\n          "starts": 55,\n          "wins": 3,\n          "seconds": 8,\n          "thirds": 6\n        },\n        "trainerStats": {\n          "starts": 95,\n          "wins": 11,\n          "seconds": 12,\n          "thirds": 9\n        },\n        "prizeMoneyAtRace": 3150000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 92.8,\n            "cornerPositions": [\n              2,\n              2,\n              5\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 93.5,\n            "cornerPositions": [\n              1,\n              1,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 7,\n            "timeSeconds": 94.2,\n            "cornerPositions": [\n              3,\n              3,\n              6\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 94.9,\n            "cornerPositions": [\n              2,\n              2,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "阪神",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 95.6,\n            "cornerPositions": [\n              4,\n              4,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 6,\n        "horseNumber": 6,\n        "frameNumber": 6,\n        "name": "ライトニングベル",\n        "age": 4,\n        "sex": "牝",\n        "carriedWeight": 52.5,\n        "jockey": "渡辺騎手",\n        "trainer": "藤原厩舎",\n        "jockeyStats": {\n          "starts": 58,\n          "wins": 4,\n          "seconds": 4,\n          "thirds": 7\n        },\n        "trainerStats": {\n          "starts": 100,\n          "wins": 12,\n          "seconds": 7,\n          "thirds": 10\n        },\n        "prizeMoneyAtRace": 3620000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 4,\n            "timeSeconds": 93.4,\n            "cornerPositions": [\n              4,\n              4,\n              3\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 4,\n            "timeSeconds": 94.1,\n            "cornerPositions": [\n              5,\n              5,\n              4\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 94.8,\n            "cornerPositions": [\n              3,\n              3,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 2,\n            "timeSeconds": 95.5,\n            "cornerPositions": [\n              4,\n              3,\n              2\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "東京",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 96.2,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 7,\n        "horseNumber": 7,\n        "frameNumber": 7,\n        "name": "サクラブレイブ",\n        "age": 5,\n        "sex": "牡",\n        "carriedWeight": 53.0,\n        "jockey": "高橋騎手",\n        "trainer": "小林厩舎",\n        "jockeyStats": {\n          "starts": 61,\n          "wins": 5,\n          "seconds": 6,\n          "thirds": 8\n        },\n        "trainerStats": {\n          "starts": 105,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 11\n        },\n        "prizeMoneyAtRace": 4090000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 93.9,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 94.6,\n            "cornerPositions": [\n              7,\n              6,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 4,\n            "timeSeconds": 95.3,\n            "cornerPositions": [\n              5,\n              4,\n              3\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 5,\n            "timeSeconds": 96.0,\n            "cornerPositions": [\n              6,\n              6,\n              5\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "中山",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 6,\n            "timeSeconds": 96.7,\n            "cornerPositions": [\n              5,\n              5,\n              5\n            ],\n            "weather": "晴"\n          }\n        ]\n      },\n      {\n        "id": 8,\n        "horseNumber": 8,\n        "frameNumber": 8,\n        "name": "クロノフェザー",\n        "age": 6,\n        "sex": "牝",\n        "carriedWeight": 53.5,\n        "jockey": "伊藤騎手",\n        "trainer": "松本厩舎",\n        "jockeyStats": {\n          "starts": 64,\n          "wins": 6,\n          "seconds": 8,\n          "thirds": 5\n        },\n        "trainerStats": {\n          "starts": 110,\n          "wins": 7,\n          "seconds": 9,\n          "thirds": 12\n        },\n        "prizeMoneyAtRace": 4560000,\n        "recentRaces": [\n          {\n            "date": "2026-09-20",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 7,\n            "timeSeconds": 94.5,\n            "cornerPositions": [\n              8,\n              8,\n              6\n            ],\n            "weather": "晴"\n          },\n          {\n            "date": "2026-09-17",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "稍重",\n            "finish": 5,\n            "timeSeconds": 95.2,\n            "cornerPositions": [\n              8,\n              7,\n              5\n            ],\n            "weather": "曇"\n          },\n          {\n            "date": "2026-09-14",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "重",\n            "finish": 5,\n            "timeSeconds": 95.9,\n            "cornerPositions": [\n              7,\n              6,\n              4\n            ],\n            "weather": "小雨"\n          },\n          {\n            "date": "2026-09-11",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "不良",\n            "finish": 8,\n            "timeSeconds": 96.6,\n            "cornerPositions": [\n              8,\n              8,\n              8\n            ],\n            "weather": "雨"\n          },\n          {\n            "date": "2026-09-08",\n            "track": "新潟",\n            "distance": 1600,\n            "condition": "良",\n            "finish": 5,\n            "timeSeconds": 97.3,\n            "cornerPositions": [\n              6,\n              5,\n              4\n            ],\n            "weather": "晴"\n          }\n        ]\n      }\n    ],\n    "weather": "曇",\n    "circuit": "中央"\n  }\n]')


# --- NAR official live data connector ---------------------------------
NAR_DAILY_RACE_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily"
NAR_MONTHLY_RACE_URL = (
    "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload"
    "?type=monthly&k_year={year}&k_month={month}"
)

DATA_ROOT = Path(os.getenv("KEIBA_DATA_DIR", "/tmp/keiba_data"))
ARCHIVE_DIR = DATA_ROOT / "nar" / "archives"
DB_PATH = DATA_ROOT / "nar" / "nar.sqlite3"

# Official CSV fixed-column indexes, based on NAR's published data specification.
RACE_IDX = {
    "track": 0,
    "date": 1,
    "race_no": 2,
    "start_time": 3,
    "race_type": 4,
    "title": 5,
    "surface": 21,
    "direction": 22,
    "distance": 23,
    "weather": 24,
    "condition": 25,
    "field_size": 26,
    "class_condition": 27,
    "prize1": 28,
    "prize2": 29,
    "prize3": 30,
    "prize4": 31,
    "prize5": 32,
    "corner_name_start": 50,
    "corner_order_start": 58,
}
HORSE_IDX = {
    "track": 0,
    "date": 1,
    "race_no": 2,
    "frame_no": 3,
    "horse_no": 5,
    "name": 6,
    "sex": 7,
    "age": 8,
    "jockey": 14,
    "carried_weight": 16,
    "trainer": 18,
    "finish": 31,
    "time": 32,
}


def _clean(value: str | None) -> str:
    return (value or "").strip().replace("\u3000", " ")


def _int(value: str | None, default: int = 0) -> int:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


def _float(value: str | None, default: float = 0.0) -> float:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _iso_date(yyyymmdd: str) -> str:
    s = re.sub(r"\D", "", yyyymmdd)
    if len(s) != 8:
        return yyyymmdd
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def _start_time(hhmm: str) -> str:
    s = re.sub(r"\D", "", hhmm)
    if len(s) == 3:
        s = "0" + s
    if len(s) != 4:
        return _clean(hhmm)
    return f"{s[:2]}:{s[2:]}"


def _time_seconds(raw: str) -> float:
    """NAR result time e.g. '2043' => 2:04.3, '594' => 59.4."""
    s = re.sub(r"[^0-9]", "", _clean(raw))
    if not s:
        return 0.0
    if len(s) <= 3:
        return int(s) / 10.0
    minutes = int(s[:-3])
    sec_tenths = int(s[-3:])
    return minutes * 60 + sec_tenths / 10.0


def _normalize_sex(value: str) -> str:
    s = _clean(value)
    if s in {"セン", "セ", "騸"}:
        return "セ"
    if s.startswith("牝"):
        return "牝"
    return "牡"


def _normalize_weather(value: str) -> str:
    s = _clean(value)
    for v in ("晴", "曇", "小雨", "雨", "小雪", "雪"):
        if v in s:
            return v
    return "不明"


def _normalize_condition(value: str) -> str:
    s = _clean(value)
    # Banei uses a moisture percentage rather than 良/稍重/重/不良.
    for v in ("不良", "稍重", "重", "良"):
        if v in s:
            return v
    return "不明"


def _stable_id(*parts: object) -> int:
    digest = hashlib.blake2s("|".join(map(str, parts)).encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") & 0x7FFFFFFF


def decode_csv_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_csv_from_zip(zip_bytes: bytes, suffix: str) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        matches = [n for n in zf.namelist() if n.lower().endswith(suffix.lower())]
        if not matches:
            return []
        text = decode_csv_bytes(zf.read(matches[0]))
    return [row for row in csv.reader(io.StringIO(text)) if row]


def strip_header(rows: list[list[str]]) -> list[list[str]]:
    if rows and rows[0] and _clean(rows[0][0]) == "競馬場":
        return rows[1:]
    return rows


def _top_level_tokens(text: str) -> list[str]:
    """Split a NAR corner-order string while keeping '(2,7)' as one group."""
    text = _clean(text)
    if not text:
        return []
    tokens: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            if buf:
                tokens.append("".join(buf).strip())
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf).strip())
    return tokens


def parse_corner_order(text: str) -> dict[int, int]:
    """
    Convert NAR's race-level passage order to {horse_number: position}.
    Parenthesized groups are treated as tied; hyphens are distance separators,
    not missing horses, so numbers remain sequential positions.
    """
    positions: dict[int, int] = {}
    rank = 1
    for token in _top_level_tokens(text):
        tied = token.startswith("(") and token.endswith(")")
        nums = [int(x) for x in re.findall(r"\d+", token)]
        if not nums:
            continue
        if tied and len(nums) > 1:
            for horse_no in nums:
                positions[horse_no] = rank
            rank += len(nums)
        else:
            for horse_no in nums:
                positions[horse_no] = rank
                rank += 1
    return positions


@dataclass
class RaceRow:
    track: str
    date: str
    race_no: int
    start_time: str
    title: str
    distance: int
    weather: str
    condition: str
    field_size: int
    prize: tuple[int, int, int, int, int]
    corners: list[dict[int, int]]


@dataclass
class EntryRow:
    track: str
    date: str
    race_no: int
    frame_no: int
    horse_no: int
    name: str
    sex: str
    age: int
    carried_weight: float
    jockey: str
    trainer: str
    finish: int
    time_seconds: float


class NarArchiveParser:
    def parse(self, zip_bytes: bytes) -> tuple[list[RaceRow], list[EntryRow]]:
        race_rows = strip_header(read_csv_from_zip(zip_bytes, "_racelist.csv"))
        horse_rows = strip_header(read_csv_from_zip(zip_bytes, "_horselist.csv"))

        races: list[RaceRow] = []
        for row in race_rows:
            if len(row) < 33:
                continue
            corner_orders: list[dict[int, int]] = []
            for i in range(8):
                idx = RACE_IDX["corner_order_start"] + i
                if idx < len(row) and _clean(row[idx]):
                    corner_orders.append(parse_corner_order(row[idx]))
            races.append(
                RaceRow(
                    track=_clean(row[RACE_IDX["track"]]),
                    date=_iso_date(row[RACE_IDX["date"]]),
                    race_no=_int(row[RACE_IDX["race_no"]]),
                    start_time=_start_time(row[RACE_IDX["start_time"]]),
                    title=_clean(row[RACE_IDX["title"]]),
                    distance=_int(row[RACE_IDX["distance"]]),
                    weather=_normalize_weather(row[RACE_IDX["weather"]]),
                    condition=_normalize_condition(row[RACE_IDX["condition"]]),
                    field_size=_int(row[RACE_IDX["field_size"]]),
                    prize=tuple(_int(row[RACE_IDX[f"prize{i}"]]) for i in range(1, 6)),
                    corners=corner_orders,
                )
            )

        entries: list[EntryRow] = []
        for row in horse_rows:
            if len(row) < 19:
                continue
            entries.append(
                EntryRow(
                    track=_clean(row[HORSE_IDX["track"]]),
                    date=_iso_date(row[HORSE_IDX["date"]]),
                    race_no=_int(row[HORSE_IDX["race_no"]]),
                    frame_no=_int(row[HORSE_IDX["frame_no"]]),
                    horse_no=_int(row[HORSE_IDX["horse_no"]]),
                    name=_clean(row[HORSE_IDX["name"]]),
                    sex=_normalize_sex(row[HORSE_IDX["sex"]]),
                    age=_int(row[HORSE_IDX["age"]]),
                    jockey=_clean(row[HORSE_IDX["jockey"]]),
                    carried_weight=_float(row[HORSE_IDX["carried_weight"]]),
                    trainer=_clean(row[HORSE_IDX["trainer"]]),
                    finish=_int(row[HORSE_IDX["finish"]]) if len(row) > HORSE_IDX["finish"] else 0,
                    time_seconds=_time_seconds(row[HORSE_IDX["time"]]) if len(row) > HORSE_IDX["time"] else 0,
                )
            )
        return races, entries


class NarStore:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS races (
                track TEXT NOT NULL,
                date TEXT NOT NULL,
                race_no INTEGER NOT NULL,
                start_time TEXT NOT NULL DEFAULT '',
                scheduled_start_time TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                distance INTEGER NOT NULL DEFAULT 0,
                weather TEXT NOT NULL DEFAULT '不明',
                condition TEXT NOT NULL DEFAULT '不明',
                field_size INTEGER NOT NULL DEFAULT 0,
                prize1 INTEGER NOT NULL DEFAULT 0,
                prize2 INTEGER NOT NULL DEFAULT 0,
                prize3 INTEGER NOT NULL DEFAULT 0,
                prize4 INTEGER NOT NULL DEFAULT 0,
                prize5 INTEGER NOT NULL DEFAULT 0,
                corners_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(track, date, race_no)
            );
            CREATE TABLE IF NOT EXISTS entries (
                track TEXT NOT NULL,
                date TEXT NOT NULL,
                race_no INTEGER NOT NULL,
                frame_no INTEGER NOT NULL DEFAULT 0,
                horse_no INTEGER NOT NULL,
                name TEXT NOT NULL,
                sex TEXT NOT NULL DEFAULT '牡',
                age INTEGER NOT NULL DEFAULT 0,
                carried_weight REAL NOT NULL DEFAULT 0,
                jockey TEXT NOT NULL DEFAULT '',
                trainer TEXT NOT NULL DEFAULT '',
                finish INTEGER NOT NULL DEFAULT 0,
                time_seconds REAL NOT NULL DEFAULT 0,
                corner_positions_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(track, date, race_no, horse_no)
            );
            CREATE INDEX IF NOT EXISTS idx_entries_name_date ON entries(name, date);
            CREATE INDEX IF NOT EXISTS idx_entries_jockey_date ON entries(jockey, date);
            CREATE INDEX IF NOT EXISTS idx_entries_trainer_date ON entries(trainer, date);
            CREATE TABLE IF NOT EXISTS sync_log (
                cache_key TEXT PRIMARY KEY,
                synced_at INTEGER NOT NULL,
                archive_path TEXT NOT NULL DEFAULT ''
            );
            """
        )
        race_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(races)").fetchall()}
        if "scheduled_start_time" not in race_cols:
            self.conn.execute("ALTER TABLE races ADD COLUMN scheduled_start_time TEXT NOT NULL DEFAULT ''")
        self.conn.execute("UPDATE races SET scheduled_start_time=start_time WHERE scheduled_start_time=''")
        self.conn.commit()

    def import_rows(self, races: Iterable[RaceRow], entries: Iterable[EntryRow]) -> None:
        races = list(races)
        race_lookup = {(r.track, r.date, r.race_no): r for r in races}
        with self.conn:
            for r in races:
                self.conn.execute(
                    """
                    INSERT INTO races(track,date,race_no,start_time,scheduled_start_time,title,distance,weather,condition,field_size,
                                      prize1,prize2,prize3,prize4,prize5,corners_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(track,date,race_no) DO UPDATE SET
                      start_time=excluded.start_time,title=excluded.title,distance=excluded.distance,
                      weather=excluded.weather,condition=excluded.condition,field_size=excluded.field_size,
                      prize1=excluded.prize1,prize2=excluded.prize2,prize3=excluded.prize3,
                      prize4=excluded.prize4,prize5=excluded.prize5,corners_json=excluded.corners_json
                    """,
                    (
                        r.track, r.date, r.race_no, r.start_time, r.start_time, r.title, r.distance, r.weather, r.condition,
                        r.field_size, *r.prize,
                        json.dumps([{str(k): v for k, v in c.items()} for c in r.corners], ensure_ascii=False),
                    ),
                )
            for e in entries:
                race = race_lookup.get((e.track, e.date, e.race_no))
                corners: list[int] = []
                if race:
                    for c in race.corners:
                        if e.horse_no in c:
                            corners.append(c[e.horse_no])
                self.conn.execute(
                    """
                    INSERT INTO entries(track,date,race_no,frame_no,horse_no,name,sex,age,carried_weight,
                                        jockey,trainer,finish,time_seconds,corner_positions_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(track,date,race_no,horse_no) DO UPDATE SET
                      frame_no=excluded.frame_no,name=excluded.name,sex=excluded.sex,age=excluded.age,
                      carried_weight=excluded.carried_weight,jockey=excluded.jockey,trainer=excluded.trainer,
                      finish=excluded.finish,time_seconds=excluded.time_seconds,
                      corner_positions_json=excluded.corner_positions_json
                    """,
                    (
                        e.track, e.date, e.race_no, e.frame_no, e.horse_no, e.name, e.sex, e.age,
                        e.carried_weight, e.jockey, e.trainer, e.finish, e.time_seconds,
                        json.dumps(corners, ensure_ascii=False),
                    ),
                )

    def mark_synced(self, cache_key: str, archive_path: Path) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO sync_log(cache_key,synced_at,archive_path) VALUES(?,?,?)",
                (cache_key, int(time.time()), str(archive_path)),
            )

    def synced_at(self, cache_key: str) -> int | None:
        row = self.conn.execute("SELECT synced_at FROM sync_log WHERE cache_key=?", (cache_key,)).fetchone()
        return int(row[0]) if row else None

    def stats(self, role: str, name: str, cutoff: str) -> dict[str, int]:
        if role not in {"jockey", "trainer"} or not name:
            return {"starts": 0, "wins": 0, "seconds": 0, "thirds": 0}
        row = self.conn.execute(
            f"""
            SELECT COUNT(*) starts,
                   SUM(CASE WHEN finish=1 THEN 1 ELSE 0 END) wins,
                   SUM(CASE WHEN finish=2 THEN 1 ELSE 0 END) seconds,
                   SUM(CASE WHEN finish=3 THEN 1 ELSE 0 END) thirds
            FROM entries WHERE {role}=? AND date<? AND finish>0
            """,
            (name, cutoff),
        ).fetchone()
        return {k: int(row[k] or 0) for k in ("starts", "wins", "seconds", "thirds")}

    def prize_before(self, horse_name: str, cutoff: str) -> int:
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(CASE e.finish
                WHEN 1 THEN r.prize1 WHEN 2 THEN r.prize2 WHEN 3 THEN r.prize3
                WHEN 4 THEN r.prize4 WHEN 5 THEN r.prize5 ELSE 0 END), 0) AS prize
            FROM entries e
            JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
            WHERE e.name=? AND e.date<? AND e.finish>0
            """,
            (horse_name, cutoff),
        ).fetchone()
        return int(row["prize"] or 0)

    def recent_races(self, horse_name: str, cutoff: str, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT e.*, r.distance, r.weather, r.condition
            FROM entries e
            JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
            WHERE e.name=? AND e.date<? AND e.finish>0
            ORDER BY e.date DESC, e.race_no DESC
            LIMIT ?
            """,
            (horse_name, cutoff, limit),
        ).fetchall()
        return [
            {
                "date": row["date"],
                "track": row["track"],
                "distance": int(row["distance"] or 0),
                "condition": row["condition"] or "不明",
                "weather": row["weather"] or "不明",
                "finish": int(row["finish"] or 0),
                "timeSeconds": float(row["time_seconds"] or 0),
                "cornerPositions": json.loads(row["corner_positions_json"] or "[]"),
            }
            for row in rows
        ]

    def races_json(self, iso_date: str) -> list[dict]:
        race_rows = self.conn.execute(
            "SELECT * FROM races WHERE date=? ORDER BY track, race_no", (iso_date,)
        ).fetchall()
        result: list[dict] = []
        for race in race_rows:
            entries = self.conn.execute(
                "SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",
                (race["track"], iso_date, race["race_no"]),
            ).fetchall()
            if not entries:
                continue
            horses = []
            for e in entries:
                horses.append(
                    {
                        "id": _stable_id(iso_date, race["track"], race["race_no"], e["horse_no"], e["name"]),
                        "horseNumber": int(e["horse_no"]),
                        "frameNumber": int(e["frame_no"] or 0),
                        "name": e["name"],
                        "age": int(e["age"] or 0),
                        "sex": e["sex"] or "牡",
                        "carriedWeight": float(e["carried_weight"] or 0),
                        "jockey": e["jockey"] or "",
                        "trainer": e["trainer"] or "",
                        "jockeyStats": self.stats("jockey", e["jockey"], iso_date),
                        "trainerStats": self.stats("trainer", e["trainer"], iso_date),
                        "prizeMoneyAtRace": self.prize_before(e["name"], iso_date),
                        "recentRaces": self.recent_races(e["name"], iso_date, 5),
                    }
                )
            finishers = []
            for e in entries:
                fin = int(e["finish"] or 0)
                if fin > 0:
                    finishers.append({
                        "finish": fin,
                        "horseNumber": int(e["horse_no"]),
                        "frameNumber": int(e["frame_no"] or 0),
                        "name": e["name"],
                        "timeSeconds": float(e["time_seconds"] or 0),
                        "cornerPositions": json.loads(e["corner_positions_json"] or "[]"),
                    })
            finishers.sort(key=lambda x: (x["finish"], x["horseNumber"]))
            need = min(3, len(entries))
            ranks = {x["finish"] for x in finishers}
            finalized = need > 0 and all(i in ranks for i in range(1, need + 1))
            result_obj = {"status": "確定", "finishers": finishers} if finalized else None
            result.append(
                {
                    "id": f"nar-{iso_date}-{race['track']}-{int(race['race_no']):02d}",
                    "circuit": "地方",
                    "date": iso_date,
                    "track": race["track"],
                    "raceNumber": int(race["race_no"]),
                    "title": race["title"] or f"{int(race['race_no'])}R",
                    "distance": int(race["distance"] or 0),
                    "condition": race["condition"] or "不明",
                    "weather": race["weather"] or "不明",
                    "startTime": race["start_time"] or "",
                    "scheduledStartTime": race["scheduled_start_time"] or race["start_time"] or "",
                    "startTimeChanged": bool((race["scheduled_start_time"] or "") and (race["start_time"] or "") and race["scheduled_start_time"] != race["start_time"]),
                    "horses": horses,
                    "result": result_obj,
                    "source": "NAR公式",
                }
            )
        return result

    def coverage(self) -> dict:
        row = self.conn.execute("SELECT MIN(date) min_date, MAX(date) max_date FROM races").fetchone()
        return {"minDate": row["min_date"], "maxDate": row["max_date"]}


class NarSync:
    def __init__(self, store: NarStore | None = None, parser: NarArchiveParser | None = None):
        self.store = store or NarStore()
        self.parser = parser or NarArchiveParser()
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    def _download(self, url: str, destination: Path) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
                "Accept": "application/zip,application/octet-stream,*/*",
                "Referer": "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
                "Accept-Language": "ja-JP,ja;q=0.9",
            },
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise RuntimeError("NAR response was not a ZIP archive")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return data

    def import_zip_bytes(self, data: bytes, cache_key: str, archive_path: Path) -> dict:
        races, entries = self.parser.parse(data)
        self.store.import_rows(races, entries)
        self.store.mark_synced(cache_key, archive_path)
        return {"races": len(races), "entries": len(entries), "cacheKey": cache_key}

    def sync_daily(self, force: bool = False) -> dict:
        cache_key = "daily"
        synced = self.store.synced_at(cache_key)
        ttl = int(os.getenv("NAR_DAILY_TTL_SECONDS", "120"))
        if not force and synced and int(time.time()) - synced < ttl:
            return {"status": "cached", "cacheKey": cache_key}
        dest = ARCHIVE_DIR / "daily_race.zip"
        data = self._download(NAR_DAILY_RACE_URL, dest)
        info = self.import_zip_bytes(data, cache_key, dest)
        return {"status": "synced", **info}

    def sync_month(self, year: int, month: int, force: bool = False) -> dict:
        if not 1 <= month <= 12:
            raise ValueError("month must be 1...12")
        cache_key = f"month-{year:04d}-{month:02d}"
        synced = self.store.synced_at(cache_key)
        today = datetime.now().date()
        is_current_month = (year == today.year and month == today.month)
        current_ttl = int(os.getenv("NAR_CURRENT_MONTH_TTL_SECONDS", "300"))
        if not force and synced:
            age = int(time.time()) - synced
            if (not is_current_month) or age < current_ttl:
                return {"status": "cached", "cacheKey": cache_key}
        dest = ARCHIVE_DIR / f"{year:04d}{month:02d}_race.zip"
        url = NAR_MONTHLY_RACE_URL.format(year=year, month=month)
        data = self._download(url, dest)
        info = self.import_zip_bytes(data, cache_key, dest)
        return {"status": "synced", **info}

    def import_file(self, path: Path, cache_key: str | None = None) -> dict:
        data = path.read_bytes()
        key = cache_key or f"file-{path.name}-{int(path.stat().st_mtime)}"
        return self.import_zip_bytes(data, key, path)



CENTRAL_DB_PATH = DATA_ROOT / "central" / "central.sqlite3"

class CentralStore:
    def __init__(self, path: Path = CENTRAL_DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS central_races(
              id TEXT PRIMARY KEY,
              date TEXT NOT NULL,
              track TEXT NOT NULL,
              race_no INTEGER NOT NULL,
              payload TEXT NOT NULL,
              updated_at INTEGER NOT NULL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_central_date ON central_races(date,track,race_no)")
        self.conn.commit()

    def upsert(self, rows: list[dict]) -> int:
        n = 0
        with self.conn:
            for raw in rows:
                r = normalize_central_race(raw)
                if not r:
                    continue
                self.conn.execute(
                    """INSERT INTO central_races(id,date,track,race_no,payload,updated_at)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET date=excluded.date,track=excluded.track,
                         race_no=excluded.race_no,payload=excluded.payload,updated_at=excluded.updated_at""",
                    (r["id"], r["date"], r["track"], r["raceNumber"], json.dumps(r, ensure_ascii=False), int(time.time())),
                )
                n += 1
        return n

    def races_json(self, iso_date: str) -> list[dict]:
        rows = self.conn.execute("SELECT payload FROM central_races WHERE date=? ORDER BY track,race_no", (iso_date,)).fetchall()
        return [json.loads(x["payload"]) for x in rows]

    def coverage(self) -> dict:
        row = self.conn.execute("SELECT MIN(date) min_date, MAX(date) max_date, COUNT(*) cnt FROM central_races").fetchone()
        return {"minDate": row["min_date"], "maxDate": row["max_date"], "count": int(row["cnt"] or 0)}


def normalize_central_race(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    date = _clean(str(raw.get("date") or ""))
    track = _clean(str(raw.get("track") or ""))
    race_no = _int(str(raw.get("raceNumber") or raw.get("race_no") or "0"))
    if not date or not track or race_no <= 0:
        return None
    horses = raw.get("horses") if isinstance(raw.get("horses"), list) else []
    rid = _clean(str(raw.get("id") or f"jra-{date}-{track}-{race_no:02d}"))
    out = dict(raw)
    out.update({
        "id": rid, "circuit": "中央", "date": date, "track": track, "raceNumber": race_no,
        "title": raw.get("title") or f"{race_no}R", "distance": int(raw.get("distance") or 0),
        "condition": raw.get("condition") or "不明", "weather": raw.get("weather") or "不明",
        "startTime": raw.get("startTime") or raw.get("actualStartTime") or "",
        "scheduledStartTime": raw.get("scheduledStartTime") or raw.get("originalStartTime") or raw.get("startTime") or raw.get("actualStartTime") or "",
        "horses": horses, "source": raw.get("source") or "中央本番フィード",
    })
    out["startTimeChanged"] = bool(out.get("scheduledStartTime") and out.get("startTime") and out.get("scheduledStartTime") != out.get("startTime"))
    return out


def fetch_central_feed(iso_date: str) -> list[dict]:
    base = _clean(os.getenv("CENTRAL_FEED_URL", ""))
    if not base:
        return []
    if "{date}" in base:
        url = base.replace("{date}", iso_date)
    else:
        url = base + ("&" if "?" in base else "?") + "date=" + iso_date
    headers = {"User-Agent": "KeibaPredictor/3.0", "Accept": "application/json"}
    token = _clean(os.getenv("CENTRAL_FEED_TOKEN", ""))
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
    rows = body if isinstance(body, list) else body.get("races", [])
    return [r for r in (normalize_central_race(x) for x in rows) if r]

def iter_months_back(target: dt_date, count: int) -> Iterator[tuple[int, int]]:
    year, month = target.year, target.month
    for _ in range(count):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        yield year, month


def sync_recent_history(months: int = 12) -> list[dict]:
    sync = NarSync()
    out = []
    today = datetime.now().date()
    for year, month in reversed(list(iter_months_back(today, months))):
        out.append(sync.sync_month(year, month))
    return out


_history_lock = threading.Lock()
_history_started = False
_history_ready = False
_history_error = ""

def _history_worker(months_back: int = 3):
    global _history_ready, _history_error
    sync = NarSync()
    today = datetime.now().date()
    jobs = [(today.year, today.month)] + list(iter_months_back(today, months_back))
    errors = []
    for y, m in jobs:
        try:
            sync.sync_month(y, m)
        except Exception as exc:
            errors.append(f"{y:04d}-{m:02d}:{exc}")
    _history_error = " | ".join(errors)
    _history_ready = True

def ensure_history_async():
    global _history_started
    with _history_lock:
        if _history_started:
            return
        _history_started = True
        threading.Thread(target=_history_worker, daemon=True).start()

def _today_iso():
    return datetime.now().astimezone().strftime("%Y-%m-%d")

# --- v13 interactive five-stage pace board -----------------------------
CSS += r"""
.pace-panel{padding:0;overflow:hidden}
.pace-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 11px 7px}
.pace-head .section-title{margin:0}
.pace-reset{border:1px solid var(--line);background:#fff;border-radius:8px;padding:6px 9px;font-size:11px;color:#475569}
.pace-tabs{display:grid;grid-template-columns:repeat(5,1fr);gap:3px;padding:0 7px 7px}
.pace-tab{border:0;background:#eef2f7;color:#64748b;border-radius:8px;padding:7px 1px;font-size:10px;white-space:nowrap}
.pace-tab.active{background:#111827;color:#fff}
.pace-stage-caption{font-size:12px;color:#475569;padding:0 11px 7px}
.pace-board{position:relative;height:350px;margin:0 7px 10px;border-radius:13px;overflow:hidden;background:linear-gradient(#dff4fb 0 24%,#e7d29a 24% 100%);border:1px solid #d8dee8;touch-action:pan-y}
.pace-board:before{content:"";position:absolute;left:0;right:0;top:24%;height:2px;background:rgba(255,255,255,.9)}
.pace-board:after{content:"";position:absolute;left:8%;right:8%;top:35%;bottom:8%;background:repeating-linear-gradient(90deg,rgba(255,255,255,.12) 0,rgba(255,255,255,.12) 1px,transparent 1px,transparent 48px);pointer-events:none}
.pace-direction{position:absolute;left:10px;top:8px;font-size:11px;color:#6b4d2e;background:rgba(255,255,255,.84);padding:4px 8px;border-radius:999px;z-index:2}
.pace-rear{position:absolute;right:10px;top:8px;font-size:10px;color:#64748b;background:rgba(255,255,255,.75);padding:4px 7px;border-radius:999px;z-index:2}
.pace-horse{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;gap:2px;min-width:50px;max-width:72px;z-index:5;touch-action:none;user-select:none;-webkit-user-select:none;cursor:grab}
.pace-horse.dragging{z-index:20;cursor:grabbing;filter:drop-shadow(0 5px 5px rgba(0,0,0,.2))}
.pace-horse .frame-badge{width:31px;height:31px;font-size:14px;border-radius:50%;box-shadow:0 1px 2px rgba(0,0,0,.18)}
.pace-horse-name{font-size:10px;line-height:1.05;max-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;background:rgba(255,255,255,.76);padding:2px 4px;border-radius:5px;font-weight:700}
.pace-help{font-size:10px;color:#64748b;padding:0 11px 10px}
@media(max-width:390px){.pace-board{height:326px}.pace-horse{min-width:44px;max-width:62px}.pace-horse-name{font-size:9px;max-width:60px}.pace-tab{font-size:9px;padding:7px 0}}
"""

_old_render_start = JS.find('function renderRace(){')
_old_render_end = JS.find('\nfunction render(){', _old_render_start)
if _old_render_start >= 0 and _old_render_end > _old_render_start:
    _new_render = r"""function paceKey(r,stage){return "keiba-pace-layout:"+String(r.id)+":"+String(stage)}
function paceStageShort(i){return ["スタート","1角","向正面","3-4角","直線"][i]||"展開"}
function paceStagePositions(r,p,stageIndex){
  var saved=storedJSON(paceKey(r,stageIndex));
  if(saved&&typeof saved==="object")return saved;
  var groups=(p.stages[stageIndex]&&p.stages[stageIndex][1])||[],out={},columns=[17,50,82],rowYs=[39,55,71,87];
  for(var g=0;g<groups.length;g++){
    var arr=groups[g]||[],cx=columns[Math.min(g,2)];
    for(var i=0;i<arr.length;i++){
      var h=arr[i].horse||arr[i],spread=arr.length<=1?0:(i-(arr.length-1)/2)*8;
      var y=rowYs[(i+g)%rowYs.length];
      out[String(h.horseNumber)]={x:Math.max(7,Math.min(93,cx+spread)),y:y};
    }
  }
  return out;
}
function paceBoardHtml(r,p){
  var tabs="";for(var i=0;i<5;i++)tabs+='<button class="pace-tab '+(i===0?'active':'')+'" data-pace-stage="'+i+'">'+paceStageShort(i)+'</button>';
  return '<section class="card pace-panel"><div class="pace-head"><div class="section-title">3　隊列</div><button class="pace-reset" id="pace-reset">AI配置に戻す</button></div><div class="pace-tabs">'+tabs+'</div><div class="pace-stage-caption" id="pace-stage-caption">'+esc(p.stages[0][0])+'</div><div class="pace-board" id="pace-board"><div class="pace-direction">← 先頭</div><div class="pace-rear">後方 →</div></div><div class="pace-help">馬を指で動かせます。配置はこの端末に自動保存されます。</div></section>';
}
function drawPaceStage(r,p,stageIndex,reset){
  var board=document.getElementById('pace-board');if(!board)return;
  if(reset){try{localStorage.removeItem(paceKey(r,stageIndex))}catch(e){}}
  var pos=paceStagePositions(r,p,stageIndex),html='<div class="pace-direction">← 先頭</div><div class="pace-rear">後方 →</div>';
  var hs=(r.horses||[]).slice().sort(function(a,b){return a.horseNumber-b.horseNumber});
  for(var i=0;i<hs.length;i++){
    var h=hs[i],xy=pos[String(h.horseNumber)]||{x:50,y:60};
    html+='<div class="pace-horse" data-pace-horse="'+h.horseNumber+'" style="left:'+xy.x+'%;top:'+xy.y+'%">'+badge(h)+'<span class="pace-horse-name">'+esc(h.name)+'</span></div>';
  }
  board.innerHTML=html;
  var cap=document.getElementById('pace-stage-caption');if(cap)cap.textContent=p.stages[stageIndex][0];
  var tabs=document.querySelectorAll('[data-pace-stage]');for(i=0;i<tabs.length;i++)tabs[i].classList.toggle('active',Number(tabs[i].getAttribute('data-pace-stage'))===stageIndex);
  board.setAttribute('data-stage',String(stageIndex));
  bindPaceDrag(r,p,stageIndex);
}
function bindPaceDrag(r,p,stageIndex){
  var board=document.getElementById('pace-board');if(!board)return;
  var nodes=board.querySelectorAll('[data-pace-horse]');
  for(var i=0;i<nodes.length;i++)(function(el){
    var active=false,pid=null;
    el.onpointerdown=function(ev){active=true;pid=ev.pointerId;el.classList.add('dragging');try{el.setPointerCapture(pid)}catch(e){};ev.preventDefault()};
    el.onpointermove=function(ev){if(!active||ev.pointerId!==pid)return;var rect=board.getBoundingClientRect(),x=(ev.clientX-rect.left)/rect.width*100,y=(ev.clientY-rect.top)/rect.height*100;x=Math.max(5,Math.min(95,x));y=Math.max(31,Math.min(92,y));el.style.left=x+'%';el.style.top=y+'%';ev.preventDefault()};
    el.onpointerup=el.onpointercancel=function(ev){if(!active)return;active=false;el.classList.remove('dragging');var all=board.querySelectorAll('[data-pace-horse]'),save={};for(var j=0;j<all.length;j++)save[String(all[j].getAttribute('data-pace-horse'))]={x:parseFloat(all[j].style.left)||50,y:parseFloat(all[j].style.top)||60};setStored(paceKey(r,stageIndex),save)};
  })(nodes[i]);
}
function initPaceBoard(r,p){
  if(!document.getElementById('pace-board'))return;
  var stage=0;drawPaceStage(r,p,stage,false);
  var tabs=document.querySelectorAll('[data-pace-stage]');for(var i=0;i<tabs.length;i++)tabs[i].onclick=function(){stage=Number(this.getAttribute('data-pace-stage'))||0;drawPaceStage(r,p,stage,false)};
  var reset=document.getElementById('pace-reset');if(reset)reset.onclick=function(){drawPaceStage(r,p,stage,true)};
}
function renderRace(){
  var r=state.selectedRace,p=predict(r);predictionForReview(r,p);
  var rows=p.rows.slice().sort(function(a,b){return Number(a.horse.horseNumber)-Number(b.horse.horseNumber)}),early=p.occ.early.map(circled).join(' '),moved=p.occ.moved.map(circled).join(' ');
  var style=rows.map(function(x){var h=x.horse;return '<div class="style-row"><div class="style-top">'+badge(h)+'<span class="horse-name">'+esc(h.name)+'</span><span class="score">点 '+x.score.toFixed(2)+'</span><span class="expected">'+esc(x.expected)+'</span></div><div class="rates"><span class="rate"><small>逃</small>'+pct(x.front)+'</span><span class="rate"><small>先</small>'+pct(x.stalk)+'</span><span class="rate"><small>差</small>'+pct(x.mid)+'</span><span class="rate"><small>追</small>'+pct(x.close)+'</span><span class="rate"><small>下</small>'+pct(x.fade)+'</span></div></div>'}).join('');
  var sc=p.scenarios.map(function(s){return '<div class="scenario"><div class="scenario-title">'+s.code+' '+esc(s.title)+'</div><div class="prob">'+s.prob+'%</div><div class="scenario-horses">'+s.horses.map(function(h){return badge(h)}).join('')+'</div></div>'}).join('');
  var mk=p.marks.map(function(m){return '<div class="mark"><span class="mark-symbol">'+m[0]+'</span>'+badge(m[1])+'<span class="horse-name">'+esc(m[1].name)+'</span></div>'}).join('');
  var data=(r.horses||[]).slice().sort(function(a,b){return a.horseNumber-b.horseNumber}).map(function(h){var rec=(h.recentRaces||[]).map(function(rr){return '<div class="recent">'+esc(rr.date)+' '+esc(rr.track)+' '+esc(rr.distance)+'m　'+esc(rr.finish)+'着 / '+fmtTime(rr.timeSeconds)+'<br><span class="muted">'+esc(rr.condition)+'・'+esc(rr.weather||'不明')+'・'+season(rr.date)+'・通過 '+esc((rr.cornerPositions||[]).join('-')||'—')+'</span></div>'}).join('');return '<details class="horse-card"><summary>'+badge(h)+'<span class="horse-name">'+esc(h.name)+'</span><span>'+esc(h.sex)+esc(h.age)+' '+esc(h.carriedWeight)+'kg</span></summary><div class="horse-detail"><div>騎手：'+esc(h.jockey)+'　'+(h.jockeyStats&&h.jockeyStats.starts?h.jockeyStats.starts+'戦 '+h.jockeyStats.wins+'勝 / 複勝率 '+pct(placeRate(h.jockeyStats)):'成績データなし')+'</div><div>調教師：'+esc(h.trainer)+'　'+(h.trainerStats&&h.trainerStats.starts?h.trainerStats.starts+'戦 '+h.trainerStats.wins+'勝 / 複勝率 '+pct(placeRate(h.trainerStats)):'成績データなし')+'</div><div>このレース時点の獲得賞金：'+money(h.prizeMoneyAtRace)+'円</div>'+rec+'</div></details>'}).join('');
  var resultTop=isFinal(r)?renderResult(r,p):'';
  return '<div class="shell">'+header(r.track+' '+r.raceNumber+'R',true,r.title+'｜'+r.distance+'m・'+r.condition+'・'+(r.weather||'不明'))+'<main class="main">'+resultTop+'<section class="card"><div class="metrics"><div class="metric"><b>'+r.distance+'m</b><span>距離</span></div><div class="metric"><b>'+esc(r.condition)+'</b><span>馬場</span></div><div class="metric"><b>'+esc(r.weather||'不明')+'</b><span>天候</span></div><div class="metric"><b>'+season(r.date)+'</b><span>季節</span></div><div class="metric"><b>'+r.horses.length+'頭</b><span>頭数</span></div></div><div class="source-tag">'+esc(r.source||'')+'</div></section><section class="card"><div class="section-title">1　先行馬占有率</div><div class="big-number">'+pct(p.occ.rate)+'</div><div class="muted">対象：'+(p.occ.nums.map(circled).join(' ')||'—')+'</div><div class="muted">最初から前：'+(early||'—')+'　途中進出：'+(moved||'—')+'</div></section><section class="card"><div class="section-title">2　脚質マップ</div><div class="style-list">'+style+'</div></section>'+paceBoardHtml(r,p)+'<section class="card"><div class="section-title">4　ABC</div><div class="scenario-grid">'+sc+'</div></section><section class="card"><div class="section-title">5　印</div><div class="marks">'+mk+'</div></section><section class="card"><h2>出馬データ</h2>'+data+'</section></main></div>';
}"""
    JS = JS[:_old_render_start] + _new_render + JS[_old_render_end:]

_old_bind_start = JS.find('function bind(){')
_old_bind_end = JS.find('\nfunction loadRaces(){', _old_bind_start)
if _old_bind_start >= 0 and _old_bind_end > _old_bind_start:
    _old_bind = JS[_old_bind_start:_old_bind_end]
    _old_bind = _old_bind[:-1] + "var rr=state.selectedRace;if(rr&&document.getElementById('pace-board'))initPaceBoard(rr,predict(rr));}"
    JS = JS[:_old_bind_start] + _old_bind + JS[_old_bind_end:]


@app.get("/health")
def health():
    try:
        nar_coverage = NarStore().coverage()
    except Exception:
        nar_coverage = {"minDate": None, "maxDate": None}
    try:
        central_coverage = CentralStore().coverage()
    except Exception:
        central_coverage = {"minDate": None, "maxDate": None, "count": 0}
    return {
        "status":"ok", "mode":"production-v10", "historyStarted":_history_started,
        "historyReady":_history_ready, "historyError":_history_error, "narCoverage":nar_coverage,
        "centralCoverage":central_coverage, "centralFeedConfigured":bool(os.getenv("CENTRAL_FEED_URL")),
    }

@app.get("/api/v1/history-status")
def history_status():
    return {"started":_history_started,"ready":_history_ready,"error":_history_error}

@app.get("/api/v1/central-status")
def central_status():
    return {
        "feedConfigured": bool(os.getenv("CENTRAL_FEED_URL")),
        "ingestEnabled": bool(os.getenv("CENTRAL_INGEST_TOKEN")),
        "coverage": CentralStore().coverage(),
    }

@app.post("/api/v1/central-ingest")
async def central_ingest(request: Request):
    expected = _clean(os.getenv("CENTRAL_INGEST_TOKEN", ""))
    if not expected:
        raise HTTPException(status_code=503, detail="CENTRAL_INGEST_TOKEN is not configured")
    supplied = _clean(request.headers.get("X-Ingest-Token", ""))
    if supplied != expected:
        raise HTTPException(status_code=401, detail="invalid ingest token")
    body = await request.json()
    rows = body if isinstance(body, list) else body.get("races", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="races must be a list")
    count = CentralStore().upsert(rows)
    return {"status":"ok","stored":count}

@app.get("/api/v1/central-schema")
def central_schema():
    return {
      "description":"中央本番フィードの正規化JSON。JRA-VAN等のライセンス済みデータをこの形式へ変換して送信します。",
      "requiredRaceFields":["date","track","raceNumber","distance","horses"],
      "horseFields":["horseNumber","frameNumber","name","age","sex","carriedWeight","jockey","trainer","jockeyStats","trainerStats","prizeMoneyAtRace","recentRaces"],
      "optionalResult":{"status":"確定","finishers":[{"finish":1,"horseNumber":1,"name":"馬名","timeSeconds":92.3,"cornerPositions":[2,2,1]}]},
    }

@app.get("/api/v1/races")
def races(date: str = Query(...)):
    ensure_history_async()
    try:
        live_local = NarStore().races_json(date)
    except Exception as exc:
        print(f"NAR cache read failed: {exc}")
        live_local = []

    # NAR: always refresh target month in background; today also refresh the 2-minute daily ZIP.
    def _bg_nar_sync():
        try:
            target = datetime.strptime(date, "%Y-%m-%d").date()
            sync = NarSync()
            jobs = [(target.year, target.month)] + list(iter_months_back(target, 4))
            for y, m in jobs:
                try: sync.sync_month(y, m, force=False)
                except Exception as exc: print(f"NAR month {y}-{m:02d} skipped: {exc}")
            if date == _today_iso():
                try: sync.sync_daily(force=False)
                except Exception as exc: print(f"NAR daily skipped: {exc}")
        except Exception as exc:
            print(f"NAR background sync failed: {exc}")
    threading.Thread(target=_bg_nar_sync, daemon=True).start()

    central_store = CentralStore()
    central_rows = central_store.races_json(date)
    if os.getenv("CENTRAL_FEED_URL"):
        try:
            fresh = fetch_central_feed(date)
            if fresh:
                central_store.upsert(fresh)
                central_rows = central_store.races_json(date)
        except Exception as exc:
            print(f"Central feed fetch failed: {exc}")
    return live_local + central_rows

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(INDEX, headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/styles.css")
def styles():
    return Response(CSS, media_type="text/css", headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/app.js")
def appjs():
    return Response(JS, media_type="application/javascript", headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/manifest.webmanifest")
def manifest():
    return Response(MANIFEST, media_type="application/manifest+json", headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/sw.js")
def service_worker():
    return Response(SW, media_type="application/javascript", headers={"Service-Worker-Allowed":"/"})
