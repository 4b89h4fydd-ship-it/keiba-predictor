/* ARVEXQ minimal UI.
   Venue list (JRA / NAR) -> race list -> racecard table only:
   mark (unifiedForecast.marks, by horse number), frame, number, name.
   Data sources are unchanged: api-static/day/<date>.json and
   api-static/race/<raceId>.json ({detail, summary} wrapper). */
(function () {
  'use strict';

  function arvexqBasePath() {
    var b = String(window.ARVEXQ_BASE_PATH || '/');
    if (b.charAt(0) !== '/') b = '/' + b;
    if (b.charAt(b.length - 1) !== '/') b = b + '/';
    return b;
  }
  function staticDayUrl(date) {
    return arvexqBasePath() + 'api-static/day/' + encodeURIComponent(String(date || '')) + '.json';
  }
  function staticRaceUrl(id) {
    return arvexqBasePath() + 'api-static/race/' + encodeURIComponent(String(id || '')) + '.json';
  }

  function todayJst() {
    var parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(new Date());
    var y = '', m = '', d = '';
    parts.forEach(function (p) {
      if (p.type === 'year') y = p.value;
      if (p.type === 'month') m = p.value;
      if (p.type === 'day') d = p.value;
    });
    return y + '-' + m + '-' + d;
  }

  function fetchJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  /* Standard frame assignment when the pack carries no frame for a horse:
     8 frames; the outermost frames take the extra horses. */
  function frameFor(number, field) {
    if (!number || !field) return '';
    if (field <= 8) return number;
    var q = Math.floor(field / 8), r = field % 8, acc = 0, i, count;
    for (i = 1; i <= 8; i++) {
      count = i > 8 - r ? q + 1 : q;
      acc += count;
      if (number <= acc) return i;
    }
    return 8;
  }

  function raceRows(detail) {
    var horses = Array.isArray(detail.horses) ? detail.horses : [];
    var frameByName = {};
    horses.forEach(function (h) {
      if (h && h.name && Number(h.frameNumber) >= 1) frameByName[String(h.name)] = Number(h.frameNumber);
    });
    var rcv = Array.isArray(detail.raceCardView) ? detail.raceCardView : [];
    var rows = [];
    if (rcv.length) {
      rcv.forEach(function (r) {
        if (r) rows.push({ number: Number(r.number), name: String(r.name || ''), frame: frameByName[String(r.name || '')] || 0 });
      });
    } else {
      horses.forEach(function (h) {
        if (h) rows.push({ number: Number(h.horseNumber), name: String(h.name || ''), frame: Number(h.frameNumber) || 0 });
      });
    }
    rows = rows.filter(function (r) { return r.number >= 1; });
    rows.sort(function (a, b) { return a.number - b.number; });
    var field = rows.length;
    rows.forEach(function (row) {
      if (!(row.frame >= 1)) row.frame = frameFor(row.number, field);
    });
    return rows;
  }

  function marksByNumber(detail) {
    var uf = detail.unifiedForecast || {};
    var map = {};
    (Array.isArray(uf.marks) ? uf.marks : []).forEach(function (m) {
      if (m && m.horseNumber != null && m.markSymbol) map[Number(m.horseNumber)] = String(m.markSymbol);
    });
    return map;
  }

  var app = document.getElementById('app');
  var dayCache = null; // {date, races}
  var raceCache = {};  // id -> detail

  function loadDay() {
    var date = todayJst();
    if (dayCache && dayCache.date === date) return Promise.resolve(dayCache);
    return fetchJson(staticDayUrl(date)).then(function (body) {
      if (!body || !Array.isArray(body.races)) throw new Error('static day pack invalid');
      dayCache = { date: date, races: body.races };
      return dayCache;
    });
  }

  function renderMessage(text) {
    app.textContent = '';
    app.appendChild(el('p', 'message', text));
  }

  function renderVenues() {
    loadDay().then(function (day) {
      app.textContent = '';
      app.appendChild(el('h1', 'app-title', 'ARVEXQ'));
      var circuits = [];
      day.races.forEach(function (r) {
        var c = String(r.circuit || '');
        if (circuits.indexOf(c) === -1) circuits.push(c);
      });
      circuits.sort(function (a, b) {
        var order = { '中央': 0, '地方': 1 };
        var oa = order[a] != null ? order[a] : 2;
        var ob = order[b] != null ? order[b] : 2;
        return oa - ob;
      });
      circuits.forEach(function (circuit) {
        app.appendChild(el('h2', 'section-title', circuit));
        var list = el('ul', 'pick-list');
        var seen = [];
        day.races.forEach(function (r) {
          if (String(r.circuit || '') !== circuit) return;
          var track = String(r.track || '');
          if (seen.indexOf(track) !== -1) return;
          seen.push(track);
          var a = el('a');
          a.href = '#/v/' + encodeURIComponent(circuit) + '/' + encodeURIComponent(track);
          a.appendChild(el('span', 'pick-main', track));
          var li = el('li');
          li.appendChild(a);
          list.appendChild(li);
        });
        app.appendChild(list);
      });
      if (!day.races.length) renderMessage('本日のレース情報がありません');
    }).catch(function () {
      renderMessage('本日のレース情報がありません');
    });
  }

  function renderRaceList(circuit, track) {
    loadDay().then(function (day) {
      var races = day.races.filter(function (r) {
        return String(r.circuit || '') === circuit && String(r.track || '') === track;
      });
      races.sort(function (a, b) { return Number(a.raceNumber) - Number(b.raceNumber); });
      app.textContent = '';
      var back = el('a', 'back', '← 会場一覧');
      back.href = '#/';
      app.appendChild(back);
      app.appendChild(el('h2', 'race-title', track));
      var list = el('ul', 'pick-list');
      races.forEach(function (r) {
        var a = el('a');
        a.href = '#/r/' + encodeURIComponent(String(r.id || ''));
        a.appendChild(el('span', 'pick-main', String(r.raceNumber) + 'R ' + String(r.title || '')));
        a.appendChild(el('span', 'pick-sub', String(r.startTime || '')));
        var li = el('li');
        li.appendChild(a);
        list.appendChild(li);
      });
      app.appendChild(list);
      if (!races.length) renderMessage('レース情報がありません');
    }).catch(function () {
      renderMessage('レース情報がありません');
    });
  }

  function renderRace(id) {
    var done = function (detail) {
      app.textContent = '';
      var back = el('a', 'back', '← レース一覧');
      back.href = '#/v/' + encodeURIComponent(String(detail.circuit || '')) + '/' + encodeURIComponent(String(detail.track || ''));
      app.appendChild(back);
      app.appendChild(el('h2', 'race-title',
        String(detail.track || '') + ' ' + String(detail.raceNumber) + 'R ' + String(detail.title || '')));
      var marks = marksByNumber(detail);
      var table = el('table', 'racecard');
      var thead = el('thead');
      var htr = el('tr');
      htr.appendChild(el('th', 'mark', '印'));
      htr.appendChild(el('th', 'frame', '枠'));
      htr.appendChild(el('th', 'number', '馬番'));
      htr.appendChild(el('th', 'name', '馬名'));
      thead.appendChild(htr);
      table.appendChild(thead);
      var tbody = el('tbody');
      raceRows(detail).forEach(function (row) {
        var tr = el('tr');
        tr.appendChild(el('td', 'mark', marks[row.number] || ''));
        tr.appendChild(el('td', 'frame', row.frame || ''));
        tr.appendChild(el('td', 'number', row.number));
        tr.appendChild(el('td', 'name', row.name));
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      app.appendChild(table);
    };
    if (raceCache[id]) { done(raceCache[id]); return; }
    fetchJson(staticRaceUrl(id)).then(function (body) {
      var detail = (body && body.detail) || {};
      raceCache[id] = detail;
      done(detail);
    }).catch(function () {
      renderMessage('レース情報がありません');
    });
  }

  function render() {
    var hash = String(location.hash || '');
    var seg = hash.replace(/^#\/?/, '').split('/').map(function (s) {
      try { return decodeURIComponent(s); } catch (e) { return s; }
    });
    if (seg[0] === 'v' && seg.length >= 3) renderRaceList(seg[1], seg[2]);
    else if (seg[0] === 'r' && seg.length >= 2) renderRace(seg.slice(1).join('/'));
    else renderVenues();
  }

  window.addEventListener('hashchange', render);
  render();
})();
