/* ARVEXQ minimal UI.
   Venue list (JRA / NAR) -> race list -> racecard table only.
   Columns: mark (unifiedForecast.marks, by horse number), number
   (coloured by frame, netkeiba waku colours), name, popularity,
   win probability and top-3 probability (unifiedForecast.diagnosis,
   by horse number, shown as percentages).
   Rows are grouped by frame with a divider at each frame boundary.
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
     8 frames; horses take frames in number order, and when the field is
     larger than 8 the outermost frames take the extra horses. The input
     is the horse's rank in number order (not the number itself), so
     fields with skipped numbers still map onto frames 1..8. */
  function frameFor(rank, field) {
    if (!rank || !field) return '';
    if (field <= 8) return rank;
    var q = Math.floor(field / 8), r = field % 8, acc = 0, i, count;
    for (i = 1; i <= 8; i++) {
      count = i > 8 - r ? q + 1 : q;
      acc += count;
      if (rank <= acc) return i;
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
    rows.forEach(function (row, idx) {
      if (!(row.frame >= 1)) row.frame = frameFor(idx + 1, field);
    });
    var odds = oddsByNumber(detail);
    rows.forEach(function (row) {
      var o = odds[row.number] || { win: 0, pop: 0 };
      row.win = o.win > 0 ? o.win : null;
      row.pop = o.pop >= 1 ? o.pop : null;
    });
    rows.forEach(function (row) {
      if (row.pop == null && row.win != null) {
        var rank = 1;
        rows.forEach(function (other) {
          if (other.win != null && other.win < row.win) rank++;
        });
        row.pop = rank;
      }
    });
    var probs = probabilitiesByNumber(detail);
    rows.forEach(function (row) {
      var p = probs[row.number];
      row.winProb = p ? p.win : null;
      row.top3Prob = p ? p.top3 : null;
    });
    return rows;
  }

  /* Win / top-3 probabilities per horse number, from the forecast
     diagnosis. Values are fractions (0..1) and are shown as
     percentages. Horses with no diagnosis entry (or a race with no
     forecast at all) stay blank -- never filled in. */
  function probabilitiesByNumber(detail) {
    var uf = detail.unifiedForecast || {};
    var map = {};
    (Array.isArray(uf.diagnosis) ? uf.diagnosis : []).forEach(function (d) {
      if (!d || d.horseNumber == null) return;
      var w = d.winProbability, t = d.top3Probability;
      map[Number(d.horseNumber)] = {
        win: (typeof w === 'number' && isFinite(w)) ? w : null,
        top3: (typeof t === 'number' && isFinite(t)) ? t : null
      };
    });
    return map;
  }

  function formatProb(p) {
    return p != null ? (p * 100).toFixed(1) + '%' : '';
  }

  /* Win odds / popularity per horse number.
     Primary: the pack's top-level odds rows (win_odds / popularity).
     Fallback: raceCardView odds / popularity. When odds exist but the
     pack carries no popularity rank, the rank is derived from the
     ascending win odds. No odds anywhere -> both stay blank. */
  function oddsByNumber(detail) {
    var map = {};
    (Array.isArray(detail.packOdds) ? detail.packOdds : []).forEach(function (o) {
      if (o && o.horse_no != null) {
        map[Number(o.horse_no)] = { win: Number(o.win_odds) || 0, pop: Number(o.popularity) || 0 };
      }
    });
    (Array.isArray(detail.raceCardView) ? detail.raceCardView : []).forEach(function (r) {
      if (!r || r.number == null) return;
      var n = Number(r.number);
      if (!map[n]) map[n] = { win: 0, pop: 0 };
      if (!(map[n].win > 0) && Number(r.odds) > 0) map[n].win = Number(r.odds);
      if (!(map[n].pop >= 1) && Number(r.popularity) >= 1) map[n].pop = Number(r.popularity);
    });
    return map;
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
      htr.appendChild(el('th', 'number', '馬番'));
      htr.appendChild(el('th', 'name', '馬名'));
      htr.appendChild(el('th', 'popularity', '人気'));
      htr.appendChild(el('th', 'winprob', '勝率'));
      htr.appendChild(el('th', 'top3prob', '3着内率'));
      thead.appendChild(htr);
      table.appendChild(thead);
      var tbody = el('tbody');
      var rows = raceRows(detail);
      rows.forEach(function (row, idx) {
        var tr = el('tr');
        if (idx === 0 || row.frame !== rows[idx - 1].frame) tr.className = 'frame-first';
        var waku = row.frame >= 1 && row.frame <= 8 ? ' waku' + row.frame : '';
        tr.appendChild(el('td', 'mark', marks[row.number] || ''));
        tr.appendChild(el('td', 'number' + waku, row.number));
        tr.appendChild(el('td', 'name', row.name));
        tr.appendChild(el('td', 'popularity', row.pop != null ? row.pop : ''));
        tr.appendChild(el('td', 'winprob', formatProb(row.winProb)));
        tr.appendChild(el('td', 'top3prob', formatProb(row.top3Prob)));
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      app.appendChild(table);
    };
    if (raceCache[id]) { done(raceCache[id]); return; }
    fetchJson(staticRaceUrl(id)).then(function (body) {
      var detail = (body && body.detail) || {};
      detail.packOdds = (body && body.odds) || [];
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
