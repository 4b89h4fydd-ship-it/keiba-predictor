// Exercise the real loading renderer without network or browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../arvexq/ui/static/app.js'), 'utf8');
const renderer = source.slice(source.indexOf('function renderRaceLoading(){'),
  source.indexOf('function mergeResultHorseFields'));
for (const hasSummary of [false, true]) {
  for (const error of [null, '詳細を取得できませんでした']) {
    const context = {
      state: {races: hasSummary ? [{id: 'test', track: '園田'}] : [],
        raceLoading: 'test', track: '園田', error},
      smartRaceTopBar: r => '<header>' + r.track + '</header>',
      smartTopBar: () => '<header>レース詳細</header>',
      smartRaceHead: () => '<section>概要</section>',
      esc: x => x, cinematicFooter: () => '<footer></footer>'
    };
    vm.createContext(context);
    const html = vm.runInContext(renderer + ';renderRaceLoading()', context);
    assert.ok(html.startsWith('<div class="smart-shell"><header>'));
    assert.ok(html.includes('<main class="smart-main smart-race-page">'));
    assert.ok(html.includes(error || 'レース詳細を読み込み中'));
    assert.equal(html.includes('data-race="test"'), Boolean(error && hasSummary));
    assert.ok(html.endsWith('</main><footer></footer></div>'));
  }
}
console.log('Race loading: summary present/absent, loading/error states passed');
