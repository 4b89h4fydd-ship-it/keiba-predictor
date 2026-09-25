from fastapi import FastAPI, Query
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

app = FastAPI(title="競馬展開AI", version="2.1-ui-v4")

INDEX = '<!doctype html>\n<html lang="ja">\n<head>\n  <meta charset="utf-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />\n  <meta name="theme-color" content="#0f172a" />\n  <meta name="apple-mobile-web-app-capable" content="yes" />\n  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />\n  <meta name="apple-mobile-web-app-title" content="競馬展開AI" />\n  <link rel="manifest" href="./manifest.webmanifest" />\n  <link rel="apple-touch-icon" href="./assets/icon-192.png" />\n  <link rel="stylesheet" href="./styles.css" />\n  <title>競馬展開AI</title>\n</head>\n<body>\n  <div id="app"></div>\n  <script type="module" src="./app.js"></script>\n</body>\n</html>\n'
CSS = ':root {\n  --bg: #f5f6fa;\n  --card: #ffffff;\n  --text: #111827;\n  --muted: #6b7280;\n  --line: #e5e7eb;\n  --dark: #0f172a;\n  --soft: #f8fafc;\n  --accent: #111827;\n  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Hiragino Sans", "Noto Sans JP", sans-serif;\n  color: var(--text);\n  background: var(--bg);\n}\n* { box-sizing: border-box; }\nbody { margin: 0; min-height: 100vh; background: var(--bg); }\nbutton, input, select { font: inherit; }\nbutton { cursor: pointer; }\n.shell { max-width: 880px; margin: 0 auto; padding-bottom: calc(28px + env(safe-area-inset-bottom)); }\n.header { position: sticky; top: 0; z-index: 20; padding: calc(10px + env(safe-area-inset-top)) 16px 12px; background: rgba(15,23,42,.96); color: white; backdrop-filter: blur(14px); }\n.header-row { display:flex; align-items:center; justify-content:space-between; gap: 10px; }\n.header-title-wrap { min-width:0; flex:1; }\n.header-title-wrap h1, .header-title-wrap small { display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }\n.header h1 { margin: 0; font-size: 20px; }\n.header small { color: #cbd5e1; }\n.icon-btn { border: 0; background: rgba(255,255,255,.12); color: white; border-radius: 12px; padding: 9px 11px; }\n.main { padding: 14px; display: grid; gap: 12px; }\n.card { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 15px; box-shadow: 0 8px 26px rgba(15,23,42,.04); }\n.card h2 { margin: 0 0 10px; font-size: 17px; }\n.card h3 { margin: 0 0 8px; font-size: 15px; }\n.muted { color: var(--muted); }\n.row { display:flex; gap: 10px; align-items:center; flex-wrap: wrap; }\n.row.between { justify-content: space-between; }\n.segment { display:grid; grid-template-columns:1fr 1fr; gap: 8px; }\n.segment button { border:1px solid var(--line); background:white; border-radius:14px; padding:12px; font-weight:700; }\n.segment button.active { background:var(--dark); color:white; border-color:var(--dark); }\n.date-input { width:100%; border:1px solid var(--line); border-radius:14px; padding:12px; background:white; }\n.venue-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }\n.venue-btn { text-align:left; border:1px solid var(--line); background:white; border-radius:15px; padding:13px; }\n.venue-btn strong { display:block; }\n.venue-btn span { font-size:12px; color:var(--muted); }\n.race-list { display:grid; gap:9px; }\n.race-btn { width:100%; text-align:left; border:1px solid var(--line); background:white; border-radius:15px; padding:12px 13px; display:flex; justify-content:space-between; gap:12px; align-items:center; }\n.race-btn.disabled { opacity:.45; }\n.pill { display:inline-flex; align-items:center; gap:5px; border-radius:999px; padding:5px 9px; background:#eef2f7; font-size:12px; font-weight:700; }\n.metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }\n.metric { background:var(--soft); border-radius:14px; padding:10px; }\n.metric b { display:block; font-size:15px; }\n.metric span { font-size:11px; color:var(--muted); }\n.section-title { font-size:18px; font-weight:800; margin:5px 0 3px; }\n.table-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; border:1px solid var(--line); border-radius:14px; }\ntable { width:100%; border-collapse:collapse; min-width:760px; background:white; }\nth, td { padding:9px 8px; border-bottom:1px solid var(--line); text-align:center; font-size:12px; white-space:nowrap; }\nth { position:sticky; top:0; background:#f8fafc; z-index:1; font-size:11px; color:#475569; }\ntd.name { text-align:left; font-weight:700; }\n.score { font-weight:900; font-variant-numeric:tabular-nums; }\n.stage { padding:10px 0; border-bottom:1px solid var(--line); }\n.stage:last-child { border-bottom:0; }\n.stage b { display:block; font-size:12px; color:var(--muted); margin-bottom:4px; }\n.stage div { font-size:17px; font-weight:800; line-height:1.55; }\n.scenario-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }\n.scenario { background:var(--soft); border-radius:14px; padding:11px; min-height:104px; }\n.scenario .prob { font-size:22px; font-weight:900; }\n.scenario .horses { margin-top:8px; font-weight:800; }\n.marks { display:grid; gap:7px; }\n.mark-row { display:flex; align-items:center; gap:10px; background:var(--soft); border-radius:14px; padding:10px 12px; }\n.mark-symbol { width:28px; font-size:21px; font-weight:900; text-align:center; }\n.horse-card { border:1px solid var(--line); border-radius:14px; padding:11px; margin-top:9px; }\n.horse-card summary { cursor:pointer; font-weight:800; }\n.horse-detail { display:grid; gap:8px; padding-top:9px; }\n.statline { font-size:12px; color:#374151; }\n.recent { border-top:1px dashed var(--line); padding-top:8px; font-size:12px; }\n.back-btn { border:0; background:transparent; color:white; font-weight:700; padding:6px 0; }\n.empty { text-align:center; color:var(--muted); padding:28px 10px; }\n.notice { border-radius:14px; padding:11px 12px; background:#fff7ed; color:#9a3412; font-size:12px; }\n@media (max-width:620px) {\n  .main { padding:10px; }\n  .card { border-radius:16px; padding:13px; }\n  .scenario-grid { grid-template-columns:1fr; }\n  .metrics { grid-template-columns:1fr 1fr; }\n}\n\n/* iPhone compact home */\n@media (max-width:620px) {\n  .home-shell { min-height:100dvh; overflow:hidden; }\n  .home-shell .header { padding:calc(5px + env(safe-area-inset-top)) 12px 6px; }\n  .home-shell .header h1 { font-size:18px; }\n  .home-shell .header small { font-size:10px; }\n  .home-shell .icon-btn { padding:6px 8px; border-radius:10px; }\n  .home-shell .main { padding:7px 8px; gap:7px; }\n  .home-shell .card { padding:9px 10px; border-radius:13px; }\n  .home-shell .card h2 { font-size:14px; margin:0 0 5px; }\n  .home-shell .setup-grid { display:grid; grid-template-columns:1.15fr .85fr; gap:8px; align-items:end; }\n  .home-shell .setup-block label { display:block; font-size:10px; color:var(--muted); margin-bottom:3px; font-weight:800; }\n  .home-shell .date-input { padding:7px 8px; min-height:38px; border-radius:10px; font-size:14px; }\n  .home-shell .segment { gap:5px; }\n  .home-shell .segment button { padding:7px 4px; border-radius:10px; font-size:13px; }\n  .home-shell .venue-grid { gap:6px; }\n  .home-shell .venue-btn { padding:8px 9px; border-radius:11px; min-height:48px; }\n  .home-shell .venue-btn strong { font-size:15px; line-height:1.05; }\n  .home-shell .venue-btn span { font-size:10px; }\n  .home-shell .pill { padding:3px 7px; font-size:10px; }\n  .home-shell .empty { padding:14px 8px; font-size:12px; }\n}\n\n/* iPhone compact prediction - no horizontal scrolling */\n.style-map-list { display:grid; gap:6px; }\n.style-map-row { border:1px solid var(--line); border-radius:12px; padding:8px 9px; background:#fff; }\n.style-map-top { display:grid; grid-template-columns:auto minmax(0,1fr) auto auto; gap:6px; align-items:center; }\n.style-rank { width:22px; height:22px; border-radius:999px; display:grid; place-items:center; background:#eef2f7; font-size:10px; font-weight:900; }\n.style-horse { min-width:0; font-size:13px; font-weight:900; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }\n.style-score { font-size:13px; font-weight:900; font-variant-numeric:tabular-nums; }\n.style-expected { font-size:10px; font-weight:800; padding:3px 6px; border-radius:999px; background:#f1f5f9; white-space:nowrap; }\n.style-rate-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:3px; margin-top:6px; }\n.style-rate { background:var(--soft); border-radius:8px; padding:4px 2px; text-align:center; min-width:0; }\n.style-rate b { display:block; font-size:9px; color:var(--muted); line-height:1.1; }\n.style-rate span { display:block; font-size:10px; font-weight:900; margin-top:2px; font-variant-numeric:tabular-nums; }\n.prediction-shell .table-wrap { overflow-x:hidden; }\n.prediction-shell table { min-width:0; }\n@media (max-width:620px) {\n  .prediction-shell .header { position:sticky !important; top:0; z-index:50; padding:calc(5px + env(safe-area-inset-top)) 10px 6px; box-shadow:0 2px 10px rgba(15,23,42,.18); }\n  .prediction-shell .header h1 { font-size:17px; }\n  .prediction-shell .header small { font-size:9px; }\n  .prediction-shell .main { padding:7px 8px; gap:7px; }\n  .prediction-shell .card { padding:9px 10px; border-radius:13px; }\n  .prediction-shell .section-title { font-size:15px; margin:1px 0 4px; }\n  .prediction-shell .metrics { grid-template-columns:repeat(5,1fr); gap:4px; }\n  .prediction-shell .metric { padding:6px 3px; text-align:center; border-radius:9px; }\n  .prediction-shell .metric b { font-size:11px; }\n  .prediction-shell .metric span { font-size:8px; }\n  .prediction-shell .stage { padding:5px 0; }\n  .prediction-shell .stage b { font-size:9px; margin-bottom:1px; }\n  .prediction-shell .stage div { font-size:12px; line-height:1.35; }\n  .prediction-shell .scenario-grid { grid-template-columns:repeat(3,1fr); gap:4px; }\n  .prediction-shell .scenario { padding:7px 5px; min-height:72px; border-radius:10px; }\n  .prediction-shell .scenario b { font-size:9px; }\n  .prediction-shell .scenario .prob { font-size:17px; }\n  .prediction-shell .scenario .horses { margin-top:4px; font-size:10px; }\n  .prediction-shell .marks { grid-template-columns:1fr 1fr; gap:5px; }\n  .prediction-shell .mark-row { padding:6px 7px; gap:6px; border-radius:10px; min-width:0; }\n  .prediction-shell .mark-symbol { width:20px; font-size:16px; }\n  .prediction-shell .mark-row strong { font-size:11px; display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }\n  .prediction-shell .mark-row .muted { display:none; }\n  .prediction-shell .horse-card { padding:8px; margin-top:5px; border-radius:10px; }\n  .prediction-shell .horse-card summary { font-size:11px; }\n  .prediction-shell .style-map-row { padding:6px 7px; }\n  .prediction-shell .style-map-top { grid-template-columns:auto minmax(0,1fr) auto; }\n  .prediction-shell .style-expected { grid-column:2 / 4; justify-self:start; margin-top:-2px; }\n  .prediction-shell .style-rate-grid { margin-top:4px; }\n}\n\n'
JS = 'const CENTRAL = ["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"];\nconst LOCAL = ["帯広","門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"];\nconst API_DEFAULT = localStorage.getItem("keiba_api_base") || window.location.origin;\nconst TODAY_JST = new Intl.DateTimeFormat("sv-SE", {timeZone:"Asia/Tokyo", year:"numeric", month:"2-digit", day:"2-digit"}).format(new Date());\n\nconst state = {\n  circuit: "地方",\n  date: TODAY_JST,\n  races: [],\n  selectedTrack: null,\n  selectedRace: null,\n  loading: false,\n  error: null,\n};\n\nconst app = document.querySelector("#app");\nconst circled = n => n >= 1 && n <= 20 ? String.fromCodePoint(0x245f + n) : String(n);\nconst pct = v => `${Math.round(v * 100)}%`;\nconst fmtMoney = n => new Intl.NumberFormat("ja-JP").format(n || 0);\nconst seasonOf = iso => {\n  const m = Number(String(iso).split("-")[1]);\n  if (m >= 3 && m <= 5) return "春";\n  if (m >= 6 && m <= 8) return "夏";\n  if (m >= 9 && m <= 11) return "秋";\n  return "冬";\n};\n\nfunction styleRates(horse) {\n  const counts = {front:0, stalk:0, mid:0, close:0};\n  let total = 0;\n  for (const r of horse.recentRaces || []) {\n    const first = r.cornerPositions?.[0];\n    if (!Number.isFinite(first)) continue;\n    total++;\n    if (first === 1) counts.front++;\n    else if (first <= 4) counts.stalk++;\n    else if (first <= 7) counts.mid++;\n    else counts.close++;\n  }\n  const d = total || 1;\n  return {front:counts.front/d, stalk:counts.stalk/d, mid:counts.mid/d, close:counts.close/d};\n}\nfunction fadeRate(horse) {\n  const eligible = (horse.recentRaces || []).filter(r => (r.cornerPositions?.[0] ?? 99) <= 4);\n  if (!eligible.length) return 0;\n  const faded = eligible.filter(r => {\n    const first = r.cornerPositions?.[0];\n    const last = r.cornerPositions?.at(-1);\n    return Number.isFinite(first) && Number.isFinite(last) && (last >= first + 2 || r.finish >= first + 3);\n  }).length;\n  return faded / eligible.length;\n}\nfunction styleScore(horse) {\n  const r = styleRates(horse);\n  return r.front*1 + r.stalk*2 + r.mid*3 + r.close*4;\n}\nfunction expectedStyle(score) {\n  if (score < 1.6) return "逃げ";\n  if (score < 2.35) return "先行";\n  if (score < 3.1) return "好位〜差し";\n  return "後方";\n}\nfunction occupancy(horses) {\n  const early = [], moved = [];\n  for (const h of horses) {\n    const last = h.recentRaces?.[0];\n    if (!last?.cornerPositions?.length) continue;\n    const pos = last.cornerPositions;\n    if (!pos.some(x => x <= 3)) continue;\n    if (pos[0] <= 3) early.push(h.horseNumber); else moved.push(h.horseNumber);\n  }\n  const nums = [...early, ...moved].sort((a,b)=>a-b);\n  return { rate: horses.length ? nums.length/horses.length : 0, nums, early, moved };\n}\nfunction styleMap(horses) {\n  return horses.map(h => {\n    const r = styleRates(h), score = styleScore(h);\n    return {horse:h, score, ...r, fade:fadeRate(h), expected:expectedStyle(score)};\n  }).sort((a,b)=> a.score-b.score || a.horse.horseNumber-b.horse.horseNumber);\n}\nfunction buildStages(rows) {\n  const nums = rows.map(r=>r.horse.horseNumber);\n  const n = nums.length;\n  const fEnd = Math.max(1, Math.ceil(n*.25));\n  const sEnd = Math.max(fEnd+1, Math.ceil(n*.55));\n  const front = nums.slice(0,fEnd), stalk = nums.slice(fEnd,sEnd), back = nums.slice(sEnd);\n  const join = arr => arr.map(circled).join(" ") || "—";\n  const base = `${join(front)} → ${join(stalk)} → ${join(back)}`;\n  const movers = [...back.slice(0,2)].reverse();\n  const late = `${join(front)} → ${join(stalk)} → ${join(movers.length?movers:back)}`;\n  return [\n    ["スタート〜100m", base], ["最初のコーナー", base], ["向正面", late], ["3〜4角", late], ["直線", late]\n  ];\n}\nfunction scenarios(rows, occ) {\n  const front = rows.filter(r=>r.score<2.35);\n  const highFade = front.filter(r=>r.fade>=.5).length;\n  let a=40,c=20;\n  if (front.length<=2){a+=10;c-=5}\n  if (highFade>=2){c+=10;a-=5}\n  if (occ.rate>=.6){c+=5;a-=5}\n  a=Math.max(15,Math.min(60,a)); c=Math.max(10,Math.min(45,c));\n  const b=100-a-c;\n  return [\n    {code:"A", title:"前残り", prob:a, horses:rows.filter(r=>r.score<2.8).slice(0,4).map(r=>r.horse.horseNumber)},\n    {code:"B", title:"平均", prob:b, horses:rows.slice(0,5).map(r=>r.horse.horseNumber)},\n    {code:"C", title:"前崩れ・差し届く", prob:c, horses:[...rows].sort((x,y)=>y.score-x.score).slice(0,4).map(r=>r.horse.horseNumber)}\n  ];\n}\nfunction placeRate(s){return !s?.starts ? 0 : ((s.wins||0)+(s.seconds||0)+(s.thirds||0))/s.starts}\nfunction marks(race, rows) {\n  const maxPrize = Math.max(...race.horses.map(h=>h.prizeMoneyAtRace||0),1);\n  const scored = race.horses.map(h=>{\n    const recent=(h.recentRaces||[]).slice(0,3);\n    const rs=recent.length?recent.reduce((s,r)=>s+Math.max(0,12-r.finish),0)/recent.length:0;\n    const ps=(h.prizeMoneyAtRace||0)/maxPrize*3;\n    const js=placeRate(h.jockeyStats)*2, ts=placeRate(h.trainerStats)*1.5;\n    const sustain=(1-fadeRate(h))*2;\n    const fit=Math.max(0,2-Math.abs(styleScore(h)-2.2));\n    return {h, score:rs+ps+js+ts+sustain+fit};\n  }).sort((a,b)=>b.score-a.score);\n  const syms=["◎","○","▲","☆","△","注"];\n  return syms.map((s,i)=> scored[i] ? [s,scored[i].h] : null).filter(Boolean);\n}\nfunction predict(race){\n  const occ=occupancy(race.horses), rows=styleMap(race.horses);\n  return {occ,rows,stages:buildStages(rows),scenarios:scenarios(rows,occ),marks:marks(race,rows)};\n}\n\nasync function loadRaces() {\n  state.loading=true; state.error=null; render();\n  try {\n    let races=[];\n    if (API_DEFAULT) {\n      const url=`${API_DEFAULT.replace(/\\/$/,"")}/api/v1/races?date=${encodeURIComponent(state.date)}`;\n      const res=await fetch(url,{cache:"no-store"});\n      if (!res.ok) throw new Error(`API ${res.status}`);\n      const body=await res.json(); races=Array.isArray(body)?body:(body.races||[]);\n    } else {\n      const res=await fetch("./data/sample_races.json",{cache:"no-store"});\n      if (!res.ok) throw new Error("sample load failed");\n      races=await res.json();\n    }\n    state.races=races.filter(r=>r.date===state.date);\n    state.selectedTrack=null; state.selectedRace=null;\n  } catch (e) { state.error=String(e.message||e); state.races=[]; }\n  finally { state.loading=false; render(); }\n}\n\nfunction header(title, back=false, subtitle="競馬展開AI") {\n  return `<header class="header"><div class="header-row">${back?\'<button class="back-btn" data-action="back">‹ 戻る</button>\':\'\'}<div class="header-title-wrap"><h1>${title}</h1><small>${subtitle}</small></div><button class="icon-btn" data-action="reload">↻</button></div></header>`;\n}\nfunction renderHome(){\n  const venues=(state.circuit==="中央"?CENTRAL:LOCAL).filter(t=>state.races.some(r=>r.circuit===state.circuit&&r.track===t));\n  return `<div class="shell home-shell">${header("レース選択")}\n    <main class="main">\n      <section class="card"><div class="setup-grid">\n        <div class="setup-block"><label>日付</label><input class="date-input" id="date" type="date" value="${state.date}"></div>\n        <div class="setup-block"><label>区分</label><div class="segment"><button data-circuit="中央" class="${state.circuit===\'中央\'?\'active\':\'\'}">中央</button><button data-circuit="地方" class="${state.circuit===\'地方\'?\'active\':\'\'}">地方</button></div></div>\n      </div></section>\n      <section class="card"><div class="row between"><h2>開催場</h2><span class="pill">${state.circuit==="地方"&&state.races.some(r=>r.source?.startsWith("NAR"))?"NAR公式・":""}${state.races.filter(r=>r.circuit===state.circuit).length}R</span></div>\n      ${state.loading?\'<div class="empty">読込中…</div>\':state.error?`<div class="notice">${state.error}</div>`:venues.length?`<div class="venue-grid">${venues.map(t=>{const n=state.races.filter(r=>r.circuit===state.circuit&&r.track===t).length;return `<button class="venue-btn" data-track="${t}"><strong>${t}</strong><span>${n}レース</span></button>`}).join(\'\')}</div>`:\'<div class="empty">この日の取得データはありません</div>\'}</section>\n    </main></div>`;\n}\nfunction renderVenue(){\n  const races=state.races.filter(r=>r.circuit===state.circuit&&r.track===state.selectedTrack).sort((a,b)=>a.raceNumber-b.raceNumber);\n  const byNo=Object.fromEntries(races.map(r=>[r.raceNumber,r]));\n  return `<div class="shell">${header(state.selectedTrack,true)}<main class="main"><section class="card"><div class="row between"><div><h2>${state.date}</h2><div class="muted">${state.circuit}・${state.selectedTrack}</div></div><span class="pill">${seasonOf(state.date)}</span></div></section><section class="card"><h2>1R〜12R</h2><div class="race-list">${Array.from({length:12},(_,i)=>i+1).map(no=>{const r=byNo[no]; return r?`<button class="race-btn" data-race="${r.id}"><div><strong>${no}R ${r.title}</strong><div class="muted">${r.distance}m・${r.condition}・${r.weather||\'不明\'}・${r.startTime}</div></div><span>›</span></button>`:`<button class="race-btn disabled" disabled><div><strong>${no}R</strong><div class="muted">未取得</div></div></button>`}).join(\'\')}</div></section></main></div>`;\n}\nfunction renderRace(){\n  const r=state.selectedRace, p=predict(r);\n  const early=p.occ.early.map(circled).join(\' \'), moved=p.occ.moved.map(circled).join(\' \');\n  return `<div class="shell prediction-shell">${header(`${r.track} ${r.raceNumber}R`,true, `${r.title}｜${r.distance}m・${r.condition}・${r.weather||\'不明\'}`)}<main class="main">\n    <section class="card"><div class="row between"><div><h2>${r.title}</h2><div class="muted">${r.date} ${r.startTime}</div></div><span class="pill">${r.circuit}</span></div><div class="metrics" style="margin-top:10px"><div class="metric"><b>${r.distance}m</b><span>距離</span></div><div class="metric"><b>${r.condition}</b><span>馬場</span></div><div class="metric"><b>${r.weather||\'不明\'}</b><span>天候</span></div><div class="metric"><b>${seasonOf(r.date)}</b><span>季節</span></div><div class="metric"><b>${r.horses.length}頭</b><span>頭数</span></div></div></section>\n    <section class="card"><div class="section-title">1\u3000先行馬占有率</div><div style="font-size:32px;font-weight:900">${pct(p.occ.rate)}</div><div class="muted">対象：${p.occ.nums.map(circled).join(\' \')||\'—\'}</div><div class="muted" style="font-size:12px;margin-top:4px">最初から前：${early||\'—\'}\u3000途中進出：${moved||\'—\'}</div></section>\n    <section class="card"><div class="section-title">2\u3000脚質マップ</div><div class="muted" style="font-size:10px;margin-bottom:6px">脚質点 昇順（低いほど前）</div><div class="style-map-list">${p.rows.map((x,i)=>`<div class="style-map-row"><div class="style-map-top"><span class="style-rank">${i+1}</span><span class="style-horse">${circled(x.horse.horseNumber)} ${x.horse.name}</span><span class="style-score">${x.score.toFixed(2)}</span><span class="style-expected">${x.expected}</span></div><div class="style-rate-grid"><span class="style-rate"><b>逃</b><span>${pct(x.front)}</span></span><span class="style-rate"><b>先</b><span>${pct(x.stalk)}</span></span><span class="style-rate"><b>差</b><span>${pct(x.mid)}</span></span><span class="style-rate"><b>追</b><span>${pct(x.close)}</span></span><span class="style-rate"><b>下</b><span>${pct(x.fade)}</span></span></div></div>`).join(\'\')}</div></section>\n    <section class="card"><div class="section-title">3\u3000隊列</div>${p.stages.map(([n,v])=>`<div class="stage"><b>${n}</b><div>${v}</div></div>`).join(\'\')}</section>\n    <section class="card"><div class="section-title">4\u3000ABC</div><div class="scenario-grid">${p.scenarios.map(s=>`<div class="scenario"><b>${s.code} ${s.title}</b><div class="prob">${s.prob}%</div><div class="horses">${s.horses.map(circled).join(\' \')}</div></div>`).join(\'\')}</div></section>\n    <section class="card"><div class="section-title">5\u3000印</div><div class="marks">${p.marks.map(([s,h])=>`<div class="mark-row"><div class="mark-symbol">${s}</div><div><strong>${circled(h.horseNumber)} ${h.name}</strong><div class="muted" style="font-size:12px">${h.sex}${h.age}・${h.carriedWeight}kg・${h.jockey}</div></div></div>`).join(\'\')}</div></section>\n    <section class="card"><h2>出走馬データ</h2>${r.horses.sort((a,b)=>a.horseNumber-b.horseNumber).map(h=>`<details class="horse-card"><summary>${circled(h.horseNumber)} ${h.name}\u3000${h.sex}${h.age} ${h.carriedWeight}kg</summary><div class="horse-detail"><div class="statline">騎手：${h.jockey}（${h.jockeyStats?.starts||0}戦 ${h.jockeyStats?.wins||0}勝 / 複勝率${pct(placeRate(h.jockeyStats))}）</div><div class="statline">調教師：${h.trainer}（${h.trainerStats?.starts||0}戦 ${h.trainerStats?.wins||0}勝 / 複勝率${pct(placeRate(h.trainerStats))}）</div><div class="statline">このレース時点の獲得賞金：${fmtMoney(h.prizeMoneyAtRace)}円</div>${(h.recentRaces||[]).map(rr=>`<div class="recent"><b>${rr.date} ${rr.track} ${rr.distance}m</b>\u3000${rr.finish}着 / ${rr.timeSeconds.toFixed(1)}秒<br><span class="muted">${rr.condition}・${rr.weather||\'不明\'}・${seasonOf(rr.date)}\u3000通過 ${rr.cornerPositions?.join(\'-\')||\'—\'}</span></div>`).join(\'\')}</div></details>`).join(\'\')}</section>\n  </main></div>`;\n}\nfunction render(){\n  if (state.selectedRace) app.innerHTML=renderRace();\n  else if (state.selectedTrack) app.innerHTML=renderVenue();\n  else app.innerHTML=renderHome();\n  bind();\n}\nfunction bind(){\n  document.querySelectorAll(\'[data-circuit]\').forEach(b=>b.onclick=()=>{state.circuit=b.dataset.circuit;state.selectedTrack=null;state.selectedRace=null;render()});\n  document.querySelector(\'#date\')?.addEventListener(\'change\',e=>{state.date=e.target.value;loadRaces()});\n  document.querySelectorAll(\'[data-track]\').forEach(b=>b.onclick=()=>{state.selectedTrack=b.dataset.track;render()});\n  document.querySelectorAll(\'[data-race]\').forEach(b=>b.onclick=()=>{state.selectedRace=state.races.find(r=>r.id===b.dataset.race);render()});\n  document.querySelectorAll(\'[data-action="back"]\').forEach(b=>b.onclick=()=>{if(state.selectedRace)state.selectedRace=null;else state.selectedTrack=null;render()});\n  document.querySelectorAll(\'[data-action="reload"]\').forEach(b=>b.onclick=()=>loadRaces());\n}\nif (\'serviceWorker\' in navigator) window.addEventListener(\'load\',()=>navigator.serviceWorker.register(\'./sw.js\').catch(()=>{}));\nloadRaces();\n'


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

