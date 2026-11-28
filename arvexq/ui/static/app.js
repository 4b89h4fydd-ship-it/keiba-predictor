/* ARVEXQ minimal UI.
   Venue list (JRA / NAR) -> race list -> racecard table only.
   The racecard follows the netkeiba entry-table layout with the
   ARVEXQ mark in the position of netkeiba's check column:
   number (coloured by frame, netkeiba waku colours) / mark
   (unifiedForecast.marks, by horse number) / name (one line, with
   sex+age, jockey and carried weight in a small grey sub-line) /
   win probability / top-3 probability (unifiedForecast.diagnosis,
   by horse number, shown as percentages).
   Fixed column widths and one uniform row height for every row.
   Under the race title sits a previous / next nav that walks the
   same venue's races for the day in race-number order (the ends
   of the card get no link on that side).
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

  /* Per-horse detail for the name sub-line, keyed by horse name:
     sex+age, jockey and carried weight. These live on horses[] in
     both circuits (raceCardView.sexAge is blank in the packs and
     raceCardView itself is empty for NAR), so horses[] is the single
     source; items that are absent stay absent. */
  function horseDetailByName(detail) {
    var map = {};
    (Array.isArray(detail.horses) ? detail.horses : []).forEach(function (h) {
      if (!h || !h.name) return;
      var sexAge = '';
      if (h.sex) sexAge += String(h.sex);
      if (h.age != null && h.age !== '') sexAge += String(h.age);
      var cw = Number(h.carriedWeight);
      map[String(h.name)] = {
        sexAge: sexAge,
        jockey: h.jockey ? String(h.jockey) : '',
        carriedWeight: isFinite(cw) && cw > 0 ? cw.toFixed(1) : ''
      };
    });
    return map;
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
    var details = horseDetailByName(detail);
    rows.forEach(function (row) {
      var d = details[row.name] || { sexAge: '', jockey: '', carriedWeight: '' };
      row.sexAge = d.sexAge;
      row.jockey = d.jockey;
      row.carriedWeight = d.carriedWeight;
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

  /* Previous / next race within the same venue on the same day,
     in the venue race list's order (race number ascending); venues
     are never crossed. The nav slots are rendered with the race and
     filled from the day pack: at the ends of the venue's card the
     slot on that side stays empty, so the other side keeps its
     place. Links use the normal hash routing (#/r/<id>), so moving
     between races never reloads the page. */
  function fillRaceNav(nav, detail, currentId) {
    loadDay().then(function (day) {
      if (!app.contains(nav)) return;
      var races = day.races.filter(function (r) {
        return String(r.circuit || '') === String(detail.circuit || '') &&
          String(r.track || '') === String(detail.track || '');
      });
      races.sort(function (a, b) { return Number(a.raceNumber) - Number(b.raceNumber); });
      var idx = -1;
      races.forEach(function (r, i) {
        if (idx === -1 && String(r.id || '') === String(currentId)) idx = i;
      });
      if (idx === -1) {
        races.forEach(function (r, i) {
          if (idx === -1 && Number(r.raceNumber) === Number(detail.raceNumber)) idx = i;
        });
      }
      if (idx === -1) return;
      if (idx > 0) {
        var prev = el('a', 'race-nav-link', '← 前のレース');
        prev.href = '#/r/' + encodeURIComponent(String(races[idx - 1].id || ''));
        nav.children[0].appendChild(prev);
      }
      if (idx < races.length - 1) {
        var next = el('a', 'race-nav-link', '次のレース →');
        next.href = '#/r/' + encodeURIComponent(String(races[idx + 1].id || ''));
        nav.children[1].appendChild(next);
      }
    }).catch(function () { /* no day pack: the nav stays empty */ });
  }

  function renderRace(id) {
    var done = function (detail) {
      app.textContent = '';
      var back = el('a', 'back', '← レース一覧');
      back.href = '#/v/' + encodeURIComponent(String(detail.circuit || '')) + '/' + encodeURIComponent(String(detail.track || ''));
      app.appendChild(back);
      app.appendChild(el('h2', 'race-title',
        String(detail.track || '') + ' ' + String(detail.raceNumber) + 'R ' + String(detail.title || '')));
      var nav = el('nav', 'race-nav');
      nav.appendChild(el('span', 'race-nav-slot'));
      nav.appendChild(el('span', 'race-nav-slot race-nav-next'));
      app.appendChild(nav);
      fillRaceNav(nav, detail, id);
      var marks = marksByNumber(detail);
      var table = el('table', 'racecard');
      var colgroup = document.createElement('colgroup');
      ['col-number', 'col-mark', 'col-name', 'col-winprob', 'col-top3prob'].forEach(function (c) {
        var col = document.createElement('col');
        col.className = c;
        colgroup.appendChild(col);
      });
      table.appendChild(colgroup);
      var thead = el('thead');
      var htr = el('tr');
      htr.appendChild(el('th', 'number', '馬番'));
      htr.appendChild(el('th', 'mark', '印'));
      htr.appendChild(el('th', 'name', '馬名'));
      htr.appendChild(el('th', 'winprob', '勝率'));
      htr.appendChild(el('th', 'top3prob', '3着内率'));
      thead.appendChild(htr);
      table.appendChild(thead);
      var tbody = el('tbody');
      var rows = raceRows(detail);
      rows.forEach(function (row) {
        var tr = el('tr');
        var waku = row.frame >= 1 && row.frame <= 8 ? ' waku' + row.frame : '';
        tr.appendChild(el('td', 'number' + waku, row.number));
        tr.appendChild(el('td', 'mark', marks[row.number] || ''));
        var nameTd = el('td', 'name');
        nameTd.appendChild(el('div', 'hname', row.name));
        var sub = [row.sexAge, row.jockey, row.carriedWeight].filter(function (s) { return s; }).join(' ');
        nameTd.appendChild(el('div', 'hsub', sub));
        tr.appendChild(nameTd);
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
