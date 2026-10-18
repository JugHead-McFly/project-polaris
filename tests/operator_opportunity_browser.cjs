// Run against the synthetic fixture, never an authenticated production session.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8114/operator');
  await page.locator('.hosted-schedule-block').first().waitFor();
  for (const [score,tone,label] of [[90,'excellent','Excellent'],[75,'good','Very good'],[60,'fair','Usable'],[40,'challenging','Challenging'],[20,'poor','Poor']]) {
    await page.evaluate(({score,label}) => renderOpportunityScore({total:score,label,components:[]}), {score,label});
    assert.equal(await page.locator('.hosted-opportunity-score').getAttribute('data-tone'), tone);
    assert.equal(await page.locator('#hosted-opportunity-score').innerText(), `${score.toFixed(1)}%`);
    assert.match(await page.locator('.hosted-opportunity-reading').getAttribute('aria-label'), new RegExp(`${score.toFixed(1)} percent.*${label}`));
    const ring=await page.locator('.hosted-opportunity-reading').evaluate(e => {
      const s=getComputedStyle(e),p=getComputedStyle(e,'::before'),r=e.getBoundingClientRect();
      return {width:r.width,height:r.height,border:s.borderTopColor,fill:p.backgroundImage,visible:p.display};
    });
    assert.equal(ring.width,ring.height);
    assert.equal(ring.width,148);
    assert.notEqual(ring.visible,'none');
    assert.ok(ring.fill.includes(ring.border), JSON.stringify(ring));
  }
  await page.evaluate(() => renderOpportunityScore({total:88,label:'No imaging window',components:[]}));
  assert.equal(await page.locator('#hosted-opportunity-score').innerText(),'STOP');
  assert.match(await page.locator('.hosted-opportunity-reading').getAttribute('aria-label'),/Hard stop/);
  await page.evaluate(() => renderOpportunityScore(null));
  assert.equal(await page.locator('.hosted-opportunity-score').getAttribute('data-tone'),'unavailable');
  assert.equal(await page.locator('.hosted-opportunity-reading').getAttribute('aria-label'),'Opportunity score unavailable');
  await page.evaluate(async () => {
    const data=await(await fetch('/tonight')).json();
    data.schedule.decision='Use Caution';
    data.weather={...data.weather,temperature_f:70,planned_temperature_f:70,wind_speed_mph:4,planned_wind_speed_mph:4,humidity_percent:40,planned_humidity_percent:40,planned_cloud_cover_percent:40,cache_status:'fresh',status:'Live weather',planned_cloud_forecast_sources:['a','b'],planned_cloud_forecast_spread:10};
    data.opportunity_score={total:63.4,label:'Usable',components:data.opportunity_score.components};
    renderHostedTonight(data);
  });
  assert.equal(await page.locator('#hosted-decision').innerText(),'Fair conditions');
  for (const width of [1440,390]) {
    await page.setViewportSize({width,height:1000});
    for (const selector of ['#hosted-schedule-summary','#compact-planning-details > summary','#nightly-confidence-details > summary']) {
      const summary=page.locator(selector);
      await summary.scrollIntoViewIfNeeded();
      const initial=await summary.evaluate(e=>e.parentElement.open);
      const before=await summary.evaluate(e=>getComputedStyle(e,'::after').transform);
      await summary.focus();
      await summary.press('Enter');
      assert.equal(await summary.evaluate(e=>e.parentElement.open),!initial);
      assert.notEqual(await summary.evaluate(e=>getComputedStyle(e,'::after').transform),before);
      await summary.press('Space');
      assert.equal(await summary.evaluate(e=>e.parentElement.open),initial);
      const arrow=await summary.evaluate(e=>{
        const p=getComputedStyle(e,'::after');
        return {content:p.content,width:p.width,right:p.right,top:parseFloat(p.top),height:e.getBoundingClientRect().height};
      });
      assert.equal(arrow.content,'""');
      assert.equal(arrow.width,'8px');
      assert.equal(arrow.right,'8px');
      assert.ok(Math.abs(arrow.top-arrow.height/2)<1);
    }
  }
  for (const width of [1440,768,390,375,320]) {
    await page.setViewportSize({width,height:1000});
    await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`overflow at ${width}`);
    const bounds=await page.locator('.hosted-opportunity-reading').boundingBox();
    assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width);
    if(width===1440 || width===390) await page.screenshot({path:`../opportunity-dial-${width}.png`,fullPage:true});
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await page.locator('.hosted-opportunity-reading').evaluate(e=>getComputedStyle(e,'::before').animationName),'none');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({checks:'passed',scoreBands:5,viewports:[1440,768,390,375,320],errors}));
  await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
