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

app = FastAPI(title="競馬展開AI", version="4.1-production-v22-neon-home")

INDEX = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b1220">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="競馬展開AI">
<link rel="manifest" href="/manifest.webmanifest?v=22">
<link rel="stylesheet" href="/styles.css?v=22">
<title>競馬展開AI</title>
</head>
<body>
<div id="app"><div class="boot">競馬展開AIを起動中…</div></div>
<script src="/app.js?v=22"></script>
</body>
</html>"""

CSS = r"""
:root{--bg:#f3f5f9;--card:#fff;--text:#101828;--muted:#667085;--line:#e4e7ec;--navy:#0b1220;--blue:#2563eb;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Hiragino Sans","Yu Gothic",sans-serif}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-weight:400;-webkit-text-size-adjust:100%}button,input{font:inherit;font-weight:400}.boot{padding:42px 16px;text-align:center;color:#64748b}.shell{max-width:760px;margin:0 auto;padding-bottom:calc(30px + env(safe-area-inset-bottom))}.header{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.98);color:#fff;padding:calc(8px + env(safe-area-inset-top)) 10px 9px;box-shadow:0 1px 8px rgba(0,0,0,.14)}.header-row{display:flex;align-items:center;gap:8px}.header-title{min-width:0;flex:1}.header h1{font-size:18px;margin:0;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.header small{display:block;color:#cbd5e1;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.header button{border:0;background:rgba(255,255,255,.12);color:#fff;border-radius:10px;padding:7px 10px}.main{padding:8px;display:grid;gap:8px}.card{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:11px;box-shadow:0 1px 2px rgba(16,24,40,.03)}.section-title,.card h2{margin:0 0 8px;font-size:17px;font-weight:500}.muted{color:var(--muted)}.row{display:flex;align-items:center;gap:8px}.between{justify-content:space-between}.label{font-size:11px;color:var(--muted);margin-bottom:4px}.setup-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:8px}.date{width:100%;height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;background:#fff}.segment{display:grid;grid-template-columns:1fr 1fr;gap:5px}.segment button{height:40px;border:1px solid var(--line);background:#fff;border-radius:10px}.segment button.active{background:var(--navy);color:#fff;border-color:var(--navy)}.home-heading{font-size:14px;font-weight:500;margin-bottom:8px}.pill{font-size:10px;background:#eef2f6;border-radius:999px;padding:4px 8px}.live-dot{font-size:9px;background:#fee2e2;color:#b42318;border-radius:999px;padding:4px 7px}.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}.live-race{border:1px solid var(--line);background:#fff;border-radius:11px;padding:9px;text-align:left;min-width:0}.live-top{display:flex;justify-content:space-between;gap:5px;align-items:center}.live-track{font-size:13px}.live-title{font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:4px 0}.live-time{font-size:20px}.live-tag{font-size:9px;border-radius:999px;padding:3px 5px;background:#eff6ff;color:#1d4ed8}.live-tag.now{background:#fff1f2;color:#be123c}.live-tag.running{background:#ecfdf3;color:#027a48}.empty{padding:16px 6px;text-align:center;color:var(--muted);font-size:12px}.notice{background:#fff7ed;color:#9a3412;border-radius:10px;padding:10px;font-size:12px}.ai-card{overflow:hidden;position:relative;background:linear-gradient(135deg,#0b1220,#172554 68%,#1d4ed8);color:#fff;border:0}.ai-card:after{content:"";position:absolute;width:170px;height:170px;border-radius:50%;right:-80px;top:-80px;background:rgba(59,130,246,.25)}.ai-kicker{font-size:10px;letter-spacing:.12em;color:#93c5fd}.ai-title{font-size:22px;font-weight:600;margin:4px 0}.ai-next{font-size:13px;color:#dbeafe;margin:7px 0 10px}.ai-actions{display:grid;grid-template-columns:1fr auto;gap:7px;position:relative;z-index:1}.ai-primary,.ai-secondary{border:0;border-radius:11px;padding:10px 12px}.ai-primary{background:#fff;color:#111827}.ai-secondary{background:rgba(255,255,255,.13);color:#fff;border:1px solid rgba(255,255,255,.2)}.venue-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.venue{border:1px solid var(--line);background:#fff;border-radius:11px;padding:11px;text-align:left}.venue .name{font-size:17px}.venue .count{font-size:11px;color:var(--muted);margin-top:2px}.race-list{display:grid;gap:7px}.race{width:100%;border:1px solid var(--line);background:#fff;border-radius:11px;padding:10px;text-align:left;display:flex;align-items:center;justify-content:space-between;gap:8px}.race.final{background:#f0fdf4;border-color:#a7f3d0}.race-main{min-width:0}.race-top{display:flex;gap:7px;align-items:baseline;min-width:0}.race-no{font-size:17px}.race-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:14px}.race-time{font-size:12px;color:#475467;margin-top:3px}.final-badge{font-size:11px;color:#067647;border:1px solid #75e0a7;background:#fff;border-radius:6px;padding:3px 7px}.picker-list{display:grid;gap:6px}.picker-item{border:1px solid var(--line);background:#fff;border-radius:11px;padding:11px;display:flex;justify-content:space-between;align-items:center;text-align:left}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-top:9px}.metric{background:#f8fafc;border-radius:9px;padding:7px 2px;text-align:center}.metric b{display:block;font-size:12px;font-weight:400}.metric span{font-size:8px;color:var(--muted)}.occupancy{font-size:32px;margin:2px 0 4px}.style-list{display:grid;gap:6px}.style-row{border:1px solid var(--line);border-radius:11px;padding:8px}.style-top{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto;gap:6px;align-items:center}.horse-name{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.score{font-size:12px}.expected{font-size:9px;background:#f1f5f9;border-radius:999px;padding:3px 6px}.rates{display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin-top:6px}.rate{background:#f8fafc;border-radius:7px;text-align:center;padding:5px 1px;font-size:11px}.rate small{display:block;font-size:8px;color:var(--muted)}.frame-badge{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;border:1px solid rgba(0,0,0,.16);font-size:13px;flex:0 0 auto}.frame1{background:#fff;color:#111}.frame2{background:#222;color:#fff}.frame3{background:#e53935;color:#fff}.frame4{background:#1e66d0;color:#fff}.frame5{background:#f5d547;color:#111}.frame6{background:#3a9b56;color:#fff}.frame7{background:#f28c28;color:#111}.frame8{background:#e894b7;color:#111}.pace-card{overflow:hidden}.pace-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.pace-stage{font-size:13px;background:#eff6ff;color:#1d4ed8;border-radius:999px;padding:4px 8px}.pace-board{position:relative;height:290px;border-radius:13px;overflow:hidden;background:linear-gradient(90deg,#e7f6e8 0 14%,#f3ead8 14% 88%,#e7f6e8 88%);border:1px solid #d0d5dd}.pace-board:before,.pace-board:after{content:"";position:absolute;top:0;bottom:0;width:2px;background:rgba(255,255,255,.75)}.pace-board:before{left:14%}.pace-board:after{right:12%}.pace-chip{position:absolute;height:25px;display:flex;align-items:center;gap:4px;transition:left 1.25s ease,top 1.25s ease;white-space:nowrap;max-width:118px}.pace-chip .frame-badge{width:24px;height:24px;font-size:11px;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.2)}.pace-name{background:rgba(255,255,255,.93);border:1px solid rgba(0,0,0,.08);border-radius:6px;padding:3px 5px;font-size:9px;overflow:hidden;text-overflow:ellipsis;max-width:78px}.pace-legend{display:flex;gap:5px;margin-top:7px}.pace-legend button{flex:1;border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 2px;font-size:11px}.pace-legend button.active{background:#111827;color:#fff}.scenario-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.scenario{background:#f8fafc;border-radius:11px;padding:9px 4px;text-align:center}.scenario .prob{font-size:24px;margin:4px 0}.scenario-horses{display:flex;justify-content:center;gap:3px;flex-wrap:wrap}.scenario-horses .frame-badge{width:24px;height:24px;font-size:11px}.marks{display:grid;grid-template-columns:1fr 1fr;gap:5px}.mark{display:grid;grid-template-columns:30px 28px minmax(0,1fr);gap:5px;align-items:center;background:#f8fafc;border-radius:10px;padding:8px}.mark-symbol{font-size:18px}.mark strong{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.horse-card{border:1px solid var(--line);border-radius:11px;padding:9px;margin-top:6px}.horse-card summary{list-style:none;display:flex;align-items:center;gap:7px}.horse-card summary::-webkit-details-marker{display:none}.horse-detail{padding-top:8px;font-size:12px;line-height:1.5}.recent{border-top:1px dashed var(--line);padding-top:6px;margin-top:6px}.result-row{display:grid;grid-template-columns:34px 28px minmax(0,1fr) auto;gap:6px;align-items:center;padding:7px 0;border-bottom:1px solid var(--line)}.result-row:last-child{border-bottom:0}.result-name{font-weight:700}.time-old{text-decoration:line-through;color:#98a2b3;margin-right:4px}.time-changed{color:#d92d20}.backline{font-size:11px;color:var(--muted);margin-top:4px}
@media(max-width:390px){.main{padding:6px}.card{padding:9px}.live-grid{grid-template-columns:1fr 1fr}.style-top{grid-template-columns:auto minmax(0,1fr) auto}.expected{grid-column:2/4;justify-self:start}.marks{grid-template-columns:1fr}.pace-board{height:280px}}

/* v22 home: lightweight neon/glass top, no heavy images */
.home-shell{max-width:760px;min-height:100vh;margin:0 auto;padding-bottom:calc(30px + env(safe-area-inset-bottom));background:
 radial-gradient(640px 300px at 78% -2%,rgba(17,111,255,.34),transparent 62%),
 radial-gradient(420px 240px at 12% 18%,rgba(0,214,255,.12),transparent 70%),
 linear-gradient(180deg,#061b3f 0,#04152f 42%,#031126 100%);color:#f7fbff;overflow:hidden}
.home-main{padding:0 12px 18px;display:grid;gap:12px}
.home-hero{position:relative;display:flex;align-items:center;justify-content:space-between;min-height:154px;padding:calc(18px + env(safe-area-inset-top)) 15px 12px;overflow:hidden}
.home-hero:before{content:"♞";position:absolute;right:66px;top:calc(3px + env(safe-area-inset-top));font-size:126px;line-height:1;color:rgba(36,130,255,.20);filter:drop-shadow(0 0 18px rgba(25,137,255,.28));transform:rotate(-7deg);pointer-events:none}
.brand-wrap{position:relative;z-index:2;min-width:0}.brand-main{font-size:34px;line-height:1.04;font-weight:760;letter-spacing:.015em;color:#fff;text-shadow:0 2px 18px rgba(0,0,0,.28)}
.brand-main .ai{background:linear-gradient(180deg,#58f2ff,#2f8cff);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand-sub{margin-top:6px;color:#75e8ff;font-size:14px;letter-spacing:.22em;font-weight:400}
.hero-refresh{position:relative;z-index:3;width:66px;height:66px;flex:0 0 66px;border-radius:50%;border:1px solid rgba(122,194,255,.48);background:linear-gradient(180deg,rgba(19,72,126,.68),rgba(7,38,81,.72));color:#fff;box-shadow:inset 0 0 22px rgba(61,149,255,.16),0 8px 24px rgba(0,0,0,.18);display:grid;place-items:center;padding:0}
.hero-refresh .refresh-icon{font-size:29px;line-height:1}.hero-refresh small{display:block;font-size:10px;margin-top:-10px;color:#ddecff}
.home-card{position:relative;border:1px solid rgba(77,156,232,.44);border-radius:17px;background:linear-gradient(180deg,rgba(11,47,92,.79),rgba(6,33,70,.88));box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 7px 24px rgba(0,0,0,.12);padding:13px;overflow:hidden}
.home-section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:11px}.home-section-title{display:flex;align-items:center;gap:8px;font-size:17px;font-weight:650}.home-section-icon{width:24px;height:24px;display:grid;place-items:center;color:#b9d8ff;font-size:18px}.home-link{border:0;background:transparent;color:#a9c1df;font-size:12px;padding:5px 2px}.home-link:after{content:" ›";font-size:18px;vertical-align:-1px}
.home-date-row{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(190px,.85fr);gap:11px;align-items:end}.home-date-wrap{min-width:0}.home-date-label{font-size:13px;color:#bfd1ea;margin-bottom:6px}.home-date{width:100%;height:49px;border:0;background:transparent;color:#fff;font-size:24px;font-weight:620;padding:0;color-scheme:dark}.home-date::-webkit-calendar-picker-indicator{filter:invert(1) opacity(.8)}
.home-segment{display:grid;grid-template-columns:1fr 1fr;border:1px solid rgba(118,174,231,.58);border-radius:13px;overflow:hidden;background:rgba(3,22,53,.48)}.home-segment button{height:49px;border:0;background:transparent;color:#dfeeff;font-size:17px}.home-segment button.active{color:#fff;background:linear-gradient(135deg,#235de4,#5f45eb);box-shadow:inset 0 0 0 1px #52dbff,0 0 18px rgba(34,164,255,.28)}
.home-live-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.home-live-race{position:relative;min-height:123px;border:1px solid rgba(96,156,220,.54);border-radius:13px;overflow:hidden;padding:11px;text-align:left;color:#fff;background:linear-gradient(150deg,rgba(12,43,81,.96),rgba(18,59,112,.74));box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}
.home-live-race:after{content:"";position:absolute;inset:auto -20% -32% 26%;height:78%;background:repeating-linear-gradient(168deg,rgba(101,161,220,.14) 0 2px,transparent 2px 18px);transform:skewX(-18deg);pointer-events:none}
.home-live-race.urgent{border-color:rgba(255,89,108,.9);box-shadow:0 0 16px rgba(255,53,83,.13),inset 0 1px 0 rgba(255,255,255,.04)}
.home-live-race .live-top{position:relative;z-index:1}.home-live-race .live-tag{font-size:9px;padding:4px 8px}.home-live-race .live-tag.running{background:#ef4e5c;color:#fff}.home-live-race .live-tag.now{background:#648f3d;color:#fff}.home-live-race .live-tag:not(.running):not(.now){background:#1460ae;color:#dceeff}.home-race-line{position:relative;z-index:1;display:flex;align-items:baseline;gap:5px;margin-top:13px;min-width:0}.home-track{font-size:18px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.home-rno{font-size:25px;font-weight:750;color:#59ebff;white-space:nowrap}.home-rtitle{position:relative;z-index:1;font-size:12px;color:#e8f0fa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}.home-rtime{position:relative;z-index:1;font-size:17px;color:#e8f2ff;margin-top:6px}.home-rtime:before{content:"◷";font-size:14px;margin-right:5px;color:#c9ddf7}
.home-empty{padding:18px 6px;text-align:center;color:#91a9c8;font-size:12px}
.home-venue-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.home-venue{height:64px;border:1px solid rgba(94,155,218,.55);border-radius:13px;background:linear-gradient(145deg,rgba(11,43,82,.92),rgba(14,54,100,.64));color:#fff;display:grid;grid-template-columns:41px minmax(0,1fr) auto auto;gap:8px;align-items:center;padding:8px 10px;text-align:left}.venue-mark{width:39px;height:39px;border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at 35% 30%,#fff,#dff5ff 72%);color:#0c5b9a;font-size:16px;font-weight:780;box-shadow:0 0 0 2px rgba(83,211,255,.14)}.home-venue-name{font-size:17px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.home-venue-count{font-size:12px;color:#d5e3f5}.home-arrow{font-size:25px;color:#d6e8fa}
.home-ai-card{padding:13px}.home-ai-top{display:flex;align-items:center;gap:9px}.home-ai-bars{display:flex;align-items:end;gap:3px;width:27px;height:25px}.home-ai-bars i{display:block;width:5px;border-radius:2px;background:#52edff;box-shadow:0 0 8px rgba(82,237,255,.28)}.home-ai-bars i:nth-child(1){height:9px}.home-ai-bars i:nth-child(2){height:17px}.home-ai-bars i:nth-child(3){height:24px}.home-ai-copy{min-width:0;flex:1}.home-ai-title{font-size:20px;font-weight:720}.home-ai-sub{font-size:11px;color:#b4c8e0;margin-top:2px}.home-ai-actions{display:flex;gap:7px;align-items:center}.home-ai-select{border:1px solid rgba(114,173,232,.55);background:rgba(5,28,61,.72);color:#dceeff;border-radius:10px;padding:9px 10px;font-size:11px}.home-ai-go{border:1px solid #54ddff;background:linear-gradient(135deg,#156ee9,#6546ee);color:#fff;border-radius:999px;padding:11px 15px;font-size:13px;box-shadow:0 0 17px rgba(55,161,255,.23)}
.home-ai-next{font-size:11px;color:#aecaeb;margin:8px 0 7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mini-track{position:relative;height:126px;border-radius:13px;overflow:hidden;border:1px solid rgba(95,180,222,.45);background:linear-gradient(180deg,#194c61 0 18%,#2e8b62 18% 29%,#af9066 29% 83%,#3b9365 83%);box-shadow:inset 0 0 28px rgba(0,0,0,.18)}.mini-track:before,.mini-track:after{content:"";position:absolute;left:0;right:0;height:2px;background:rgba(255,255,255,.78)}.mini-track:before{top:31px}.mini-track:after{bottom:21px}.mini-stage-row{position:absolute;left:10px;right:10px;top:5px;display:flex;justify-content:space-between;font-size:9px;color:#edf7ff;z-index:2}.mini-stage-row span{background:rgba(4,25,55,.66);border-radius:999px;padding:3px 8px}.mini-horse{position:absolute;width:25px;height:25px;border-radius:50%;display:grid;place-items:center;border:2px solid rgba(255,255,255,.87);font-size:10px;box-shadow:0 2px 4px rgba(0,0,0,.28);font-weight:600}.mini-next-label{position:absolute;right:9px;bottom:6px;font-size:8px;color:rgba(255,255,255,.75)}
.home-card .time-old{color:#8097b4}.home-card .time-changed{color:#ff858f}.home-card button{-webkit-tap-highlight-color:transparent}
@media(max-width:460px){.home-hero{min-height:140px;padding-left:13px;padding-right:13px}.brand-main{font-size:30px}.brand-sub{font-size:12px}.hero-refresh{width:59px;height:59px;flex-basis:59px}.home-main{padding-left:9px;padding-right:9px}.home-card{padding:11px}.home-date-row{grid-template-columns:1.05fr .95fr;gap:7px}.home-date{font-size:21px}.home-segment button{font-size:15px}.home-live-race{min-height:116px;padding:9px}.home-track{font-size:16px}.home-rno{font-size:23px}.home-rtime{font-size:15px}.home-venue{height:59px;padding:7px}.venue-mark{width:36px;height:36px}.home-venue-name{font-size:16px}.home-ai-title{font-size:18px}.home-ai-actions{gap:5px}.home-ai-select{padding:8px 8px}.home-ai-go{padding:10px 12px}.mini-track{height:120px}}
@media(max-width:360px){.brand-main{font-size:27px}.home-date-row{grid-template-columns:1fr}.home-live-grid,.home-venue-grid{grid-template-columns:1fr}.home-ai-top{flex-wrap:wrap}.home-ai-actions{width:100%;justify-content:flex-end}}

"""

JS = r"""
(function(){
"use strict";
var CENTRAL=["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"];
var LOCAL=["帯広","門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"];
var app=document.getElementById("app");
var state={date:today(),circuit:"地方",races:[],track:null,race:null,picker:false,loading:false,error:null,stage:0,timer:null};
function today(){var d=new Date(Date.now()+9*3600000);return d.toISOString().slice(0,10)}
function esc(v){return String(v==null?"":v).replace(/[&<>\"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]})}
function n(v,d){var x=Number(v);return isFinite(x)?x:(d||0)}
function clamp(x,a,b){return Math.max(a,Math.min(b,x))}
function pct(v){return Math.round(clamp(n(v),0,1)*100)+"%"}
function mean(a){if(!a.length)return 0;var s=0,i;for(i=0;i<a.length;i++)s+=a[i];return s/a.length}
function placeRate(s){s=s||{};var starts=n(s.starts);return starts?(n(s.wins)+n(s.seconds)+n(s.thirds))/starts:0}
function season(iso){var m=n(String(iso||"").split("-")[1]);if(m>=3&&m<=5)return"春";if(m>=6&&m<=8)return"夏";if(m>=9&&m<=11)return"秋";return"冬"}
function fmtMoney(v){try{return new Intl.NumberFormat("ja-JP").format(n(v))}catch(e){return String(n(v))}}
function fmtTime(v){v=n(v);if(!v)return"—";var m=Math.floor(v/60),s=(v-m*60).toFixed(1);if(m===0)return s;return m+":"+(Number(s)<10?"0":"")+s}
function frame(h){var f=n(h&&h.frameNumber,n(h&&h.horseNumber,1));return clamp(f,1,8)}
function badge(h){return '<span class="frame-badge frame'+frame(h)+'">'+esc(h&&h.horseNumber)+'</span>'}
function horseByNo(r,no){var hs=r.horses||[],i;for(i=0;i<hs.length;i++)if(n(hs[i].horseNumber)===n(no))return hs[i];return null}
function isFinal(r){return !!(r&&r.result&&(r.result.status==="確定"||(r.result.finishers||[]).length))}
function mins(t){var m=String(t||"").match(/^(\d{1,2}):(\d{2})/);return m?n(m[1])*60+n(m[2]):9999}
function nowMins(){var d=new Date(Date.now()+9*3600000);return d.getUTCHours()*60+d.getUTCMinutes()}
function timeHtml(r){var a=String(r.startTime||"—"),o=String(r.scheduledStartTime||a),c=!!r.startTimeChanged||(a!==o&&a!=="—"&&o!=="—");return c?'<span class="time-old">'+esc(o)+'</span><span class="time-changed">'+esc(a)+' 修正</span>':esc(a)}
function header(title,back,sub){return '<header class="header"><div class="header-row">'+(back?'<button data-action="back">‹</button>':'')+'<div class="header-title"><h1>'+esc(title)+'</h1>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div><button data-action="reload">↻</button></div></header>'}
function styleRates(h){var rs=(h.recentRaces||[]).slice(0,8),c=[0,0,0,0],valid=0,i,p,x;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];x=n(p[0],0);if(!x)continue;valid++;if(x===1)c[0]++;else if(x<=4)c[1]++;else if(x<=7)c[2]++;else c[3]++}var d=valid||1;return{front:c[0]/d,stalk:c[1]/d,mid:c[2]/d,close:c[3]/d}}
function fadeRate(h){var rs=(h.recentRaces||[]).slice(0,8),e=0,f=0,i,p,first,last,fin;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];first=n(p[0]);if(!first||first>4)continue;e++;last=n(p[p.length-1]);fin=n(rs[i].finish);if((last&&last>=first+2)||(fin&&fin>=first+3))f++}return e?f/e:0}
function moveRate(h){var rs=(h.recentRaces||[]).slice(0,8),v=0,g=0,i,p,a,b;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(p.length<2)continue;v++;a=n(p[0]);b=n(p[p.length-1]);if(a&&b&&b<=a-2)g++}return v?g/v:0}
function stylePoint(rt){return rt.front+2*rt.stalk+3*rt.mid+4*rt.close}
function styleName(pt){if(pt<1.65)return"逃げ";if(pt<2.35)return"先行";if(pt<3.15)return"差し";return"追込"}
function earlyOcc(r){var hs=r.horses||[],nums=[],early=[],moved=[],i,rr,p,j,hit;for(i=0;i<hs.length;i++){rr=(hs[i].recentRaces||[])[0];if(!rr)continue;p=rr.cornerPositions||[];hit=false;for(j=0;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3){hit=true;break}if(hit){nums.push(n(hs[i].horseNumber));if(n(p[0])<=3)early.push(n(hs[i].horseNumber));else moved.push(n(hs[i].horseNumber))}}return{nums:nums,early:early,moved:moved,rate:hs.length?nums.length/hs.length:0}}
function recentDistance(h){var rr=(h.recentRaces||[])[0];return rr?n(rr.distance):0}
function recentFirst(h){var rr=(h.recentRaces||[])[0],p=rr&&rr.cornerPositions||[];return n(p[0],99)}
function recentFinishScore(h){var rs=(h.recentRaces||[]).slice(0,5),a=[],i,f;for(i=0;i<rs.length;i++){f=n(rs[i].finish);if(f)a.push(clamp((10-f)/9,0,1))}return a.length?mean(a):0.45}
function speedRaw(h,dist){var rs=(h.recentRaces||[]).slice(0,6),a=[],i,rr,t;for(i=0;i<rs.length;i++){rr=rs[i];t=n(rr.timeSeconds);if(t&&n(rr.distance)){a.push((n(rr.distance)/t)*(1-Math.min(Math.abs(n(rr.distance)-dist)/dist,.3)*.3))}}return a.length?Math.max.apply(null,a):0}
function normalize(vals,x){if(!vals.length)return.5;var lo=Math.min.apply(null,vals),hi=Math.max.apply(null,vals);return hi===lo?.5:(x-lo)/(hi-lo)}
function buildRows(r){var hs=r.horses||[],tmp=[],speeds=[],prizes=[],i,h,rt,pt,sr;for(i=0;i<hs.length;i++){h=hs[i];rt=styleRates(h);pt=stylePoint(rt);sr=speedRaw(h,n(r.distance));tmp.push({horse:h,front:rt.front,stalk:rt.stalk,mid:rt.mid,close:rt.close,fade:fadeRate(h),move:moveRate(h),score:pt,expected:styleName(pt),speedRaw:sr});speeds.push(sr);prizes.push(n(h.prizeMoneyAtRace))}for(i=0;i<tmp.length;i++){var x=tmp[i],hh=x.horse,rf=recentFirst(hh),rd=recentDistance(hh),shorten=rd>n(r.distance)+150?1:0,outer=n(hh.horseNumber)>(hs.length*.72)?1:0,edge=n(hh.horseNumber)===hs.length?1:0;var forward=x.front*1.45+x.stalk*.85+(rf<99?clamp((8-rf)/7,0,1)*.35:0)+shorten*(x.front*.35+x.stalk*.12)+edge*.08-outer*.04;var abil=recentFinishScore(hh)*.32+normalize(speeds,x.speedRaw)*.20+normalize(prizes,n(hh.prizeMoneyAtRace))*.12+placeRate(hh.jockeyStats)*.10+placeRate(hh.trainerStats)*.07+(1-x.fade)*.09+x.move*.06+clamp((57-n(hh.carriedWeight))/8,0,1)*.04;x.forward=forward;x.ability=abil}return tmp}
function rowByNo(rows,no){var i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===n(no))return rows[i];return null}
function pressureInfo(rows){var sorted=rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),p={};var i,x,l,r;for(i=0;i<sorted.length;i++){x=sorted[i];l=i?sorted[i-1]:null;r=i<sorted.length-1?sorted[i+1]:null;var lp=l?l.forward:0,rp=r?r.forward:0;var sandwich=(lp>.8&&rp>.8)?1:0,adj=(lp>.8?1:0)+(rp>.8?1:0);p[n(x.horse.horseNumber)]={adj:adj,sandwich:sandwich}}return p}
function scenarioModel(r,rows){var p=pressureInfo(rows),front=rows.slice().sort(function(a,b){return b.forward-a.forward}),front3=front.slice(0,Math.min(3,front.length));var fade=mean(front3.map(function(x){return x.fade})),pressure=mean(front3.map(function(x){var q=p[n(x.horse.horseNumber)]||{};return n(q.adj)*.18+n(q.sandwich)*.28}));var shortFront=0,i;if(front.length&&recentDistance(front[0].horse)>n(r.distance)+150)shortFront=.08;var courseFront=(r.circuit==="地方"&&n(r.distance)<=1400)?.08:(n(r.distance)<=1200?.05:0);var A=.34+courseFront+shortFront-(fade*.12)-(pressure*.08);var C=.24+(fade*.15)+(pressure*.12)-courseFront*.45-shortFront*.5;A=clamp(A,.18,.60);C=clamp(C,.12,.50);var B=1-A-C;if(B<.20){var need=.20-B;A-=need*.55;C-=need*.45;B=.20}var sum=A+B+C;A/=sum;B/=sum;C/=sum;return[{code:"A",title:"前残り",prob:A},{code:"B",title:"平均",prob:B},{code:"C",title:"差し届く",prob:C}]}
function startOrder(rows){return rows.slice().sort(function(a,b){return b.forward-a.forward||n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function cornerScores(r,rows,sc){var top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0].code,out=[],i,x,s;for(i=0;i<rows.length;i++){x=rows[i];s=x.forward*.42+x.ability*.35+x.move*.18-x.fade*.18;if(top==="A")s+=x.forward*.22-x.fade*.12;if(top==="C")s+=x.move*.28+x.mid*.10+x.close*.14-x.forward*.04;out.push({row:x,s:s})}return out.sort(function(a,b){return b.s-a.s}).map(function(z){return z.row})}
function suitability(rows,sc){var out={},i,x,win,place,show;for(i=0;i<rows.length;i++){x=rows[i];win=0;place=0;show=0;for(var j=0;j<sc.length;j++){var s=sc[j],base=x.ability,fit=0;if(s.code==="A")fit=x.forward*.38+(1-x.fade)*.24-x.close*.08;else if(s.code==="B")fit=x.ability*.18+(1-Math.abs(x.score-2.55)/2.5)*.16+x.move*.08;else fit=x.move*.30+x.mid*.16+x.close*.22-x.fade*.06;var q=base+fit;win+=s.prob*q;place+=s.prob*(q*.82+(1-x.fade)*.16+x.forward*.06);show+=s.prob*(q*.70+(1-x.fade)*.19+x.move*.10)}out[n(x.horse.horseNumber)]={win:win,place:place,show:show,overall:win*.52+place*.30+show*.18}}return out}
function makeMarks(rows,suit){var a=rows.slice().sort(function(x,y){var sx=suit[n(x.horse.horseNumber)],sy=suit[n(y.horse.horseNumber)];return sy.overall-sx.overall}),syms=["◎","○","▲","☆","△","注"],out=[],i;for(i=0;i<Math.min(syms.length,a.length);i++)out.push([syms[i],a[i].horse]);return out}
function predict(r){var rows=buildRows(r),occ=earlyOcc(r),sc=scenarioModel(r,rows),suit=suitability(rows,sc),marks=makeMarks(rows,suit),start=startOrder(rows),corner=cornerScores(r,rows,sc),straight=rows.slice().sort(function(a,b){return suit[n(b.horse.horseNumber)].overall-suit[n(a.horse.horseNumber)].overall});for(var i=0;i<sc.length;i++){var code=sc[i].code,candidates=rows.slice().sort(function(a,b){function ss(x){var z=suit[n(x.horse.horseNumber)];if(code==="A")return z.overall+x.forward*.22-x.fade*.12;if(code==="C")return z.overall+x.move*.18+x.close*.12;return z.overall}return ss(b)-ss(a)});sc[i].horses=candidates.slice(0,3).map(function(x){return x.horse})}return{rows:rows,occ:occ,scenarios:sc,marks:marks,plan:{start:start,corner:corner,straight:straight},suit:suit}}
function nextRace(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime});a.sort(function(x,y){var ax=mins(x.startTime),ay=mins(y.startTime),now=nowMins(),kx=ax>=now?ax:ax+1440,ky=ay>=now?ay:ay+1440;return kx-ky});return a.length?a[0]:null}
function liveRaces(){if(state.date!==today())return[];var now=nowMins(),a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime&&mins(r.startTime)>=now-25});a.sort(function(x,y){return mins(x.startTime)-mins(y.startTime)});return a.slice(0,4)}
function liveTag(r){var d=mins(r.startTime)-nowMins();if(d<0&&d>=-25)return'<span class="live-tag running">進行中</span>';if(d>=0&&d<=10)return'<span class="live-tag now">まもなく</span>';return'<span class="live-tag">次走</span>'}
function homeVenueMark(track){var t=String(track||"?");return '<span class="venue-mark">'+esc(t.slice(0,1))+'</span>'}
function miniPacePreview(r){if(!r||!(r.horses||[]).length)return '<div class="mini-track"><div class="mini-stage-row"><span>スタート</span><span>4コーナー</span><span>直線</span></div><div class="home-empty">出走馬データ取得待ち</div></div>';try{var p=predict(r),a=(p.plan&&p.plan.corner)||[],count=Math.min(a.length,14),chips=[],i,h,frameNo,left,top;if(!count)return '<div class="mini-track"><div class="mini-stage-row"><span>スタート</span><span>4コーナー</span><span>直線</span></div></div>';for(i=0;i<count;i++){h=a[i].horse||a[i];frameNo=frame(h);left=6+(count-1-i)*(84/Math.max(1,count-1));top=39+((i*31)%58);chips.push('<span class="mini-horse frame'+frameNo+'" style="left:calc('+left.toFixed(1)+'% - 12px);top:'+top+'px">'+esc(h.horseNumber)+'</span>')}return '<div class="mini-track"><div class="mini-stage-row"><span>スタート</span><span>4コーナー</span><span>直線</span></div>'+chips.join("")+'<span class="mini-next-label">AI隊列プレビュー</span></div>'}catch(e){return '<div class="mini-track"><div class="mini-stage-row"><span>スタート</span><span>4コーナー</span><span>直線</span></div></div>'}}
function renderHome(){var all=state.circuit==="中央"?CENTRAL:LOCAL,venues=[],i,t,c;for(i=0;i<all.length;i++){t=all[i];c=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===t}).length;if(c)venues.push([t,c])}
var live=liveRaces(),liveHtml="";if(state.loading)liveHtml='<div class="home-empty">読込中…</div>';else if(state.date!==today())liveHtml='<div class="home-empty">当日を選ぶとリアルタイム表示します</div>';else if(live.length)liveHtml='<div class="home-live-grid">'+live.map(function(r){var tag=liveTag(r),urgent=tag.indexOf('running')>=0?' urgent':'';return '<button class="home-live-race'+urgent+'" data-race="'+esc(r.id)+'"><div class="live-top">'+tag+'<span class="home-arrow">›</span></div><div class="home-race-line"><span class="home-track">'+esc(r.track)+'</span><span class="home-rno">'+esc(r.raceNumber)+'R</span></div><div class="home-rtitle">'+esc(r.title||"")+'</div><div class="home-rtime">'+timeHtml(r)+'</div></button>'}).join("")+'</div>';else liveHtml='<div class="home-empty">直近の未確定レースはありません</div>';
var vh=venues.length?'<div class="home-venue-grid">'+venues.map(function(v){return '<button class="home-venue" data-track="'+esc(v[0])+'">'+homeVenueMark(v[0])+'<span class="home-venue-name">'+esc(v[0])+'</span><span class="home-venue-count">'+v[1]+'レース</span><span class="home-arrow">›</span></button>'}).join("")+'</div>':'<div class="home-empty">'+(state.error?esc(state.error):(state.circuit==="中央"?"中央データ源未接続、または開催データなし":"この日の取得データはありません"))+'</div>';
var nx=nextRace(),aiNext=nx?'次のレース：'+esc(nx.track)+' '+esc(nx.raceNumber)+'R　'+timeHtml(nx):'未確定レースの取得待ち',aiButtons=nx?'<div class="home-ai-actions"><button class="home-ai-select" data-action="pace-pick">選択</button><button class="home-ai-go" data-action="pace-next">展開を見る ›</button></div>':'<div class="home-ai-actions"><button class="home-ai-select" data-action="pace-pick">選択</button></div>';
return '<div class="home-shell"><div class="home-hero"><div class="brand-wrap"><div class="brand-main">競馬展開<span class="ai">AI</span></div><div class="brand-sub">Race Intelligence</div></div><button class="hero-refresh" data-action="reload"><span class="refresh-icon">↻</span><small>更新</small></button></div><main class="home-main">'+
'<section class="home-card"><div class="home-section-head"><div class="home-section-title"><span class="home-section-icon">▣</span>日付・開催区分</div></div><div class="home-date-row"><div class="home-date-wrap"><div class="home-date-label">開催日</div><input id="date" class="home-date" type="date" value="'+esc(state.date)+'"></div><div class="home-segment"><button data-circuit="中央" class="'+(state.circuit==="中央"?"active":"")+'">中央</button><button data-circuit="地方" class="'+(state.circuit==="地方"?"active":"")+'">地方</button></div></div></section>'+
'<section class="home-card"><div class="home-section-head"><div class="home-section-title"><span class="home-section-icon">◉</span>リアルタイムのレース</div></div>'+liveHtml+'</section>'+
'<section class="home-card"><div class="home-section-head"><div class="home-section-title"><span class="home-section-icon">●</span>開催場</div></div>'+vh+'</section>'+
'<section class="home-card home-ai-card"><div class="home-ai-top"><span class="home-ai-bars"><i></i><i></i><i></i></span><div class="home-ai-copy"><div class="home-ai-title">AI展開予想</div><div class="home-ai-sub">AIがペースを解析し、隊列と展開を予測</div></div>'+aiButtons+'</div><div class="home-ai-next">'+aiNext+'</div>'+miniPacePreview(nx)+'</section>'+
'</main></div>'}
function renderPicker(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)});a.sort(function(x,y){return mins(x.startTime)-mins(y.startTime)});return'<div class="shell">'+header("展開予想を選択",true,state.date+'・'+state.circuit)+'<main class="main"><section class="card"><div class="picker-list">'+(a.length?a.map(function(r){return'<button class="picker-item" data-race="'+esc(r.id)+'"><span>'+esc(r.track)+' '+esc(r.raceNumber)+'R　'+esc(r.title||"")+'</span><strong>'+timeHtml(r)+'</strong></button>'}).join(""):'<div class="empty">未確定レースはありません</div>')+'</div></section></main></div>'}
function renderVenue(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===state.track});a.sort(function(x,y){return n(x.raceNumber)-n(y.raceNumber)});return'<div class="shell">'+header(state.track,true,state.date+'・'+state.circuit)+'<main class="main"><section class="card"><div class="race-list">'+(a.length?a.map(function(r){return'<button class="race '+(isFinal(r)?'final':'')+'" data-race="'+esc(r.id)+'"><span class="race-main"><span class="race-top"><span class="race-no">'+esc(r.raceNumber)+'R</span><span class="race-title">'+esc(r.title||"")+'</span></span><div class="race-time">'+timeHtml(r)+'</div></span>'+(isFinal(r)?'<span class="final-badge">確定</span>':'<span>›</span>')+'</button>'}).join(""):'<div class="empty">レースデータなし</div>')+'</div></section></main></div>'}
function renderResult(r){if(!isFinal(r))return"";var f=(r.result.finishers||[]).slice(0,3);return'<section class="card"><div class="section-title">結果</div>'+f.map(function(x){var h=horseByNo(r,x.horseNumber)||x;return'<div class="result-row"><span>'+esc(x.finish)+'着</span>'+badge(h)+'<span class="result-name">'+esc(x.name||h.name||"")+'</span><span>'+fmtTime(x.timeSeconds)+'</span></div>'}).join("")+'</section>'}
function paceBoard(r,p){var hs=(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)});return'<section class="card pace-card"><div class="pace-head"><div class="section-title" style="margin:0">3　AI展開予想</div><span id="pace-stage-name" class="pace-stage">スタート</span></div><div id="pace-board" class="pace-board">'+hs.map(function(h,i){return'<div class="pace-chip" data-horse="'+esc(h.horseNumber)+'" style="left:4%;top:'+(8+i*(260/Math.max(1,hs.length)))+'px">'+badge(h)+'<span class="pace-name">'+esc(h.name)+'</span></div>'}).join("")+'</div><div class="pace-legend"><button data-stage="0" class="active">スタート</button><button data-stage="1">4コーナー</button><button data-stage="2">直線</button></div></section>'}
function renderRace(){var r=state.race,p=predict(r),rows=p.rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),early=p.occ.early.join(" "),moved=p.occ.moved.join(" ");return'<div class="shell">'+header(r.track+' '+r.raceNumber+'R',true,(r.title||'')+'｜'+r.distance+'m・'+r.condition)+'<main class="main">'+renderResult(r)+'<section class="card"><div class="row between"><div><h2>'+esc(r.title||"")+'</h2><div class="muted">'+esc(r.date)+' '+timeHtml(r)+'</div></div><span class="pill">'+esc(r.circuit)+'</span></div><div class="metrics"><div class="metric"><b>'+esc(r.distance)+'m</b><span>距離</span></div><div class="metric"><b>'+esc(r.condition||'不明')+'</b><span>馬場</span></div><div class="metric"><b>'+esc(r.weather||'不明')+'</b><span>天候</span></div><div class="metric"><b>'+season(r.date)+'</b><span>季節</span></div><div class="metric"><b>'+esc((r.horses||[]).length)+'頭</b><span>頭数</span></div></div></section><section class="card"><div class="section-title">1　先行馬占有率</div><div class="occupancy">'+pct(p.occ.rate)+'</div><div class="muted">対象：'+(p.occ.nums.join(' ')||'—')+'</div><div class="backline">最初から前：'+(early||'—')+'　途中進出：'+(moved||'—')+'</div></section><section class="card"><div class="section-title">2　脚質マップ</div><div class="style-list">'+rows.map(function(x){return'<div class="style-row"><div class="style-top">'+badge(x.horse)+'<span class="horse-name">'+esc(x.horse.name)+'</span><span class="score">点 '+x.score.toFixed(2)+'</span><span class="expected">'+esc(x.expected)+'</span></div><div class="rates"><span class="rate"><small>逃</small>'+pct(x.front)+'</span><span class="rate"><small>先</small>'+pct(x.stalk)+'</span><span class="rate"><small>差</small>'+pct(x.mid)+'</span><span class="rate"><small>追</small>'+pct(x.close)+'</span><span class="rate"><small>下</small>'+pct(x.fade)+'</span></div></div>'}).join("")+'</div></section>'+paceBoard(r,p)+'<section class="card"><div class="section-title">4　ABC</div><div class="scenario-grid">'+p.scenarios.map(function(s){return'<div class="scenario"><div>'+s.code+' '+esc(s.title)+'</div><div class="prob">'+Math.round(s.prob*100)+'%</div><div class="scenario-horses">'+s.horses.map(function(h){return badge(h)}).join("")+'</div></div>'}).join("")+'</div></section><section class="card"><div class="section-title">5　印</div><div class="marks">'+p.marks.map(function(m){return'<div class="mark"><span class="mark-symbol">'+m[0]+'</span>'+badge(m[1])+'<strong>'+esc(m[1].name)+'</strong></div>'}).join("")+'</div></section><section class="card"><h2>出馬データ</h2>'+(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}).map(function(h){return'<details class="horse-card"><summary>'+badge(h)+'<span class="horse-name">'+esc(h.name)+'</span><span class="muted">'+esc(h.sex)+esc(h.age)+' '+esc(h.carriedWeight)+'kg</span></summary><div class="horse-detail">騎手：'+esc(h.jockey)+' / 調教師：'+esc(h.trainer)+'<br>このレース時点の獲得賞金：'+fmtMoney(h.prizeMoneyAtRace)+'円'+(h.recentRaces||[]).slice(0,5).map(function(rr){return'<div class="recent"><b>'+esc(rr.date)+' '+esc(rr.track)+' '+esc(rr.distance)+'m</b>　'+esc(rr.finish)+'着 / '+fmtTime(rr.timeSeconds)+'<br><span class="muted">'+esc(rr.condition)+'・'+esc(rr.weather||'不明')+'　通過 '+esc((rr.cornerPositions||[]).join('-'))+'</span></div>'}).join("")+'</div></details>'}).join("")+'</section></main></div>'}
function render(){stopTimer();try{if(state.race)app.innerHTML=renderRace();else if(state.picker)app.innerHTML=renderPicker();else if(state.track)app.innerHTML=renderVenue();else app.innerHTML=renderHome();bind();if(state.race)startPace()}catch(e){app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(e&&e.message||e)+'<br><button onclick="location.reload()">再読み込み</button></div>'}}
function bind(){var els=document.querySelectorAll('[data-circuit]'),i;for(i=0;i<els.length;i++)els[i].onclick=function(){state.circuit=this.getAttribute('data-circuit');state.track=null;state.race=null;state.picker=false;render()};var d=document.getElementById('date');if(d)d.onchange=function(){state.date=this.value;state.track=null;state.race=null;state.picker=false;load()};els=document.querySelectorAll('[data-track]');for(i=0;i<els.length;i++)els[i].onclick=function(){state.track=this.getAttribute('data-track');render()};els=document.querySelectorAll('[data-race]');for(i=0;i<els.length;i++)els[i].onclick=function(){var id=this.getAttribute('data-race'),j;for(j=0;j<state.races.length;j++)if(String(state.races[j].id)===String(id)){state.race=state.races[j];break}state.picker=false;render()};var b=document.querySelectorAll('[data-action="back"]');for(i=0;i<b.length;i++)b[i].onclick=function(){if(state.race)state.race=null;else if(state.picker)state.picker=false;else state.track=null;render()};var rr=document.querySelectorAll('[data-action="reload"]');for(i=0;i<rr.length;i++)rr[i].onclick=load;var pn=document.querySelector('[data-action="pace-next"]');if(pn)pn.onclick=function(){var x=nextRace();if(x){state.race=x;render()}};var pp=document.querySelector('[data-action="pace-pick"]');if(pp)pp.onclick=function(){state.picker=true;state.track=null;render()};els=document.querySelectorAll('[data-stage]');for(i=0;i<els.length;i++)els[i].onclick=function(){setPaceStage(n(this.getAttribute('data-stage')))}}
function stopTimer(){if(state.timer){clearInterval(state.timer);state.timer=null}}
function orderAt(p,st){if(st===0)return p.plan.start;if(st===1)return p.plan.corner;return p.plan.straight}
function setPaceStage(st){state.stage=st;var r=state.race;if(!r)return;var p=predict(r),order=orderAt(p,st),board=document.getElementById('pace-board');if(!board)return;var labels=['スタート','4コーナー','直線'],name=document.getElementById('pace-stage-name');if(name)name.textContent=labels[st];var btns=document.querySelectorAll('[data-stage]'),i;for(i=0;i<btns.length;i++)btns[i].className=n(btns[i].getAttribute('data-stage'))===st?'active':'';var max=Math.max(1,order.length-1);for(i=0;i<order.length;i++){var h=order[i],chip=board.querySelector('[data-horse="'+h.horse.horseNumber+'"]');if(!chip)continue;var left=8+(max-i)*(70/max);if(st===2)left=12+(max-i)*(72/max);var lane=n(h.horse.horseNumber)-1;var top=8+lane*(260/Math.max(1,(r.horses||[]).length));chip.style.left=left+'%';chip.style.top=top+'px'}}
function startPace(){state.stage=0;setTimeout(function(){setPaceStage(0)},50);state.timer=setInterval(function(){state.stage=(state.stage+1)%3;setPaceStage(state.stage)},3000)}
function load(){state.loading=true;state.error=null;render();fetch('/api/v1/races?date='+encodeURIComponent(state.date),{cache:'no-store'}).then(function(res){if(!res.ok)throw new Error('API '+res.status);return res.json()}).then(function(body){state.races=Array.isArray(body)?body:(body.races||[]);state.loading=false;state.error=null;render()}).catch(function(){state.loading=false;state.error='データ取得待機中。↻で再読込できます';render()})}
window.onerror=function(msg){if(app)app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(msg)+'<br><button onclick="location.reload()">再読み込み</button></div>';return false};
render();setTimeout(load,0);
})();
"""

MANIFEST = r'''{
  "name":"競馬展開AI",
  "short_name":"競馬展開AI",
  "description":"競馬の脚質・展開・ABC・印を確認するPWA",
  "start_url":"/",
  "scope":"/",
  "display":"standalone",
  "background_color":"#041126",
  "theme_color":"#0b1220",
  "lang":"ja"
}'''
SW = 'self.addEventListener("install",function(){self.skipWaiting()});self.addEventListener("activate",function(e){e.waitUntil(self.registration.unregister())});'

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
        "status":"ok", "mode":"production-v22-neon-home", "historyStarted":_history_started,
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
