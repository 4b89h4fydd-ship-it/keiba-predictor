from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
import json
import base64
import calendar
import csv
import hashlib
import io
import os
import re
import sqlite3
import threading
import time
import urllib.request
import urllib.parse
import zipfile
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date as dt_date, datetime
from pathlib import Path
from typing import Iterable, Iterator
from bs4 import BeautifulSoup

app = FastAPI(title="競馬展開AI", version="7.3-production-v60-runtime-deps-fixed")

INDEX = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b1220">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="競馬展開AI">
<link rel="manifest" href="/manifest-v60.webmanifest">
<link rel="stylesheet" href="/styles-v60.css">
<title>競馬展開AI</title>
</head>
<body>
<div id="app"><div class="boot">競馬展開AIを起動中…</div></div>
<script src="/app-v60.js"></script>
</body>
</html>"""

CSS = r"""
:root{--bg:#f3f5f9;--card:#fff;--text:#101828;--muted:#667085;--line:#e4e7ec;--navy:#0b1220;--blue:#2563eb;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Hiragino Sans","Yu Gothic",sans-serif}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-weight:400;-webkit-text-size-adjust:100%}button,input{font:inherit;font-weight:400}.boot{padding:42px 16px;text-align:center;color:#64748b}.shell{max-width:760px;margin:0 auto;padding-bottom:calc(30px + env(safe-area-inset-bottom))}.header{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.98);color:#fff;padding:calc(8px + env(safe-area-inset-top)) 10px 9px;box-shadow:0 1px 8px rgba(0,0,0,.14)}.header-row{display:flex;align-items:center;gap:8px}.header-title{min-width:0;flex:1}.header h1{font-size:18px;margin:0;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.header small{display:block;color:#cbd5e1;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.header button{border:0;background:rgba(255,255,255,.12);color:#fff;border-radius:10px;padding:7px 10px}.main{padding:8px;display:grid;gap:8px}.card{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:11px;box-shadow:0 1px 2px rgba(16,24,40,.03)}.section-title,.card h2{margin:0 0 8px;font-size:17px;font-weight:500}.muted{color:var(--muted)}.row{display:flex;align-items:center;gap:8px}.between{justify-content:space-between}.label{font-size:11px;color:var(--muted);margin-bottom:4px}.setup-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:8px}.date{width:100%;height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;background:#fff}.segment{display:grid;grid-template-columns:1fr 1fr;gap:5px}.segment button{height:40px;border:1px solid var(--line);background:#fff;border-radius:10px}.segment button.active{background:var(--navy);color:#fff;border-color:var(--navy)}.home-heading{font-size:14px;font-weight:500;margin-bottom:8px}.pill{font-size:10px;background:#eef2f6;border-radius:999px;padding:4px 8px}.live-dot{font-size:9px;background:#fee2e2;color:#b42318;border-radius:999px;padding:4px 7px}.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}.live-race{border:1px solid var(--line);background:#fff;border-radius:11px;padding:9px;text-align:left;min-width:0}.live-top{display:flex;justify-content:space-between;gap:5px;align-items:center}.live-track{font-size:13px}.live-title{font-size:11px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:4px 0}.live-time{font-size:20px}.live-tag{font-size:9px;border-radius:999px;padding:3px 5px;background:#eff6ff;color:#1d4ed8}.live-tag.now{background:#fff1f2;color:#be123c}.live-tag.running{background:#ecfdf3;color:#027a48}.empty{padding:16px 6px;text-align:center;color:var(--muted);font-size:12px}.notice{background:#fff7ed;color:#9a3412;border-radius:10px;padding:10px;font-size:12px}.ai-card{overflow:hidden;position:relative;background:linear-gradient(135deg,#0b1220,#172554 68%,#1d4ed8);color:#fff;border:0}.ai-card:after{content:"";position:absolute;width:170px;height:170px;border-radius:50%;right:-80px;top:-80px;background:rgba(59,130,246,.25)}.ai-kicker{font-size:10px;letter-spacing:.12em;color:#93c5fd}.ai-title{font-size:22px;font-weight:600;margin:4px 0}.ai-next{font-size:13px;color:#dbeafe;margin:7px 0 10px}.ai-actions{display:grid;grid-template-columns:1fr auto;gap:7px;position:relative;z-index:1}.ai-primary,.ai-secondary{border:0;border-radius:11px;padding:10px 12px}.ai-primary{background:#fff;color:#111827}.ai-secondary{background:rgba(255,255,255,.13);color:#fff;border:1px solid rgba(255,255,255,.2)}.venue-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.venue{border:1px solid var(--line);background:#fff;border-radius:11px;padding:11px;text-align:left}.venue .name{font-size:17px}.venue .count{font-size:11px;color:var(--muted);margin-top:2px}.race-list{display:grid;gap:7px}.race{width:100%;border:1px solid var(--line);background:#fff;border-radius:11px;padding:10px;text-align:left;display:flex;align-items:center;justify-content:space-between;gap:8px}.race.final{background:#f0fdf4;border-color:#a7f3d0}.race-main{min-width:0}.race-top{display:flex;gap:7px;align-items:baseline;min-width:0}.race-no{font-size:17px}.race-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:14px}.race-time{font-size:12px;color:#475467;margin-top:3px}.final-badge{font-size:11px;color:#067647;border:1px solid #75e0a7;background:#fff;border-radius:6px;padding:3px 7px}.picker-list{display:grid;gap:6px}.picker-item{border:1px solid var(--line);background:#fff;border-radius:11px;padding:11px;display:flex;justify-content:space-between;align-items:center;text-align:left}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-top:9px}.metric{background:#f8fafc;border-radius:9px;padding:7px 2px;text-align:center}.metric b{display:block;font-size:12px;font-weight:400}.metric span{font-size:8px;color:var(--muted)}.occupancy{font-size:32px;margin:2px 0 4px}.style-list{display:grid;gap:6px}.style-row{border:1px solid var(--line);border-radius:11px;padding:8px}.style-top{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto;gap:6px;align-items:center}.horse-name{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.score{font-size:12px}.expected{font-size:9px;background:#f1f5f9;border-radius:999px;padding:3px 6px}.rates{display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin-top:6px}.rate{background:#f8fafc;border-radius:7px;text-align:center;padding:5px 1px;font-size:11px}.rate small{display:block;font-size:8px;color:var(--muted)}.frame-badge{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;border:1px solid rgba(0,0,0,.16);font-size:13px;flex:0 0 auto}.frame1{background:#fff;color:#111}.frame2{background:#222;color:#fff}.frame3{background:#e53935;color:#fff}.frame4{background:#1e66d0;color:#fff}.frame5{background:#f5d547;color:#111}.frame6{background:#3a9b56;color:#fff}.frame7{background:#f28c28;color:#111}.frame8{background:#e894b7;color:#111}.pace-card{overflow:hidden}.pace-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.pace-stage{font-size:13px;background:#eff6ff;color:#1d4ed8;border-radius:999px;padding:4px 8px}.pace-board{position:relative;height:290px;border-radius:13px;overflow:hidden;background:linear-gradient(90deg,#e7f6e8 0 14%,#f3ead8 14% 88%,#e7f6e8 88%);border:1px solid #d0d5dd}.pace-board:before,.pace-board:after{content:"";position:absolute;top:0;bottom:0;width:2px;background:rgba(255,255,255,.75)}.pace-board:before{left:14%}.pace-board:after{right:12%}.pace-chip,.ai-race-runner{position:absolute;height:28px;display:flex;align-items:center;justify-content:center;transition:left 1.25s ease,top 1.25s ease;white-space:nowrap;z-index:2}.pace-chip .frame-badge,.ai-race-runner .frame-badge{width:28px;height:28px;font-size:12px;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.28)}.pace-name{display:none}.runner-grade-line{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:2px}.summary-chip{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:3px 8px;font-size:10px;border:1px solid var(--line);background:#f8fafc;color:#344054}.summary-chip.grade{background:#eef2ff;border-color:#c7d2fe;color:#3730a3}.summary-chip.mark{background:#fff7ed;border-color:#fed7aa;color:#9a3412;font-weight:800;font-size:12px}.summary-chip.expected{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8}.runner-subline{display:flex;gap:8px;flex-wrap:wrap;margin-top:3px;color:var(--muted);font-size:11px}.runner-detail-top{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin:8px 0}.runner-style-head{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-bottom:8px}.runner-mini-score{background:#f8fafc;border-radius:10px;padding:8px;text-align:center}.runner-mini-score small{display:block;font-size:10px;color:var(--muted)}.runner-mini-score b{font-size:14px;font-weight:600}.pace-legend{display:flex;gap:5px;margin-top:7px}.pace-legend button{flex:1;border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 2px;font-size:11px}.pace-legend button.active{background:#111827;color:#fff}.scenario-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}.scenario{background:#f8fafc;border-radius:11px;padding:9px 4px;text-align:center}.scenario .prob{font-size:24px;margin:4px 0}.scenario-horses{display:flex;justify-content:center;gap:3px;flex-wrap:wrap}.scenario-horses .frame-badge{width:24px;height:24px;font-size:11px}.marks{display:grid;grid-template-columns:1fr 1fr;gap:5px}.mark{display:grid;grid-template-columns:30px 28px minmax(0,1fr);gap:5px;align-items:center;background:#f8fafc;border-radius:10px;padding:8px}.mark-symbol{font-size:18px}.mark strong{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.horse-card{border:1px solid var(--line);border-radius:11px;padding:9px;margin-top:6px}.horse-card summary{list-style:none;display:flex;align-items:center;gap:7px}.horse-card summary::-webkit-details-marker{display:none}.horse-detail{padding-top:8px;font-size:12px;line-height:1.5}.recent{border-top:1px dashed var(--line);padding-top:6px;margin-top:6px}.result-row{display:grid;grid-template-columns:34px 28px minmax(0,1fr) auto;gap:6px;align-items:center;padding:7px 0;border-bottom:1px solid var(--line)}.result-row:last-child{border-bottom:0}.result-name{font-weight:700}.time-old{text-decoration:line-through;color:#98a2b3;margin-right:4px}.time-changed{color:#d92d20}.backline{font-size:11px;color:var(--muted);margin-top:4px}
.build-badge{font-size:9px;font-weight:800;letter-spacing:.04em;color:#67e8f9;border:1px solid rgba(103,232,249,.45);background:rgba(8,47,73,.55);border-radius:999px;padding:4px 6px;white-space:nowrap}
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


/* v23 — screenshot-matched home + course-specific pace board */
html,body{overflow-x:hidden}
.home-shell{max-width:760px;background:radial-gradient(700px 330px at 72% -3%,rgba(22,105,255,.42),transparent 61%),linear-gradient(180deg,#061b45 0%,#03152f 48%,#021024 100%)}
.home-hero{min-height:188px;padding-top:calc(18px + env(safe-area-inset-top));padding-bottom:10px;align-items:flex-start}
.home-hero:before{display:none}
.hero-horse{position:absolute;right:82px;top:calc(0px + env(safe-area-inset-top));width:242px;height:168px;object-fit:cover;object-position:center;border-radius:0;opacity:.96;mix-blend-mode:screen;mask-image:linear-gradient(90deg,transparent 0,#000 25%,#000 88%,transparent 100%);-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 25%,#000 88%,transparent 100%);pointer-events:none;filter:saturate(1.08) contrast(1.02)}
.brand-wrap{padding-top:44px}.brand-main{font-size:36px;letter-spacing:.005em}.brand-sub{font-size:14px;letter-spacing:.20em;color:#63e3ff}.hero-refresh{margin-top:45px}
.home-main{gap:14px;padding:0 11px 18px}.home-card{border-radius:18px;border-color:rgba(77,157,235,.47);background:linear-gradient(180deg,rgba(11,48,95,.83),rgba(5,31,67,.91));padding:14px}
.home-section-title{font-size:18px}.home-section-icon{font-size:20px}.home-link{font-size:13px}
.home-date{font-size:28px;height:54px}.home-segment button{height:54px;font-size:18px}
.home-live-grid,.home-venue-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;width:100%;overflow:hidden}
.home-live-race,.home-venue{min-width:0;width:100%}.home-live-race{min-height:132px;background:linear-gradient(145deg,rgba(12,45,87,.88),rgba(12,52,102,.72)),radial-gradient(circle at 78% 24%,rgba(75,128,190,.26),transparent 44%)}
.home-venue{grid-template-columns:40px minmax(0,1fr) auto auto;height:64px;padding:8px 9px;overflow:hidden}.home-venue-name{min-width:0}.home-venue-count{white-space:nowrap}.home-arrow{flex:0 0 auto}
.home-ai-card{padding:13px}.home-ai-next{display:none}.home-ai-preview-photo{position:relative;margin-top:10px;height:154px;border-radius:14px;overflow:hidden;border:1px solid rgba(83,191,240,.55);background:#102d47}.home-ai-preview-photo img{width:100%;height:100%;object-fit:cover;display:block}.home-ai-preview-overlay{position:absolute;inset:0;box-shadow:inset 0 0 32px rgba(1,16,40,.22);pointer-events:none}
.home-ai-actions{margin-left:auto}.home-ai-go{font-size:15px;padding:12px 19px}.home-ai-select{font-size:11px}

/* Detail pace view: clean chips on racecourse geometry, no cartoon horses */
.pace-card{padding:11px}.course-wrap{position:relative;height:330px;border-radius:15px;overflow:hidden;border:1px solid #cbd5e1;background:radial-gradient(circle at 50% 50%,#dfead8 0 44%,#b9d4ad 45% 100%)}
.course-svg{position:absolute;inset:0;width:100%;height:100%}.course-infield{fill:#c8ddb9}.course-track-under{fill:none;stroke:#f2efe7;stroke-width:27;stroke-linecap:round;stroke-linejoin:round}.course-track{fill:none;stroke:#c89d6b;stroke-width:21;stroke-linecap:round;stroke-linejoin:round}.course-rail{fill:none;stroke:rgba(255,255,255,.92);stroke-width:1.3;stroke-dasharray:3 2}.course-finish{stroke:#fff;stroke-width:2.5}.course-start{fill:#5de9ff;stroke:#fff;stroke-width:1.5}.course-start-label,.course-finish-label{font-size:7px;fill:#17324f;font-weight:600}.course-meta{position:absolute;left:9px;top:8px;z-index:4;background:rgba(5,24,52,.83);color:#eef7ff;border:1px solid rgba(119,190,239,.5);border-radius:999px;padding:5px 9px;font-size:10px;backdrop-filter:blur(5px)}
.course-runner{position:absolute;z-index:5;transform:translate(-50%,-50%);transition:left 1.2s cubic-bezier(.2,.8,.2,1),top 1.2s cubic-bezier(.2,.8,.2,1);will-change:left,top}.course-runner .frame-badge{width:29px;height:29px;border-radius:50%;box-shadow:0 2px 7px rgba(0,0,0,.32);border-width:2px}.course-order{position:absolute;left:8px;right:8px;bottom:8px;z-index:6;background:rgba(5,24,52,.82);border:1px solid rgba(255,255,255,.18);color:#f5fbff;border-radius:10px;padding:7px 8px;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;backdrop-filter:blur(5px)}
.pace-legend{margin-top:8px}.pace-stage{background:#e7f1ff}

@media(max-width:460px){.home-hero{min-height:170px}.brand-wrap{padding-top:38px}.brand-main{font-size:31px}.hero-horse{right:63px;width:218px;height:151px}.hero-refresh{margin-top:38px}.home-date{font-size:23px}.home-live-race{min-height:122px}.home-venue{height:60px;grid-template-columns:36px minmax(0,1fr) auto 16px;gap:6px;padding:7px}.venue-mark{width:34px;height:34px}.home-venue-name{font-size:15px}.home-venue-count{font-size:11px}.home-ai-preview-photo{height:137px}.course-wrap{height:300px}}
@media(max-width:360px){.home-live-grid,.home-venue-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.home-main{padding-left:7px;padding-right:7px}.home-card{padding:9px}.home-date-row{grid-template-columns:1.06fr .94fr}.home-date{font-size:18px}.home-segment button{font-size:14px}.home-track{font-size:14px}.home-rno{font-size:20px}.home-venue-name{font-size:13px}.home-venue-count{font-size:9px}.home-ai-top{flex-wrap:nowrap}.home-ai-actions{width:auto}.home-ai-preview-photo{height:125px}}

/* v24 — unified race card + result review */
.runner-style-list{display:grid;gap:7px}.runner-style{border:1px solid var(--line);border-radius:12px;background:#fff;overflow:hidden}.runner-style summary{list-style:none;padding:9px;cursor:pointer}.runner-style summary::-webkit-details-marker{display:none}.runner-main{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto;gap:7px;align-items:center}.runner-meta{font-size:10px;color:var(--muted);white-space:nowrap}.runner-style[open]{border-color:#b9cdf7;box-shadow:0 0 0 1px rgba(37,99,235,.05)}.runner-style .horse-detail{padding:0 9px 9px;border-top:1px dashed var(--line);margin-top:0}.course-runner{display:flex;align-items:center;gap:2px}.course-mark{display:grid;place-items:center;min-width:22px;height:22px;padding:0 3px;border-radius:999px;background:rgba(4,24,52,.92);color:#fff;font-size:12px;font-weight:700;box-shadow:0 2px 6px rgba(0,0,0,.28)}.pace-prob{display:flex;align-items:center;gap:12px}.pace-prob b{font-size:34px;font-weight:500;min-width:78px}.pace-prob-track{height:9px;flex:1;border-radius:999px;background:#edf2f7;overflow:hidden}.pace-prob-track span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#20c9e8,#315bea)}.gap-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.gap-grid>div{background:#f8fafc;border-radius:10px;padding:8px}.gap-grid small{display:block;color:var(--muted);font-size:9px;margin-bottom:3px}.gap-grid b{font-size:12px;font-weight:500;line-height:1.35}.gap-order{margin-top:8px;padding:8px;background:#f8fafc;border-radius:10px;font-size:11px;line-height:1.7}.gap-order span{color:var(--muted);display:inline-block;width:58px}.actual-flow{overflow:hidden}.actual-stage{display:grid;grid-template-columns:42px minmax(0,1fr);gap:7px;align-items:start;padding:7px 0;border-bottom:1px solid var(--line)}.actual-stage:last-child{border-bottom:0}.actual-stage>b{font-size:11px;padding-top:5px;font-weight:500}.actual-order{display:flex;align-items:center;gap:3px;overflow-x:auto;padding-bottom:2px;-webkit-overflow-scrolling:touch}.actual-order>span{display:inline-flex;align-items:center;gap:4px;white-space:nowrap;background:#f8fafc;border-radius:999px;padding:2px 6px 2px 2px}.actual-order .frame-badge{width:23px;height:23px;border-radius:50%;font-size:10px}.actual-order em{font-style:normal;font-size:9px;max-width:72px;overflow:hidden;text-overflow:ellipsis}.actual-order i{font-style:normal;color:#98a2b3}.result-card{border-color:#b7e4cc;background:#f6fffa}.race-title-card h2{font-size:18px}.pace-card+.pace-prob-card{margin-top:0}@media(max-width:390px){.runner-main{grid-template-columns:auto minmax(0,1fr) auto}.runner-main .expected{grid-column:3}.runner-meta{display:none}.gap-grid{grid-template-columns:1fr}.actual-stage{grid-template-columns:38px minmax(0,1fr)}}

/* v26 — 50-run Monte Carlo pace simulation */
.sim-board .course-runner{transition:none!important}.sim-live-podium{position:absolute;left:8px;right:8px;top:39px;z-index:7;display:flex;justify-content:center;gap:5px;pointer-events:none}.sim-live-podium b{display:inline-block;background:rgba(3,20,45,.78);color:#fff;border:1px solid rgba(255,255,255,.16);border-radius:999px;padding:4px 7px;font-size:9px;font-weight:500;backdrop-filter:blur(4px)}.sim-live-podium i{font-style:normal;color:rgba(255,255,255,.7);font-size:9px}.sim-controls{display:flex;align-items:center;gap:8px;margin-top:9px}.sim-start{flex:1;border:0;border-radius:11px;background:#111827;color:#fff;padding:10px 12px;font-size:13px}.sim-speed{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}.sim-speed button{border:1px solid var(--line);background:#fff;border-radius:8px;padding:8px 7px;font-size:10px;min-width:38px}.sim-speed button.active{background:#2563eb;color:#fff;border-color:#2563eb}.sim-progress{margin-top:8px}.sim-progress>div:first-child{display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-bottom:4px}.sim-progress-track{height:7px;background:#edf2f7;border-radius:999px;overflow:hidden}.sim-progress-track span{display:block;height:100%;background:linear-gradient(90deg,#22c7e8,#315bea);border-radius:999px;transition:width .15s linear}.sim-podium-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.sim-podium-card{background:#f8fafc;border-radius:11px;padding:8px;min-width:0}.sim-podium-card small{display:block;color:var(--muted);font-size:9px;margin-bottom:5px}.sim-podium-card>div{display:flex;align-items:center;gap:5px;min-width:0}.sim-podium-card .frame-badge{width:24px;height:24px;border-radius:50%;font-size:10px}.sim-podium-card b{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sim-podium-card strong{display:block;margin-top:5px;font-size:19px;font-weight:500}.sim-confidence{display:flex;justify-content:space-between;align-items:center;padding:8px 2px;border-bottom:1px solid var(--line);font-size:11px}.sim-confidence b{font-size:16px;font-weight:500}.sim-rate-list{display:grid;gap:4px;margin:8px 0}.sim-rate-row{display:grid;grid-template-columns:24px minmax(0,1fr) auto auto auto;gap:5px;align-items:center;background:#f8fafc;border-radius:9px;padding:5px}.sim-rate-row .frame-badge{width:23px;height:23px;border-radius:50%;font-size:9px}.sim-rate-name{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:11px}.sim-rate-row>span:not(.sim-rate-name){font-size:9px;color:#475467;white-space:nowrap}
@media(max-width:390px){.sim-controls{align-items:stretch;flex-direction:column}.sim-speed{width:100%}.sim-start{width:100%}.sim-podium-grid{gap:4px}.sim-podium-card{padding:6px}.sim-rate-row{grid-template-columns:23px minmax(0,1fr) auto auto}.sim-rate-row>span:last-child{display:none}.sim-live-podium{top:38px}.sim-live-podium b{font-size:8px;padding:3px 5px}}

/* v27 — selectable deep simulation controls */
.sim-count-picker{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-top:8px}.sim-count-picker button{border:1px solid var(--line);background:#fff;border-radius:9px;padding:8px 2px;font-size:10px}.sim-count-picker button.active{background:#0f172a;color:#fff;border-color:#0f172a}.sim-actions{display:grid;grid-template-columns:1.45fr .9fr .8fr;gap:5px;flex:1}.sim-action{border:0;border-radius:10px;padding:10px 7px;font-size:11px}.sim-action.primary{background:#111827;color:#fff}.sim-action.pause{background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe}.sim-action.stop{background:#fff1f2;color:#be123c;border:1px solid #fecdd3}.sim-action:disabled{opacity:.45}.sim-depth{margin-top:7px;display:flex;gap:5px;flex-wrap:wrap}.sim-depth span{font-size:9px;padding:4px 7px;border-radius:999px;background:#f1f5f9;color:#475467}.sim-note{font-size:10px;line-height:1.55;color:#667085;margin-top:7px}.data-depth{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.data-depth span{font-size:9px;border:1px solid #dbe4ef;background:#f8fafc;border-radius:999px;padding:4px 7px;color:#475467}
@media(max-width:390px){.sim-actions{grid-template-columns:1fr 1fr 1fr}.sim-action{font-size:10px;padding:9px 4px}.sim-count-picker{gap:3px}.sim-count-picker button{font-size:9px;padding:7px 1px}}

/* v33 — iPhone-safe runner/style map: never squeeze horse rows */
.runner-style-list{width:100%;min-width:0;gap:8px}
.runner-style{width:100%;min-width:0;overflow:hidden}
.runner-style summary{display:block;width:100%;min-width:0;padding:10px 10px 9px}
.runner-main{display:grid;grid-template-columns:30px minmax(0,1fr) auto;grid-template-rows:auto auto;column-gap:8px;row-gap:2px;align-items:center;width:100%;min-width:0}
.runner-main>.frame-badge{grid-column:1;grid-row:1 / span 2;align-self:center}
.runner-main>.horse-name{grid-column:2;grid-row:1;display:block;min-width:0;font-size:14px;line-height:1.25;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.runner-main>.runner-meta{grid-column:2;grid-row:2;display:block!important;min-width:0;font-size:10px;line-height:1.2;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.runner-main>.expected{grid-column:3;grid-row:1 / span 2;align-self:center;justify-self:end;max-width:74px;font-size:10px;line-height:1.15;text-align:center;white-space:normal;padding:4px 7px}
.runner-style .rates{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:4px;width:100%;min-width:0;margin-top:8px}
.runner-style .rate{min-width:0;padding:6px 1px 5px;border-radius:8px;font-size:12px;line-height:1.15;white-space:nowrap}
.runner-style .rate small{font-size:9px;line-height:1;margin-bottom:3px}
.runner-style .horse-detail{overflow-wrap:anywhere;word-break:break-word}
@media(max-width:390px){
  .runner-style summary{padding:9px 8px 8px}
  .runner-main{grid-template-columns:28px minmax(0,1fr) 58px;column-gap:6px}
  .runner-main>.frame-badge{width:27px;height:27px;font-size:12px}
  .runner-main>.horse-name{font-size:13px}
  .runner-main>.runner-meta{font-size:9px}
  .runner-main>.expected{max-width:58px;font-size:9px;padding:4px 4px}
  .runner-style .rates{gap:3px;margin-top:7px}
  .runner-style .rate{font-size:11px;padding:6px 0 5px}
}
@media(max-width:340px){
  .runner-main{grid-template-columns:26px minmax(0,1fr) 52px;column-gap:5px}
  .runner-main>.horse-name{font-size:12px}
  .runner-main>.expected{max-width:52px;font-size:8px}
  .runner-style .rate{font-size:10px}
}


/* v34: scenario-first pace view, no simulation controls */
.scenario-prob-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin:6px 0 10px}
.scenario-prob-card{border:1px solid #d7e2ef;background:#f8fbff;border-radius:12px;padding:9px 6px;text-align:center;min-width:0}
.scenario-prob-card.active{border-color:#27c7e8;background:linear-gradient(180deg,#e9fbff,#eef4ff);box-shadow:0 0 0 1px rgba(39,199,232,.18),0 6px 18px rgba(30,99,220,.10)}
.scenario-prob-card small{display:block;font-size:10px;color:#667085;white-space:nowrap}
.scenario-prob-card b{display:block;font-size:13px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.scenario-prob-card strong{display:block;font-size:22px;line-height:1.1;margin-top:4px}
.scenario-main-note{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:2px 0 9px;padding:8px 10px;border-radius:10px;background:#071a35;color:#f4fbff}
.scenario-main-note span{font-size:11px;color:#a9c5ea}.scenario-main-note b{font-size:13px}
.pace-stage-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:8px}
.pace-stage-tabs button{border:1px solid #cbd5e1;background:#fff;border-radius:999px;padding:8px 4px;font-size:11px;color:#344054}
.pace-stage-tabs button.active{background:#0b1f42;color:#fff;border-color:#0b1f42;box-shadow:0 4px 12px rgba(11,31,66,.16)}
.course-runner.pace-runner{display:flex;align-items:center;gap:3px;max-width:108px;transition:left .42s ease,top .42s ease;z-index:5}
.course-runner.pace-runner .pace-name{font-size:8px;max-width:65px;padding:2px 4px}
.course-runner.pace-runner .course-mark{font-size:11px;font-weight:700;line-height:1;color:#fff;text-shadow:0 1px 2px #000;position:absolute;transform:translate(-6px,-12px)}
.pace-order-full{position:absolute;left:8px;right:8px;bottom:8px;z-index:7;background:rgba(5,24,52,.86);color:#fff;border:1px solid rgba(255,255,255,.18);border-radius:10px;padding:6px 8px;font-size:9px;line-height:1.35;backdrop-filter:blur(5px)}
.pace-order-full b{color:#67e8f9;margin-right:6px}.pace-order-full span{white-space:nowrap}
.runner-style summary{cursor:pointer}.rates.four-rates{grid-template-columns:repeat(4,minmax(0,1fr))!important}
.horse-info-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.horse-info-cell{background:#f8fafc;border-radius:8px;padding:7px}.horse-info-cell small{display:block;color:#667085;font-size:9px}.horse-info-cell b{display:block;font-size:11px;margin-top:2px;font-weight:500}
.fit-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}.fit-chip{background:#eef4ff;border-radius:8px;padding:6px 4px;text-align:center}.fit-chip small{display:block;color:#667085;font-size:8px}.fit-chip b{font-size:11px;font-weight:500}
.role-box{margin-top:8px;padding:7px 8px;border:1px solid #e4e7ec;border-radius:9px}.role-box b{font-size:11px}.role-box div{font-size:10px;color:#475467;margin-top:3px}
.recent-list-title{margin-top:10px;font-size:11px;font-weight:700}.recent{font-size:10px;line-height:1.45}
@media(max-width:390px){.scenario-prob-card strong{font-size:19px}.scenario-prob-card b{font-size:12px}.course-runner.pace-runner .pace-name{display:none}.horse-info-grid{grid-template-columns:1fr 1fr}.fit-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}

/* v35 strong style map */
.runner-map-card{overflow:hidden}.section-title-row{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:9px}.section-title-row .section-title{margin:0}.section-sub{font-size:10px;color:#667085;margin-top:2px}.map-hint{font-size:9px;color:#667085;background:#f2f4f7;border-radius:999px;padding:5px 7px;white-space:nowrap}.runner-style-list{display:grid;gap:8px;width:100%;min-width:0}.runner-style{width:100%;min-width:0;border:1px solid #dbe3ee;border-radius:13px;background:#fff;overflow:hidden}.runner-style[open]{border-color:#79bff5;box-shadow:0 0 0 1px rgba(42,133,224,.08)}.runner-style summary{list-style:none;display:block;width:100%;min-width:0;padding:9px 9px 8px;cursor:pointer}.runner-style summary::-webkit-details-marker{display:none}.runner-line{display:grid;grid-template-columns:30px minmax(0,1fr) 18px;gap:7px;align-items:center;min-width:0}.runner-id{display:flex;align-items:center}.runner-id .frame-badge{width:29px;height:29px;border-radius:8px;font-size:12px}.runner-copy{min-width:0}.runner-name-line{display:flex;align-items:center;gap:5px;min-width:0}.runner-mark{font-size:14px;font-weight:700;flex:0 0 auto}.runner-name-line .horse-name{min-width:0;max-width:100%;font-size:14px;line-height:1.2;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.runner-name-line .expected{margin-left:auto;flex:0 0 auto;max-width:62px;text-align:center;font-size:9px;line-height:1.1;padding:4px 5px;background:#eef6ff;color:#175cd3}.runner-subline{display:flex;gap:6px;margin-top:3px;min-width:0;color:#667085;font-size:9px;white-space:nowrap;overflow:hidden}.runner-subline span{overflow:hidden;text-overflow:ellipsis}.runner-subline span:last-child{min-width:0;flex:1}.open-caret{font-size:15px;color:#98a2b3;text-align:center;transition:transform .2s}.runner-style[open] .open-caret{transform:rotate(180deg)}.style-rate-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:8px;width:100%;min-width:0}.style-rate{min-width:0;border:1px solid #edf1f5;background:#f8fafc;border-radius:8px;padding:5px 5px 6px}.style-rate.dominant{border-color:#b9d8ff;background:#f2f8ff}.style-rate-head{display:flex;align-items:center;justify-content:space-between;gap:2px;font-size:9px;color:#667085}.style-rate-head b{font-size:10px;font-weight:500;color:#344054}.style-bar{height:4px;background:#e9eef5;border-radius:99px;overflow:hidden;margin-top:4px}.style-bar i{display:block;height:100%;border-radius:99px;background:#7d9cc5}.style-rate.front .style-bar i{background:#e25b58}.style-rate.stalk .style-bar i{background:#e8a72f}.style-rate.mid .style-bar i{background:#3aa675}.style-rate.close .style-bar i{background:#5478d4}.runner-style .horse-detail{padding:0 9px 10px;border-top:1px dashed #e4e7ec;margin-top:0;overflow-wrap:anywhere;word-break:break-word}.detail-heading{font-size:11px;font-weight:600;margin:9px 0 5px;color:#344054}.recent-head{display:flex;justify-content:space-between;align-items:center;gap:6px}.recent-head strong{font-size:11px;font-weight:600}.empty.compact{padding:8px 2px;text-align:left}.pace-stage-tabs{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px;margin-top:8px;overflow:visible}.pace-stage-tabs button{min-width:0;border:1px solid #dbe3ee;background:#fff;border-radius:8px;padding:7px 1px;font-size:9px;white-space:nowrap}.pace-stage-tabs button.active{background:#0b1f3a;color:#fff;border-color:#0b1f3a}.scenario-prob-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
@media(max-width:390px){.runner-map-card{padding:9px}.section-title-row{margin-bottom:7px}.section-sub{font-size:9px}.runner-style summary{padding:8px 7px}.runner-line{grid-template-columns:28px minmax(0,1fr) 14px;gap:6px}.runner-id .frame-badge{width:27px;height:27px}.runner-name-line .horse-name{font-size:13px}.runner-name-line .expected{max-width:54px;font-size:8px;padding:4px}.runner-subline{font-size:8px;gap:4px}.style-rate-grid{gap:3px;margin-top:7px}.style-rate{padding:5px 3px}.style-rate-head{font-size:8px}.style-rate-head b{font-size:9px}.pace-stage-tabs{gap:3px}.pace-stage-tabs button{font-size:8px;padding:7px 0}.horse-info-grid{grid-template-columns:1fr 1fr}.fit-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}

/* v36 — deep pace logic + frame-aware style map + visual AI race flow */
.style-position-map{margin:8px 0 10px;border:1px solid #dbe3ee;border-radius:13px;background:linear-gradient(180deg,#f8fbff,#f5f8fc);padding:9px 8px 7px;overflow:hidden}
.style-map-axis{display:flex;justify-content:space-between;color:#667085;font-size:9px;margin:0 2px 6px}.style-map-axis b{font-weight:500;color:#344054}
.style-lane{display:grid;grid-template-columns:48px minmax(0,1fr);gap:5px;align-items:center;margin:3px 0}.style-lane-label{font-size:9px;color:#475467;text-align:right;padding-right:3px}.style-lane-track{position:relative;height:30px;border-radius:8px;background:repeating-linear-gradient(90deg,rgba(148,163,184,.12) 0,rgba(148,163,184,.12) 1px,transparent 1px,transparent 12.5%);border:1px solid rgba(203,213,225,.7)}
.style-map-horse{position:absolute;top:50%;transform:translate(-50%,-50%);transition:left .45s ease;z-index:2}.style-map-horse .frame-badge{width:24px;height:24px;border-radius:50%;font-size:10px;box-shadow:0 1px 4px rgba(15,23,42,.22)}.style-map-horse.shifted .frame-badge{outline:2px solid #22c7e8;outline-offset:1px}.style-map-horse .map-mark{position:absolute;right:-4px;top:-7px;font-size:9px;background:#0b1f3a;color:#fff;border-radius:999px;padding:1px 3px}.style-map-note{font-size:9px;color:#667085;margin-top:6px;line-height:1.45}.style-map-note b{color:#344054;font-weight:600}
.runner-score-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:6px}.runner-score-chip{background:#f2f4f7;border-radius:7px;padding:5px 3px;text-align:center;min-width:0}.runner-score-chip small{display:block;font-size:8px;color:#667085}.runner-score-chip b{font-size:10px;font-weight:600;color:#344054}.style-rate-grid.five-rates{grid-template-columns:repeat(5,minmax(0,1fr))}.style-rate.fade .style-bar i{background:#9b6bd6}.style-rate.fade.dominant{border-color:#d9c5f5;background:#faf7ff}
.pressure-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;margin-top:7px}.pressure-chip{border:1px solid #e4e7ec;border-radius:8px;padding:6px;background:#fff}.pressure-chip small{display:block;color:#667085;font-size:8px}.pressure-chip b{font-size:10px;font-weight:600}.pressure-chip.danger{border-color:#fecaca;background:#fff7f7;color:#b42318}.pressure-chip.safe{border-color:#bbf7d0;background:#f6fff8;color:#067647}
.ai-flow-card{padding:0!important;overflow:hidden;background:linear-gradient(180deg,#082750,#061b3d);border:1px solid rgba(61,145,225,.55);color:#fff;box-shadow:0 8px 24px rgba(2,20,48,.16)}
.ai-flow-head{display:flex;align-items:flex-start;gap:9px;padding:13px 13px 9px}.ai-flow-bars{display:flex;align-items:end;gap:3px;width:29px;height:28px;flex:0 0 29px}.ai-flow-bars i{display:block;width:6px;border-radius:3px;background:#54edff;box-shadow:0 0 10px rgba(84,237,255,.32)}.ai-flow-bars i:nth-child(1){height:10px}.ai-flow-bars i:nth-child(2){height:19px}.ai-flow-bars i:nth-child(3){height:27px}.ai-flow-copy{min-width:0;flex:1}.ai-flow-title{font-size:20px;font-weight:720;line-height:1.15}.ai-flow-sub{font-size:10px;color:#b8cbe2;margin-top:3px;line-height:1.45}.ai-flow-scenario{font-size:9px;color:#dff8ff;border:1px solid rgba(88,210,255,.5);background:rgba(12,51,92,.64);border-radius:999px;padding:5px 7px;white-space:nowrap}
.ai-stage-tabs{display:flex;gap:5px;overflow-x:auto;padding:0 10px 8px;-webkit-overflow-scrolling:touch;scrollbar-width:none}.ai-stage-tabs::-webkit-scrollbar{display:none}.ai-stage-tabs button{flex:0 0 auto;border:1px solid rgba(108,169,226,.48);background:rgba(4,25,56,.62);color:#c9dbef;border-radius:999px;padding:7px 12px;font-size:10px;white-space:nowrap}.ai-stage-tabs button.active{background:linear-gradient(135deg,#156ee9,#6948ed);border-color:#57e5ff;color:#fff;box-shadow:0 0 14px rgba(54,161,255,.22)}
.ai-race-visual{position:relative;height:275px;margin:0 10px 10px;border-radius:15px;overflow:hidden;border:1px solid rgba(83,191,240,.55);background-image:linear-gradient(180deg,rgba(4,19,41,.10),rgba(4,19,41,.02)),url('/pace-preview.webp?v=59');background-size:cover;background-position:center;box-shadow:inset 0 0 34px rgba(1,16,40,.26)}.ai-race-visual:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(2,17,39,.25),transparent 18%,transparent 82%,rgba(2,17,39,.18));pointer-events:none}.ai-race-meta{position:absolute;left:9px;top:9px;z-index:8;border:1px solid rgba(143,204,248,.48);background:rgba(2,22,50,.72);border-radius:999px;padding:5px 8px;color:#e9f7ff;font-size:9px;backdrop-filter:blur(5px)}
.ai-race-runner{position:absolute;z-index:6;transform:translate(-50%,-50%);display:flex;align-items:center;gap:3px;transition:left .62s cubic-bezier(.2,.8,.2,1),top .62s cubic-bezier(.2,.8,.2,1);will-change:left,top;filter:drop-shadow(0 2px 2px rgba(0,0,0,.28))}.ai-race-runner .frame-badge{width:29px;height:29px;border-radius:50%;font-size:11px;border-width:2px}.ai-race-runner .pace-name{font-size:8px;max-width:70px;padding:2px 4px;background:rgba(255,255,255,.90)}.ai-race-runner .course-mark{position:absolute;left:-6px;top:-10px;background:#071a35;color:#fff;border:1px solid rgba(255,255,255,.22);border-radius:999px;font-size:9px;padding:1px 4px}.ai-race-order{position:absolute;left:8px;right:8px;bottom:8px;z-index:9;background:rgba(3,22,50,.78);border:1px solid rgba(255,255,255,.18);border-radius:10px;color:#fff;padding:7px 8px;font-size:9px;line-height:1.45;backdrop-filter:blur(5px)}.ai-race-order b{color:#58ebff;margin-right:6px}.ai-race-order span{white-space:normal}.ai-race-note{padding:0 12px 12px;font-size:9px;color:#abc2dd;line-height:1.45}
.scenario-diagnostics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;margin-top:7px}.scenario-diagnostic{background:#f8fafc;border-radius:8px;padding:6px 4px;text-align:center}.scenario-diagnostic small{display:block;font-size:8px;color:#667085}.scenario-diagnostic b{display:block;font-size:11px;margin-top:2px;font-weight:600}.scenario-warning{margin-top:7px;padding:7px 8px;border-radius:9px;background:#fff7ed;color:#9a3412;font-size:9px;line-height:1.45}
.front-battle-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.front-battle-box{border:1px solid #dbe3ee;background:#f8fafc;border-radius:10px;padding:8px;min-width:0}.front-battle-box small{display:block;color:#667085;font-size:8px;margin-bottom:4px}.front-battle-box b{display:block;font-size:11px;line-height:1.4}.front-battle-note{margin-top:7px;font-size:9px;line-height:1.5;color:#475467}.front-battle-alert{margin-top:6px;border-radius:9px;background:#fff7ed;color:#9a3412;padding:7px 8px;font-size:9px;line-height:1.45}
.ai-stage-event{margin:0 10px 10px;border:1px solid rgba(95,165,226,.35);background:rgba(4,25,56,.64);border-radius:10px;padding:8px 9px;color:#dbeafe;font-size:9px;line-height:1.5}.ai-stage-event b{color:#5eeafa}.ai-stage-event .event-warn{color:#fecaca}.ai-stage-event .event-good{color:#bbf7d0}

@media(max-width:390px){.front-battle-grid{grid-template-columns:1fr}.style-lane{grid-template-columns:43px minmax(0,1fr)}.style-map-horse .frame-badge{width:22px;height:22px;font-size:9px}.runner-score-row{grid-template-columns:repeat(2,minmax(0,1fr))}.style-rate-grid.five-rates{gap:2px}.style-rate-grid.five-rates .style-rate{padding-left:2px;padding-right:2px}.ai-flow-head{padding:11px 10px 8px}.ai-flow-title{font-size:18px}.ai-stage-tabs{padding-left:8px;padding-right:8px}.ai-stage-tabs button{padding:6px 9px;font-size:9px}.ai-race-visual{height:245px;margin-left:8px;margin-right:8px}.ai-race-runner .pace-name{display:none}.ai-race-runner .frame-badge{width:27px;height:27px}.scenario-diagnostics{grid-template-columns:repeat(2,minmax(0,1fr))}}

/* v37 — real history first; clean, readable pace board */
.history-search-card{border-color:#9bd8ff;background:linear-gradient(180deg,#f4fbff,#eef7ff);padding:14px}.history-search-head{display:flex;align-items:center;gap:10px}.history-spinner{width:22px;height:22px;border:3px solid #cfe9fb;border-top-color:#1677d2;border-radius:50%;animation:historySpin .8s linear infinite;flex:0 0 auto}@keyframes historySpin{to{transform:rotate(360deg)}}.history-search-title{font-size:15px;font-weight:700}.history-search-sub{font-size:10px;color:#52657a;margin-top:2px;line-height:1.5}.history-progress{height:7px;background:#dcecf7;border-radius:99px;overflow:hidden;margin:10px 0 6px}.history-progress i{display:block;height:100%;background:linear-gradient(90deg,#20c9e8,#2563eb);border-radius:99px;transition:width .35s ease}.history-stats{display:flex;gap:5px;flex-wrap:wrap}.history-stats span{font-size:9px;background:#fff;border:1px solid #d7e6f2;border-radius:999px;padding:4px 7px;color:#41566d}.history-horses{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}.history-horses span{display:inline-flex;align-items:center;gap:4px;background:#fff;border-radius:999px;border:1px solid #dbe8f2;padding:3px 7px 3px 3px;font-size:9px}.history-horses .frame-badge{width:22px;height:22px;border-radius:50%;font-size:9px}
.ai-race-visual{height:310px;background:linear-gradient(180deg,#dfeeda 0 15%,#c59b68 15% 84%,#dfeeda 84%)!important;background-image:none!important;border-color:rgba(104,183,221,.72);box-shadow:inset 0 0 0 1px rgba(255,255,255,.34),inset 0 0 24px rgba(3,24,52,.08)}.ai-race-visual:before{content:"";position:absolute;left:0;right:0;top:22%;bottom:20%;background:repeating-linear-gradient(180deg,rgba(255,255,255,.0) 0 39px,rgba(255,255,255,.28) 40px 41px);pointer-events:none}.ai-race-visual:after{content:"";position:absolute;top:15%;bottom:16%;right:8%;width:2px;background:rgba(255,255,255,.9);box-shadow:0 0 0 1px rgba(0,0,0,.05);pointer-events:none}.ai-race-runner{z-index:6}.ai-race-runner .pace-name{display:none!important}.ai-race-runner .frame-badge{width:31px;height:31px;font-size:12px;box-shadow:0 2px 7px rgba(0,0,0,.28);border-radius:50%}.ai-race-runner .course-mark{position:absolute;top:-10px;right:-7px;min-width:19px;height:19px;padding:0 3px;border-radius:999px;background:#071a35;display:grid;place-items:center;font-size:10px;border:1px solid rgba(255,255,255,.4)}.ai-race-order{font-size:10px;line-height:1.45;max-height:68px;overflow:auto}.ai-race-meta{background:rgba(2,22,50,.86)}
.style-rate.unknown{background:#fafafa;border-color:#eceff3}.style-rate.unknown .style-rate-head b{color:#98a2b3}.style-rate.unknown .style-bar i{width:0!important}.runner-score-chip.unknown b,.fit-chip .unknown{color:#98a2b3}.data-source-note{font-size:9px;color:#667085;margin-top:5px}
@media(max-width:390px){.ai-race-visual{height:300px}.ai-race-runner .frame-badge{width:29px;height:29px}.history-search-card{padding:11px}}


/* v38 — inline grade, explicit front/back axis, clickable past races */
.overall-grade{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:24px;border-radius:7px;font-size:12px;font-weight:800;line-height:1;flex:0 0 auto;border:1px solid rgba(15,23,42,.12)}
.overall-grade.grade-s{background:#111827;color:#fff}.overall-grade.grade-a{background:#e7f1ff;color:#175cd3}.overall-grade.grade-b{background:#ecfdf3;color:#067647}.overall-grade.grade-c{background:#f2f4f7;color:#667085}.overall-grade.grade-hold{min-width:36px;background:#fff7ed;color:#9a3412;font-size:9px}
.overall-summary{margin-top:9px;border:1px solid #dbe3ee;border-radius:11px;padding:8px;background:linear-gradient(180deg,#fbfdff,#f7f9fc)}.overall-summary-head{display:flex;align-items:center;gap:7px}.overall-summary-head b{font-size:11px}.overall-summary-head strong{font-size:20px;line-height:1}.overall-summary-head span{margin-left:auto;font-size:11px;color:#475467}.overall-reasons{margin-top:6px;display:flex;gap:4px;flex-wrap:wrap}.overall-reasons i{font-style:normal;font-size:9px;border-radius:999px;background:#eef2f6;color:#475467;padding:4px 7px}.overall-reasons i.good{background:#ecfdf3;color:#067647}.overall-reasons i.warn{background:#fff1f2;color:#b42318}.runner-summary-name{display:grid;grid-template-columns:30px minmax(0,1fr) 18px;gap:7px;align-items:center}.runner-summary-name .horse-name{font-size:14px;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.runner-eval-table{display:grid;grid-template-columns:1.15fr .9fr .65fr 1.2fr;gap:4px;margin-top:8px}.runner-eval-cell{border:1px solid #e4e7ec;background:#f8fafc;border-radius:8px;padding:6px 4px;text-align:center;min-width:0}.runner-eval-cell small{display:block;font-size:8px;color:#667085;white-space:nowrap}.runner-eval-cell b{display:block;font-size:12px;font-weight:700;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.runner-eval-cell.grade b{font-size:18px;line-height:1}.runner-eval-cell.mark b{font-size:18px;line-height:1;color:#b54708}.runner-position-title{display:flex;align-items:center;justify-content:space-between;margin-top:8px;margin-bottom:4px}.runner-position-title b{font-size:10px;color:#344054}.runner-position-title span{font-size:8px;color:#98a2b3}.runner-summary-scores{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:5px}.runner-summary-score{border:1px solid #edf1f5;background:#f8fafc;border-radius:8px;padding:5px 3px;text-align:center;min-width:0}.runner-summary-score small{display:block;font-size:8px;color:#667085}.runner-summary-score b{display:block;font-size:10px;font-weight:600;color:#344054;margin-top:1px}.horse-detail .detail-heading:first-child{margin-top:9px}.detail-tap-note{font-size:8px;color:#98a2b3;text-align:right;margin-top:5px}@media(max-width:390px){.runner-eval-table{grid-template-columns:1fr .85fr .58fr 1.15fr;gap:3px}.runner-eval-cell{padding:5px 2px}.runner-eval-cell small{font-size:7px}.runner-eval-cell b{font-size:10px}.runner-eval-cell.grade b,.runner-eval-cell.mark b{font-size:16px}.runner-summary-scores{gap:3px}.runner-summary-score{padding:5px 2px}.runner-summary-score small{font-size:7px}.runner-summary-score b{font-size:9px}}
.ai-race-axis{position:absolute;left:10px;right:10px;top:41px;z-index:9;display:flex;align-items:center;justify-content:space-between;pointer-events:none}.ai-race-axis span{font-size:10px;font-weight:700;color:#fff;background:rgba(3,20,45,.78);border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:5px 8px;backdrop-filter:blur(4px);box-shadow:0 2px 8px rgba(0,0,0,.18)}.ai-race-axis .front{color:#67e8f9}.ai-race-axis:before{content:"";position:absolute;left:61px;right:78px;top:50%;height:1px;background:linear-gradient(90deg,rgba(255,255,255,.28),rgba(103,232,249,.82));z-index:-1}
.recent{position:relative}.recent-open{margin-top:6px;width:100%;border:1px solid #bfdbfe;background:#eff6ff;color:#175cd3;border-radius:8px;padding:7px 8px;text-align:left;font-size:10px;font-weight:600}.recent-open:after{content:"›";float:right;font-size:16px;line-height:10px}.past-race-badge{font-size:9px;border-radius:999px;padding:4px 7px;background:#fff7ed;color:#9a3412;border:1px solid #fed7aa}
@media(max-width:390px){.overall-grade{min-width:22px;height:22px;font-size:11px}.overall-grade.grade-hold{min-width:32px;font-size:8px}.ai-race-axis{top:39px}.ai-race-axis span{font-size:9px;padding:4px 6px}.ai-race-axis:before{left:54px;right:68px}}

/* v42 clean home pace preview — no photo */
.mini-flow-demo{background:linear-gradient(180deg,#0b2a52,#0a2344)!important;position:relative}
.mini-flow-axis{position:absolute;left:10px;right:10px;top:10px;display:flex;justify-content:space-between;align-items:center;color:#dff5ff;font-size:9px;z-index:3}.mini-flow-axis b{font-size:10px;color:#67e8f9}
.mini-flow-line{position:absolute;left:9%;right:9%;top:58%;height:4px;border-radius:99px;background:linear-gradient(90deg,rgba(103,232,249,.12),rgba(103,232,249,.7));box-shadow:0 0 18px rgba(56,189,248,.18)}
.mini-flow-dot{position:absolute;top:calc(58% - 14px);width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-size:11px;font-weight:800;color:#fff;border:2px solid rgba(255,255,255,.88);box-shadow:0 4px 10px rgba(0,0,0,.28)}
.mini-flow-dot.d1{left:15%;background:#1e66d0}.mini-flow-dot.d2{left:38%;background:#3a9b56}.mini-flow-dot.d3{left:61%;background:#e53935}.mini-flow-dot.d4{left:80%;background:#f28c28;color:#111}
.mini-flow-caption{position:absolute;left:10px;right:10px;bottom:8px;color:#9cc5ec;font-size:9px;text-align:center}


/* v60 — runtime dependency fix */
.runner-name-btn{border:0;background:none;padding:0;margin:0;display:inline-flex;align-items:baseline;gap:6px;max-width:100%;cursor:pointer}.runner-name-btn .horse-name{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.horse-modal-layer{position:fixed;inset:0;z-index:60}.horse-modal-backdrop{position:absolute;inset:0;background:rgba(11,18,32,.56);backdrop-filter:blur(2px)}.horse-modal{position:absolute;left:10px;right:10px;top:calc(10px + env(safe-area-inset-top));bottom:calc(10px + env(safe-area-inset-bottom));background:#fff;border-radius:18px;box-shadow:0 24px 60px rgba(0,0,0,.28);display:flex;flex-direction:column;overflow:hidden}.horse-modal-head{display:grid;grid-template-columns:42px minmax(0,1fr) 42px 42px;gap:8px;align-items:center;padding:12px 12px 8px;border-bottom:1px solid #e4e7ec;background:#f8fafc}.horse-modal-head button{border:1px solid #d0d5dd;background:#fff;border-radius:12px;height:42px;font-size:20px}.horse-modal-title{min-width:0}.horse-modal-title-top{display:flex;align-items:center;gap:8px;min-width:0}.horse-modal-title .frame-badge{width:34px;height:34px;border-radius:10px;font-size:16px;font-weight:800}.horse-modal-name{font-size:21px;font-weight:800;line-height:1.1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.horse-modal-title .runner-weight-inline{font-size:12px;color:#667085}.horse-modal-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:5px;color:#667085;font-size:12px}.horse-modal-sidechips{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:6px}.horse-modal-chip{display:inline-flex;align-items:center;justify-content:center;border-radius:999px;padding:4px 9px;font-size:11px;border:1px solid var(--line);background:#f8fafc;color:#344054}.horse-modal-chip.mark{background:#fff7ed;border-color:#fed7aa;color:#b54708;font-weight:900}.horse-modal-chip.grade{background:#eef2ff;border-color:#c7d2fe;color:#3730a3;font-weight:800}.horse-modal-swipe{padding:6px 14px 8px;font-size:11px;color:#667085;border-bottom:1px solid #eef2f6;background:#fff}.horse-modal-body{padding:12px;overflow:auto;-webkit-overflow-scrolling:touch}.horse-modal .horse-detail{padding-top:0}.horse-modal-counter{font-size:11px;color:#667085;margin-top:2px}.horse-modal-nav.disabled{opacity:.45}.horse-modal-close{font-size:18px}@media(max-width:390px){.horse-modal{left:6px;right:6px;top:calc(6px + env(safe-area-inset-top));bottom:calc(6px + env(safe-area-inset-bottom))}.horse-modal-head{gap:6px;padding:10px 10px 8px;grid-template-columns:40px minmax(0,1fr) 40px 40px}.horse-modal-head button{height:40px}.horse-modal-name{font-size:18px}}
.runner-map-card .section-sub{font-size:11px;color:#667085}.runner-style{border:1px solid #d8e0ea;border-radius:16px;background:#fff;overflow:hidden}.runner-style summary{list-style:none}.runner-style summary::-webkit-details-marker{display:none}.runner-summary-table{display:grid;grid-template-columns:44px 54px minmax(0,1fr) 86px 16px;gap:8px;align-items:center}.runner-summary-no .frame-badge{width:42px;height:42px;border-radius:11px;font-size:18px;font-weight:800}.runner-mark-toggle{border:1px solid #d0d5dd;background:#fff;border-radius:13px;min-height:46px;padding:4px 0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;color:#667085}.runner-mark-toggle b{font-size:20px;line-height:1;font-weight:900;color:#b54708}.runner-mark-toggle.empty b{color:#98a2b3}.runner-mark-toggle small{font-size:9px}.runner-summary-topline{display:flex;align-items:baseline;gap:6px;min-width:0}.runner-summary-topline .horse-name{display:block;font-size:21px;line-height:1.1;font-weight:800;letter-spacing:.01em;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.runner-weight-inline{font-size:12px;color:#667085;white-space:nowrap}.runner-summary-meta.compact{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;color:#667085;font-size:13px;line-height:1.2}.runner-summary-meta.compact span{white-space:nowrap}.runner-grade-side{border:1px solid #dbe3ee;background:#f8fafc;border-radius:12px;padding:6px 6px;text-align:center}.runner-grade-side small{display:block;font-size:9px;color:#667085}.runner-grade-side b{display:block;font-size:24px;line-height:1;font-weight:900;margin:2px 0 3px}.runner-grade-side span{display:block;font-size:11px;color:#475467}.runner-style .open-caret{font-size:14px;color:#98a2b3}.runner-style summary .runner-position-title{margin-top:10px}.runner-style summary .style-rate-grid.five-rates{gap:5px}.runner-style summary .style-rate{padding:9px 4px}.runner-style summary .style-rate-head{font-size:11px}.runner-style summary .style-rate-head b{font-size:14px}.runner-style .detail-tap-note{margin-top:6px}.runner-style .runner-overall-box{margin-top:2px}.runner-summary-main{min-width:0}@media(max-width:390px){.runner-summary-table{grid-template-columns:40px 48px minmax(0,1fr) 74px 12px;gap:6px}.runner-summary-no .frame-badge{width:38px;height:38px;font-size:16px}.runner-mark-toggle{min-height:42px}.runner-mark-toggle b{font-size:18px}.runner-summary-topline .horse-name{font-size:18px}.runner-weight-inline{font-size:11px}.runner-summary-meta.compact{font-size:12px;gap:6px}.runner-grade-side{padding:5px 4px}.runner-grade-side b{font-size:22px}.runner-grade-side span{font-size:10px}}
.ai-race-topline{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:0 12px 8px}.ai-race-meta-chip{display:inline-flex;align-items:center;border:1px solid rgba(108,169,226,.48);background:rgba(4,25,56,.62);color:#e6f1ff;border-radius:999px;padding:8px 12px;font-size:11px;white-space:nowrap}.ai-race-axis-strip{display:flex;align-items:center;justify-content:space-between;gap:8px;flex:1;color:#aee9ff;font-size:11px}.ai-race-board-wrap{padding:0 12px}.ai-race-order-panel{margin:10px 12px 0;background:rgba(3,22,50,.78);border:1px solid rgba(255,255,255,.18);border-radius:12px;color:#fff;padding:9px 10px;font-size:10px;line-height:1.5}.ai-race-order-panel b{color:#58ebff;margin-right:6px}.ai-race-order-panel span{white-space:normal}.ai-race-swipe-hint{padding:0 12px 8px;color:#abc2dd;font-size:10px}.ai-race-visual{margin-left:12px!important;margin-right:12px!important;height:250px!important}.ai-race-visual:before{top:0!important;bottom:0!important;background:repeating-linear-gradient(180deg,rgba(255,255,255,.0) 0 49px,rgba(255,255,255,.24) 50px 51px)!important}.ai-race-visual:after{display:none!important}.ai-stage-event{margin-top:10px}
.runner-style summary{padding:14px 14px 12px}
.runner-summary-name{grid-template-columns:44px minmax(0,1fr) 22px;gap:12px;align-items:center}
.runner-summary-name .runner-id .frame-badge{width:42px;height:42px;border-radius:11px;font-size:18px;font-weight:700}
.runner-summary-main{min-width:0}
.runner-summary-name .horse-name{display:block;font-size:21px;line-height:1.15;font-weight:800;letter-spacing:.01em}
.runner-summary-meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;color:#667085;font-size:14px;line-height:1.2}
.runner-summary-meta span{white-space:nowrap}
.runner-overall-box{margin-top:13px;border:1px solid #d7e0eb;border-radius:16px;padding:13px 14px;background:linear-gradient(180deg,#fcfdff,#f7f9fc)}
.runner-overall-head{display:flex;align-items:center;gap:10px;min-width:0}
.runner-overall-head .label{margin:0;font-size:18px;font-weight:800;color:#1d2939;white-space:nowrap}
.runner-overall-head .overall-grade{width:44px;height:44px;min-width:44px;border-radius:12px;font-size:29px}
.runner-overall-mark{display:inline-flex;align-items:center;justify-content:center;min-width:46px;height:38px;border-radius:11px;background:#fff7ed;border:1px solid #fed7aa;color:#b54708;font-size:24px;font-weight:900;line-height:1}
.runner-overall-score{margin-left:auto;font-size:17px;color:#475467;white-space:nowrap}
.runner-overall-box .overall-reasons{margin-top:10px;gap:6px}
.runner-overall-box .overall-reasons i{font-size:12px;padding:6px 9px}
.runner-position-title{margin-top:14px;margin-bottom:7px}
.runner-position-title b{font-size:16px;color:#344054}
.runner-position-title span{font-size:11px;color:#98a2b3}
.runner-style summary .style-rate-grid.five-rates{gap:7px;margin-top:0}
.runner-style summary .style-rate{border-radius:12px;padding:9px 8px 10px}
.runner-style summary .style-rate-head{font-size:13px}
.runner-style summary .style-rate-head b{font-size:16px;font-weight:700}
.runner-style summary .style-bar{height:6px;margin-top:7px}
.runner-style summary .detail-tap-note{font-size:10px;margin-top:8px}
.runner-detail-scores{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:7px}
.runner-detail-score{border:1px solid #edf1f5;background:#f8fafc;border-radius:10px;padding:8px;text-align:center}
.runner-detail-score small{display:block;font-size:10px;color:#667085}
.runner-detail-score b{display:block;margin-top:2px;font-size:14px;font-weight:700;color:#344054}
@media(max-width:390px){
.runner-style summary{padding:13px 11px 11px}.runner-summary-name{grid-template-columns:40px minmax(0,1fr) 18px;gap:9px}.runner-summary-name .runner-id .frame-badge{width:38px;height:38px;font-size:17px}.runner-summary-name .horse-name{font-size:19px}.runner-summary-meta{font-size:13px;gap:8px;margin-top:5px}.runner-overall-box{padding:12px 11px;border-radius:14px}.runner-overall-head{gap:7px}.runner-overall-head .label{font-size:16px}.runner-overall-head .overall-grade{width:40px;height:40px;min-width:40px;font-size:26px}.runner-overall-mark{min-width:40px;height:34px;font-size:21px}.runner-overall-score{font-size:15px}.runner-overall-box .overall-reasons i{font-size:11px;padding:5px 8px}.runner-position-title b{font-size:15px}.runner-position-title span{font-size:10px}.runner-style summary .style-rate-grid.five-rates{gap:4px}.runner-style summary .style-rate{padding:8px 4px 9px}.runner-style summary .style-rate-head{font-size:12px}.runner-style summary .style-rate-head b{font-size:14px}}

"""

JS = r"""
(function(){
"use strict";
var CENTRAL=["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"];
var LOCAL=["帯広","門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"];
var COURSE={
"帯広":{lap:200,straight:200,dir:1,shape:"straight",turn:"直線",firstTurn:999},
"門別":{lap:1600,straight:330,dir:-1,shape:"wide",turn:"右",firstTurn:350},
"盛岡":{lap:1600,straight:300,dir:1,shape:"wide",turn:"左",firstTurn:300},
"水沢":{lap:1200,straight:245,dir:-1,shape:"compact",turn:"右",firstTurn:250},
"浦和":{lap:1200,straight:220,dir:1,shape:"compact",turn:"左",firstTurn:250},
"船橋":{lap:1400,straight:308,dir:1,shape:"boxy",turn:"左",firstTurn:300},
"大井":{lap:1600,straight:386,dir:-1,shape:"wide",turn:"右",firstTurn:350},
"川崎":{lap:1200,straight:300,dir:1,shape:"compact",turn:"左",firstTurn:250},
"金沢":{lap:1200,straight:236,dir:-1,shape:"pocket",turn:"右",firstTurn:250},
"笠松":{lap:1100,straight:201,dir:-1,shape:"compact",turn:"右",firstTurn:230},
"名古屋":{lap:1180,straight:240,dir:-1,shape:"spiral",turn:"右",firstTurn:250},
"園田":{lap:1051,straight:213,dir:-1,shape:"compact",turn:"右",firstTurn:220},
"姫路":{lap:1200,straight:230,dir:-1,shape:"boxy",turn:"右",firstTurn:260},
"高知":{lap:1100,straight:200,dir:-1,shape:"egg",turn:"右",firstTurn:220},
"佐賀":{lap:1100,straight:200,dir:-1,shape:"compact",turn:"右",firstTurn:230},
"札幌":{lap:1641,straight:266,dir:-1,shape:"round",turn:"右",firstTurn:300},
"函館":{lap:1627,straight:262,dir:-1,shape:"compact",turn:"右",firstTurn:270},
"福島":{lap:1600,straight:292,dir:-1,shape:"boxy",turn:"右",firstTurn:300},
"新潟":{lap:2223,straight:659,dir:1,shape:"long",turn:"左",firstTurn:450},
"東京":{lap:2084,straight:526,dir:1,shape:"long",turn:"左",firstTurn:400},
"中山":{lap:1667,straight:310,dir:-1,shape:"boxy",turn:"右",firstTurn:300},
"中京":{lap:1706,straight:413,dir:1,shape:"wide",turn:"左",firstTurn:350},
"京都":{lap:1783,straight:328,dir:-1,shape:"wide",turn:"右",firstTurn:350},
"阪神":{lap:1689,straight:357,dir:-1,shape:"wide",turn:"右",firstTurn:330},
"小倉":{lap:1615,straight:293,dir:-1,shape:"compact",turn:"右",firstTurn:280}
};
function courseProfile(r){return COURSE[r.track]||{lap:1400,straight:300,dir:-1,shape:"wide",turn:"右",firstTurn:300}}
function coursePathD(p){if(p.shape==="straight")return "M18 92 L182 92";if(p.shape==="round")return "M174 90 C174 42 142 18 97 18 C50 18 22 46 22 90 C22 134 50 162 97 162 C142 162 174 138 174 90 Z";if(p.shape==="long")return "M184 90 C184 53 160 34 126 34 L67 34 C34 34 16 54 16 90 C16 126 34 146 67 146 L126 146 C160 146 184 127 184 90 Z";if(p.shape==="boxy")return "M178 90 C178 57 158 36 130 32 L66 32 C36 36 20 58 20 90 C20 122 36 144 66 148 L130 148 C158 144 178 123 178 90 Z";if(p.shape==="pocket")return "M176 91 C176 52 151 29 116 27 L69 30 C36 33 18 56 20 91 C21 126 40 147 73 151 L124 147 C157 142 176 122 176 91 Z";if(p.shape==="spiral")return "M178 91 C178 52 154 31 118 29 L72 31 C38 33 18 56 20 91 C22 128 44 148 78 149 L125 145 C157 140 178 120 178 91 Z";if(p.shape==="egg")return "M177 91 C177 49 147 25 106 24 C66 23 31 43 21 78 C11 113 31 146 71 154 C115 162 158 142 174 111 C178 103 179 97 177 91 Z";return "M176 90 C176 51 151 28 116 28 L72 28 C38 28 20 51 20 90 C20 129 38 152 72 152 L116 152 C151 152 176 129 176 90 Z"}
function normFrac(x){x=x%1;return x<0?x+1:x}
function courseStageFrac(r,st){var p=courseProfile(r);if(p.shape==="straight")return st===0?.05:(st===1?.67:.92);var laps=Math.max(.1,n(r.distance,1200)/p.lap),start=normFrac(.965-p.dir*(laps%1)),prog=st===0?.015:(st===1?.81:.965);return normFrac(start+p.dir*laps*prog)}
var app=document.getElementById("app");
var state={date:today(),circuit:"地方",races:[],track:null,race:null,raceLoading:null,picker:false,loading:false,error:null,timer:null,anim:null,simSpeed:5,simTarget:20,simRunning:false,simPaused:false,simStopped:false,simIndex:0,simDone:0,simCounts:null,simCurrentT:0,pred:null,requestSeq:0,historyTimer:null,raceStack:[],historyPrefetch:{},paceStage:0,horseModalNo:null};

function cacheKey(d){return "keiba:v60:races:"+d}
function loadRaceCache(d){try{var raw=localStorage.getItem(cacheKey(d));if(!raw)return null;var x=JSON.parse(raw);if(!x||!Array.isArray(x.rows))return null;if(Date.now()-n(x.ts)>6*3600000)return null;return x.rows}catch(e){return null}}
function saveRaceCache(d,rows){try{localStorage.setItem(cacheKey(d),JSON.stringify({ts:Date.now(),rows:rows}))}catch(e){}}
function clearOldPwa(){try{if("serviceWorker" in navigator)navigator.serviceWorker.getRegistrations().then(function(rs){for(var i=0;i<rs.length;i++)rs[i].unregister()}).catch(function(){});if(window.caches)caches.keys().then(function(ks){return Promise.all(ks.map(function(k){return caches.delete(k)}))}).catch(function(){})}catch(e){}}
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
function header(title,back,sub){return '<header class="header"><div class="header-row">'+(back?'<button data-action="back">‹</button>':'')+'<div class="header-title"><h1>'+esc(title)+'</h1>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div><span class="build-badge">v60</span><button data-action="reload">↻</button></div></header>'}
function recencyWeights(len){var a=[],i;for(i=0;i<len;i++)a.push(Math.pow(.82,i));return a}
function weightedRate(vals,weights,def){var s=0,w=0,i;for(i=0;i<vals.length;i++){if(vals[i]==null)continue;var q=weights&&weights[i]!=null?weights[i]:1;s+=n(vals[i])*q;w+=q}return w?s/w:(def==null?.5:def)}
function raceField(rr){return Math.max(4,n(rr&&rr.fieldSize,12))}
function firstCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[0],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
function lastCornerNorm(rr){var p=rr&&rr.cornerPositions||[],x=n(p[p.length-1],0);if(!x)return null;return clamp(1-(x-1)/Math.max(1,raceField(rr)-1),0,1)}
function styleRates(h,r){var rs=(h.recentRaces||[]).slice(0,5),rw=recencyWeights(rs.length),c=[0,0,0,0],den=0,earlyDen=0,early3=0,moved3=0,tempoVals=[],tempoW=[],i,rr,p,pos,fs,norm,ww,delta,rel,j,bestLater;for(i=0;i<rs.length;i++){rr=rs[i];p=rr.cornerPositions||[];pos=n(p[0],0);if(!pos)continue;fs=raceField(rr);norm=(pos-1)/Math.max(1,fs-1);delta=Math.abs(n(rr.distance)-n(r&&r.distance));rel=1;if(delta<=100)rel*=1.22;else if(delta<=300)rel*=1.08;else if(delta>=700)rel*=.74;if(r&&rr.track===r.track)rel*=1.10;if(r&&sameCondition(rr.condition,r.condition))rel*=1.05;ww=rw[i]*rel;den+=ww;earlyDen+=ww;if(pos===1)c[0]+=ww;else if(pos<=3||norm<=.22)c[1]+=ww;else if(norm<=.62)c[2]+=ww;else c[3]+=ww;if(pos<=3)early3+=ww;bestLater=99;for(j=1;j<p.length;j++){var z=n(p[j],0);if(z&&z<bestLater)bestLater=z}if(pos>3&&bestLater<=3)moved3+=ww;tempoVals.push(clamp(1-(pos-1)/Math.max(3,fs-1),0,1));tempoW.push(ww)}if(!den)return{front:0,stalk:0,mid:0,close:0,early3:0,moved3:0,ten:.5,samples:0,unknown:true};return{front:c[0]/den,stalk:c[1]/den,mid:c[2]/den,close:c[3]/den,early3:earlyDen?early3/earlyDen:0,moved3:earlyDen?moved3/earlyDen:0,ten:weightedRate(tempoVals,tempoW,.5),samples:tempoVals.length,unknown:false}}
function tenScore(h,r){var rt=styleRates(h,r),rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),v=[],ws=[],i,rr,p,fs,delta,rel;for(i=0;i<rs.length;i++){rr=rs[i];p=rr.cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rr);delta=Math.abs(n(rr.distance)-n(r&&r.distance));rel=delta<=100?1.18:(delta<=300?1.05:.88);v.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1));ws.push((w[i]||1)*rel)}return clamp(weightedRate(v,ws,rt.ten)*.72+rt.front*.18+rt.early3*.10,0,1)}
function firstThreeType(h){var rr=(h.recentRaces||[])[0],p=rr&&rr.cornerPositions||[],j;if(!p.length)return"不明";if(n(p[0])>0&&n(p[0])<=3)return"最初から前";for(j=1;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3)return"途中から上昇";return"前走は中後方"}
function fadeRate(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),e=0,f=0,i,p,first,last,fin,fs,ww,sev;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];first=n(p[0]);if(!first||first>4)continue;ww=w[i];fs=raceField(rs[i]);e+=ww;last=n(p[p.length-1]);fin=n(rs[i].finish);sev=0;if(last)sev=Math.max(sev,clamp((last-first)/Math.max(3,fs-1)*2.2,0,1));if(fin)sev=Math.max(sev,clamp((fin-first)/Math.max(3,fs-1)*1.8,0,1));if((last&&last>=first+2)||(fin&&fin>=first+3))sev=Math.max(sev,.55);f+=ww*sev}return e?clamp(f/e,0,1):.25}
function moveRate(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),e=0,g=0,i,p,a,b,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(p.length<2)continue;a=n(p[0]);b=n(p[p.length-1]);if(!a||!b)continue;ww=w[i];e+=ww;if(b<=a-2)g+=ww}return e?g/e:.2}
function holdRate(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),e=0,g=0,i,p,a,b,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);b=n(p[p.length-1]);if(!a||a>4)continue;ww=w[i];e+=ww;if((b&&b<=4)||n(rs[i].finish)<=4)g+=ww}return e?g/e:.5}
function yieldFlex(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),e=0,g=0,i,p,a,fin,ww;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);if(!a||a===1||a>5)continue;ww=w[i];e+=ww;if(fin>0&&fin<=4)g+=ww}return e?g/e:.45}

function breakReliability(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),v=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);v.push(clamp(1-(n(p[0])-1)/Math.max(3,fs-1),0,1))}return weightedRate(v,w,.5)}
function lateGainScore(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),v=[],i,p,a,b,fin,fs,g;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!p.length)continue;a=n(p[p.length-1]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||!fin)continue;g=(a-fin)/Math.max(3,fs-1);v.push(clamp(.5+g*1.8,0,1))}return weightedRate(v,w,.5)}
function positionConsistency(h){var rs=(h.recentRaces||[]).slice(0,5),vals=[],i,p,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];if(!n(p[0]))continue;fs=raceField(rs[i]);vals.push((n(p[0])-1)/Math.max(3,fs-1))}if(vals.length<2)return.5;var m=mean(vals),vv=0;for(i=0;i<vals.length;i++)vv+=(vals[i]-m)*(vals[i]-m);vv/=vals.length;return clamp(1-Math.sqrt(vv)*2.1,0,1)}
function earlyCollapseSeverity(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),vals=[],ws=[],i,p,a,fin,fs;for(i=0;i<rs.length;i++){p=rs[i].cornerPositions||[];a=n(p[0]);fin=n(rs[i].finish);fs=raceField(rs[i]);if(!a||a>4||!fin)continue;vals.push(clamp((fin-a)/Math.max(3,fs-1),0,1));ws.push(w[i])}return weightedRate(vals,ws,.18)}
function stylePoint(rt){return rt.front+2*rt.stalk+3*rt.mid+4*rt.close}
function styleName(pt){if(pt<1.65)return"逃げ";if(pt<2.35)return"先行";if(pt<3.15)return"差し";return"追込"}
function earlyOcc(r){var hs=r.horses||[],nums=[],early=[],moved=[],i,rr,p,j,hit;for(i=0;i<hs.length;i++){rr=(hs[i].recentRaces||[])[0];if(!rr)continue;p=rr.cornerPositions||[];hit=false;for(j=0;j<p.length;j++)if(n(p[j])>0&&n(p[j])<=3){hit=true;break}if(hit){nums.push(n(hs[i].horseNumber));if(n(p[0])<=3)early.push(n(hs[i].horseNumber));else moved.push(n(hs[i].horseNumber))}}return{nums:nums,early:early,moved:moved,rate:hs.length?nums.length/hs.length:0}}
function recentDistance(h){var rr=(h.recentRaces||[])[0];return rr?n(rr.distance):0}
function recentFirst(h){var rr=(h.recentRaces||[])[0],p=rr&&rr.cornerPositions||[];return n(p[0],99)}
function targetSeason(r){return season(r.date)}
function sameCondition(a,b){a=String(a||"");b=String(b||"");return a&&b&&a!=="不明"&&b!=="不明"&&a===b}
function contextualRuns(h,r){var rs=(h.recentRaces||[]).slice(0,5),tw=targetSeason(r),out={track:[],distance:[],condition:[],weather:[],season:[],surface:[],level:[]},i,rr,delta;for(i=0;i<rs.length;i++){rr=rs[i];delta=Math.abs(n(rr.distance)-n(r.distance));if(rr.track===r.track)out.track.push(rr);if(delta<=100||(n(r.distance)>=1800&&delta<=200))out.distance.push(rr);if(sameCondition(rr.condition,r.condition))out.condition.push(rr);if(String(rr.weather||"")===String(r.weather||"")&&r.weather&&r.weather!=="不明")out.weather.push(rr);if(season(rr.date)===tw)out.season.push(rr);if(n(r.racePrize1)>0&&n(rr.racePrize1)>=n(r.racePrize1)*.8)out.level.push(rr)}return out}
function runFinishQuality(rr){var f=n(rr.finish,0),fs=raceField(rr);if(!f)return.45;return clamp(1-(f-1)/Math.max(3,fs-1),0,1)}
function runTimeIndex(rr,targetDist){var t=n(rr.timeSeconds),d=n(rr.distance);if(!t||!d)return null;var speed=d/t,distPenalty=1-Math.min(.28,Math.abs(d-targetDist)/Math.max(600,targetDist)*.55),cond=String(rr.condition||"");var surfaceAdj=1;if(cond.indexOf("重")>=0||cond.indexOf("不")>=0)surfaceAdj=.985;else if(cond.indexOf("稍")>=0)surfaceAdj=.993;return speed*distPenalty/surfaceAdj}
function recentFinishScore(h){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),v=[],i;for(i=0;i<rs.length;i++)v.push(runFinishQuality(rs[i]));return weightedRate(v,w,.45)}
function speedRaw(h,dist){var rs=(h.recentRaces||[]).slice(0,5),w=recencyWeights(rs.length),vals=[],ws=[],i,x;for(i=0;i<rs.length;i++){x=runTimeIndex(rs[i],dist);if(x!=null){vals.push(x);ws.push(w[i])}}if(!vals.length)return 0;var best=Math.max.apply(null,vals),avg=weightedRate(vals,ws,0);return best*.55+avg*.45}
function normalize(vals,x){var v=vals.filter(function(z){return isFinite(z)&&z>0});if(!v.length||!isFinite(x)||x<=0)return.5;var lo=Math.min.apply(null,v),hi=Math.max.apply(null,v);return hi===lo?.5:clamp((x-lo)/(hi-lo),0,1)}
function listQuality(list,targetDist){if(!list||!list.length)return.5;var w=recencyWeights(list.length),v=[],i,q,t;for(i=0;i<list.length;i++){q=runFinishQuality(list[i]);t=runTimeIndex(list[i],targetDist);v.push(q*.72+(t?clamp(t/18,0,1)*.28:.14))}return weightedRate(v,w,.5)}
function roleProfileScore(p){p=p||{};var starts=n(p.starts);if(!starts)return.5;var sample=clamp(starts/40,0,1);var q=n(p.overall,.5)*.30+n(p.track,.5)*.28+n(p.distance,.5)*.24+n(p.condition,.5)*.18;return .5*(1-sample)+q*sample}
function genericRoleScore(stats){stats=stats||{};var st=n(stats.starts);if(!st)return.5;var pr=(n(stats.wins)+n(stats.seconds)+n(stats.thirds))/st;var sample=clamp(st/50,0,1);return .5*(1-sample)+clamp(pr/.45,0,1)*sample}
function courseTraits(r){var cp=courseProfile(r),d=n(r.distance,1200),short=d<=1400,veryShort=d<=1200,compact=(cp.shape==="compact"||cp.shape==="pocket"||cp.shape==="egg"||cp.shape==="spiral"),wide=(cp.shape==="long"||cp.shape==="wide"),straight=clamp(cp.straight/520,0,1),turnLoad=compact?.78:(cp.shape==="boxy"?.62:(wide?.34:.48)),frontBias=clamp(.44+(veryShort?.14:(short?.08:0))+turnLoad*.12-straight*.12,0,1),outerLoad=clamp((short?.20:.07)+turnLoad*.12-straight*.05,0,.38),moveRoom=clamp(.35+straight*.38+(wide?.10:0)-turnLoad*.10,0,1);return{frontBias:frontBias,outerLoad:outerLoad,moveRoom:moveRoom,turnLoad:turnLoad,straight:straight}}
function ageSexScore(h,r){var age=n(h.age),sex=String(h.sex||"");var x=.5;if(age>0){if(r.circuit==="中央"){if(age>=3&&age<=5)x=.58;else if(age===6)x=.51;else if(age>=7)x=.44}else{if(age>=3&&age<=7)x=.54;else if(age>=8)x=.49}}if(sex.indexOf("牝")>=0)x+=.005;return clamp(x,0,1)}
function weightScore(h){var rs=(h.recentRaces||[]).slice(0,3),vals=[],i;for(i=0;i<rs.length;i++)if(n(rs[i].carriedWeight)>0)vals.push(n(rs[i].carriedWeight));if(!vals.length||!n(h.carriedWeight))return.5;var avg=mean(vals),diff=n(h.carriedWeight)-avg;return clamp(.55-diff*.035,.28,.72)}
function conditionFit(h,r){var c=contextualRuns(h,r);return{track:listQuality(c.track,n(r.distance)),distance:listQuality(c.distance,n(r.distance)),condition:listQuality(c.condition,n(r.distance)),weather:listQuality(c.weather,n(r.distance)),season:listQuality(c.season,n(r.distance)),level:listQuality(c.level,n(r.distance)),counts:{track:c.track.length,distance:c.distance.length,condition:c.condition.length,weather:c.weather.length,season:c.season.length,level:c.level.length}}}
function confidenceBlend(score,count){var q=clamp(n(count)/3,0,1);return .5*(1-q)+score*q}
function buildRows(r){var hs=r.horses||[],tmp=[],speeds=[],prizes=[],i,h,rt,pt,sr,fit,ct=courseTraits(r),cp=courseProfile(r),field=Math.max(1,hs.length);for(i=0;i<hs.length;i++){h=hs[i];rt=styleRates(h,r);pt=rt.samples?stylePoint(rt):9;sr=speedRaw(h,n(r.distance));fit=conditionFit(h,r);var cf=rt.samples?rt.front:.08,cs=rt.samples?rt.stalk:.28,cm=rt.samples?rt.mid:.40,cc=rt.samples?rt.close:.24,ce=rt.samples?rt.early3:.24,cmo=rt.samples?rt.moved3:.08;tmp.push({horse:h,front:cf,stalk:cs,mid:cm,close:cc,rawFront:rt.front,rawStalk:rt.stalk,rawMid:rt.mid,rawClose:rt.close,early3:ce,moved3:cmo,styleSamples:rt.samples,styleUnknown:!rt.samples,ten:tenScore(h,r),fade:fadeRate(h),move:moveRate(h),hold:holdRate(h),yieldFlex:yieldFlex(h),breakRel:breakReliability(h),lateGain:lateGainScore(h),posCons:positionConsistency(h),collapse:earlyCollapseSeverity(h),score:pt,pastStyle:rt.samples?styleName(pt):"履歴なし",expected:rt.samples?styleName(pt):"不明",speedRaw:sr,fit:fit});speeds.push(sr);prizes.push(n(h.prizeMoneyAtRace))}
for(i=0;i<tmp.length;i++){var x=tmp[i],hh=x.horse,rf=recentFirst(hh),rd=recentDistance(hh),distChange=rd?rd-n(r.distance):0,shorten=distChange>=150?1:0,lengthen=distChange<=-150?1:0,no=n(hh.horseNumber),draw=(no-1)/Math.max(1,field-1),outer=draw>.70?1:0,edge=no===field?1:0,inner=draw<.28?1:0,recentEarly=(rf<99?clamp((8-rf)/7,0,1):.5),jp=hh.jockeyProfile||{},jockeyFront=n(jp.early3Rate,0),leadHabit=n(jp.leaderRate,0),needLead=clamp(x.front*.78+Math.max(0,x.front-x.stalk)*.48+leadHabit*.10,0,1),flexibility=clamp(x.yieldFlex*.58+x.stalk*.25+x.mid*.12+(1-needLead)*.05,0,1),shortenBoost=shorten*(x.front*.12+x.stalk*.08+x.ten*.07),lengthenBoost=lengthen*(x.stalk*.05+x.mid*.06),firstTurnRush=clamp(1-n(cp.firstTurn,300)/650,0,1),outerStress=outer*firstTurnRush*ct.turnLoad*(edge?.45:1),drawAdj=inner*ct.turnLoad*.055+edge*(1-ct.outerLoad)*.055-outerStress*.095,jf=hh.jockeyProfile?roleProfileScore(hh.jockeyProfile):genericRoleScore(hh.jockeyStats),tf=hh.trainerProfile?roleProfileScore(hh.trainerProfile):genericRoleScore(hh.trainerStats),trackFit=confidenceBlend(x.fit.track,x.fit.counts.track),distFit=confidenceBlend(x.fit.distance,x.fit.counts.distance),condFit=confidenceBlend(x.fit.condition,x.fit.counts.condition),weatherFit=confidenceBlend(x.fit.weather,x.fit.counts.weather),seasonFit=confidenceBlend(x.fit.season,x.fit.counts.season),levelFit=confidenceBlend(x.fit.level,x.fit.counts.level),speed=normalize(speeds,x.speedRaw),prize=normalize(prizes,n(hh.prizeMoneyAtRace)),baseAbility=recentFinishScore(hh)*.20+speed*.18+distFit*.11+trackFit*.08+condFit*.07+levelFit*.10+prize*.06+jf*.07+tf*.035+seasonFit*.02+weatherFit*.015+weightScore(hh)*.035+ageSexScore(hh,r)*.025+x.lateGain*.025,dataN=Math.min(8,(hh.recentRaces||[]).length),coverage=clamp(dataN/5,0,1)*.60+clamp((x.fit.counts.distance+x.fit.counts.track)/4,0,1)*.22+clamp(n(jp.starts)/30,0,1)*.18,frontIntent=clamp(x.front*.36+x.stalk*.17+x.ten*.18+x.early3*.10+jockeyFront*.07+leadHabit*.05+needLead*.07,0,1.25),goBase=clamp(frontIntent+shortenBoost+lengthenBoost+drawAdj,0,1.25);x.forward=frontIntent;x.goProbBase=clamp(goBase*.72+x.breakRel*.14+x.ten*.14,0,1);x.goProb=x.goProbBase;x.needLead=needLead;x.flexibility=flexibility;x.ability=clamp(baseAbility*.90+x.posCons*.035+(1-x.collapse)*.035+x.lateGain*.03,0,1);x.coverage=coverage;x.draw=draw;x.outer=outer;x.edge=edge;x.inner=inner;x.outerStress=outerStress;x.shorten=shorten;x.lengthen=lengthen;x.distanceChange=distChange;x.course=ct;x.jockeyFront=jockeyFront;x.stamina=clamp((1-x.fade)*.35+x.hold*.26+distFit*.15+x.posCons*.10+x.ability*.09+(rd>n(r.distance)?.05:0),0,1);x.holdFront=clamp(x.hold*.33+(1-x.fade)*.30+x.stamina*.15+x.ability*.12+distFit*.06+ct.frontBias*.04,0,1);x.latePower=clamp(x.lateGain*.28+x.move*.25+x.close*.14+x.mid*.07+x.ability*.18+(1-x.fade)*.08,0,1);x.turnSkill=clamp(trackFit*.22+x.move*.18+x.flexibility*.18+x.posCons*.16+(1-ct.turnLoad)*.06+x.ability*.20,0,1);x.breakSkill=clamp(x.breakRel*.32+x.ten*.30+x.goProbBase*.20+recentEarly*.10+jockeyFront*.08,0,1);x.trafficTol=clamp(x.flexibility*.34+x.move*.24+x.posCons*.18+x.turnSkill*.18+x.lateGain*.06,0,1)}
var p0=pressureInfo(tmp);for(i=0;i<tmp.length;i++){var y=tmp[i],q=p0[n(y.horse.horseNumber)]||{},pressurePenalty=(q.conflict||0)*(.055+.055*y.needLead)+(q.sandwich||0)*.075*(1-y.flexibility)+y.outerStress*.055;y.leftPressure=q.left||0;y.rightPressure=q.right||0;y.sandwichRisk=q.sandwich||0;y.frontCost=clamp(pressurePenalty,0,.28);y.goProb=clamp(y.goProbBase-pressurePenalty+(q.freeOuter||0)*.08,0,1);if(y.goProb>=.68&&y.front>=.16&&y.ten>=.55)y.expected="逃げ候補";else if(y.goProb>=.54)y.expected="先行";else if(y.goProb>=.40||y.stalk>=.32)y.expected="好位";else if(y.close>=.42&&y.mid<.36)y.expected="後方";else y.expected="中団";if(y.styleUnknown)y.expected="不明";y.frontStay=clamp(y.goProb*.34+y.holdFront*.34+(1-y.fade)*.12+y.ability*.12+y.course.frontBias*.08-y.frontCost*.30,0,1);y.comeFromBehind=clamp(y.latePower*.46+y.move*.20+y.ability*.16+y.course.moveRoom*.10+(1-y.goProb)*.08,0,1)}return tmp}
function rowByNo(rows,no){var i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===n(no))return rows[i];return null}
function pressureInfo(rows){var sorted=rows.slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)}),p={},i,x,l,r,lp,rp,base;function attack(z){if(!z)return 0;base=z.goProbBase!=null?z.goProbBase:z.goProb;return clamp(base*(.46+.34*z.needLead+.20*z.ten),0,1.2)}for(i=0;i<sorted.length;i++){x=sorted[i];l=i?sorted[i-1]:null;r=i<sorted.length-1?sorted[i+1]:null;lp=attack(l);rp=attack(r);var leftHot=lp>.50,rightHot=rp>.50,sandwich=leftHot&&rightHot?1:0,adj=(leftHot?1:0)+(rightHot?1:0),near2=0;if(i>1)near2+=attack(sorted[i-2])*.16;if(i<sorted.length-2)near2+=attack(sorted[i+2])*.16;var conflict=(lp+rp)*(.43+.38*x.needLead+.19*x.ten)*(1-.42*x.flexibility)+near2,freeOuter=x.edge&&adj===0?(.08+.08*x.flexibility):0;p[n(x.horse.horseNumber)]={adj:adj,sandwich:sandwich,conflict:clamp(conflict,0,1.6),freeOuter:freeOuter,left:lp,right:rp,leftHot:leftHot,rightHot:rightHot}}return p}
function scenarioModel(r,rows){var p=pressureInfo(rows),front=rows.slice().sort(function(a,b){return b.goProb-a.goProb}),active=front.filter(function(x){return x.goProb>.50}),lead=front.filter(function(x){return x.goProb>.60&&x.ten>.52}),top=active.slice(0,Math.min(5,active.length)),fade=top.length?mean(top.map(function(x){return x.fade})):0,hold=top.length?mean(top.map(function(x){return x.holdFront})):0,conf=top.length?mean(top.map(function(x){return (p[n(x.horse.horseNumber)]||{}).conflict||0})):0,sand=top.length?mean(top.map(function(x){return (p[n(x.horse.horseNumber)]||{}).sandwich||0})):0,outer=top.length?mean(top.map(function(x){return x.outerStress||0})):0,flex=top.length?mean(top.map(function(x){return x.flexibility})):0,ct=rows.length?rows[0].course:courseTraits(r),clear=front.length>1?clamp((front[0].goProb-front[1].goProb)*1.8+front[0].holdFront*.10+(front[0].edge?0.04:0),0,.42):.25,adjPairs=0,i,j;for(i=0;i<active.length;i++)for(j=i+1;j<active.length;j++)if(Math.abs(n(active[i].horse.horseNumber)-n(active[j].horse.horseNumber))===1)adjPairs+=active[i].needLead*active[j].needLead;var adjDensity=active.length>1?clamp(adjPairs/(active.length-1),0,1):0,leadCount=lead.length,frontVolume=clamp(active.length/Math.max(1,rows.length),0,1),A=.29+ct.frontBias*.23+clear*.23+hold*.15+(1-fade)*.07+(1-clamp(conf,0,1))*.05-flex*.015,C=.18+(1-ct.frontBias)*.10+ct.moveRoom*.10+fade*.19+clamp(conf,0,1)*.13+sand*.10+adjDensity*.08+outer*.06+Math.max(0,leadCount-1)*.025,B=.34+flex*.07+(1-Math.abs(A-C))*.035;C+=Math.max(0,frontVolume-.45)*.055;A+=leadCount===1?.035:0;A=clamp(A,.15,.68);B=clamp(B,.20,.50);C=clamp(C,.12,.58);var sum=A+B+C;A/=sum;B/=sum;C/=sum;return[{code:"A",title:"前残り",prob:A},{code:"B",title:"平均",prob:B},{code:"C",title:"前崩れ・差し届く",prob:C}]}
function startOrder(rows){var p=pressureInfo(rows);return rows.slice().sort(function(a,b){function s(x){var q=p[n(x.horse.horseNumber)]||{};return x.goProb+x.needLead*.12+(q.freeOuter||0)-q.conflict*.035}return s(b)-s(a)||n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function scenarioSuit(x,code,pressure){var q=pressure[n(x.horse.horseNumber)]||{},earlyCost=(q.conflict||0)*x.goProb*(.34+.42*x.needLead)*(1-.34*x.flexibility)+x.outerStress*.06,frontStay=x.goProb*.27+x.holdFront*.31+(1-x.fade)*.12+x.ability*.18+x.stamina*.07+x.course.frontBias*.05-earlyCost*.16,balanced=x.ability*.34+x.holdFront*.14+x.latePower*.13+x.move*.10+x.stamina*.10+x.goProb*.08+x.flexibility*.06+(1-x.fade)*.05,close=x.ability*.27+x.latePower*.28+x.move*.17+x.mid*.08+x.close*.09+x.course.moveRoom*.07+x.trafficTol*.06-x.goProb*.02;if(code==="A")return clamp(frontStay,0,1.25);if(code==="C")return clamp(close,0,1.25);return clamp(balanced,0,1.25)}
function suitability(rows,sc){var out={},pressure=pressureInfo(rows),i,x,win,place,show,j,q,scenarioScores=[];for(i=0;i<rows.length;i++){x=rows[i];win=place=show=0;scenarioScores=[];for(j=0;j<sc.length;j++){q=scenarioSuit(x,sc[j].code,pressure);scenarioScores.push({code:sc[j].code,score:q});win+=sc[j].prob*(q*.72+x.ability*.20+x.hold*.08);place+=sc[j].prob*(q*.57+x.ability*.20+(1-x.fade)*.13+x.flexibility*.06+x.hold*.04);show+=sc[j].prob*(q*.46+x.ability*.20+(1-x.fade)*.14+x.move*.09+x.flexibility*.06+x.hold*.05)}var overall=win*.54+place*.29+show*.17;out[n(x.horse.horseNumber)]={win:win,place:place,show:show,overall:overall,rankScore:win*.62+place*.24+show*.14,scenario:scenarioScores}}return out}
function cornerScores(r,rows,sc,suit){var pressure=pressureInfo(rows),top=sc.slice().sort(function(a,b){return b.prob-a.prob})[0].code,out=[],i,x,z,q,s,earlyCost;for(i=0;i<rows.length;i++){x=rows[i];z=suit[n(x.horse.horseNumber)]||{overall:.5};q=pressure[n(x.horse.horseNumber)]||{};earlyCost=q.conflict*x.goProb*(.4+.4*x.needLead);s=x.goProb*.25+x.hold*.20+x.ability*.21+x.move*.11+(1-x.fade)*.11+z.overall*.12-earlyCost*.10;if(top==="A")s+=x.goProb*.11+x.hold*.07;if(top==="C")s+=x.move*.12+x.mid*.06+x.close*.08-x.goProb*.02;out.push({row:x,s:s})}return out.sort(function(a,b){return b.s-a.s}).map(function(z){return z.row})}
function seedHash(v){var s=String(v||"race"),h=2166136261,i;for(i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function prng(seed){var a=seed>>>0;return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function jitter(rng){return(rng()+rng()+rng()+rng()+rng()+rng()-3)/3}
function chooseScenario(sc,rng){var u=rng(),c=0,i;for(i=0;i<sc.length;i++){c+=sc[i].prob;if(u<=c)return sc[i].code}return sc.length?sc[sc.length-1].code:"B"}
function packStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,visualRankGap,scoreGap,lane,cp=courseProfile(r);for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);visualRankGap=(stage<2?.0048:(stage<5?.0065:.0085))*i;scoreGap=diff*(stage<2?.030:(stage<5?.043:.060));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&visualRankGap<.02)lane+=((i%3)-1);out.push({no:no,gap:clamp(visualRankGap+scoreGap,0,.42),lane:clamp(lane,-3,3)})}return out}
function stageMap(pack){var o={},i;for(i=0;i<pack.length;i++)o[pack[i].no]=pack[i];return o}
function stageByNo(pack,no){for(var i=0;i<pack.length;i++)if(n(pack[i].no)===n(no))return pack[i];return null}
function simulateOne(r,rows,sc,suit,seed){var rng=prng(seed),code=chooseScenario(sc,rng),pressure=pressureInfo(rows),cp=courseProfile(r),ct=courseTraits(r),dist=n(r.distance,1200),distanceLoad=clamp((dist-1000)/1800,0,1),firstTurnRush=clamp(1-n(cp.firstTurn,300)/650,0,1),paceHeat=0,i,x,no,q,noise;var S0={},S1={},S2={},S3={},S4={},S5={},S6={},S7={},L0={},L1={},L2={},L3={},L4={},L5={},L6={},L7={},energy={};
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);S0[no]=x.breakSkill*.50+x.goProb*.30+x.needLead*.08+x.jockeyFront*.05+(q.freeOuter||0)-q.conflict*.035+noise*.07;L0[no]=clamp(Math.round((x.draw-.5)*5),-3,3);energy[no]=1;if(x.goProb>.50)paceHeat+=x.goProb*(.45+.55*x.needLead)}
paceHeat=clamp((paceHeat-1.10)/Math.max(.8,rows.length*.18),0,1.55);
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var rushCost=(q.conflict||0)*(.08+.11*x.needLead)+paceHeat*x.goProb*.045+firstTurnRush*x.outer*.045;energy[no]-=rushCost;S1[no]=S0[no]*.56+x.goProb*.20+x.breakSkill*.10+x.flexibility*.05-x.collapse*.035-rushCost*.22+noise*.065;L1[no]=clamp(L0[no]+(x.edge&&x.goProb>.55?-1:0)+(q.sandwich&&x.flexibility<.45?1:0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var turnCost=Math.abs(L1[no])*.012*ct.turnLoad+x.outer*firstTurnRush*.025+(q.sandwich||0)*(.035-.020*x.trafficTol);energy[no]-=turnCost;S2[no]=S1[no]*.48+x.hold*.16+x.turnSkill*.12+x.ability*.12+x.flexibility*.06-turnCost*.32+noise*.06;L2[no]=clamp(L1[no]+(x.inner&&x.goProb<.35?0:Math.round((x.flexibility-.5)*-1)),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var draft=(x.stalk*.045+x.mid*.025)*(1-x.needLead),leaderDrain=paceHeat*x.goProb*(.045+.055*x.needLead)*(1+.45*distanceLoad);energy[no]-=leaderDrain;S3[no]=S2[no]*.43+x.ability*.18+x.hold*.13+x.stamina*.10+draft+x.move*.05+noise*.065;L3[no]=clamp(L2[no]+(x.move>.45&&x.goProb<.45?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var moveKick=x.move*(.08+.07*ct.moveRoom)+x.latePower*.055,wideCost=Math.max(0,Math.abs(L3[no])-1)*.018*ct.turnLoad;energy[no]-=wideCost;S4[no]=S3[no]*.42+x.ability*.17+x.stamina*.12+x.turnSkill*.09+moveKick-wideCost*.30+noise*.07;L4[no]=clamp(L3[no]+(x.move>.50?Math.round((rng()-.42)*2):0),-3,3)}
var pack4=packStage(r,rows,S4,L4,4),map4=stageMap(pack4);
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var pos4=map4[no]||{gap:.2,lane:0},blocked=0;if(pos4.gap>.025&&Math.abs(pos4.lane)<=1&&x.trafficTol<.55&&rng()>.48)blocked=(.02+.06*(1-x.trafficTol));var scFit=scenarioSuit(x,code,pressure),fatigue=(1-energy[no])*.16+x.collapse*.07+paceHeat*x.goProb*.035*distanceLoad;S5[no]=S4[no]*.37+scFit*.16+x.ability*.15+x.stamina*.11+x.turnSkill*.07+x.latePower*.07-blocked-fatigue+noise*.075;L5[no]=clamp(L4[no]+(blocked>0?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);noise=jitter(rng);var straightBoost=x.latePower*(.10+.12*ct.straight)+x.move*.055*ct.moveRoom,frontKick=(code==="A"?x.goProb*.055+x.hold*.035:0),closeKick=(code==="C"?x.close*.07+x.move*.055:0),fatigue2=(1-energy[no])*.12+x.fade*.08;S6[no]=S5[no]*.34+x.ability*.20+x.stamina*.12+straightBoost+frontKick+closeKick-fatigue2+noise*.085;L6[no]=clamp(L5[no]+(x.latePower>.58&&Math.abs(L5[no])<3?(rng()>.5?1:-1):0),-3,3)}
for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=pressure[no]||{};noise=jitter(rng);var suitx=suit[no]||{overall:.5},uncert=(1-x.coverage)*.070*jitter(rng);S7[no]=S6[no]*.34+suitx.overall*.24+x.ability*.18+x.latePower*.10+x.stamina*.08+(1-x.fade)*.05-q.conflict*.015+noise*.09+uncert;L7[no]=L6[no]}
var packs=[packStage(r,rows,S0,L0,0),packStage(r,rows,S1,L1,1),packStage(r,rows,S2,L2,2),packStage(r,rows,S3,L3,3),packStage(r,rows,S4,L4,4),packStage(r,rows,S5,L5,5),packStage(r,rows,S6,L6,6),packStage(r,rows,S7,L7,7)],maps=packs.map(stageMap),finish=packs[7];return{scenario:code,checkpoints:packs,maps:maps,start:packs[1],corner:packs[5],finish:finish,startMap:maps[1],cornerMap:maps[5],finishMap:maps[7],podium:finish.slice(0,3).map(function(z){return z.no}),paceHeat:paceHeat}}
function generateSimulations(r,rows,sc,suit,count){var runs=[],stats={},scenarioCount={A:0,B:0,C:0},combo={},i,j,no,run,key;for(i=0;i<rows.length;i++){no=n(rows[i].horse.horseNumber);stats[no]={horse:rows[i].horse,win:0,second:0,third:0,top3:0,startRank:0,cornerRank:0,finishRank:0}}var base=seedHash([r.id,r.date,r.track,r.raceNumber,r.distance,(r.horses||[]).length].join("|"));for(i=0;i<count;i++){run=simulateOne(r,rows,sc,suit,(base+Math.imul(i+1,2654435761))>>>0);runs.push(run);scenarioCount[run.scenario]=(scenarioCount[run.scenario]||0)+1;key=run.podium.join("-");combo[key]=(combo[key]||0)+1;for(j=0;j<run.start.length;j++)stats[run.start[j].no].startRank+=j+1;for(j=0;j<run.corner.length;j++)stats[run.corner[j].no].cornerRank+=j+1;for(j=0;j<run.finish.length;j++)stats[run.finish[j].no].finishRank+=j+1;if(run.podium[0]){stats[run.podium[0]].win++;stats[run.podium[0]].top3++}if(run.podium[1]){stats[run.podium[1]].second++;stats[run.podium[1]].top3++}if(run.podium[2]){stats[run.podium[2]].third++;stats[run.podium[2]].top3++}}var summary=Object.keys(stats).map(function(k){var z=stats[k];z.no=n(k);z.winRate=z.win/count;z.secondRate=z.second/count;z.thirdRate=z.third/count;z.top3Rate=z.top3/count;z.avgStart=z.startRank/count;z.avgCorner=z.cornerRank/count;z.avgFinish=z.finishRank/count;z.markScore=z.winRate*.53+z.secondRate*.24+z.thirdRate*.13+z.top3Rate*.10;return z}).sort(function(a,b){return b.markScore-a.markScore||a.avgFinish-b.avgFinish});var first=summary[0]||null,rest=summary.slice(1),second=rest.slice().sort(function(a,b){return b.secondRate-a.secondRate||b.top3Rate-a.top3Rate})[0]||summary[1]||null,thirdPool=summary.filter(function(z){return(!first||z.no!==first.no)&&(!second||z.no!==second.no)}),third=thirdPool.slice().sort(function(a,b){return b.thirdRate-a.thirdRate||b.top3Rate-a.top3Rate})[0]||summary[2]||null,podium=[first,second,third].filter(Boolean),exact=0,setHit=0,target=podium.map(function(z){return z.no}),targetKey=target.join("-");exact=combo[targetKey]||0;for(i=0;i<runs.length;i++){var a=runs[i].podium.slice().sort(function(a,b){return a-b}),b=target.slice().sort(function(a,b){return a-b});if(a.length===b.length&&a.join("-")===b.join("-"))setHit++}return{count:count,runs:runs,summary:summary,podium:podium,exactRate:exact/count,setRate:setHit/count,scenarioCount:scenarioCount}}
function avgOrder(rows,sim,key){var prop=key==="start"?"avgStart":(key==="corner"?"avgCorner":"avgFinish"),sm={};for(var i=0;i<sim.summary.length;i++)sm[sim.summary[i].no]=sim.summary[i][prop];return rows.slice().sort(function(a,b){return sm[n(a.horse.horseNumber)]-sm[n(b.horse.horseNumber)]})}
function packScenarioStage(r,rows,scoreMap,laneMap,stage){var a=rows.slice().sort(function(x,y){return scoreMap[n(y.horse.horseNumber)]-scoreMap[n(x.horse.horseNumber)]||n(x.horse.horseNumber)-n(y.horse.horseNumber)}),lead=a.length?scoreMap[n(a[0].horse.horseNumber)]:0,out=[],i,x,no,diff,rankGap,scoreGap,lane;for(i=0;i<a.length;i++){x=a[i];no=n(x.horse.horseNumber);diff=Math.max(0,lead-scoreMap[no]);rankGap=(stage<=1?.010:(stage<=3?.013:.016))*i;scoreGap=diff*(stage<=1?.06:(stage<=3?.08:.10));lane=laneMap&&laneMap[no]!=null?laneMap[no]:Math.round((x.draw-.5)*4);if(i>0&&i%3===0)lane+=1;if(i>0&&i%4===0)lane-=1;out.push({no:no,gap:clamp(rankGap+scoreGap,0,.34),lane:clamp(lane,-3,3),score:scoreMap[no]})}return out}
function rowsFromPack(rows,pack){var map={};for(var i=0;i<rows.length;i++)map[n(rows[i].horse.horseNumber)]=rows[i];return pack.map(function(z){return map[n(z.no)]}).filter(Boolean)}
function scenarioPlan(r,rows,sc,suit){var scenario=sc.slice().sort(function(a,b){return b.prob-a.prob})[0],code=scenario.code,p=pressureInfo(rows),ct=courseTraits(r),S=[{},{},{},{},{},{}],L=[{},{},{},{},{},{}],i,x,no,q,scfit,markScore={},leadLoad;for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);q=p[no]||{};leadLoad=x.goProb*(.045+.055*x.needLead)+x.frontCost*.13;S[0][no]=x.breakSkill*.26+x.ten*.26+x.goProb*.27+x.needLead*.08+x.jockeyFront*.05+(q.freeOuter||0)*.06-x.frontCost*.10;L[0][no]=clamp(Math.round((x.draw-.5)*5),-3,3);S[1][no]=S[0][no]*.40+x.goProb*.17+x.holdFront*.13+x.turnSkill*.11+x.flexibility*.06+x.ability*.08-x.frontCost*.09-x.outerStress*.05;L[1][no]=clamp(L[0][no]+(x.edge&&x.goProb>.55?-1:0)+(q.sandwich&&x.flexibility<.45?1:0),-3,3);scfit=scenarioSuit(x,code,p);S[2][no]=S[1][no]*.31+x.ability*.16+x.holdFront*.15+x.stamina*.13+x.stalk*.07+x.mid*.04+scfit*.11-(code==='C'?leadLoad*.12:leadLoad*.05)+(code==='A'?x.goProb*.06:0);L[2][no]=clamp(L[1][no]+(x.move>.52&&x.goProb<.46?1:0),-3,3);S[3][no]=S[2][no]*.27+x.ability*.16+x.move*.16+x.turnSkill*.11+scfit*.14+x.latePower*.09+x.holdFront*.04-(x.fade*x.goProb)*(code==='C'?.09:.04);L[3][no]=clamp(L[2][no]+(x.move>.56?1:0),-3,3);S[4][no]=S[3][no]*.24+scfit*.20+x.ability*.18+x.holdFront*.11+x.move*.10+x.latePower*.10+(1-x.fade)*.05-(q.sandwich||0)*.025;L[4][no]=clamp(L[3][no]+(x.latePower>.61?1:0),-3,3);var su=suit[no]||{rankScore:.5};markScore[no]=S[4][no]*.31+su.rankScore*.42+x.ability*.10+x.latePower*.08+x.stamina*.05+x.coverage*.02+(1-x.fade)*.02;if(code==='A')markScore[no]+=x.frontStay*.045;if(code==='C')markScore[no]+=x.comeFromBehind*.045;S[5][no]=markScore[no];L[5][no]=L[4][no]}var labels=['スタート','1コーナー','向正面','3コーナー','4コーナー','直線'],packs=[],stages=[];for(i=0;i<6;i++){packs[i]=packScenarioStage(r,rows,S[i],L[i],i);stages.push({key:['start','first','back','turn3','turn4','straight'][i],label:labels[i],pack:packs[i]})}return{scenario:scenario,stages:stages,start:rowsFromPack(rows,packs[0]),corner:rowsFromPack(rows,packs[4]),straight:rowsFromPack(rows,packs[5]),markScore:markScore}}
function gradeClass(g){return g==='S'?'grade-s':(g==='A'?'grade-a':(g==='B'?'grade-b':(g==='C'?'grade-c':'grade-hold')))}
function assignOverallGrades(rows,suit,sc,pressure){var eligible=[],i,x,no,su,cnt,fitVals,fitScore,raw;for(i=0;i<rows.length;i++){x=rows[i];no=n(x.horse.horseNumber);su=suit[no]||{overall:.5};cnt=x.fit&&x.fit.counts||{};fitVals=[];if(n(cnt.distance))fitVals.push(confidenceBlend(x.fit.distance,cnt.distance));if(n(cnt.track))fitVals.push(confidenceBlend(x.fit.track,cnt.track));if(n(cnt.condition))fitVals.push(confidenceBlend(x.fit.condition,cnt.condition));fitScore=fitVals.length?mean(fitVals):.5;raw=x.ability*.29+n(su.overall,.5)*.27+Math.max(x.frontStay,x.comeFromBehind)*.13+fitScore*.10+x.stamina*.06+(1-x.fade)*.05+x.posCons*.04+x.coverage*.06;raw=clamp(raw,0,1);x.overallRaw=raw;x.overallReasons=[];if((x.horse.recentRaces||[]).length<2||x.styleSamples<2){x.overallGrade='保留';x.overallScore=null;x.overallReasons=['実データ不足'];continue}if(x.ability>=.62)x.overallReasons.push('能力評価高め');if(n(su.overall)>=.62)x.overallReasons.push('展開適性高め');if(x.frontStay>=.64)x.overallReasons.push('前残り力');if(x.comeFromBehind>=.64)x.overallReasons.push('差し込み力');if(x.fade<=.25)x.overallReasons.push('下がり率低め');if(fitVals.length&&fitScore>=.58)x.overallReasons.push('今回条件に実績');if(x.frontCost>=.12)x.overallReasons.push('隣接圧力注意');if(x.fade>=.50)x.overallReasons.push('下がり率注意');if(x.coverage<.45)x.overallReasons.push('データ量少なめ');eligible.push(x)}if(!eligible.length)return;var lo=Math.min.apply(null,eligible.map(function(z){return z.overallRaw})),hi=Math.max.apply(null,eligible.map(function(z){return z.overallRaw}));eligible.forEach(function(z){var rel=hi===lo?.5:(z.overallRaw-lo)/(hi-lo);z.overallScore=Math.round(clamp(z.overallRaw*.78+(.45+.55*rel)*.22,0,1)*100)});eligible.sort(function(a,b){return b.overallScore-a.overallScore||b.ability-a.ability||n(a.horse.horseNumber)-n(b.horse.horseNumber)});var m=eligible.length;eligible.forEach(function(z,rank){var pct=(rank+1)/m,score=z.overallScore;if((score>=82)||(pct<=.12&&score>=70))z.overallGrade='S';else if((score>=72)||(pct<=.35&&score>=64))z.overallGrade='A';else if((score>=60)||(pct<=.70))z.overallGrade='B';else z.overallGrade='C';if(!z.overallReasons.length)z.overallReasons.push('総合バランス型')})}
function assignPredictionMarks(rows){var syms=["◎","○","▲","☆","△","注"],eligible=rows.filter(function(x){return x.overallScore!=null&&x.overallGrade!=="保留"}).slice().sort(function(a,b){return n(b.overallScore)-n(a.overallScore)||n(b.ability)-n(a.ability)||n(a.horse.horseNumber)-n(b.horse.horseNumber)});rows.forEach(function(x){x.predMark=""});eligible.slice(0,syms.length).forEach(function(x,i){x.predMark=syms[i]})}
function predict(r){var rows=buildRows(r),occ=earlyOcc(r),sc=scenarioModel(r,rows),suit=suitability(rows,sc),pressure=pressureInfo(rows),plan=scenarioPlan(r,rows,sc,suit),i;assignOverallGrades(rows,suit,sc,pressure);assignPredictionMarks(rows);for(i=0;i<sc.length;i++){var code=sc[i].code,candidates=rows.slice().sort(function(a,b){return scenarioSuit(b,code,pressure)-scenarioSuit(a,code,pressure)});sc[i].horses=candidates.slice(0,3).map(function(x){return x.horse})}var cov=mean(rows.map(function(x){return x.coverage}));return{rows:rows,occ:occ,scenarios:sc,plan:plan,suit:suit,coverage:cov,pressure:pressure}}
function nextRace(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime});a.sort(function(x,y){var ax=mins(x.startTime),ay=mins(y.startTime),now=nowMins(),kx=ax>=now?ax:ax+1440,ky=ay>=now?ay:ay+1440;return kx-ky});return a.length?a[0]:null}
function liveRaces(){if(state.date!==today())return[];var now=nowMins(),a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.startTime&&mins(r.startTime)>=now-25});a.sort(function(x,y){return mins(x.startTime)-mins(y.startTime)});return a.slice(0,4)}
function liveTag(r){var d=mins(r.startTime)-nowMins();if(d<0&&d>=-25)return'<span class="live-tag running">進行中</span>';if(d>=0&&d<=10)return'<span class="live-tag now">まもなく</span>';return'<span class="live-tag">次走</span>'}
function homeVenueMark(track){var t=String(track||"?");return '<span class="venue-mark">'+esc(t.slice(0,1))+'</span>'}
function horseBodyWeightText(h){var raw=h&&h.bodyWeight!=null&&h.bodyWeight!==''?h.bodyWeight:(h&&h.horseWeight!=null&&h.horseWeight!==''?h.horseWeight:(h&&h.currentBodyWeight!=null&&h.currentBodyWeight!==''?h.currentBodyWeight:'')),chg=h&&h.bodyWeightChange!=null&&h.bodyWeightChange!==''?h.bodyWeightChange:(h&&h.weightChange!=null&&h.weightChange!==''?h.weightChange:(h&&h.weightDiff!=null&&h.weightDiff!==''?h.weightDiff:null));if(raw===''||raw==null)return'';var s=String(raw);if(/^-?\d+(\.\d+)?$/.test(s))s+='kg';if(chg!=null&&chg!==''&&!/[()]/.test(s)){var c=n(chg);s+=c>0?' (+'+c+')':' ('+c+')'}return s}
function markStoreKey(r,no){return'keiba:v60:mark:'+[(r&&r.circuit)||'',(r&&r.date)||'',(r&&r.track)||'',(r&&r.raceNumber)||'',no||''].join('|')}
function rowMark(r,row){var v=null;try{v=localStorage.getItem(markStoreKey(r,row&&row.horse?row.horse.horseNumber:''))}catch(e){}if(v===null)return row&&row.predMark?row.predMark:'';return v==='__EMPTY__'?'':v}
function cycleMark(no){if(!state.race||!state.pred)return;var row=rowByNo(state.pred.rows,no);if(!row)return;var cur=rowMark(state.race,row),order=['','◎','○','▲','△','☆','注'],idx=order.indexOf(cur);if(idx<0)idx=0;var nxt=order[(idx+1)%order.length];try{localStorage.setItem(markStoreKey(state.race,no),nxt?nxt:'__EMPTY__')}catch(e){}render()}
function sortedHorseRows(rows){return(rows||[]).slice().sort(function(a,b){return n(a.horse.horseNumber)-n(b.horse.horseNumber)})}
function openHorseModal(no){state.horseModalNo=n(no,0)||null;render()}
function closeHorseModal(){state.horseModalNo=null;render()}
function moveHorseModal(dir){if(!state.pred||!state.pred.rows||!state.pred.rows.length)return;var rows=sortedHorseRows(state.pred.rows),cur=n(state.horseModalNo,0),idx=0,i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===cur){idx=i;break}idx=(idx+(dir>0?1:-1)+rows.length)%rows.length;state.horseModalNo=n(rows[idx].horse.horseNumber);render()}
function runnerDetailBody(r,p,x){var h=x.horse,fit=x.fit||{},cnt=fit.counts||{},j=h.jockeyProfile||{},t=h.trainerProfile||{},fade=x.styleSamples?Math.round(x.fade*100):null,q=p.pressure&&p.pressure[n(h.horseNumber)]||{};function fitVal(k){return Math.round(confidenceBlend(fit[k],cnt[k])*100)}function fitText(k){return n(cnt[k])?fitVal(k)+' / '+n(cnt[k])+'走':'— / 0走'}var recent=(h.recentRaces||[]).slice(0,5),distTxt=x.shorten?'短縮 '+Math.abs(x.distanceChange)+'m':(x.lengthen?'延長 '+Math.abs(x.distanceChange)+'m':'同距離帯'),pressureTxt=(q.sandwich?'逃げハサミ警戒':((q.leftHot||q.rightHot)?'逃げ横あり':'隣接圧力弱め')),reasons=(x.overallReasons||[]),manualMark=rowMark(r,x),bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明';return'<div class="horse-detail"><div class="runner-overall-box"><div class="runner-overall-head"><span class="label">AI総合評価</span><strong class="overall-grade '+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'保留')+'</strong><span class="runner-overall-mark">'+esc(manualMark||x.predMark||'—')+'</span><span class="runner-overall-score">総合 '+(x.overallScore==null?'—':esc(x.overallScore))+'</span></div>'+(reasons.length?'<div class="overall-reasons">'+reasons.map(function(z){var warn=String(z).indexOf('注意')>=0||String(z).indexOf('不足')>=0;return'<i class="'+(warn?'warn':'good')+'">'+esc(z)+'</i>'}).join('')+'</div>':'')+'</div><div class="detail-heading">基本情報</div><div class="horse-info-grid"><div class="horse-info-cell"><small>馬番 / 枠</small><b>'+esc(h.horseNumber)+'番 / '+esc(h.frameNumber||frame(h))+'枠</b></div><div class="horse-info-cell"><small>性齢 / 斤量</small><b>'+esc(h.sex||'—')+esc(h.age||'—')+' / '+esc(h.carriedWeight||'—')+'kg</b></div><div class="horse-info-cell"><small>脚質</small><b>'+esc(styleTxt)+'</b></div><div class="horse-info-cell"><small>騎手</small><b>'+esc(h.jockey||'—')+'</b></div><div class="horse-info-cell"><small>調教師</small><b>'+esc(h.trainer||'—')+'</b></div><div class="horse-info-cell"><small>馬体重</small><b>'+(bodyTxt?esc(bodyTxt):'—')+'</b></div><div class="horse-info-cell"><small>当時獲得賞金</small><b>'+((h.recentRaces||[]).length||n(h.prizeMoneyAtRace)>0?fmtMoney(h.prizeMoneyAtRace)+'円':'—')+'</b></div><div class="horse-info-cell"><small>今回の位置想定</small><b>'+esc(x.pastStyle)+' → '+esc(x.expected)+'</b></div><div class="horse-info-cell"><small>距離変更</small><b>'+esc(distTxt)+'</b></div><div class="horse-info-cell"><small>前走の前進区分</small><b>'+esc(firstThreeType(h))+'</b></div></div><div class="detail-heading">脚質詳細</div><div class="runner-detail-scores"><div class="runner-detail-score"><small>脚質点</small><b>'+(x.styleSamples?x.score.toFixed(2):'—')+'</b></div><div class="runner-detail-score"><small>前へ行く</small><b>'+(x.styleSamples?Math.round(x.goProb*100)+'%':'—')+'</b></div><div class="runner-detail-score"><small>テン</small><b>'+(x.styleSamples?Math.round(x.ten*100)+'%':'—')+'</b></div><div class="runner-detail-score"><small>前残り力</small><b>'+(x.styleSamples?Math.round(x.frontStay*100)+'%':'—')+'</b></div></div><div class="detail-heading">今回の位置取り診断</div><div class="pressure-grid"><div class="pressure-chip '+(q.leftHot?'danger':'safe')+'"><small>内隣圧力</small><b>'+Math.round(n(q.left)*100)+'%</b></div><div class="pressure-chip '+(q.rightHot?'danger':'safe')+'"><small>外隣圧力</small><b>'+Math.round(n(q.right)*100)+'%</b></div><div class="pressure-chip '+(q.sandwich?'danger':'')+'"><small>逃げハサミ</small><b>'+(q.sandwich?'成立警戒':'なし')+'</b></div><div class="pressure-chip"><small>判定</small><b>'+esc(pressureTxt)+'</b></div><div class="pressure-chip"><small>最初から3番手内</small><b>'+(x.styleSamples?Math.round(x.early3*100)+'%':'—')+'</b></div><div class="pressure-chip"><small>途中から3番手内</small><b>'+(x.styleSamples?Math.round(x.moved3*100)+'%':'—')+'</b></div><div class="pressure-chip"><small>差し上げ力</small><b>'+Math.round(x.comeFromBehind*100)+'</b></div><div class="pressure-chip"><small>下がり率</small><b>'+(fade==null?'—':fade+'%')+'</b></div></div><div class="detail-heading">今回条件への適性</div><div class="fit-grid"><div class="fit-chip"><small>距離</small><b>'+fitText('distance')+'</b></div><div class="fit-chip"><small>競馬場</small><b>'+fitText('track')+'</b></div><div class="fit-chip"><small>馬場</small><b>'+fitText('condition')+'</b></div><div class="fit-chip"><small>天候</small><b>'+fitText('weather')+'</b></div><div class="fit-chip"><small>季節</small><b>'+fitText('season')+'</b></div><div class="fit-chip"><small>相手レベル</small><b>'+fitText('level')+'</b></div></div>'+roleDetail('騎手成績',h.jockeyStats,j)+roleDetail('調教師成績',h.trainerStats,t)+'<div class="recent-list-title">近走データ（直近5走）</div>'+(recent.length?recent.map(function(rr){var rid=rr.raceId||((r.circuit==='地方'&&rr.date&&rr.track&&n(rr.raceNumber))?('nar-'+rr.date+'-'+rr.track+'-'+String(n(rr.raceNumber)).padStart(2,'0')):'');return'<div class="recent"><div class="recent-head"><b>'+esc(rr.date)+' '+esc(rr.track)+' '+(n(rr.raceNumber)?esc(rr.raceNumber)+'R ':'')+esc(rr.distance)+'m</b><strong>'+esc(rr.finish||'—')+'着</strong></div><div>'+fmtTime(rr.timeSeconds)+'　'+esc(rr.condition||'不明')+' / '+esc(rr.weather||'不明')+'</div><div class="muted">'+(rr.title?esc(rr.title)+'　':'')+'通過 '+esc((rr.cornerPositions||[]).join('-')||'—')+'　頭数 '+esc(rr.fieldSize||'—')+(n(rr.carriedWeight)>0?'　斤量 '+esc(rr.carriedWeight)+'kg':'')+(n(rr.racePrize1)>0?'　1着賞金 '+fmtMoney(rr.racePrize1):'')+(rr.jockey?'　騎手 '+esc(rr.jockey):'')+(rr.trainer?'　調教師 '+esc(rr.trainer):'')+'</div>'+(rid?'<button type="button" class="recent-open" data-past-race="'+esc(rid)+'">この過去レースを見る</button>':'')+'</div>'}).join(''):'<div class="empty compact">過去データを確認できませんでした</div>')+'</div>'}
function horseModal(r,p){var no=n(state.horseModalNo,0);if(!no)return'';var rows=sortedHorseRows(p.rows),idx=-1,i;for(i=0;i<rows.length;i++)if(n(rows[i].horse.horseNumber)===no){idx=i;break}if(idx<0)return'';var x=rows[idx],h=x.horse,bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明',manualMark=rowMark(r,x);return'<div class="horse-modal-layer"><div class="horse-modal-backdrop" data-horse-close="1"></div><section class="horse-modal" role="dialog" aria-modal="true"><div class="horse-modal-head"><button type="button" class="horse-modal-nav" data-horse-prev="1">‹</button><div class="horse-modal-title"><div class="horse-modal-title-top">'+badge(h)+'<div style="min-width:0"><div class="horse-modal-name">'+esc(h.name)+'</div>'+(bodyTxt?'<div class="runner-weight-inline">('+esc(bodyTxt)+')</div>':'')+'</div></div><div class="horse-modal-meta"><span>'+esc(h.sex||'—')+esc(h.age||'—')+'</span><span>'+esc(styleTxt)+'</span><span>'+esc(h.jockey||'騎手不明')+'</span><span>'+esc(h.carriedWeight||'—')+'kg</span></div><div class="horse-modal-sidechips"><span class="horse-modal-chip grade">総合評価 '+esc(x.overallGrade||'保留')+'</span><span class="horse-modal-chip">総合点 '+(x.overallScore==null?'—':esc(x.overallScore))+'</span><span class="horse-modal-chip mark">印 '+esc(manualMark||x.predMark||'—')+'</span></div><div class="horse-modal-counter">'+(idx+1)+' / '+rows.length+' 頭</div></div><button type="button" class="horse-modal-nav" data-horse-next="1">›</button><button type="button" class="horse-modal-close" data-horse-close="1">×</button></div><div class="horse-modal-swipe">← 横スワイプで前後の馬へ切替 →</div><div id="horse-modal-panel" class="horse-modal-body">'+runnerDetailBody(r,p,x)+'</div></section></div>'}
function miniPacePreview(r){return '<div class="home-ai-preview-photo mini-flow-demo"><div class="mini-flow-axis"><span>← 後方</span><b>隊列イメージ</b><span>前方 →</span></div><div class="mini-flow-line"></div><i class="mini-flow-dot d1">1</i><i class="mini-flow-dot d2">4</i><i class="mini-flow-dot d3">7</i><i class="mini-flow-dot d4">10</i><div class="mini-flow-caption">写真背景なし・右が前</div></div>'}
function renderHome(){var all=state.circuit==="中央"?CENTRAL:LOCAL,venues=[],i,t,c;for(i=0;i<all.length;i++){t=all[i];c=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===t}).length;if(c)venues.push([t,c])}
var live=liveRaces(),liveHtml="";if(state.loading)liveHtml='<div class="home-empty">読込中…</div>';else if(state.date!==today())liveHtml='<div class="home-empty">当日を選ぶとリアルタイム表示します</div>';else if(live.length)liveHtml='<div class="home-live-grid">'+live.map(function(r){var tag=liveTag(r),urgent=tag.indexOf('running')>=0?' urgent':'';return '<button class="home-live-race'+urgent+'" data-race="'+esc(r.id)+'"><div class="live-top">'+tag+'<span class="home-arrow">›</span></div><div class="home-race-line"><span class="home-track">'+esc(r.track)+'</span><span class="home-rno">'+esc(r.raceNumber)+'R</span></div><div class="home-rtitle">'+esc(r.title||"")+'</div><div class="home-rtime">'+timeHtml(r)+'</div></button>'}).join("")+'</div>';else liveHtml='<div class="home-empty">直近の未確定レースはありません</div>';
var vh=venues.length?'<div class="home-venue-grid">'+venues.slice(0,4).map(function(v){return '<button class="home-venue" data-track="'+esc(v[0])+'">'+homeVenueMark(v[0])+'<span class="home-venue-name">'+esc(v[0])+'</span><span class="home-venue-count">'+v[1]+'レース</span><span class="home-arrow">›</span></button>'}).join("")+'</div>':'<div class="home-empty">'+(state.error?esc(state.error):(state.circuit==="中央"?"中央データ取得中、または開催データなし":"この日の取得データはありません"))+'</div>';
var nx=nextRace(),aiButtons=nx?'<div class="home-ai-actions"><button class="home-ai-select" data-action="pace-pick">選択</button><button class="home-ai-go" data-action="pace-next">展開を見る ›</button></div>':'<div class="home-ai-actions"><button class="home-ai-select" data-action="pace-pick">選択</button></div>';
return '<div class="home-shell"><div class="home-hero"><img class="hero-horse" src="/hero-horse.webp?v=59" alt=""><div class="brand-wrap"><div class="brand-main">競馬展開<span class="ai">AI</span></div><div class="brand-sub">Race Intelligence · v60</div></div><button class="hero-refresh" data-action="reload"><span class="refresh-icon">↻</span><small>更新</small></button></div><main class="home-main">'+
'<section class="home-card"><div class="home-section-head"><div class="home-section-title"><span class="home-section-icon">▣</span>日付・開催区分</div></div><div class="home-date-row"><div class="home-date-wrap"><input id="date" class="home-date" type="date" value="'+esc(state.date)+'"></div><div class="home-segment"><button data-circuit="中央" class="'+(state.circuit==="中央"?"active":"")+'">中央</button><button data-circuit="地方" class="'+(state.circuit==="地方"?"active":"")+'">地方</button></div></div></section>'+
'<section class="home-card"><div class="home-section-head"><div class="home-section-title"><span class="home-section-icon">◉</span>リアルタイムのレース</div><span class="home-link">すべて見る</span></div>'+liveHtml+'</section>'+
'<section class="home-card"><div class="home-section-head"><div class="home-section-title"><span class="home-section-icon">●</span>開催場</div><span class="home-link">すべて見る</span></div>'+vh+'</section>'+
'<section class="home-card home-ai-card"><div class="home-ai-top"><span class="home-ai-bars"><i></i><i></i><i></i></span><div class="home-ai-copy"><div class="home-ai-title">AI展開予想</div><div class="home-ai-sub">脚質・枠順・コースから本線の隊列を予測します</div></div>'+aiButtons+'</div>'+miniPacePreview(nx)+'</section>'+
'</main></div>'}
function renderPicker(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)});a.sort(function(x,y){return mins(x.startTime)-mins(y.startTime)});return'<div class="shell">'+header("展開予想を選択",true,state.date+'・'+state.circuit)+'<main class="main"><section class="card"><div class="picker-list">'+(a.length?a.map(function(r){return'<button class="picker-item" data-race="'+esc(r.id)+'"><span>'+esc(r.track)+' '+esc(r.raceNumber)+'R　'+esc(r.title||"")+'</span><strong>'+timeHtml(r)+'</strong></button>'}).join(""):'<div class="empty">未確定レースはありません</div>')+'</div></section></main></div>'}
function renderVenue(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&r.track===state.track});a.sort(function(x,y){return n(x.raceNumber)-n(y.raceNumber)});return'<div class="shell">'+header(state.track,true,state.date+'・'+state.circuit)+'<main class="main"><section class="card"><div class="race-list">'+(a.length?a.map(function(r){return'<button class="race '+(isFinal(r)?'final':'')+'" data-race="'+esc(r.id)+'"><span class="race-main"><span class="race-top"><span class="race-no">'+esc(r.raceNumber)+'R</span><span class="race-title">'+esc(r.title||"")+'</span></span><div class="race-time">'+timeHtml(r)+'</div></span>'+(isFinal(r)?'<span class="final-badge">確定</span>':'<span>›</span>')+'</button>'}).join(""):'<div class="empty">レースデータなし</div>')+'</div></section></main></div>'}
function resultFinish(r,no){var f=r&&r.result&&r.result.finishers||[];for(var i=0;i<f.length;i++)if(n(f[i].horseNumber)===n(no))return n(f[i].finish);return 0}
function actualCornerLeaders(r,idx){var f=r&&r.result&&r.result.finishers||[],best=999,out=[],i,p,v;for(i=0;i<f.length;i++){p=f[i].cornerPositions||[];v=n(p[idx],0);if(v&&v<best){best=v;out=[f[i]]}else if(v&&v===best)out.push(f[i])}return out}
function actualCornerCount(r){var f=r&&r.result&&r.result.finishers||[],m=0,i;for(i=0;i<f.length;i++)m=Math.max(m,(f[i].cornerPositions||[]).length);return m}
function actualCornerLabel(i,count){if(count===1)return"4角";if(count===2)return i===0?"3角":"4角";if(count===3)return["2角","3角","4角"][i];if(count===4)return["1角","2角","3角","4角"][i];return(i+1)+"角"}
function actualOrderAt(r,idx){var f=(r.result&&r.result.finishers||[]).slice(),a=[];for(var i=0;i<f.length;i++){var p=f[i].cornerPositions||[],v=n(p[idx],0);if(v)a.push({x:f[i],pos:v})}a.sort(function(u,v){return u.pos-v.pos||n(u.x.finish)-n(v.x.finish)});return a}
function renderResult(r){if(!isFinal(r))return"";var f=(r.result.finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)}).slice(0,3);return'<section class="card result-card"><div class="section-title">レース結果</div>'+f.map(function(x){var h=horseByNo(r,x.horseNumber)||x;return'<div class="result-row"><span>'+esc(x.finish)+'着</span>'+badge(h)+'<span class="result-name">'+esc(x.name||h.name||"")+'</span><span>'+fmtTime(x.timeSeconds)+'</span></div>'}).join("")+'</section>'}
function gradeRank(g){return g==='S'?0:(g==='A'?1:(g==='B'?2:(g==='C'?3:9)))}
function renderResultGap(r,p){if(!isFinal(r))return"";var f=(r.result.finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)}),actualTop=f.slice(0,3).map(function(x){return n(x.horseNumber)}),ranked=(p.rows||[]).slice().filter(function(x){return x.overallScore!=null}).sort(function(a,b){return gradeRank(a.overallGrade)-gradeRank(b.overallGrade)||n(b.overallScore)-n(a.overallScore)||n(a.horse.horseNumber)-n(b.horse.horseNumber)}),predTop=ranked.slice(0,3).map(function(x){return n(x.horse.horseNumber)}),hit=0,i;for(i=0;i<predTop.length;i++)if(actualTop.indexOf(predTop[i])>=0)hit++;var top=ranked.length?ranked[0]:null,topFin=top?resultFinish(r,top.horse.horseNumber):0;var predLead=p.plan.start.length?p.plan.start[0].horse:null,count=actualCornerCount(r),firstLeaders=count?actualCornerLeaders(r,0):[],lastLeaders=count?actualCornerLeaders(r,count-1):[];function nums(a){return a.length?a.map(function(x){return x.horseNumber}).join("・"):"—"}return'<section class="card gap-card"><div class="section-title">レース結果とのズレ</div><div class="gap-grid"><div><small>AI最上位評価の結果</small><b>'+(top?esc(top.overallGrade)+' '+esc(top.horse.horseNumber)+' '+esc(top.horse.name)+' → '+(topFin?topFin+'着':'着外/不明'):'—')+'</b></div><div><small>総合評価上位3頭一致</small><b>'+hit+'/3</b></div><div><small>予想ハナ → 実際序盤</small><b>'+(predLead?esc(predLead.horseNumber):'—')+' → '+nums(firstLeaders)+'</b></div><div><small>予想4角先頭 → 実際4角</small><b>'+(p.plan.corner.length?esc(p.plan.corner[0].horse.horseNumber):'—')+' → '+nums(lastLeaders)+'</b></div></div><div class="gap-order"><span>AI評価上位</span> '+predTop.join(" → ")+'<br><span>実着順</span> '+actualTop.join(" → ")+'</div></section>'}
function renderActualFlow(r){if(!isFinal(r))return"";var count=actualCornerCount(r),html='<section class="card actual-flow"><div class="section-title">実際の展開順序</div>';if(!count)html+='<div class="muted">コーナー通過順データなし</div>';for(var j=0;j<count;j++){var a=actualOrderAt(r,j);html+='<div class="actual-stage"><b>'+actualCornerLabel(j,count)+'</b><div class="actual-order">'+a.map(function(z){var h=horseByNo(r,z.x.horseNumber)||z.x;return'<span>'+badge(h)+'<em>'+esc(h.name||z.x.name||"")+'</em></span>'}).join('<i>›</i>')+'</div></div>'}var f=(r.result.finishers||[]).slice().sort(function(a,b){return n(a.finish)-n(b.finish)});html+='<div class="actual-stage"><b>ゴール</b><div class="actual-order">'+f.map(function(x){var h=horseByNo(r,x.horseNumber)||x;return'<span>'+badge(h)+'<em>'+esc(h.name||x.name||"")+'</em></span>'}).join('<i>›</i>')+'</div></div></section>';return html}
function roleDetail(label,stats,profile){stats=stats||{};profile=profile||{};var st=n(stats.starts)||n(profile.starts),w=n(stats.wins),s=n(stats.seconds),t=n(stats.thirds);if(!st)return'<div class="role-box"><b>'+esc(label)+'</b><div>過去データ未取得 / 該当履歴なし</div></div>';var wr=Math.round(w/st*100),rr=Math.round((w+s)/st*100),pr=Math.round((w+s+t)/st*100),bits=['出走 '+st,'1着 '+w,'2着 '+s,'3着 '+t,'勝率 '+wr+'%','連対 '+rr+'%','複勝 '+pr+'%'];if(n(profile.starts)>0){bits.push('競馬場 '+Math.round(n(profile.track)*100)+'%');bits.push('距離 '+Math.round(n(profile.distance)*100)+'%');if(profile.condition!=null)bits.push('馬場 '+Math.round(n(profile.condition)*100)+'%');if(n(profile.early3Rate,0))bits.push('序盤3番手内 '+Math.round(n(profile.early3Rate)*100)+'%');if(n(profile.leaderRate,0))bits.push('逃げ '+Math.round(n(profile.leaderRate)*100)+'%')}return'<div class="role-box"><b>'+esc(label)+'</b><div>'+bits.join(' / ')+'</div></div>'}
function styleDisplayPcts(x){if(!x||!n(x.styleSamples))return[null,null,null,null];var raw=[n(x.rawFront,x.front),n(x.rawStalk,x.stalk),n(x.rawMid,x.mid),n(x.rawClose,x.close)],vals=[],sum=0,i,maxi=0;for(i=0;i<4;i++){vals[i]=Math.max(0,Math.round(raw[i]*100));sum+=vals[i];if(raw[i]>raw[maxi])maxi=i}vals[maxi]+=100-sum;return vals}
function styleCell(label,val,active,cls){var unk=val==null||!isFinite(Number(val));return '<div class="style-rate '+cls+(active?' dominant':'')+(unk?' unknown':'')+'"><div class="style-rate-head"><span>'+label+'</span><b>'+(unk?'—':val+'%')+'</b></div><div class="style-bar"><i style="width:'+(unk?0:Math.max(2,val))+'%"></i></div></div>'}
function positionBucket(x){if(x.expected==="逃げ候補")return"逃げ候補";if(x.expected==="先行")return"先行";if(x.expected==="好位")return"好位";if(x.expected==="後方")return"後方";if(x.expected==="不明")return"不明";return"中団"}
function stylePositionMap(r,p){var rows=p.rows||[],labels=['逃げ候補','先行','好位','中団','後方','不明'],field=Math.max(1,(r.horses||[]).length),html='<div class="style-position-map"><div class="style-map-axis"><span>内枠</span><b>今回の枠順 × 想定位置</b><span>外枠</span></div>';for(var j=0;j<labels.length;j++){var lab=labels[j];html+='<div class="style-lane"><div class="style-lane-label">'+lab+'</div><div class="style-lane-track">';for(var i=0;i<rows.length;i++){var x=rows[i],h=x.horse;if(positionBucket(x)!==lab)continue;var left=field<=1?50:6+(n(h.horseNumber)-1)/Math.max(1,field-1)*88,shift=x.pastStyle!==x.expected&&!(x.pastStyle==='先行'&&x.expected==='好位');html+='<span class="style-map-horse'+(shift?' shifted':'')+'" style="left:'+left+'%" title="'+esc(h.name)+'｜過去 '+esc(x.pastStyle)+' → 今回 '+esc(x.expected)+'">'+badge(h)+'</span>'}html+='</div></div>'}html+='<div class="style-map-note"><b>水色縁</b>＝過去脚質から今回条件で位置想定が動いた馬。馬番位置は内→外の枠順を維持。</div></div>';return html}
function runnerStyleSection(r,p){var rows=sortedHorseRows(p.rows);return'<section class="card runner-map-card"><div class="section-title-row"><div><div class="section-title">出走馬表 × 脚質マップ</div><div class="section-sub">JRA表に近い一覧表示。印は切替、馬名タップで詳細表示、モーダル内で横スワイプ切替</div></div><span class="map-hint">逃 / 先 / 差 / 追 / 下</span></div>'+stylePositionMap(r,p)+'<div class="runner-list-head"><div>馬番</div><div>予想印<br><small>切替</small></div><div>馬名<br>年齢 脚質 騎手 斤量</div><div>総合評価<br>（総合点）</div></div><div class="runner-style-list jra-list">'+rows.map(function(x){var h=x.horse,ps=styleDisplayPcts(x),mx=Math.max.apply(null,ps),fade=x.styleSamples?Math.round(x.fade*100):null,manualMark=rowMark(r,x),markLabel=manualMark||'--',bodyTxt=horseBodyWeightText(h),styleTxt=x.expected||x.pastStyle||'不明';return'<details class="runner-style"><summary><div class="runner-summary-table"><div class="runner-summary-cell runner-summary-no">'+badge(h)+'</div><div class="runner-summary-cell runner-mark-cell"><button type="button" class="runner-mark-toggle '+(manualMark?'':'empty')+'" data-mark-toggle="1" data-horse-no="'+esc(h.horseNumber)+'"><b>'+esc(markLabel)+'</b><small>印</small></button></div><div class="runner-name-cell"><div class="runner-summary-main"><div class="runner-summary-topline"><button type="button" class="runner-name-btn" data-horse-open="'+esc(h.horseNumber)+'"><span class="horse-name">'+esc(h.name)+'</span>'+(bodyTxt?'<span class="runner-weight-inline">('+esc(bodyTxt)+')</span>':'')+'</button></div><div class="runner-summary-meta compact"><span>'+esc(h.sex||'—')+esc(h.age||'—')+'</span><span>'+esc(styleTxt)+'</span><span>'+esc(h.jockey||'騎手不明')+'</span><span>'+esc(h.carriedWeight||'—')+'kg</span></div></div></div><div class="runner-grade-cell"><div class="runner-grade-side"><small>総合評価</small><b class="'+gradeClass(x.overallGrade)+'">'+esc(x.overallGrade||'保留')+'</b><span>（'+(x.overallScore==null?'—':esc(x.overallScore))+'）</span></div></div><span class="open-caret">⌄</span></div><div class="runner-position-preview"><div class="runner-position-title"><b>位置取り指標</b><span>逃 / 先 / 差 / 追 / 下</span></div><div class="style-rate-grid five-rates">'+styleCell('逃',ps[0],ps[0]===mx,'front')+styleCell('先',ps[1],ps[1]===mx,'stalk')+styleCell('差',ps[2],ps[2]===mx,'mid')+styleCell('追',ps[3],ps[3]===mx,'close')+styleCell('下',fade,fade!=null&&fade>=55,'fade')+'</div><div class="detail-tap-note">馬名タップで馬ごとの基本情報、行タップでも下に詳細表示</div></div></summary>'+runnerDetailBody(r,p,x)+'</details>'}).join('')+'</div></section>'}
function rowName(x){return x&&x.horse?(x.horse.horseNumber+' '+x.horse.name):'—'}
function stageNarrative(p,idx){var rows=p.rows||[],st=p.plan&&p.plan.stages&&p.plan.stages[idx],pack=st&&st.pack||[],by={};for(var i=0;i<rows.length;i++)by[n(rows[i].horse.horseNumber)]=rows[i];var lead=pack.length?by[n(pack[0].no)]:null,front=rows.filter(function(x){return x.goProb>=.48}),sand=front.filter(function(x){return x.sandwichRisk}),wide=front.filter(function(x){return x.outerStress>=.18}),fade=front.filter(function(x){return x.fade>=.50}),movers=rows.filter(function(x){return x.move>=.40&&x.goProb<.50}).sort(function(a,b){return b.comeFromBehind-a.comeFromBehind}),closers=rows.slice().sort(function(a,b){return b.comeFromBehind-a.comeFromBehind}),bits=[];if(lead)bits.push('<b>先頭想定 '+esc(rowName(lead))+'</b>');if(idx===0){var h=front.slice().sort(function(a,b){return b.goProb-a.goProb}).slice(0,4);if(h.length)bits.push('前へ '+h.map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===1){if(sand.length)bits.push('<span class="event-warn">被され/控え警戒 '+sand.map(function(x){return esc(rowName(x))}).join('・')+'</span>');if(wide.length)bits.push('外枠テン負荷 '+wide.map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===2){var lowHold=front.filter(function(x){return x.holdFront<.52});if(lowHold.length)bits.push('前で維持力注意 '+lowHold.slice(0,3).map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===3||idx===4){if(movers.length)bits.push('<span class="event-good">位置を上げる候補 '+movers.slice(0,3).map(function(x){return esc(rowName(x))}).join('・')+'</span>');if(fade.length)bits.push('<span class="event-warn">下がり警戒 '+fade.slice(0,3).map(function(x){return esc(rowName(x))}).join('・')+'</span>');if(fade.length&&closers.length)bits.push('下がった前の後ろで得 '+closers.slice(0,2).map(function(x){return esc(rowName(x))}).join('・'))}else if(idx===5){var stay=rows.slice().sort(function(a,b){return b.frontStay-a.frontStay}).slice(0,2);bits.push('前残り適性 '+stay.map(function(x){return esc(rowName(x))}).join('・'));bits.push('差し込み適性 '+closers.slice(0,2).map(function(x){return esc(rowName(x))}).join('・'))}return bits.join('　｜　')}
function scenarioProbabilitySection(p){var top=p.scenarios.slice().sort(function(a,b){return b.prob-a.prob})[0],front=p.rows.filter(function(x){return x.goProb>=.52}),sand=front.filter(function(x){return x.sandwichRisk}).length,highFade=front.filter(function(x){return x.fade>=.50}).length,occ=p.occ||{rate:0,early:[],moved:[]},warn=[];if(sand)warn.push('逃げハサミ警戒 '+sand+'頭');if(highFade>=2)warn.push('前へ行く馬の高下がり率 '+highFade+'頭 → 差し馬を再検査');if(!warn.length)warn.push('単純な先行頭数ではなく、枠順・隣接圧力・残り性能から展開判定');return'<section class="card pace-card"><div class="section-title">展開シナリオ</div><div class="scenario-prob-grid">'+p.scenarios.map(function(s){return'<div class="scenario-prob-card '+(s.code===top.code?'active':'')+'"><small>'+s.code+'</small><b>'+esc(s.title)+'</b><strong>'+Math.round(s.prob*100)+'%</strong></div>'}).join('')+'</div><div class="scenario-main-note"><span>本線シナリオ</span><b>'+esc(top.code)+' '+esc(top.title)+'　'+Math.round(top.prob*100)+'%</b></div><div class="scenario-diagnostics"><div class="scenario-diagnostic"><small>先行馬占有率</small><b>'+Math.round(occ.rate*100)+'%</b></div><div class="scenario-diagnostic"><small>最初から前</small><b>'+occ.early.length+'頭</b></div><div class="scenario-diagnostic"><small>途中から上昇</small><b>'+occ.moved.length+'頭</b></div><div class="scenario-diagnostic"><small>今回前候補</small><b>'+front.length+'頭</b></div></div><div class="scenario-warning">'+warn.map(esc).join(' / ')+'</div></section>'}
function paceBoard(r,p){var hs=(r.horses||[]).slice().sort(function(a,b){return n(a.horseNumber)-n(b.horseNumber)}),stages=p.plan.stages||[],cp=courseProfile(r);return'<section class="card ai-flow-card"><div class="ai-flow-head"><span class="ai-flow-bars"><i></i><i></i><i></i></span><div class="ai-flow-copy"><div class="ai-flow-title">AI展開予想</div><div class="ai-flow-sub">過去走・脚質・枠順・テン・隣接圧力から局面ごとの隊列を表示</div></div><span class="ai-flow-scenario">'+esc(p.plan.scenario.code)+' '+esc(p.plan.scenario.title)+'</span></div><div class="ai-stage-tabs">'+stages.map(function(s,i){return'<button data-pace-stage="'+i+'" class="'+(i===0?'active':'')+'">'+esc(s.label)+'</button>'}).join('')+'</div><div class="ai-race-swipe-hint">← 左右にスライドして局面を切り替え →</div><div class="ai-race-topline"><div class="ai-race-meta-chip">'+esc(r.track)+'　'+esc(r.distance)+'m　'+esc(cp.turn)+(cp.shape==='straight'?'':'回り')+'</div><div class="ai-race-axis-strip"><span>← 後方</span><span>前方・先頭 →</span></div></div><div class="ai-race-board-wrap"><div id="pace-board" class="ai-race-visual">'+hs.map(function(h){return'<div class="ai-race-runner" data-horse="'+esc(h.horseNumber)+'" style="left:10%;top:50%">'+badge(h)+'</div>'}).join('')+'</div></div><div id="course-order" class="ai-race-order-panel">隊列を準備中</div><div id="pace-event" class="ai-stage-event">展開イベントを準備中</div><div class="ai-race-note">赤枠内は馬番のみ表示。説明文は下に分離し、右が先頭、左が後方です。</div></section>'}
function renderRaceLoading(){return '<div class="shell">'+header("レース読込中",true,"出走馬・近走データを準備中")+'<main class="main"><section class="card"><div class="empty">このレースだけ詳しいデータを読み込んでいます…</div></section></main></div>'}
function historySearchSection(r){var hs=r.historySearch||{},cv=hs.coverage||{},months=n(hs.monthsDone),max=n(hs.maxMonths,60),progress=max?clamp(months/max*100,4,96):8,counts=cv.counts||{},isCentral=r.circuit==='中央',horseHtml=(r.horses||[]).map(function(h){var c=n(counts[h.name]);return'<span>'+badge(h)+esc(h.name||'')+' <b>'+Math.min(5,c)+'/5</b></span>'}).join(''),src=isCentral?'中央データを過去へさかのぼり':'NAR公式履歴を過去へさかのぼり';return'<section class="card history-search-card"><div class="history-search-head"><span class="history-spinner"></span><div><div class="history-search-title">直近5走を取得中</div><div class="history-search-sub">全頭について'+src+'、直近最大5走を確認します。キャリア5走未満の馬は存在する全走を取得した時点で確定し、固定値では埋めません。取得した過去レースは詳細画面から開けます。</div></div></div><div class="history-progress"><i style="width:'+progress+'%"></i></div><div class="history-stats"><span>検索 '+months+' / '+max+'か月</span><span>'+(isCentral?'履歴確定 ':'5走取得 ')+n(isCentral?(cv.horsesResolved||cv.horsesWith5Plus):cv.horsesWith5Plus)+' / '+n(cv.totalHorses,(r.horses||[]).length)+'頭</span><span>履歴あり '+n(cv.horsesWithHistory)+'頭</span><span>取得 '+n(cv.totalRuns)+'走</span></div><div class="history-horses">'+horseHtml+'</div></section>'}
function scheduleHistoryPoll(id){if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}state.historyTimer=setTimeout(function(){fetch('/api/v1/race/'+encodeURIComponent(id)+'?refresh=1&v=59',{cache:'no-store'}).then(function(res){if(!res.ok)throw new Error('API '+res.status);return res.json()}).then(function(body){if(!state.race||String(state.race.id)!==String(id))return;state.race=body;render();if(body.historySearch&&body.historySearch.status==='running')scheduleHistoryPoll(id)}).catch(function(){if(state.race&&String(state.race.id)===String(id))scheduleHistoryPoll(id)})},400)}
function prefetchNextHistory(){var a=state.races.filter(function(r){return r.circuit===state.circuit&&!isFinal(r)&&r.id}),now=nowMins();a.sort(function(x,y){var ax=mins(x.startTime),ay=mins(y.startTime),kx=ax>=now?ax:ax+1440,ky=ay>=now?ay:ay+1440;return kx-ky});a.slice(0,2).forEach(function(x,idx){if(!x||state.historyPrefetch[x.id])return;state.historyPrefetch[x.id]=1;setTimeout(function(){fetch('/api/v1/race/'+encodeURIComponent(x.id)+'?v=59',{cache:'no-store'}).catch(function(){delete state.historyPrefetch[x.id]})},idx*260)})}
function openRace(id,keepStack,skipHistory){if(!id||state.raceLoading)return;if(!keepStack)state.raceStack=[];if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}state.raceLoading=String(id);state.race=null;state.error=null;state.picker=false;render();fetch('/api/v1/race/'+encodeURIComponent(id)+'?v=59'+(skipHistory?'&history=0':''),{cache:'no-store'}).then(function(res){if(!res.ok)throw new Error('API '+res.status);return res.json()}).then(function(body){if(String(state.raceLoading)!==String(id))return;state.raceLoading=null;state.race=body;render();if(!skipHistory&&body.historySearch&&body.historySearch.status==='running')scheduleHistoryPoll(id)}).catch(function(e){if(String(state.raceLoading)!==String(id))return;state.raceLoading=null;state.error='レース詳細の取得に失敗しました';if(state.raceStack.length)state.race=state.raceStack.pop();render()})}
function openPastRace(id){if(!id)return;if(state.race)state.raceStack.push(state.race);openRace(id,true,true)}
function reloadCurrent(){if(state.race&&state.race.id){var id=state.race.id,isPast=state.raceStack.length>0;state.race=null;openRace(id,true,isPast)}else load()}
function renderRace(){var r=state.race,hs=r.historySearch||{},historyInline='';if(hs.status==='running'){var cv=hs.coverage||{},done=n(r.circuit==='中央'?(cv.horsesResolved||cv.horsesWith5Plus):cv.horsesWith5Plus),total=n(cv.totalHorses,(r.horses||[]).length),runs=n(cv.totalRuns);historyInline='<div class="history-inline"><span><b>近走を裏で取得中</b><br><small>取得済み '+runs+'走・確定 '+done+'/'+total+'頭</small></span><span>表示は待ちません</span></div>'}var p=predict(r);state.pred=p;var sourceNote=hs.status==='done'?'<div class="data-source-note">【v60】過去走検索：'+n(hs.monthsDone)+'か月確認 / '+n((hs.coverage||{}).totalRuns)+'走取得 / '+esc(hs.source||'履歴データ')+'</div>':(hs.status==='running'?'<div class="data-source-note">【v60】近走データは取得済み分から即表示し、残りをバックグラウンド更新中</div>':(hs.status==='error'?'<div class="notice">過去走の追加取得に失敗。取得済みデータだけで表示します。</div>':''));return'<div class="shell">'+header(r.track+' '+r.raceNumber+'R',true,(r.title||'')+'｜'+r.distance+'m・'+r.condition)+'<main class="main">'+historyInline+renderResult(r)+renderResultGap(r,p)+renderActualFlow(r)+'<section class="card race-title-card"><div class="row between"><div><h2>'+esc(r.title||"")+'</h2><div class="muted">'+esc(r.date)+' '+timeHtml(r)+'</div></div><span class="pill">'+esc(r.circuit)+'</span>'+(state.raceStack.length?'<span class="past-race-badge">過去レース</span>':'')+'</div><div class="metrics"><div class="metric"><b>'+esc(r.distance)+'m</b><span>距離</span></div><div class="metric"><b>'+esc(r.condition||'不明')+'</b><span>馬場</span></div><div class="metric"><b>'+esc(r.weather||'不明')+'</b><span>天候</span></div><div class="metric"><b>'+season(r.date)+'</b><span>季節</span></div><div class="metric"><b>'+esc((r.horses||[]).length)+'頭</b><span>頭数</span></div></div><div class="data-depth"><span>近走 5走</span><span>'+(r.circuit==='中央'?'中央 直近5走を自動検索':'NAR公式 直近5走を自動検索')+'</span><span>0走は推定値を表示しない</span></div>'+sourceNote+'</section>'+runnerStyleSection(r,p)+scenarioProbabilitySection(p)+paceBoard(r,p)+'</main>'+horseModal(r,p)+'</div>'}
function render(){stopTimer();try{if(state.raceLoading)app.innerHTML=renderRaceLoading();else if(state.race)app.innerHTML=renderRace();else if(state.picker)app.innerHTML=renderPicker();else if(state.track)app.innerHTML=renderVenue();else app.innerHTML=renderHome();bind();if(state.race)initPaceBoard()}catch(e){app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(e&&e.message||e)+'<br><button onclick="location.reload()">再読み込み</button></div>'}}
function bind(){var els=document.querySelectorAll('[data-circuit]'),i;for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];state.circuit=this.getAttribute('data-circuit');state.track=null;state.race=null;state.picker=false;load()};var d=document.getElementById('date');if(d)d.onchange=function(){state.raceStack=[];state.date=this.value;state.track=null;state.race=null;state.picker=false;load()};els=document.querySelectorAll('[data-track]');for(i=0;i<els.length;i++)els[i].onclick=function(){state.raceStack=[];state.track=this.getAttribute('data-track');render()};els=document.querySelectorAll('[data-race]');for(i=0;i<els.length;i++)els[i].onclick=function(){openRace(this.getAttribute('data-race'),false,false)};els=document.querySelectorAll('[data-past-race]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openPastRace(this.getAttribute('data-past-race'))};var b=document.querySelectorAll('[data-action="back"]');for(i=0;i<b.length;i++)b[i].onclick=function(){if(state.historyTimer){clearTimeout(state.historyTimer);state.historyTimer=null}if(state.raceLoading){state.raceLoading=null;if(state.raceStack.length)state.race=state.raceStack.pop()}else if(state.race){if(state.raceStack.length)state.race=state.raceStack.pop();else state.race=null}else if(state.picker)state.picker=false;else state.track=null;render()};var rr=document.querySelectorAll('[data-action="reload"]');for(i=0;i<rr.length;i++)rr[i].onclick=reloadCurrent;var pn=document.querySelector('[data-action="pace-next"]');if(pn)pn.onclick=function(){var x=nextRace();if(x){openRace(x.id,false,false)}};var pp=document.querySelector('[data-action="pace-pick"]');if(pp)pp.onclick=function(){state.raceStack=[];state.picker=true;state.track=null;render()};els=document.querySelectorAll('[data-mark-toggle]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}cycleMark(this.getAttribute('data-horse-no'))};els=document.querySelectorAll('[data-horse-open]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}openHorseModal(this.getAttribute('data-horse-open'))};els=document.querySelectorAll('[data-horse-close]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}closeHorseModal()};els=document.querySelectorAll('[data-horse-prev]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(-1)};els=document.querySelectorAll('[data-horse-next]');for(i=0;i<els.length;i++)els[i].onclick=function(e){if(e){e.preventDefault();e.stopPropagation()}moveHorseModal(1)};els=document.querySelectorAll('[data-pace-stage]');for(i=0;i<els.length;i++)els[i].onclick=function(){drawPaceStage(n(this.getAttribute('data-pace-stage'),0))};var board=document.getElementById('pace-board');if(board){var sx=0,sy=0;board.ontouchstart=function(e){if(!e.touches||!e.touches.length)return;var t=e.touches[0];sx=t.clientX;sy=t.clientY};board.ontouchend=function(e){if(!e.changedTouches||!e.changedTouches.length)return;var t=e.changedTouches[0],dx=t.clientX-sx,dy=t.clientY-sy;if(Math.abs(dx)>40&&Math.abs(dx)>Math.abs(dy)){var cur=n(state.paceStage,0),mx=(state.pred&&state.pred.plan&&state.pred.plan.stages?state.pred.plan.stages.length-1:0),nx=clamp(cur+(dx<0?1:-1),0,mx);if(nx!==cur)drawPaceStage(nx)}};board.onmousedown=function(e){sx=e.clientX;sy=e.clientY};board.onmouseup=function(e){var dx=e.clientX-sx,dy=e.clientY-sy;if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)){var cur=n(state.paceStage,0),mx=(state.pred&&state.pred.plan&&state.pred.plan.stages?state.pred.plan.stages.length-1:0),nx=clamp(cur+(dx<0?1:-1),0,mx);if(nx!==cur)drawPaceStage(nx)}}}var panel=document.getElementById('horse-modal-panel');if(panel){var hsx=0,hsy=0;panel.ontouchstart=function(e){if(!e.touches||!e.touches.length)return;var t=e.touches[0];hsx=t.clientX;hsy=t.clientY};panel.ontouchend=function(e){if(!e.changedTouches||!e.changedTouches.length)return;var t=e.changedTouches[0],dx=t.clientX-hsx,dy=t.clientY-hsy;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy))moveHorseModal(dx<0?1:-1)};panel.onmousedown=function(e){hsx=e.clientX;hsy=e.clientY};panel.onmouseup=function(e){var dx=e.clientX-hsx,dy=e.clientY-hsy;if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy))moveHorseModal(dx<0?1:-1)}}}
function stopTimer(){if(state.timer){clearTimeout(state.timer);state.timer=null}if(state.anim){cancelAnimationFrame(state.anim);state.anim=null}state.simRunning=false}
function resetSimCounts(){var o={},hs=state.race&&state.race.horses||[],i;for(i=0;i<hs.length;i++)o[n(hs[i].horseNumber)]={w:0,s:0,t:0};state.simCounts=o;state.simDone=0;state.simCurrentT=0;state.simIndex=0}
function setSimButtons(){var p=document.querySelector('[data-action="sim-pause"]'),s=document.querySelector('[data-action="sim-stop"]'),r=document.querySelector('[data-action="sim-run"]');if(p){p.disabled=!(state.simRunning||state.simPaused);p.textContent=state.simPaused?'▶ 再開':'⏸ 一時停止'}if(s)s.disabled=!(state.simRunning||state.simPaused||state.simDone>0);if(r)r.textContent=state.simDone>0&&!state.simRunning&&!state.simPaused?'↻ 最初から':'▶ 開始'}
function updateSimHud(runIndex,run){var target=Math.max(10,n(state.simTarget,20)),c=document.getElementById('sim-count'),b=document.getElementById('sim-progress-bar'),e=document.getElementById('sim-elapsed'),st=document.getElementById('sim-status');if(c)c.textContent=state.simDone+' / '+target;if(b)b.style.width=(state.simDone/target*100)+'%';if(e)e.textContent=state.simPaused?'一時停止中':(state.simRunning?'×'+state.simSpeed+' 再生中':(state.simDone>=target?'完了':(state.simDone?'停止':'待機')));if(st)st.textContent=state.simDone>=target?target+'回 完了':'シミュレーション '+Math.min(target,runIndex+1)+'/'+target;if(run&&state.simDone>0){var live=document.getElementById('sim-live-podium'),p=run.podium;if(live)live.innerHTML=p.map(function(no,i){var h=horseByNo(state.race,no);return'<b>'+(i+1)+'着 '+esc(no)+' '+esc(h?h.name:'')+'</b>'+(i<2?'<i> / </i>':'')}).join('')}setSimButtons()}
function finishOneRun(run){var p=run.podium||[],i,z;for(i=0;i<p.length;i++){z=state.simCounts[p[i]];if(!z)continue;if(i===0)z.w++;if(i===1)z.s++;if(i===2)z.t++}state.simDone++;state.simCurrentT=0;updateSimHud(state.simIndex,run)}

function simStageLabel(t){if(t<.08)return"スタート";if(t<.22)return"ハナ争い";if(t<.38)return"1角";if(t<.55)return"向正面";if(t<.70)return"3角";if(t<.82)return"4角";if(t<.94)return"直線";return"ゴール"}
function simInterpState(run,no,t){var maps=run&&run.maps||[],last=Math.max(0,maps.length-1);if(!maps.length)return{gap:0,lane:0};var u=clamp(t,0,1)*last,i=Math.min(last-1,Math.floor(u)),f=u-i;if(last===0){i=0;f=0}var a=(maps[i]&&maps[i][no])||{gap:0,lane:0},b=(maps[Math.min(last,i+1)]&&maps[Math.min(last,i+1)][no])||a;return{gap:n(a.gap)+(n(b.gap)-n(a.gap))*f,lane:n(a.lane)+(n(b.lane)-n(a.lane))*f}}
function placeSimRunner(chip,path,board,frac,lane){if(!chip||!path||!board)return;var total=path.getTotalLength();if(!total)return;frac=normFrac(frac);var len=frac*total,p=path.getPointAtLength(len),p0=path.getPointAtLength(Math.max(0,len-1)),p1=path.getPointAtLength(Math.min(total,len+1)),dx=p1.x-p0.x,dy=p1.y-p0.y,mag=Math.sqrt(dx*dx+dy*dy)||1,nx=-dy/mag,ny=dx/mag,off=n(lane)*3.2,x=p.x+nx*off,y=p.y+ny*off;chip.style.left=clamp(x/200*100,2,98)+'%';chip.style.top=clamp(y/180*100,7,93)+'%'}
function drawSimulationRun(run,t){if(!run||!state.race)return;var r=state.race,board=document.getElementById('pace-board'),path=document.getElementById('course-path');if(!board||!path)return;var cp=courseProfile(r),rows=state.pred&&state.pred.rows||[],start=courseStageFrac(r,0),laps=Math.max(.1,n(r.distance,1200)/cp.lap),baseFrac;if(cp.shape==='straight'){var end=.92;baseFrac=start+(end-start)*clamp(t,0,1)}else{baseFrac=normFrac(start+cp.dir*laps*clamp(t,0,1))}var order=[],i,row,no,pos,frac,chip;for(i=0;i<rows.length;i++){row=rows[i];no=n(row.horse.horseNumber);pos=simInterpState(run,no,t);if(cp.shape==='straight')frac=clamp(baseFrac-pos.gap*.45,.025,.975);else frac=normFrac(baseFrac-cp.dir*pos.gap);chip=board.querySelector('[data-horse="'+no+'"]');placeSimRunner(chip,path,board,frac,pos.lane);order.push({no:no,gap:pos.gap,lane:pos.lane})}order.sort(function(a,b){return a.gap-b.gap||Math.abs(a.lane)-Math.abs(b.lane)||a.no-b.no});var top=order.slice(0,3),live=document.getElementById('sim-live-podium');if(live)live.innerHTML=top.map(function(z,j){var h=horseByNo(r,z.no);return'<b>'+(j+1)+'番手 '+esc(z.no)+' '+esc(h?h.name:'')+'</b>'+(j<top.length-1?'<i> / </i>':'')}).join('');var ob=document.getElementById('course-order');if(ob)ob.innerHTML='<b>'+simStageLabel(t)+'</b>　'+order.slice(0,8).map(function(z){var h=horseByNo(r,z.no);return esc(z.no)+(h?' '+esc(h.name):'')}).join(' → ')}

function animateOneRun(idx,fromT){if(!state.simRunning||!state.pred||!state.pred.simulation)return;var target=Math.max(10,n(state.simTarget,20)),run=state.pred.simulation.runs[idx];if(!run||idx>=target){state.simRunning=false;state.simPaused=false;updateSimHud(Math.max(0,target-1),null);return}fromT=clamp(n(fromT,0),0,1);var fullMs=2500/Math.max(1,state.simSpeed),remainMs=Math.max(35,fullMs*(1-fromT)),started=performance.now();function step(now){if(!state.simRunning)return;var t=clamp(fromT+(now-started)/remainMs*(1-fromT),0,1);state.simCurrentT=t;drawSimulationRun(run,t);if(t<1){state.anim=requestAnimationFrame(step)}else{finishOneRun(run);state.simIndex=idx+1;if(state.simIndex<target){state.timer=setTimeout(function(){if(state.simRunning)animateOneRun(state.simIndex,0)},Math.max(12,80/state.simSpeed))}else{state.simRunning=false;state.simPaused=false;updateSimHud(target-1,run)}}}state.anim=requestAnimationFrame(step)}
function startSimulation(){if(!state.race||!state.pred)return;stopTimer();state.simPaused=false;state.simStopped=false;resetSimCounts();state.simRunning=true;setSimButtons();animateOneRun(0,0)}
function togglePauseSimulation(){if(state.simRunning){if(state.anim){cancelAnimationFrame(state.anim);state.anim=null}if(state.timer){clearTimeout(state.timer);state.timer=null}state.simRunning=false;state.simPaused=true;updateSimHud(state.simIndex,null);return}if(state.simPaused){state.simPaused=false;state.simRunning=true;setSimButtons();animateOneRun(state.simIndex,state.simCurrentT)}}
function stopSimulation(){if(state.anim){cancelAnimationFrame(state.anim);state.anim=null}if(state.timer){clearTimeout(state.timer);state.timer=null}state.simRunning=false;state.simPaused=false;state.simStopped=true;updateSimHud(state.simIndex,null)}
function paceBaseFrac(r,idx){var cp=courseProfile(r),prog=[.02,.18,.44,.66,.80,.94][idx]||.02,start=courseStageFrac(r,0),laps=Math.max(.1,n(r.distance,1200)/cp.lap);if(cp.shape==='straight')return .05+(.90-.05)*prog;return normFrac(start+cp.dir*laps*prog)}
function drawPaceStage(idx){if(!state.race||!state.pred||!state.pred.plan||!state.pred.plan.stages)return;var stages=state.pred.plan.stages,st=stages[clamp(idx,0,stages.length-1)],r=state.race,board=document.getElementById('pace-board');if(!st||!board)return;state.paceStage=clamp(idx,0,stages.length-1);var order=[],i,z,chip,left,top,rank,rowIdx;for(i=0;i<st.pack.length;i++){z=st.pack[i];rank=i;rowIdx=rank%4;chip=board.querySelector('[data-horse="'+z.no+'"]');if(!chip)continue;left=clamp(90-rank*5.9-n(z.gap)*58,8,92);top=clamp(16+rowIdx*20+n(z.lane)*2.4,12,88);chip.style.left=left+'%';chip.style.top=top+'%';order.push(z.no)}var ob=document.getElementById('course-order');if(ob)ob.innerHTML='<b>'+esc(st.label)+'</b><span>'+order.map(function(no){var h=horseByNo(r,no);return esc(no)+(h?' '+esc(h.name):'')}).join(' → ')+'</span>';var ev=document.getElementById('pace-event');if(ev)ev.innerHTML=stageNarrative(state.pred,idx);var bs=document.querySelectorAll('[data-pace-stage]');for(i=0;i<bs.length;i++)bs[i].className=n(bs[i].getAttribute('data-pace-stage'))===idx?'active':''}
function initPaceBoard(){if(!state.pred||!state.pred.plan||!state.pred.plan.stages)return;drawPaceStage(0)}
function load(){var d=state.date,seq=++state.requestSeq,cached=loadRaceCache(d);state.error=null;if(cached&&cached.length){state.races=cached;state.loading=false;render();setTimeout(prefetchNextHistory,120)}else{state.loading=true;render()}var attempts=0;function request(){attempts+=1;fetch('/api/v1/races?date='+encodeURIComponent(d)+'&v=56',{cache:'no-store'}).then(function(res){if(!res.ok)throw new Error('API '+res.status);return res.json()}).then(function(body){if(seq!==state.requestSeq||state.date!==d)return;var rows=Array.isArray(body)?body:(body.races||[]);state.races=rows;saveRaceCache(d,rows);state.loading=false;state.error=null;render();setTimeout(prefetchNextHistory,120);var hasCentral=rows.some(function(z){return z.circuit==='中央'}),hasLocal=rows.some(function(z){return z.circuit==='地方'});if(state.circuit==='中央'&&!hasCentral&&attempts<10){setTimeout(request,900)}else if(state.circuit==='地方'&&!hasLocal&&attempts<10){setTimeout(request,900)}}).catch(function(){if(seq!==state.requestSeq||state.date!==d)return;if(attempts<3){setTimeout(request,700*attempts);return}state.loading=false;state.error=null;render()})}request()}
window.onerror=function(msg){if(app)app.innerHTML='<div class="notice" style="margin:20px">表示エラー：'+esc(msg)+'<br><button onclick="location.reload()">再読み込み</button></div>';return false};
clearOldPwa();render();setTimeout(load,0);
})();
"""

MANIFEST = r'''{
  "name":"競馬展開AI",
  "short_name":"競馬展開AI",
  "description":"競馬の脚質・展開シミュレーション・S/A/B/C総合評価を確認するPWA",
  "start_url":"/?v=59",
  "scope":"/",
  "display":"standalone",
  "background_color":"#041126",
  "theme_color":"#0b1220",
  "lang":"ja"
}'''
SW = 'self.addEventListener("install",function(){self.skipWaiting()});self.addEventListener("activate",function(e){e.waitUntil(self.registration.unregister())});'

HERO_HORSE_WEBP = base64.b64decode('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')
PACE_PREVIEW_WEBP = base64.b64decode('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')

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

    def role_profile(self, role: str, name: str, cutoff: str, track: str, distance: int, condition: str) -> dict:
        """Condition-aware jockey/trainer record available strictly before the target race."""
        if role not in {"jockey", "trainer"} or not name:
            return {"overall": 0.5, "track": 0.5, "distance": 0.5, "condition": 0.5,
                    "leaderRate": 0.0, "early3Rate": 0.0, "starts": 0}
        rows = self.conn.execute(
            f"""
            SELECT e.finish, e.corner_positions_json, r.track, r.distance, r.condition
            FROM entries e
            JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
            WHERE e.{role}=? AND e.date<? AND e.finish>0
            ORDER BY e.date DESC, e.race_no DESC
            LIMIT 400
            """,
            (name, cutoff),
        ).fetchall()

        def rate(subset):
            if not subset:
                return 0.5
            top3 = sum(1 for x in subset if 0 < int(x["finish"] or 0) <= 3)
            return top3 / len(subset)

        track_rows = [x for x in rows if (x["track"] or "") == track]
        dist_rows = [x for x in rows if abs(int(x["distance"] or 0) - int(distance or 0)) <= 200]
        cond_rows = [x for x in rows if condition and condition != "不明" and (x["condition"] or "") == condition]
        lead = early3 = valid = 0
        for x in rows[:120]:
            try:
                pos = json.loads(x["corner_positions_json"] or "[]")
            except Exception:
                pos = []
            if not pos:
                continue
            first = _int(str(pos[0]))
            if first <= 0:
                continue
            valid += 1
            if first == 1:
                lead += 1
            if first <= 3:
                early3 += 1
        return {
            "overall": rate(rows),
            "track": rate(track_rows),
            "distance": rate(dist_rows),
            "condition": rate(cond_rows),
            "leaderRate": (lead / valid) if valid else 0.0,
            "early3Rate": (early3 / valid) if valid else 0.0,
            "starts": len(rows),
        }

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
            SELECT e.*, r.title, r.distance, r.weather, r.condition, r.field_size, r.prize1
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
                "raceNumber": int(row["race_no"] or 0),
                "raceId": f"nar-{row['date']}-{row['track']}-{int(row['race_no'] or 0):02d}",
                "title": row["title"] or f"{int(row['race_no'] or 0)}R",
                "distance": int(row["distance"] or 0),
                "condition": row["condition"] or "不明",
                "weather": row["weather"] or "不明",
                "finish": int(row["finish"] or 0),
                "timeSeconds": float(row["time_seconds"] or 0),
                "cornerPositions": json.loads(row["corner_positions_json"] or "[]"),
                "fieldSize": int(row["field_size"] or 0),
                "racePrize1": int(row["prize1"] or 0),
                "carriedWeight": float(row["carried_weight"] or 0),
                "jockey": row["jockey"] or "",
                "trainer": row["trainer"] or "",
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
                        "jockeyProfile": self.role_profile("jockey", e["jockey"], iso_date, race["track"], int(race["distance"] or 0), race["condition"] or "不明"),
                        "trainerProfile": self.role_profile("trainer", e["trainer"], iso_date, race["track"], int(race["distance"] or 0), race["condition"] or "不明"),
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
                    "fieldSize": int(race["field_size"] or len(entries)),
                    "racePrize1": int(race["prize1"] or 0),
                    "surface": "",
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
        "surface": raw.get("surface") or raw.get("trackType") or "",
        "fieldSize": int(raw.get("fieldSize") or len(horses)),
        "racePrize1": int(raw.get("racePrize1") or raw.get("prize1") or 0),
        "startTime": raw.get("startTime") or raw.get("actualStartTime") or "",
        "scheduledStartTime": raw.get("scheduledStartTime") or raw.get("originalStartTime") or raw.get("startTime") or raw.get("actualStartTime") or "",
        "horses": horses, "source": raw.get("source") or "中央本番フィード",
    })
    out["startTimeChanged"] = bool(out.get("scheduledStartTime") and out.get("startTime") and out.get("scheduledStartTime") != out.get("startTime"))
    return out


JRA_TRACK_CODES = {"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
JRA_CNAME_RE = re.compile(r"pw01dde(?:01|10)\d{20}/[0-9A-Fa-f]{2}")
JRA_HORSE_CNAME_RE = re.compile(r"pw01dud\d{12,}/[0-9A-Fa-f]{2}")
JRA_RESULT_CNAME_RE = re.compile(r"pw01sde(?:01|10)\d{20}/[0-9A-Fa-f]{2}")
_jra_cache_lock = threading.Lock()
_jra_text_cache: dict[str, tuple[float,str]] = {}

def _jra_decode(raw: bytes) -> str:
    for enc in ("utf-8","cp932","shift_jis"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8","ignore")

def _jra_request(url: str, cname: str | None = None, cache_sec: int = 1800) -> str:
    key=url+"|"+(cname or "")
    now=time.time()
    with _jra_cache_lock:
        hit=_jra_text_cache.get(key)
        if hit and now-hit[0] < cache_sec:
            return hit[1]
    headers={"User-Agent":"Mozilla/5.0 (compatible; KeibaPredictor/6.2; +https://www.jra.go.jp/)","Accept-Language":"ja,en;q=0.8"}
    data=None
    if cname:
        data=urllib.parse.urlencode({"cname":cname}).encode("ascii")
        headers["Content-Type"]="application/x-www-form-urlencoded"
    req=urllib.request.Request(url,data=data,headers=headers)
    with urllib.request.urlopen(req,timeout=float(os.getenv("JRA_OFFICIAL_TIMEOUT_SEC","12"))) as res:
        text=_jra_decode(res.read())
    with _jra_cache_lock:
        _jra_text_cache[key]=(now,text)
    return text

def _jra_attr_cname(tag, pattern) -> str:
    if not tag: return ""
    blob=" ".join(str(v) for v in tag.attrs.values())+" "+str(tag)
    m=pattern.search(blob)
    return m.group(0) if m else ""

def _jra_text(tag) -> str:
    return re.sub(r"\s+"," ",tag.get_text(" ",strip=True) if tag else "").strip()

def _jra_iso_date(y:int,m:int,d:int)->str:
    return f"{y:04d}-{m:02d}-{d:02d}"

def _jra_date_from_cname(cname:str)->str:
    m=re.search(r"(20\d{6})/[0-9A-Fa-f]{2}$",cname or "")
    if not m:return ""
    x=m.group(1);return f"{x[:4]}-{x[4:6]}-{x[6:8]}"

def _jra_race_no_from_cname(cname:str)->int:
    m=re.search(r"pw01dde(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "")
    return int(m.group(1)) if m else 0

def _jra_track_from_cname(cname:str)->str:
    m=re.search(r"pw01dde(?:01|10)(\d{2})",cname or "")
    return JRA_TRACK_CODES.get(m.group(1),"") if m else ""

def _jra_parse_time_seconds(txt:str)->float:
    m=re.search(r"(?<!\d)(\d{1,2}):(\d{2}\.\d)(?!\d)",txt or "")
    if not m:return 0.0
    return int(m.group(1))*60+float(m.group(2))

def _jra_parse_past_cell(cell, cutoff:str) -> dict | None:
    txt=_jra_text(cell)
    dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",txt)
    if not dm:return None
    iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
    if cutoff and iso>=cutoff:return None
    track=""
    for t in list(JRA_TRACK_CODES.values())+["門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"]:
        if re.search(r"(?:日|\s)"+re.escape(t)+r"(?:\s|$)",txt): track=t;break
    finish=0
    fm=re.search(r"(?:^|\s)(\d{1,2})着(?:\s|$)",txt)
    if fm: finish=int(fm.group(1))
    field=0
    fsm=re.search(r"(\d{1,2})頭",txt)
    if fsm: field=int(fsm.group(1))
    dist=0; surface=""
    dsm=re.search(r"(\d{3,4})(芝|ダ|障)",txt)
    if dsm: dist=int(dsm.group(1)); surface=dsm.group(2)
    cond="不明"
    for c in ["不良","稍重","重","良"]:
        if c in txt: cond=c;break
    weight=0.0
    wm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",txt)
    if wm: weight=float(wm.group(1))
    corners=[]
    for li in cell.find_all("li"):
        z=_jra_text(li)
        if re.fullmatch(r"\d{1,2}",z): corners.append(int(z))
    result_cname=_jra_attr_cname(cell,JRA_RESULT_CNAME_RE)
    rid=("jraresult-"+base64.urlsafe_b64encode(result_cname.encode()).decode().rstrip("=")) if result_cname else ""
    # title is best-effort: text between track and class/finish data
    title=""
    if track:
        after=txt.split(track,1)[1].strip()
        after=re.split(r"\s+(?:\d{1,2}着|\d{1,2}頭|\d+番)",after,1)[0]
        title=after[:60].strip()
    tm=_jra_parse_time_seconds(txt)
    return {"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond,"weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":corners,"carriedWeight":weight,"raceId":rid,"source":"JRA公式"}

def _jra_profile_runs(cname:str, cutoff:str, limit:int=5)->list[dict]:
    if not cname:return []
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessU.html",cname,86400)
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for table in soup.find_all("table"):
        head=_jra_text(table.find("thead") or table.find("tr"))
        if "年月日" not in head or "レース名" not in head: continue
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"])
            if len(cells)<8: continue
            vals=[_jra_text(c) for c in cells]
            dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",vals[0])
            if not dm:continue
            iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
            if cutoff and iso>=cutoff:continue
            track=vals[1]
            title=vals[2]
            disttxt=vals[3]
            dsm=re.search(r"(芝|ダ|障)(\d{3,4})",disttxt)
            surface=dsm.group(1) if dsm else ""; dist=int(dsm.group(2)) if dsm else 0
            cond=vals[4] if len(vals)>4 else "不明"
            field=_int(vals[5]) if len(vals)>5 else 0
            finish=_int(vals[7]) if len(vals)>7 else 0
            jockey=vals[8] if len(vals)>8 else ""
            cw=float(re.sub(r"[^0-9.]","",vals[9]) or 0) if len(vals)>9 else 0
            tm=_jra_parse_time_seconds(vals[11] if len(vals)>11 else "")
            rc=_jra_attr_cname(tr,JRA_RESULT_CNAME_RE)
            rid=("jraresult-"+base64.urlsafe_b64encode(rc.encode()).decode().rstrip("=")) if rc else ""
            out.append({"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond or "不明","weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":[],"carriedWeight":cw,"jockey":jockey,"raceId":rid,"source":"JRA公式競走馬情報"})
            if len(out)>=limit:return out
    return out

def _jra_merge_runs(a:list[dict],b:list[dict],limit:int=5)->list[dict]:
    allr=[];seen=set()
    for r in list(a or [])+list(b or []):
        if not isinstance(r,dict):continue
        key=(str(r.get("date") or ""),str(r.get("track") or ""),str(r.get("title") or ""),int(r.get("distance") or 0))
        if key in seen:continue
        seen.add(key);allr.append(r)
    allr.sort(key=lambda r:str(r.get("date") or ""),reverse=True)
    return allr[:limit]

def _jra_parse_race(cname:str, supplement_profiles: bool = True)->dict|None:
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,600)
    except Exception:return None
    soup=BeautifulSoup(html,"html.parser")
    full=_jra_text(soup)
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    if not date or not track or not race_no:return None
    sm=re.search(r"発走時刻[：:]\s*(\d{1,2})時(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
    dm=re.search(r"コース[：:]\s*([\d,]+)メートル（([^）]+)）",full)
    distance=int(dm.group(1).replace(",","")) if dm else 0
    course_desc=dm.group(2) if dm else ""
    surface="芝" if "芝" in course_desc else ("ダート" if "ダート" in course_desc else ("障害" if "障" in course_desc else ""))
    weather="不明"; condition="不明"
    wm=re.search(r"天候\s*([^\s]+)",full)
    if wm:weather=wm.group(1)[:4]
    cm=re.search(r"(?:芝|ダート)\s*(良|稍重|重|不良)",full)
    if cm:condition=cm.group(1)
    title=""
    for node in soup.find_all(["h1","h2","h3","span"]):
        cl=" ".join(node.get("class") or [])
        tx=_jra_text(node)
        if ("race_name" in cl or (node.name in ("h2","h3") and tx)) and "出馬表" not in tx and len(tx)<80:
            if not re.match(r"^\d+レース$",tx): title=tx;break
    if not title:title=f"{race_no}R"
    prize1=0
    pm=re.search(r"1着\s*([\d,.]+)",full)
    if pm:
        try:prize1=int(float(pm.group(1).replace(",",""))*10000)
        except:pass
    horses=[]
    target_table=None
    for table in soup.find_all("table"):
        tx=_jra_text(table.find("thead") or table)
        if "馬番" in tx and "前走" in tx:
            target_table=table;break
    if not target_table:return None
    for tr in target_table.find_all("tr"):
        cells=tr.find_all(["th","td"])
        if len(cells)<4:continue
        # horse number among first 3 cells
        no=0; noidx=-1
        for ci,c in enumerate(cells[:3]):
            mt=re.fullmatch(r"\s*(\d{1,2})\s*",_jra_text(c))
            if mt and 1<=int(mt.group(1))<=18:
                no=int(mt.group(1));noidx=ci;break
        if not no:continue
        frame_no=0
        fm=re.search(r"枠\s*(\d)",_jra_text(cells[0])+" "+str(cells[0]))
        if fm:frame_no=int(fm.group(1))
        # identify horse info and profile cells
        info=None; profile=None; horse_cname=""
        for c in cells:
            hc=_jra_attr_cname(c,JRA_HORSE_CNAME_RE)
            if hc:
                info=c;horse_cname=hc;break
        if info is None:
            info=cells[min(len(cells)-1,noidx+1)]
        info_i=cells.index(info)
        profile=cells[info_i+1] if info_i+1<len(cells) else None
        # horse name from horse profile link or first plausible link/text
        name=""
        for a in info.find_all("a"):
            if _jra_attr_cname(a,JRA_HORSE_CNAME_RE):
                name=_jra_text(a);break
        if not name:
            name=re.split(r"\d+(?:\.\d+)?\(?",_jra_text(info),1)[0].strip()[:40]
        if not name:continue
        infot=_jra_text(info); prot=_jra_text(profile)
        sex="";age=0
        sx=re.search(r"(牡|牝|せん)(\d+)",prot)
        if sx:sex=sx.group(1);age=int(sx.group(2))
        cw=0.0
        cwm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",prot)
        if cwm:cw=float(cwm.group(1))
        jockey=""
        links=[_jra_text(a) for a in profile.find_all("a")] if profile else []
        if links:jockey=links[-1]
        if not jockey and cwm:
            jockey=prot[cwm.end():].strip().split(" ")[0:3]
            jockey=" ".join(jockey).strip()
        trainer=""
        tm=re.search(r"([^\s]+(?:\s[^\s]+)?)\((?:美浦|栗東|本会外)\)",infot)
        if tm:trainer=tm.group(1).strip()
        prize=0
        prm=re.search(r"([\d,.]+)万円",infot)
        if prm:
            try:prize=int(float(prm.group(1).replace(",",""))*10000)
            except:pass
        past=[]
        past_cells=cells[info_i+2:info_i+6]
        for c in past_cells:
            rr=_jra_parse_past_cell(c,date)
            if rr:past.append(rr)
        # JRA card exposes 前走〜4走前. If all four slots were inspected and fewer
        # than four real runs exist, that is the horse's full career to date.
        career_complete=(len(past_cells)>=4 and len(past)<4)
        horses.append({"horseNumber":no,"frameNumber":frame_no or no,"name":name,"age":age,"sex":sex,"carriedWeight":cw,"jockey":jockey,"trainer":trainer,"prizeMoneyAtRace":prize,"recentRaces":past,"_jraHorseCname":horse_cname,"_jraCareerComplete":career_complete,"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}})
    if not horses:return None
    # Listing must stay fast. Full five-run profile supplementation is done only when needed.
    if supplement_profiles:
        def supplement(h):
            if len(h.get("recentRaces") or [])>=5 or h.get("_jraCareerComplete"):return h
            extra=_jra_profile_runs(h.get("_jraHorseCname") or "",date,5)
            h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],extra,5)
            return h
        workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            horses=list(pool.map(supplement,horses))
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(horses),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"horses":horses,"source":"JRA公式","jraCname":cname})

def fetch_jra_official(iso_date:str, lightweight: bool = False)->list[dict]:
    token=iso_date.replace("-","")
    try:
        home=_jra_request("https://www.jra.go.jp/",None,120)
    except Exception:
        return []
    seeds=[]
    for c in JRA_CNAME_RE.findall(home):
        if token in c and c not in seeds:
            seeds.append(c)
    if not seeds:
        return []

    # v48: a race page contains links to the other active venue(s) too.
    # v47 filtered those links to the first venue, which could leave only Nakayama.
    # Discover one seed per track first, then expand each venue to all race-number links.
    track_seed={}
    for c in seeds:
        tr=_jra_track_from_cname(c)
        if tr and tr not in track_seed:
            track_seed[tr]=c

    discovered=[]
    processed_tracks=set()
    queue=list(track_seed.items())
    guard=0
    while queue and guard<12:
        guard+=1
        track,seed=queue.pop(0)
        if track in processed_tracks:
            continue
        processed_tracks.add(track)
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",seed,180)
        except Exception:
            continue
        links=[]
        for c in JRA_CNAME_RE.findall(html):
            if token not in c:
                continue
            if c not in links:
                links.append(c)
            if c not in discovered:
                discovered.append(c)
        # Important: do NOT restrict to the current track. Any newly linked venue
        # becomes a seed and is expanded on its own page.
        for c in links:
            tr=_jra_track_from_cname(c)
            if tr and tr not in processed_tracks and all(q[0]!=tr for q in queue):
                queue.append((tr,c))

    for c in seeds:
        if c not in discovered:
            discovered.append(c)

    # prefer detailed 01 variant and deduplicate by venue/race number
    chosen={}
    for c in discovered:
        key=(_jra_track_from_cname(c),_jra_race_no_from_cname(c))
        if not key[0] or not key[1]:
            continue
        if key not in chosen or c.startswith("pw01dde01"):
            chosen[key]=c

    def one(c):
        try:
            return _jra_parse_race(c, supplement_profiles=not lightweight)
        except Exception as exc:
            print("JRA official race parse failed",c,exc)
            return None
    workers=max(2,min(8,int(os.getenv("JRA_RACE_WORKERS","6"))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        races=[x for x in pool.map(one,chosen.values()) if x]
    races.sort(key=lambda r:(r.get("track") or "",int(r.get("raceNumber") or 0)))
    return races

def fetch_central_feed(iso_date: str, history: bool = False) -> list[dict]:
    # Prefer a licensed feed when configured. Otherwise use the official JRA website.
    base = _clean(os.getenv("CENTRAL_HISTORY_FEED_URL", "")) if history else ""
    if not base:
        base = _clean(os.getenv("CENTRAL_FEED_URL", ""))
    if not base:
        # JRA official fallback is intended for current/near-current racecards.
        return fetch_jra_official(iso_date)
    if "{date}" in base:
        url = base.replace("{date}", iso_date)
    else:
        url = base + ("&" if "?" in base else "?") + "date=" + iso_date
    headers = {"User-Agent": "KeibaPredictor/6.2", "Accept": "application/json"}
    token = _clean(os.getenv("CENTRAL_HISTORY_FEED_TOKEN", "")) if history else ""
    if not token:
        token = _clean(os.getenv("CENTRAL_FEED_TOKEN", ""))
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=float(os.getenv("CENTRAL_FEED_TIMEOUT_SEC", "12"))) as response:
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


_nar_sync_io_lock = threading.Lock()
_history_lock = threading.Lock()
_history_started = False
_history_ready = False
_history_error = ""

def _history_worker(months_back: int | None = None):
    global _history_ready, _history_error
    # v43: do not block on-demand history behind an 18-month serial startup crawl.
    # Warm only the latest few months, in parallel. Deeper history is fetched only when needed.
    time.sleep(float(os.getenv("HISTORY_START_DELAY_SEC", "0.15")))
    today = datetime.now().date()
    if months_back is None:
        months_back = max(2, min(8, int(os.getenv("NAR_HISTORY_WARM_MONTHS", "4"))))
    seen = set()
    jobs = []
    for y, m in [(today.year, today.month)] + list(iter_months_back(today, months_back - 1)):
        if (y, m) not in seen:
            jobs.append((y, m)); seen.add((y, m))
    try:
        _, errors = _sync_nar_month_wave(jobs)
        _history_error = " | ".join(errors)
    except Exception as exc:
        _history_error = str(exc)
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


@app.on_event("startup")
def _startup_history_backfill():
    # v43: targeted race prefetch is faster than a competing global crawl.
    if str(os.getenv("NAR_BACKGROUND_WARM", "0")).lower() in {"1","true","yes","on"}:
        ensure_history_async()

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
        "status":"ok", "mode":"production-v49-young-horse-history-fix", "historyStarted":_history_started,
        "historyReady":_history_ready, "historyError":_history_error, "narCoverage":nar_coverage,
        "centralCoverage":central_coverage, "centralFeedConfigured":bool(os.getenv("CENTRAL_FEED_URL")), "jraOfficialFallback":True,
        "centralHistoryFeedConfigured":bool(os.getenv("CENTRAL_HISTORY_FEED_URL") or os.getenv("CENTRAL_FEED_URL")),
        "narHistoryMonths": max(2, min(8, int(os.getenv("NAR_HISTORY_WARM_MONTHS", "4")))),
    }

@app.post("/api/v1/history-backfill-one")
def history_backfill_one(months_ago: int = Query(1, ge=1, le=24)):
    target=datetime.now().date().replace(day=1)
    y,m=target.year,target.month
    for _ in range(months_ago):
        m-=1
        if m==0:y-=1;m=12
    def worker():
        try:NarSync().sync_month(y,m,force=False)
        except Exception as exc:print(f"manual history backfill failed: {exc}")
    threading.Thread(target=worker,daemon=True).start()
    return {"status":"started","year":y,"month":m}

@app.get("/api/v1/history-status")
def history_status():
    return {"started":_history_started,"ready":_history_ready,"error":_history_error}

@app.get("/api/v1/central-status")
def central_status():
    store = CentralStore()
    try:
        coverage = store.coverage()
    finally:
        store.conn.close()
    return {
        "feedConfigured": bool(os.getenv("CENTRAL_FEED_URL")),
        "historyFeedConfigured": bool(os.getenv("CENTRAL_HISTORY_FEED_URL") or os.getenv("CENTRAL_FEED_URL")), "jraOfficialFallback": True,
        "historyUsesLiveFeedFallback": bool(not os.getenv("CENTRAL_HISTORY_FEED_URL") and os.getenv("CENTRAL_FEED_URL")),
        "ingestEnabled": bool(os.getenv("CENTRAL_INGEST_TOKEN")),
        "coverage": coverage,
        "recentRuns": 5,
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
      "recommendedRecentRaceDepth":5,
      "recommendedPastFields":["date","track","distance","condition","weather","fieldSize","finish","timeSeconds","cornerPositions","carriedWeight","racePrize1"],
      "optionalResult":{"status":"確定","finishers":[{"finish":1,"horseNumber":1,"name":"馬名","timeSeconds":92.3,"cornerPositions":[2,2,1]}]},
    }

_live_refresh_lock = threading.Lock()
_live_refresh_last: dict[str, int] = {}
_live_refresh_running: set[str] = set()

def _schedule_live_refresh(iso_date: str):
    key = f"live:{iso_date}"
    now = int(time.time())
    with _live_refresh_lock:
        if key in _live_refresh_running or now - _live_refresh_last.get(key, 0) < 90:
            return
        _live_refresh_running.add(key)
    def worker():
        changed=False
        try:
            try:
                target = datetime.strptime(iso_date, "%Y-%m-%d").date()
                sync = NarSync()
                with _nar_sync_io_lock:
                    if iso_date == _today_iso():
                        sync.sync_daily(force=False)
                    else:
                        # Target only the selected month instead of a bulk history crawl.
                        sync.sync_month(target.year,target.month,force=False)
                changed=True
            except Exception as exc:
                print(f"NAR background sync failed: {exc}")
            if changed:
                # v48: an empty list may have been cached before the async NAR fetch finished.
                with _race_list_cache_lock:
                    _race_list_cache.pop(iso_date,None)
        finally:
            with _live_refresh_lock:
                _live_refresh_running.discard(key)
                _live_refresh_last[key] = int(time.time())
    threading.Thread(target=worker, daemon=True).start()


_central_refresh_lock = threading.Lock()
_central_refresh_running: set[str] = set()
_central_refresh_last: dict[str, int] = {}

def _schedule_central_refresh(iso_date: str):
    now=int(time.time())
    with _central_refresh_lock:
        if iso_date in _central_refresh_running:
            return
        # current day can refresh frequently; older dates are effectively immutable
        ttl=90 if iso_date==_today_iso() else 3600
        if now-_central_refresh_last.get(iso_date,0)<ttl:
            return
        _central_refresh_running.add(iso_date)
    def worker():
        try:
            if _clean(os.getenv("CENTRAL_FEED_URL", "")):
                rows=fetch_central_feed(iso_date)
            else:
                rows=fetch_jra_official(iso_date, lightweight=True)
            if rows:
                st=CentralStore()
                try: st.upsert(rows)
                finally: st.conn.close()
                with _race_list_cache_lock:
                    _race_list_cache.pop(iso_date,None)
        except Exception as exc:
            print(f"Central async refresh failed: {exc}")
        finally:
            with _central_refresh_lock:
                _central_refresh_running.discard(iso_date)
                _central_refresh_last[iso_date]=int(time.time())
    threading.Thread(target=worker,daemon=True).start()

def _central_refresh_status(iso_date: str) -> dict:
    with _central_refresh_lock:
        return {"running": iso_date in _central_refresh_running, "last": _central_refresh_last.get(iso_date,0)}

def _nar_month_needs_fetch(year: int, month: int) -> bool:
    cache_key = f"month-{year:04d}-{month:02d}"
    store = NarStore()
    try:
        synced = store.synced_at(cache_key)
    finally:
        try: store.conn.close()
        except Exception: pass
    if not synced:
        return True
    today = datetime.now().date()
    if year == today.year and month == today.month:
        return int(time.time()) - synced >= int(os.getenv("NAR_CURRENT_MONTH_TTL_SECONDS", "300"))
    return False


def _download_nar_month_only(year: int, month: int) -> tuple[int, int, bytes, Path]:
    dest = ARCHIVE_DIR / f"{year:04d}{month:02d}_race.zip"
    url = NAR_MONTHLY_RACE_URL.format(year=year, month=month)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/zip,application/octet-stream,*/*",
            "Referer": "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            "Accept-Language": "ja-JP,ja;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=float(os.getenv("NAR_FAST_TIMEOUT_SEC", "22"))) as response:
        data = response.read()
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise RuntimeError(f"NAR {year:04d}-{month:02d} was not ZIP")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return year, month, data, dest


def _sync_nar_month_wave(months: list[tuple[int, int]]) -> tuple[list[dict], list[str]]:
    # Download network-bound monthly ZIPs concurrently, then import sequentially into SQLite.
    # This keeps DB writes safe while removing the largest source of wait time.
    unique = list(dict.fromkeys(months))
    need = [(y, m) for y, m in unique if _nar_month_needs_fetch(y, m)]
    results: dict[tuple[int, int], tuple[int, int, bytes, Path]] = {}
    errors: list[str] = []
    workers = max(2, min(6, int(os.getenv("NAR_HISTORY_WORKERS", "6"))))
    if need:
        with ThreadPoolExecutor(max_workers=min(workers, len(need))) as pool:
            future_map = {pool.submit(_download_nar_month_only, y, m):(y, m) for y, m in need}
            for fut in as_completed(future_map):
                y, m = future_map[fut]
                try:
                    results[(y, m)] = fut.result()
                except Exception as exc:
                    errors.append(f"{y:04d}-{m:02d}:{exc}")
    sync = NarSync()
    out = []
    try:
        for y, m in unique:
            if (y, m) not in results:
                out.append({"status":"cached","cacheKey":f"month-{y:04d}-{m:02d}"})
                continue
            _, _, data, dest = results[(y, m)]
            try:
                with _nar_sync_io_lock:
                    info = sync.import_zip_bytes(data, f"month-{y:04d}-{m:02d}", dest)
                out.append({"status":"synced", **info})
            except Exception as exc:
                errors.append(f"{y:04d}-{m:02d}:import:{exc}")
    finally:
        try: sync.store.conn.close()
        except Exception: pass
    return out, errors


_race_history_lock = threading.Lock()
_race_history_jobs: dict[str, dict] = {}

def _months_from_race_date(iso_date: str, count: int):
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    y, m = d.year, d.month
    for _ in range(max(1, count)):
        yield y, m
        m -= 1
        if m == 0:
            y -= 1
            m = 12

def _history_counts(horse_names: list[str], cutoff: str) -> dict:
    names = [x for x in dict.fromkeys(horse_names) if x]
    if not names:
        return {"totalHorses":0,"horsesWithHistory":0,"horsesWith4Plus":0,"horsesWith5Plus":0,"horsesWith6Plus":0,"totalRuns":0,"counts":{},"underFive":[]}
    store = NarStore()
    try:
        placeholders = ",".join("?" for _ in names)
        rows = store.conn.execute(
            f"SELECT name,COUNT(*) cnt FROM entries WHERE name IN ({placeholders}) AND date<? AND finish>0 GROUP BY name",
            (*names, cutoff),
        ).fetchall()
        cmap = {r["name"]: int(r["cnt"] or 0) for r in rows}
    finally:
        try: store.conn.close()
        except Exception: pass
    counts = {name: int(cmap.get(name, 0)) for name in names}
    vals = list(counts.values())
    return {
        "totalHorses": len(names),
        "horsesWithHistory": sum(1 for v in vals if v > 0),
        "horsesWith4Plus": sum(1 for v in vals if v >= 4),
        "horsesWith5Plus": sum(1 for v in vals if v >= 5),
        "horsesWith6Plus": sum(1 for v in vals if v >= 6),
        "totalRuns": sum(vals),
        "counts": counts,
        "underFive": [name for name, v in counts.items() if v < 5],
    }

def _history_is_enough(cov: dict, months_done: int) -> bool:
    total = int(cov.get("totalHorses") or 0)
    if total <= 0:
        return True
    # v39: do not stop because "most" horses are covered.  The race prediction waits until
    # every runner has five prior starts in the local official-history store.  A horse with
    # fewer than five career starts can only be confirmed after the configured lookback is
    # exhausted; until then the crawler keeps going.
    five = int(cov.get("horsesWith5Plus") or 0)
    return five >= total

def _start_race_history_search(race_id: str, iso_date: str, horse_names: list[str], force: bool = False) -> dict:
    max_months = max(12, min(84, int(os.getenv("NAR_ON_DEMAND_HISTORY_MONTHS", "60"))))
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        cov = _history_counts(horse_names, iso_date)
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"","source":"NAR公式月次レースデータ"}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        months = list(_months_from_race_date(iso_date, max_months))
        wave = max(2, min(6, int(os.getenv("NAR_ON_DEMAND_WAVE_MONTHS", "6"))))
        try:
            for pos in range(0, len(months), wave):
                batch = months[pos:pos+wave]
                _, errs = _sync_nar_month_wave(batch)
                errors.extend(errs)
                months_done += len(batch)
                cov_now = _history_counts(horse_names, iso_date)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"NAR公式 高速並列履歴"}
                if _history_is_enough(cov_now, months_done):
                    break
            cov_now = _history_counts(horse_names, iso_date)
            status = "done" if cov_now.get("horsesWithHistory",0) > 0 else ("error" if errors else "done")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"NAR公式 高速並列履歴"}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
        except Exception as exc:
            errors.append(str(exc))
            cov_now = _history_counts(horse_names, iso_date)
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":"error","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"NAR公式 高速並列履歴"}
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)

def _race_history_status(race_id: str) -> dict | None:
    with _race_history_lock:
        x = _race_history_jobs.get(race_id)
        return dict(x) if x else None

def _new_conn(path: Path):
    conn = sqlite3.connect(path, timeout=1.5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=1200")
    except Exception:
        pass
    return conn


def nar_race_summaries(iso_date: str) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = _new_conn(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT r.*,
                   COUNT(e.horse_no) AS entry_count,
                   SUM(CASE WHEN e.finish=1 THEN 1 ELSE 0 END) AS f1,
                   SUM(CASE WHEN e.finish=2 THEN 1 ELSE 0 END) AS f2,
                   SUM(CASE WHEN e.finish=3 THEN 1 ELSE 0 END) AS f3
            FROM races r
            LEFT JOIN entries e ON e.track=r.track AND e.date=r.date AND e.race_no=r.race_no
            WHERE r.date=?
            GROUP BY r.track,r.date,r.race_no
            ORDER BY r.track,r.race_no
            """,
            (iso_date,),
        ).fetchall()
        out=[]
        for r in rows:
            count=int(r["entry_count"] or r["field_size"] or 0)
            finalized=count>0 and int(r["f1"] or 0)>0 and int(r["f2"] or 0)>0 and (count<3 or int(r["f3"] or 0)>0)
            out.append({
                "id":f"nar-{iso_date}-{r['track']}-{int(r['race_no']):02d}",
                "circuit":"地方","date":iso_date,"track":r["track"],"raceNumber":int(r["race_no"]),
                "title":r["title"] or f"{int(r['race_no'])}R","distance":int(r["distance"] or 0),
                "condition":r["condition"] or "不明","weather":r["weather"] or "不明",
                "fieldSize":count,"racePrize1":int(r["prize1"] or 0),"surface":"",
                "startTime":r["start_time"] or "","scheduledStartTime":r["scheduled_start_time"] or r["start_time"] or "",
                "startTimeChanged":bool((r["scheduled_start_time"] or "") and (r["start_time"] or "") and r["scheduled_start_time"]!=r["start_time"]),
                "horses":[],"result":{"status":"確定","finishers":[{"finish":1}]} if finalized else None,"source":"NAR公式"
            })
        return out
    finally:
        conn.close()


def central_race_summaries(iso_date: str) -> list[dict]:
    if not CENTRAL_DB_PATH.exists():
        return []
    conn=_new_conn(CENTRAL_DB_PATH)
    try:
        rows=conn.execute("SELECT payload FROM central_races WHERE date=? ORDER BY track,race_no",(iso_date,)).fetchall()
        out=[]
        for x in rows:
            try:r=json.loads(x["payload"])
            except Exception:continue
            hs=r.get("horses") if isinstance(r.get("horses"),list) else []
            q=dict(r);q["fieldSize"]=int(q.get("fieldSize") or len(hs));q["horses"]=[]
            # Keep only status/minimal result on the list page.
            res=q.get("result") if isinstance(q.get("result"),dict) else None
            if res:q["result"]={"status":res.get("status") or "確定","finishers":[{"finish":1}]} if (res.get("finishers") or res.get("status")=="確定") else None
            out.append(q)
        return out
    finally:
        conn.close()


def nar_race_detail(race_id: str) -> dict | None:
    m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
    if not m:return None
    iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
    store=NarStore()
    try:
        race=store.conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
        if not race:return None
        entries=store.conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        horses=[]
        for e in entries:
            horses.append({
                "id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),"horseNumber":int(e["horse_no"]),
                "frameNumber":int(e["frame_no"] or 0),"name":e["name"],"age":int(e["age"] or 0),"sex":e["sex"] or "牡",
                "carriedWeight":float(e["carried_weight"] or 0),"jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "jockeyStats":store.stats("jockey",e["jockey"],iso_date),"trainerStats":store.stats("trainer",e["trainer"],iso_date),
                "jockeyProfile":store.role_profile("jockey",e["jockey"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "trainerProfile":store.role_profile("trainer",e["trainer"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "prizeMoneyAtRace":store.prize_before(e["name"],iso_date),"recentRaces":store.recent_races(e["name"],iso_date,5),
            })
        finishers=[]
        for e in entries:
            fin=int(e["finish"] or 0)
            if fin>0:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"],x["horseNumber"]))
        need=min(3,len(entries)); ranks={x["finish"] for x in finishers}; finalized=need>0 and all(i in ranks for i in range(1,need+1))
        return {"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),"condition":race["condition"] or "不明",
                "weather":race["weather"] or "不明","fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "","scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "startTimeChanged":bool((race["scheduled_start_time"] or "") and (race["start_time"] or "") and race["scheduled_start_time"]!=race["start_time"]),
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,"source":"NAR公式"}
    finally:
        try:store.conn.close()
        except Exception:pass



def _horse_key(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", _clean(str(value or "")))


def _central_find_horse(race: dict, horse_name: str) -> tuple[dict | None, dict | None]:
    key = _horse_key(horse_name)
    horse = None
    for h in race.get("horses", []) or []:
        if _horse_key(h.get("name")) == key:
            horse = h
            break
    finisher = None
    result = race.get("result") if isinstance(race.get("result"), dict) else {}
    finishers = result.get("finishers") if isinstance(result.get("finishers"), list) else []
    for f in finishers:
        same_no = horse is not None and int(f.get("horseNumber") or 0) == int(horse.get("horseNumber") or 0)
        same_name = _horse_key(f.get("name")) == key
        if same_no or same_name:
            finisher = f
            break
    return horse, finisher


def _central_run_from_race(race: dict, horse_name: str) -> dict | None:
    horse, fin = _central_find_horse(race, horse_name)
    if horse is None and fin is None:
        return None
    horse = horse or {}
    fin = fin or {}
    finish = int(fin.get("finish") or horse.get("finish") or 0)
    corners = fin.get("cornerPositions") or horse.get("cornerPositions") or []
    if not isinstance(corners, list):
        corners = []
    return {
        "raceId": race.get("id") or "",
        "date": race.get("date") or "",
        "track": race.get("track") or "",
        "raceNumber": int(race.get("raceNumber") or 0),
        "title": race.get("title") or "",
        "distance": int(race.get("distance") or 0),
        "condition": race.get("condition") or "不明",
        "weather": race.get("weather") or "不明",
        "surface": race.get("surface") or "",
        "fieldSize": int(race.get("fieldSize") or len(race.get("horses") or [])),
        "finish": finish,
        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),
        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],
        "carriedWeight": float(horse.get("carriedWeight") or fin.get("carriedWeight") or 0),
        "racePrize1": int(race.get("racePrize1") or 0),
        "jockey": horse.get("jockey") or fin.get("jockey") or "",
        "trainer": horse.get("trainer") or fin.get("trainer") or "",
        "source": race.get("source") or "中央フィード",
    }


def _central_resolve_race_id(run: dict) -> str:
    if run.get("raceId"):
        return str(run.get("raceId"))
    d = _clean(str(run.get("date") or ""))
    tr = _clean(str(run.get("track") or ""))
    rn = int(run.get("raceNumber") or 0)
    if not d or not tr or rn <= 0 or not CENTRAL_DB_PATH.exists():
        return ""
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        row = conn.execute(
            "SELECT id FROM central_races WHERE date=? AND track=? AND race_no=? LIMIT 1",
            (d, tr, rn),
        ).fetchone()
        return str(row["id"]) if row else ""
    finally:
        conn.close()


def _central_recent_from_store(horse_name: str, cutoff: str, limit: int = 5) -> list[dict]:
    if not CENTRAL_DB_PATH.exists() or not horse_name:
        return []
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        # Pull newest races first. We stop as soon as this horse has five actual starts.
        rows = conn.execute(
            "SELECT payload FROM central_races WHERE date<? ORDER BY date DESC,track DESC,race_no DESC LIMIT 4000",
            (cutoff,),
        ).fetchall()
        out = []
        seen = set()
        for row in rows:
            try:
                race = json.loads(row["payload"])
            except Exception:
                continue
            run = _central_run_from_race(race, horse_name)
            if not run:
                continue
            key = (run.get("date"), run.get("track"), int(run.get("raceNumber") or 0))
            if key in seen:
                continue
            seen.add(key)
            # A finish can be missing in a future-entry payload. Keep the race only when
            # the historical payload contains an actual result or explicit run result data.
            if int(run.get("finish") or 0) <= 0 and not run.get("cornerPositions") and not float(run.get("timeSeconds") or 0):
                continue
            out.append(run)
            if len(out) >= limit:
                break
        return out
    finally:
        conn.close()


def _merge_central_recent(existing: list[dict], stored: list[dict], cutoff: str, limit: int = 5) -> list[dict]:
    all_runs = []
    seen = set()
    for src in (existing or []) + (stored or []):
        if not isinstance(src, dict):
            continue
        run = dict(src)
        if cutoff and run.get("date") and str(run.get("date")) >= cutoff:
            continue
        rid = _central_resolve_race_id(run)
        if rid:
            run["raceId"] = rid
        key = run.get("raceId") or (str(run.get("date") or "") + "|" + str(run.get("track") or "") + "|" + str(int(run.get("raceNumber") or 0)))
        if key in seen:
            continue
        seen.add(key)
        all_runs.append(run)
    all_runs.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("raceNumber") or 0)), reverse=True)
    return all_runs[:limit]


def _central_detail_coverage(detail: dict) -> dict:
    horses = detail.get("horses", []) or []
    counts = {str(h.get("name") or ""): min(5, len(h.get("recentRaces") or [])) for h in horses if h.get("name")}
    complete = {str(h.get("name") or ""): bool(h.get("_jraCareerComplete")) for h in horses if h.get("name")}
    vals = list(counts.values())
    resolved = sum(1 for name,v in counts.items() if v >= 5 or complete.get(name, False))
    return {
        "totalHorses": len(counts),
        "horsesWithHistory": sum(1 for v in vals if v > 0),
        "horsesWith4Plus": sum(1 for v in vals if v >= 4),
        "horsesWith5Plus": sum(1 for v in vals if v >= 5),
        "horsesResolved": resolved,
        "horsesCareerComplete": sum(1 for name in counts if complete.get(name, False)),
        "totalRuns": sum(vals),
        "counts": counts,
        "underFive": [name for name, v in counts.items() if v < 5 and not complete.get(name, False)],
    }

def _central_month_dates(year: int, month: int, cutoff: str) -> list[str]:
    last = calendar.monthrange(year, month)[1]
    cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d").date()
    dates = []
    # JRA standard meetings are Sat/Sun and holiday Mondays. Searching these days first
    # avoids hundreds of empty requests while still covering ordinary and holiday meetings.
    for day in range(last, 0, -1):
        d = dt_date(year, month, day)
        if d >= cutoff_date:
            continue
        if d.weekday() in (0, 5, 6):
            dates.append(d.isoformat())
    return dates


def _fetch_central_days_parallel(days: list[str]) -> tuple[list[dict], list[str]]:
    if not days:
        return [], []
    workers = max(2, min(10, int(os.getenv("CENTRAL_HISTORY_WORKERS", "6"))))
    rows: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(days))) as pool:
        future_map = {pool.submit(fetch_central_feed, day, True):day for day in days}
        for fut in as_completed(future_map):
            day = future_map[fut]
            try:
                rows.extend(fut.result() or [])
            except Exception as exc:
                errors.append(f"{day}:{exc}")
    return rows, errors


def _start_central_history_search(race_id: str, iso_date: str, force: bool = False) -> dict:
    max_months = max(12, min(60, int(os.getenv("CENTRAL_ON_DEMAND_HISTORY_MONTHS", "36"))))
    detail = central_race_detail(race_id)
    cov = _central_detail_coverage(detail or {})
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        has_feed=bool(_clean(os.getenv("CENTRAL_HISTORY_FEED_URL", "")) or _clean(os.getenv("CENTRAL_FEED_URL", "")))
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"",
               "source":"中央フィード高速並列検索" if has_feed else "JRA公式 競走馬情報5走補完"}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        store = CentralStore()
        try:
            # With no external central feed, use each horse's official JRA profile directly.
            if not has_feed:
                current=central_race_detail(race_id) or {}
                horses=current.get("horses") or []
                cutoff=current.get("date") or iso_date
                def fill(h):
                    h=dict(h)
                    try:
                        extra=_jra_profile_runs(h.get("_jraHorseCname") or "",cutoff,5)
                        h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],extra,5)
                    except Exception as exc:
                        errors.append(str(exc))
                    return h
                workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
                with ThreadPoolExecutor(max_workers=min(workers,max(1,len(horses)))) as pool:
                    current["horses"]=list(pool.map(fill,horses)) if horses else []
                current["source"]="JRA公式"
                store.upsert([current])
                fresh_detail=central_race_detail(race_id) or current
                cov_now=_central_detail_coverage(fresh_detail)
                with _race_history_lock:
                    _race_history_jobs[race_id]={"status":"done" if cov_now.get("horsesWithHistory",0)>0 else "error",
                        "monthsDone":0,"maxMonths":0,"coverage":cov_now,"error":" | ".join(errors[-5:]),
                        "source":"JRA公式 競走馬情報5走補完"}
                with _detail_cache_lock:
                    _detail_cache.pop(race_id,None)
                return
            for y, m in _months_from_race_date(iso_date, max_months):
                days = _central_month_dates(y, m, iso_date)
                fresh_rows, errs = _fetch_central_days_parallel(days)
                errors.extend(errs)
                if fresh_rows:
                    store.upsert(fresh_rows)
                months_done += 1
                fresh_detail = central_race_detail(race_id) or {}
                cov_now = _central_detail_coverage(fresh_detail)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,
                                                   "coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"中央フィード高速並列検索"}
                if _history_is_enough(cov_now, months_done):
                    break
            fresh_detail = central_race_detail(race_id) or {}
            cov_now = _central_detail_coverage(fresh_detail)
            status = "done" if cov_now.get("horsesWithHistory", 0) > 0 else ("error" if errors else "done")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,
                                               "coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"中央フィード高速並列検索"}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
        finally:
            try:
                store.conn.close()
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)


def central_race_detail(race_id: str) -> dict | None:
    if not CENTRAL_DB_PATH.exists():return None
    conn=_new_conn(CENTRAL_DB_PATH)
    try:
        row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
        if not row:
            return None
        try:
            detail=json.loads(row["payload"])
        except Exception as exc:
            print("central payload decode failed",race_id,exc)
            return None
    finally:
        conn.close()
    cutoff = str(detail.get("date") or "9999-12-31")
    for h in detail.get("horses",[]) or []:
        try:
            stored = _central_recent_from_store(str(h.get("name") or ""), cutoff, 5)
            h["recentRaces"] = _merge_central_recent(h.get("recentRaces") or [], stored, cutoff, 5)
        except Exception as exc:
            # One horse's history must never reject the whole race detail.
            print("central horse history merge failed",race_id,h.get("name"),exc)
            h["recentRaces"] = [x for x in (h.get("recentRaces") or []) if isinstance(x,dict)][:5]
    return detail

_detail_cache_lock=threading.Lock()
_detail_cache:dict[str,tuple[float,dict]]={}

_race_list_cache_lock = threading.Lock()
_race_list_cache: dict[str, tuple[float, list[dict]]] = {}

@app.get("/api/v1/races")
def races(date: str = Query(...)):
    if str(os.getenv("NAR_BACKGROUND_WARM", "0")).lower() in {"1","true","yes","on"}:
        ensure_history_async()
    now=time.time()
    with _race_list_cache_lock:
        hit=_race_list_cache.get(date)
        if hit and now-hit[0]<10:
            return hit[1]
    try: live_local=nar_race_summaries(date)
    except Exception as exc:
        print(f"NAR summary read failed: {exc}"); live_local=[]
    try:
        central_rows=central_race_summaries(date)
    except Exception as exc:
        print(f"Central summary read failed: {exc}"); central_rows=[]
    # Never wait for JRA/central network on a screen request. Fetch in background and return immediately.
    _schedule_central_refresh(date)
    rows=live_local+central_rows
    with _race_list_cache_lock:
        _race_list_cache[date]=(now,rows)
        if len(_race_list_cache)>12:
            oldest=min(_race_list_cache.items(),key=lambda kv:kv[1][0])[0]; _race_list_cache.pop(oldest,None)
    # Never start the 18-month bulk backfill from a screen request.
    _schedule_live_refresh(date)
    return rows


@app.get("/api/v1/local-refresh-status")
def local_refresh_status(date: str = Query(...)):
    key=f"live:{date}"
    with _live_refresh_lock:
        running=key in _live_refresh_running
        last=_live_refresh_last.get(key,0)
    try:
        count=len(nar_race_summaries(date))
    except Exception:
        count=0
    return {"running":running,"last":last,"count":count}

@app.get("/api/v1/central-refresh-status")
def central_refresh_status(date: str = Query(...)):
    st=_central_refresh_status(date)
    try: st["count"]=len(central_race_summaries(date))
    except Exception: st["count"]=0
    return st

@app.get("/api/v1/race/{race_id}")
def race_detail(race_id: str, refresh: int = Query(0), history: int = Query(1)):
    now=time.time()
    if not refresh and history:
        with _detail_cache_lock:
            hit=_detail_cache.get(race_id)
            if hit and now-hit[0]<30:
                cached = hit[1]
                hs = cached.get("historySearch") if isinstance(cached, dict) else None
                if not hs or hs.get("status") != "running":
                    return cached
    detail=nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:
        raise HTTPException(status_code=404,detail="race not found")
    if race_id.startswith("nar-") and history:
        names=[str(h.get("name") or "") for h in detail.get("horses",[]) if h.get("name")]
        cov=_history_counts(names, detail.get("date") or "9999-12-31")
        hs=_race_history_status(race_id)
        if hs is None and not _history_is_enough(cov, 0):
            hs=_start_race_history_search(race_id, detail.get("date") or _today_iso(), names)
        elif hs is None:
            hs={"status":"done","monthsDone":0,"maxMonths":0,"coverage":cov,"error":"","source":"NAR公式ローカル履歴"}
        detail["historySearch"]=hs
        if refresh and hs and hs.get("status") in {"running","done","error"}:
            fresh=nar_race_detail(race_id)
            if fresh:
                detail=fresh; detail["historySearch"]=_race_history_status(race_id) or hs
    elif history:
        cov=_central_detail_coverage(detail)
        hs=_race_history_status(race_id)
        central_resolved=int(cov.get("horsesResolved") or cov.get("horsesWith5Plus") or 0)
        central_total=int(cov.get("totalHorses") or 0)
        if hs is None and central_resolved < central_total:
            hs=_start_central_history_search(race_id, detail.get("date") or _today_iso())
        elif hs is None:
            hs={"status":"done","monthsDone":0,"maxMonths":0,"coverage":cov,"error":"","source":"中央フィード履歴"}
        detail["historySearch"]=hs
        if refresh and hs and hs.get("status") in {"running","done","error"}:
            fresh=central_race_detail(race_id)
            if fresh:
                detail=fresh; detail["historySearch"]=_race_history_status(race_id) or hs
    else:
        detail["historySearch"]={"status":"done","monthsDone":0,"maxMonths":0,"coverage":{"totalHorses":len(detail.get("horses",[])),"totalRuns":sum(len(h.get("recentRaces") or []) for h in detail.get("horses",[]))},"error":"","source":detail.get("source") or ("NAR公式ローカル履歴" if race_id.startswith("nar-") else "中央フィード")}
    if history:
        with _detail_cache_lock:
            _detail_cache[race_id]=(now,detail)
            if len(_detail_cache)>24:
                oldest=min(_detail_cache.items(),key=lambda kv:kv[1][0])[0]; _detail_cache.pop(oldest,None)
    return detail

@app.get("/build")
def build_info():
    return {"build":"v60","appVersion":"7.3-production-v60-runtime-deps-fixed","recentRuns":5,"marks":True,"horseModalSwipe":True,"runtimeDepsFixed":True,"grade":"S/A/B/C + ◎○▲☆△注","history":"NAR + JRA公式/central feed auto-search","pastRaceOpen":True,"historySpeed":"instant-render+background-fill+parallel-prefetch","narWorkers":int(os.getenv("NAR_HISTORY_WORKERS","6")),"centralWorkers":int(os.getenv("CENTRAL_HISTORY_WORKERS","6"))}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(INDEX, headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/hero-horse.webp")
def hero_horse():
    return Response(HERO_HORSE_WEBP, media_type="image/webp", headers={"Cache-Control":"public, max-age=86400"})

@app.get("/pace-preview.webp")
def pace_preview():
    return Response(PACE_PREVIEW_WEBP, media_type="image/webp", headers={"Cache-Control":"public, max-age=86400"})

@app.get("/styles-v60.css")
def styles():
    return Response(CSS, media_type="text/css", headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/app-v60.js")
def appjs():
    return Response(JS, media_type="application/javascript", headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/manifest-v60.webmanifest")
def manifest():
    return Response(MANIFEST, media_type="application/manifest+json", headers={"Cache-Control":"no-store, max-age=0"})

@app.get("/sw.js")
def service_worker():
    return Response(SW, media_type="application/javascript", headers={"Service-Worker-Allowed":"/", "Cache-Control":"no-store, max-age=0"})
