const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({headless:true, executablePath:process.env.CHROME_EXECUTABLE});
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[]; page.on('pageerror', e=>errors.push(e.message));
 await page.goto((process.env.POLARIS_PREVIEW_URL || 'http://127.0.0.1:8110') + '/operator');
 await page.locator('.hosted-schedule-block').first().waitFor();
 await page.evaluate(()=>document.getElementById('account-email').textContent='a-very-long-observatory-account-name@example-observatory.invalid');
 await page.screenshot({path:'compact-desktop.png',fullPage:true});
 const results=[];
 for (const [width,height] of [[320,800],[375,812],[390,844],[430,932],[844,390]]) {
  await page.setViewportSize({width,height});
  if(await page.locator('#mobile-account-menu-button').isVisible()) {
    if(await page.locator('#mobile-account-menu-button').getAttribute('aria-expanded')==='false') await page.locator('#mobile-account-menu-button').click();
  }
  const measures = await page.evaluate(()=>{
    const ids=['mobile-refresh-button','hosted-refresh-button','account-email','sign-out-button'];
    const rects=ids.map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect();return {id,x:r.x,y:r.y,width:r.width,height:r.height};}).filter(r=>r.width&&r.height);
    const overlaps=[];
    rects.forEach((a,i)=>rects.slice(i+1).forEach(b=>{if(a.x<b.x+b.width&&b.x<a.x+a.width&&a.y<b.y+b.height&&b.y<a.y+a.height)overlaps.push([a.id,b.id]);}));
    return {rects,overlaps,overflow:document.documentElement.scrollWidth>innerWidth};
  });
  results.push({width,height,...measures});
  await page.screenshot({path:`compact-${width}.png`,fullPage:true});
  assert.deepEqual(measures.overlaps,[],`overlap at ${width}`);
  assert.equal(measures.overflow,false,`overflow at ${width}`);
  for (const r of measures.rects.filter(r=>r.id.includes('button'))) assert.ok(r.height>=44&&r.width>=44,JSON.stringify(r));
 }
 await page.locator('#mobile-refresh-button').isVisible().then(async visible=>{await page.locator(visible?'#mobile-refresh-button':'#hosted-refresh-button').click();});
 await page.locator('.hosted-schedule-block').first().waitFor();
 assert.equal(await page.locator('#hosted-session-plan,#hosted-command-window,#hosted-condition-alerts').count(),0);
 assert.equal(await page.locator('text=/Unallocated/').count(),0);
 assert.equal(await page.locator('.schedule-pause').count(),1);
 assert.ok(await page.locator('.mosaic-label').count());
 await page.locator('#compact-planning-details > summary').click();
 assert.equal(await page.locator('#hosted-target-card').isVisible(),true);
 await page.locator('#compact-planning-details > summary').press('Enter');
 assert.equal(await page.locator('#hosted-target-card').isVisible(),false);
 await page.evaluate(async()=>{
   const data=await (await fetch('/tonight')).json();
   const blocks=data.schedule.blocks;
   data.schedule.gaps.push({start:'2025-01-15 07:00 PM',end:blocks[0].start,minutes:60});
   data.schedule.gaps.push({start:blocks.at(-1).end,end:'2025-01-16 05:00 AM',minutes:60});
   renderHostedSchedule(data.schedule);
 });
 assert.equal(await page.locator('.schedule-pause').count(),3);
 await page.evaluate(()=>{supabaseClient.auth.signOut=async()=>({error:null});});
 await page.locator('#sign-out-button').click();
 await page.locator('#auth-gate').waitFor({state:'visible'});
 assert.deepEqual(errors,[]);
 fs.writeFileSync('compact-visual-results.json',JSON.stringify({results,errors},null,2));
 console.log(JSON.stringify({viewports:results.map(r=>r.width),errors,checks:'passed'}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});

