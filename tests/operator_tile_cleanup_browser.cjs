const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[]; page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.POLARIS_PREVIEW_URL || 'http://127.0.0.1:8122/operator');
    await page.locator('.hosted-schedule-block').first().waitFor();
    await page.evaluate(()=>{
      const plan=structuredClone(latestHostedTonightData);
      const original=plan.schedule.blocks[0];
      plan.schedule.blocks=[{}, {recommended_gain:null,recommended_filter:null}, {mosaic_required:true}].map((overrides,i)=>({
        ...original, object:['M27','M57','M31'][i], setup_minutes:5,
        recommendation_source:'rig_category_starting_point', recommended_gain:80, recommended_filter:'Astro',
        target_geometry:{samples:[{at:original.start_at,altitude_degrees:40},{at:original.end_at,altitude_degrees:60}]}, ...overrides
      }));
      renderHostedTonight(plan);
      renderForecastAgreement({state:'split',label:'Forecasts disagree',partial:false});
    });
    assert.equal(await page.locator('#forecast-agreement-label').innerText(),'Cloud forecasts vary');
    assert.equal(await page.locator('#forecast-agreement-detail').isVisible(),false);
    assert.equal(await page.getByText('Framing details',{exact:true}).count(),0);
    assert.equal(await page.locator('#hosted-target-rig-match').count(),0);
    assert.equal(await page.locator('.schedule-mini-sky svg').count(),3);
    assert.equal(await page.locator('.schedule-mini-sky line[stroke-dasharray]').count(),3);
    const text=await page.locator('.hosted-schedule-block').allTextContents().then(rows=>rows.join(' '));
    assert.doesNotMatch(text,/Category starting settings|setup included|Night path/);
    assert.match(text,/Mosaic candidate/);
    assert.match(text,/Starting exposure.*confirm gain\/filter/);
    assert.ok(await page.locator('.capture-setting-line').count()>=2);
    assert.equal(await page.locator('#hosted-setup-card .hosted-target-facts > div').count(),4);
    assert.equal(await page.locator('#hosted-target-rig, #hosted-target-fit').count(),0);
    await page.locator('#compact-planning-details > summary').click();
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      if([1440,390].includes(width)) await page.screenshot({path:`../tile-cleanup-${width}.png`,fullPage:true});
    }
    await page.evaluate(()=>renderForecastAgreement({state:'unavailable',reason:'Only one forecast source is available.'}));
    assert.equal(await page.locator('#forecast-agreement-detail').isVisible(),true);
    assert.match(await page.locator('#forecast-agreement-detail').innerText(),/Only one forecast source/);
    assert.deepEqual(errors,[]);
    console.log('PASS: full/partial/mosaic tiles, charts and floor retained, plain warning/unavailable state, four widths, screenshots, no page errors');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
