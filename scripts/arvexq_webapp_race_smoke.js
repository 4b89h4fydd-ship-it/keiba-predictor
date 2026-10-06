const { chromium } = require('playwright');

const base = process.env.ARVEXQ_BASE_URL || 'http://127.0.0.1:8788';
const timeout = Number(process.env.ARVEXQ_SMOKE_TIMEOUT || 20000);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', err => pageErrors.push(String(err && err.stack || err)));
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  try {
    await page.goto(base + '/?smoke=' + Date.now(), { waitUntil: 'domcontentloaded', timeout });
    await page.waitForFunction(() => !document.querySelector('.boot'), null, { timeout });

    if ((await page.locator('[data-race]').count()) === 0) {
      const venue = page.locator('button[data-track]').first();
      await venue.waitFor({ state: 'visible', timeout });
      await venue.click();
    }

    const race = page.locator('button[data-race]').first();
    await race.waitFor({ state: 'visible', timeout });
    const raceId = await race.getAttribute('data-race');
    if (!raceId) throw new Error('first race button has no data-race');
    await race.click();

    await page.waitForFunction(() => location.pathname === '/race' && !!document.querySelector('.smart-race-page'), null, { timeout });
    await page.waitForFunction(() => {
      const body = document.body.innerText || '';
      if (/表示エラー|起動エラー/.test(body)) return true;
      return !!document.querySelector('.racecard-table, .result-card, .accordion-panel');
    }, null, { timeout });

    const bodyText = await page.locator('body').innerText();
    if (/表示エラー|起動エラー/.test(bodyText)) throw new Error('runtime display error: ' + bodyText.slice(0, 800));
    if (await page.locator('.smart-loading').count()) throw new Error('race remained on loading screen: ' + bodyText.slice(0, 800));

    for (const key of ['diagnosis', 'detail', 'pace', 'bets']) {
      const tab = page.locator(`[data-panel="${key}"]`).first();
      if (await tab.count()) {
        await tab.click();
        await page.waitForTimeout(120);
        const txt = await page.locator('body').innerText();
        if (/表示エラー|起動エラー/.test(txt)) throw new Error(`tab ${key} caused display error: ` + txt.slice(0, 800));
      }
    }

    const close = page.locator('[data-action="back"]').first();
    if (await close.count()) {
      await close.click();
      await page.waitForFunction(() => location.pathname !== '/race', null, { timeout: 8000 });
    }

    if (pageErrors.length) throw new Error('page errors:\n' + pageErrors.join('\n'));
    const fatalConsole = consoleErrors.filter(x => !/Failed to load resource|favicon/i.test(x));
    if (fatalConsole.length) throw new Error('console errors:\n' + fatalConsole.join('\n'));
    console.log(`ARVEXQ race smoke OK race=${raceId}`);
  } finally {
    await browser.close();
  }
})().catch(err => {
  console.error(err && err.stack || err);
  process.exit(1);
});
