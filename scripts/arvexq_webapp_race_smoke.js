const { chromium, webkit, devices } = require('playwright');

const base = process.env.ARVEXQ_BASE_URL || 'http://127.0.0.1:8788';
const timeout = Number(process.env.ARVEXQ_SMOKE_TIMEOUT || 20000);
const browserName = String(process.env.ARVEXQ_BROWSER || 'chromium').toLowerCase();
const browserType = browserName === 'webkit' ? webkit : chromium;
const isLocal = /^http:\/\/(?:127\.0\.0\.1|localhost)(?::\d+)?(?:\/|$)/i.test(base);
const resetMarker = 'arvexq-hard-reset-v328-safari-runtime-20261006';

(async () => {
  const browser = await browserType.launch({ headless: true });
  const iphone = devices['iPhone 15 Pro'] || { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true };
  const page = await browser.newPage({ ...iphone, locale: 'ja-JP' });
  const pageErrors = [];
  const consoleErrors = [];
  const httpFailures = [];

  await page.addInitScript(marker => {
    try { localStorage.setItem(marker, '1'); } catch (_) {}
  }, resetMarker);

  page.on('pageerror', err => pageErrors.push(String(err && err.stack || err)));
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('response', res => {
    const status = res.status();
    if (status >= 400) httpFailures.push({ status, url: res.url() });
  });

  function hasFatalUiError(text) {
    return /表示エラー|起動エラー|undefined is not an object|Cannot read properties of undefined|Cannot read property .* of undefined/i.test(String(text || ''));
  }

  function isExpectedLocalHarnessError(text) {
    if (!isLocal) return false;
    text = String(text || '');
    return /Cannot update a null\/nonexistent service worker registration/i.test(text) ||
      /Fetch API cannot load .* due to access control checks/i.test(text) ||
      /Access to fetch at .* has been blocked by CORS policy/i.test(text) ||
      /No 'Access-Control-Allow-Origin' header is present/i.test(text) ||
      /Load failed|NetworkError when attempting to fetch resource/i.test(text);
  }

  function criticalHttpFailure(item) {
    const u = String(item && item.url || '');
    if (!u) return false;
    if (/\/app-v328\.js(?:\?|$)|\/styles-arvexq-v328\.css(?:\?|$)|\/version\.json(?:\?|$)|\/sw-v328-reset\.js(?:\?|$)/i.test(u)) return true;
    if (/\/api\/(?:day|prediction|odds|result|payout)/i.test(u)) return true;
    return Number(item.status) >= 500;
  }

  function isSelectedRaceFailure(item, raceId) {
    if (!item || !raceId || Number(item.status) < 400) return false;
    try {
      const path = decodeURIComponent(new URL(item.url).pathname);
      return path === '/api/race/' + String(raceId) || path.endsWith('/api/race/' + String(raceId));
    } catch (_) {
      return false;
    }
  }

  try {
    await page.goto(base + '/?smoke=' + Date.now() + '&browser=' + browserName, { waitUntil: 'domcontentloaded', timeout });
    await page.waitForFunction(() => !document.querySelector('.boot'), null, { timeout });

    let initialText = await page.locator('body').innerText();
    if (hasFatalUiError(initialText)) throw new Error('startup display error: ' + initialText.slice(0, 1000));

    if ((await page.locator('[data-race]').count()) === 0) {
      const venue = page.locator('button[data-track]').first();
      await venue.waitFor({ state: 'visible', timeout });
      await venue.click();
      const venueText = await page.locator('body').innerText();
      if (hasFatalUiError(venueText)) throw new Error('venue display error: ' + venueText.slice(0, 1000));
    }

    const race = page.locator('button[data-race]').first();
    await race.waitFor({ state: 'visible', timeout });
    const raceId = await race.getAttribute('data-race');
    if (!raceId) throw new Error('first race button has no data-race');
    await race.click();

    await page.waitForFunction(() => location.pathname === '/race' && !!document.querySelector('.smart-race-page'), null, { timeout });
    await page.waitForFunction(() => {
      const body = document.body.innerText || '';
      if (/表示エラー|起動エラー|undefined is not an object|Cannot read properties of undefined/i.test(body)) return true;
      return !!document.querySelector('.racecard-table, .result-card, .accordion-panel');
    }, null, { timeout });

    const bodyText = await page.locator('body').innerText();
    if (hasFatalUiError(bodyText)) throw new Error('runtime display error: ' + bodyText.slice(0, 1000));
    if (await page.locator('.smart-loading').count()) throw new Error('race remained on loading screen: ' + bodyText.slice(0, 1000));

    for (const key of ['diagnosis', 'detail', 'pace', 'bets']) {
      const tab = page.locator(`[data-panel="${key}"]`).first();
      if (await tab.count()) {
        await tab.click();
        await page.waitForTimeout(180);
        const txt = await page.locator('body').innerText();
        if (hasFatalUiError(txt)) throw new Error(`tab ${key} caused display error: ` + txt.slice(0, 1000));
      }
    }

    const close = page.locator('[data-action="back"]').first();
    if (await close.count()) {
      await close.click();
      await page.waitForFunction(() => location.pathname !== '/race', null, { timeout: 8000 });
      const backText = await page.locator('body').innerText();
      if (hasFatalUiError(backText)) throw new Error('back navigation display error: ' + backText.slice(0, 1000));
    }

    const fatalPageErrors = pageErrors.filter(x => {
      if (/ServiceWorker.*Not found|Failed to update a ServiceWorker/i.test(x)) return false;
      if (isExpectedLocalHarnessError(x)) return false;
      return true;
    });
    if (fatalPageErrors.length) throw new Error('page errors:\n' + fatalPageErrors.join('\n'));

    const criticalHttp = httpFailures.filter(x => criticalHttpFailure(x) || isSelectedRaceFailure(x, raceId));
    if (criticalHttp.length) {
      throw new Error('critical HTTP failures:\n' + criticalHttp.map(x => `${x.status} ${x.url}`).join('\n'));
    }

    const fatalConsole = consoleErrors.filter(x => {
      if (/favicon|ServiceWorker/i.test(x)) return false;
      if (/Failed to load resource: the server responded with a status of 404/i.test(x)) return false;
      if (isExpectedLocalHarnessError(x)) return false;
      if (isLocal && /Failed to load resource/i.test(x)) return false;
      return true;
    });
    if (fatalConsole.length) throw new Error('console errors:\n' + fatalConsole.join('\n'));

    if (httpFailures.length) {
      console.log('noncritical HTTP failures:', httpFailures.map(x => `${x.status} ${x.url}`).join(' | '));
    }
    console.log(`ARVEXQ ${browserName} race smoke OK race=${raceId} origin=${isLocal ? 'local' : 'production'}`);
  } finally {
    await browser.close();
  }
})().catch(err => {
  console.error(err && err.stack || err);
  process.exit(1);
});