MANIFEST = '{\n  "name": "競馬展開AI",\n  "short_name": "競馬展開AI",\n  "description": "中央・地方競馬の脚質マップ、隊列、ABC展開、印を確認するPWA",\n  "start_url": "./",\n  "scope": "./",\n  "display": "standalone",\n  "background_color": "#f6f7fb",\n  "theme_color": "#0f172a",\n  "lang": "ja",\n  "icons": [\n    {"src": "./assets/icon-192.png", "sizes": "192x192", "type": "image/png"},\n    {"src": "./assets/icon-512.png", "sizes": "512x512", "type": "image/png"}\n  ]\n}\n'
SW = "const CACHE='keiba-pwa-v1';\nconst ASSETS=['./','./index.html','./styles.css','./app.js','./manifest.webmanifest','./data/sample_races.json','./assets/icon-192.png','./assets/icon-512.png'];\nself.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));\nself.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));\nself.addEventListener('fetch',e=>{\n  if(e.request.method!=='GET') return;\n  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r;}).catch(()=>caches.match(e.request)));\n});\n"
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
        self.conn.commit()

    def import_rows(self, races: Iterable[RaceRow], entries: Iterable[EntryRow]) -> None:
        races = list(races)
        race_lookup = {(r.track, r.date, r.race_no): r for r in races}
        with self.conn:
            for r in races:
                self.conn.execute(
                    """
                    INSERT INTO races(track,date,race_no,start_time,title,distance,weather,condition,field_size,
                                      prize1,prize2,prize3,prize4,prize5,corners_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(track,date,race_no) DO UPDATE SET
                      start_time=excluded.start_time,title=excluded.title,distance=excluded.distance,
                      weather=excluded.weather,condition=excluded.condition,field_size=excluded.field_size,
                      prize1=excluded.prize1,prize2=excluded.prize2,prize3=excluded.prize3,
                      prize4=excluded.prize4,prize5=excluded.prize5,corners_json=excluded.corners_json
                    """,
                    (
                        r.track, r.date, r.race_no, r.start_time, r.title, r.distance, r.weather, r.condition,
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
                    "horses": horses,
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
        coverage = NarStore().coverage()
    except Exception:
        coverage = {"minDate": None, "maxDate": None}
    return {
        "status":"ok",
        "mode":"iphone-simple-live-local-v2",
        "historyStarted":_history_started,
        "historyReady":_history_ready,
        "historyError":_history_error,
        "narCoverage":coverage,
    }

@app.get("/api/v1/history-status")
def history_status():
    return {"started":_history_started,"ready":_history_ready,"error":_history_error}

@app.get("/api/v1/races")
def races(date: str = Query(...)):
    sample_rows = [r for r in SAMPLES if r.get("date") == date]
    central_samples = [r for r in sample_rows if r.get("circuit") == "中央"]
    live_local = []
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
        sync = NarSync()
        # Official monthly ZIP is primary and contains cards around the target date.
        sync.sync_month(target.year, target.month, force=False)
        if date == _today_iso():
            try:
                sync.sync_daily(force=False)
            except Exception as exc:
                print(f"NAR daily sync skipped: {exc}")
            ensure_history_async()
        live_local = NarStore().races_json(date)
        for row in live_local:
            row["source"] = "NAR公式"
    except Exception as exc:
        print(f"NAR official sync failed: {exc}")
        try:
            live_local = NarStore().races_json(date)
            for row in live_local:
                row["source"] = "NAR公式キャッシュ"
        except Exception:
            live_local = []

    # Never masquerade local demo data as live data.
    return live_local + central_samples

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(INDEX)

@app.get("/styles.css")
def styles():
    return Response(CSS, media_type="text/css")

@app.get("/app.js")
def appjs():
    return Response(JS, media_type="application/javascript")

@app.get("/manifest.webmanifest")
def manifest():
    return Response(MANIFEST, media_type="application/manifest+json")

@app.get("/sw.js")
def service_worker():
    return Response(SW, media_type="application/javascript", headers={"Service-Worker-Allowed":"/"})
