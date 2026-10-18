// Synthetic local fixture only. Set POLARIS_PREVIEW_URL when using another port.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.env.POLARIS_PREVIEW_URL || 'http://127.0.0.1:8115/operator');
    await page.locator('.hosted-schedule-block').first().waitFor();
    for (const [state,label] of [['close','Forecasts broadly agree'],['mixed','Forecasts differ'],['split','Forecasts disagree']]) {
      await page.evaluate(({state,label}) => renderForecastAgreement({state,label,partial:true,providers:['open-meteo','nws'],average_spread_points:20,maximum_spread_points:35,compared_minutes:120,coverage_percent:25,start:'2026-10-18T02:00:00Z',end:'2026-10-18T10:00:00Z'}),{state,label});
      assert.equal(await page.locator('#forecast-agreement').getAttribute('data-state'),state);
      assert.equal(await page.locator('#forecast-agreement-label').innerText(), `${state === 'close' ? 'Cloud forecasts broadly agree' : 'Cloud forecasts vary'} · partial window`);
    }
    const summary=page.locator('#forecast-agreement-label');
    assert.match(await summary.innerText(), /Cloud forecasts vary/);
    assert.equal(await page.locator('#forecast-agreement-detail').isVisible(), false);
    assert.equal(await page.locator('#forecast-agreement-detail').textContent(), '');
    await page.evaluate(()=>renderFilterProgress(document.querySelector('#hosted-filter-progress'),[{filter:'Astro',captured_seconds:5400,captured_frames:360},{filter:'Dual-band',captured_seconds:1800,captured_frames:120}]));
    assert.match(await page.locator('#hosted-filter-progress').textContent(),/1.50 h captured.*360 frames/);
    assert.match(await page.locator('#hosted-filter-progress').textContent(),/Usable \/ rejected: not assessed/);
    assert.match(await page.locator('#hosted-filter-progress').textContent(),/goal is shared/);
    await page.locator('#compact-planning-details > summary').click();
    assert.equal(await page.locator('#hosted-filter-progress').isVisible(),true);
    for (const width of [1440,768,390,320]) {
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`overflow at ${width}`);
      if ([1440,390].includes(width)) await page.screenshot({path:`../filter-agreement-${width}.png`,fullPage:true});
    }
    await page.evaluate(()=>renderForecastAgreement({state:'unavailable',reason:'Only one forecast source is available.'}));
    assert.equal(await summary.innerText(),'Forecast comparison unavailable');
    assert.match(await page.locator('#forecast-agreement-detail').innerText(),/Only one forecast source/);
    for (const value of [null, {}, {state:'unexpected'}]) {
      await page.evaluate(value=>renderForecastAgreement(value),value);
      assert.equal(await summary.innerText(),'Forecast comparison unavailable');
      assert.equal(await page.locator('#forecast-agreement-detail').isVisible(),true);
    }
    await page.evaluate(()=>renderFilterProgress(document.querySelector('#hosted-filter-progress'),[]));
    assert.equal(await page.locator('#hosted-filter-progress').isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log('PASS: agreement bands, partial/single-source states, plain-language warning, per-filter unknown quality, 4 widths, no page errors');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
