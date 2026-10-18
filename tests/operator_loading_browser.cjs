const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const response=await page.request.get('http://127.0.0.1:8113/tonight');
 const plan=await response.json();
 plan.forecast_accuracy={...plan.forecast_accuracy,nightly:{completed_nights:10,review_after:30,horizons:[{horizon:'afternoon',count:9},{horizon:'dusk',count:10}]}};
 let release;
 await page.route('**/tonight?*',async route=>{await new Promise(r=>release=r); await route.fulfill({json:plan});});
 await page.goto('http://127.0.0.1:8113/operator');
 await page.locator('#load-stages li[data-state="loading"]').waitFor();
 await page.waitForFunction(()=>document.querySelector('#load-stages').textContent.includes('Weather & plan'));
 assert.equal(await page.locator('#hosted-tonight-panel').isVisible(),false);
 assert.equal(await page.locator('footer').isVisible(),false);
 assert.equal(await page.locator('.site-header').isVisible(),true);
 await page.screenshot({path:'../loading-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('[data-state="loading"] .load-ring').evaluate(e=>getComputedStyle(e).animationName),'none');
 await page.screenshot({path:'../loading-mobile.png',fullPage:true});
 await page.waitForFunction(()=>typeof window !== 'undefined');
 while(!release) await new Promise(r=>setTimeout(r,10));
 release();
 await page.locator('#initial-loader').waitFor({state:'hidden'});
 assert.equal(await page.locator('#hosted-opportunity-score').isVisible(),true);
 assert.equal(await page.locator('#forecast-accuracy-link-count').innerText(),'10 nights recorded');
 assert.equal(await page.locator('#catalog-search-form').count(),0);
 assert.equal(await page.locator('#hosted-tonight-date').count(),0);
 assert.equal(await page.locator('#hosted-tonight-panel #hosted-library-history').count(),0);
 const text=await page.locator('#hosted-tonight-panel').innerText();
 assert.doesNotMatch(text,/Setup & details|native pixels|Beginner imaging|Search catalog|Planner notes|Check live conditions|Forecast details|Verify capture settings/);
 assert.match(text,/Capture settings unavailable/);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'../clean-plan-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1100});
 await page.screenshot({path:'../clean-plan-desktop.png',fullPage:true});
 const original=await page.locator('#hosted-schedule-list').innerText();
 await page.unroute('**/tonight?*');
 let fail;
 await page.route('**/tonight?*',async route=>{await new Promise(r=>fail=r); await route.fulfill({status:503,body:'Unavailable'});});
 await page.locator('#hosted-refresh-button').click();
 await page.locator('#refresh-status').waitFor();
 assert.equal(await page.locator('#hosted-schedule-list').innerText(),original);
 assert.equal(await page.locator('#initial-loader').isVisible(),false);
 while(!fail) await new Promise(r=>setTimeout(r,10)); fail();
 await page.waitForFunction(()=>document.querySelector('#refresh-status').textContent.includes('could not'));
 assert.equal(await page.locator('#hosted-schedule-list').innerText(),original);
 await page.unroute('**/tonight?*');
 await page.route('**/tonight?*',route=>route.fulfill({json:plan}));
 await page.locator('#hosted-refresh-button').click();
 await page.locator('#refresh-status').waitFor({state:'hidden'});
 // First-load failure must show retry, not empty cards.
 await page.unroute('**/tonight?*');
 await page.route('**/tonight?*',route=>route.fulfill({status:503,body:'Unavailable'}));
 await page.reload();
 await page.locator('#load-retry').waitFor();
 assert.equal(await page.locator('#hosted-tonight-panel').isVisible(),false);
 await page.unroute('**/tonight?*');
 await page.route('**/tonight?*',route=>route.fulfill({json:plan}));
 await page.locator('#load-retry').click();
 await page.locator('#initial-loader').waitFor({state:'hidden'});
 assert.deepEqual(errors,[]);
 await page.locator('#compact-planning-details').evaluate(e=>e.open=true);
 for (const id of ['hosted-target-exposure','hosted-target-gain','hosted-target-filter']) {
   assert.equal(await page.locator(`#${id}`).isVisible(),false);
 }
 assert.equal(await page.locator('#capture-settings-state').innerText(),'Capture settings unavailable');
 await page.locator('#compact-planning-details').evaluate(e=>e.open=false);
 await page.evaluate(schedule=>{
   const blocks=schedule.blocks.map(block=>({...block,recommendation_source:'rig_category_starting_point',recommended_sub_exposure_seconds:15,recommended_gain:null,recommended_filter:null}));
   renderHostedSchedule({...schedule,blocks});
 },plan.schedule);
 const partialText=await page.locator('#hosted-schedule-list').innerText();
 assert.match(partialText,/15 sec subs/);
 assert.match(partialText,/Starting exposure · confirm gain\/filter on device/);
 assert.doesNotMatch(partialText,/Gain null|Gain undefined|Capture settings unavailable/);
 assert.equal(await page.evaluate(()=>performance.getEntriesByName('polaris:Weather & plan').length),1);
 const layoutChecks=[];
 for (const width of [1536,900,390]) {
   await page.setViewportSize({width,height:1000});
   for (const count of [1,2,3,4,5]) {
     await page.evaluate(({schedule,count})=>{
       const blocks=Array.from({length:count},(_,i)=>({...schedule.blocks[i%schedule.blocks.length],object:`Test ${i}`}));
       renderHostedSchedule({...schedule,blocks,gaps:[]});
     },{schedule:plan.schedule,count});
     const cards=await page.locator('#hosted-schedule-list article').evaluateAll(nodes=>nodes.map(n=>({x:n.offsetLeft,y:n.offsetTop,width:n.offsetWidth,name:n.querySelector('.hosted-schedule-identity').textContent})));
     assert.equal(cards.length,count);
     if(width===1536 && count<=4) assert.equal(new Set(cards.map(c=>c.y)).size,1);
     if(width===390) assert.equal(new Set(cards.map(c=>c.x)).size,1);
     assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
     assert.equal(await page.locator('#hosted-schedule-list .schedule-card-visual svg').count()>0,true);
     layoutChecks.push({width,count,rows:new Set(cards.map(c=>c.y)).size});
   }
 }
 console.log(JSON.stringify({layoutChecks}));
 // A late response after sign-out must never reveal the old account's plan.
 await page.unroute('**/tonight?*');
 let late;
 await page.route('**/tonight?*',async route=>{await new Promise(r=>late=r); await route.fulfill({json:plan}).catch(()=>{});});
 await page.evaluate(()=>{ void loadHostedTonight(); });
 while(!late) await new Promise(r=>setTimeout(r,10));
 await page.evaluate(()=>handleHostedSession(null));
 late();
 await page.waitForTimeout(50);
 assert.equal(await page.locator('#auth-gate').isVisible(),true);
 assert.equal(await page.locator('#hosted-tonight-panel').isVisible(),false);
 // Local mode has three real requests; failed supporting data leaves a useful plan.
 await page.unroute('**/tonight?*');
 await page.route('**/tonight?*',route=>route.fulfill({json:plan}));
 await page.route('**/operator',async route=>{
   const response=await route.fetch();
   await route.fulfill({response,body:(await response.text()).replace('"mode": "supabase"','"mode": "local"')});
 });
 await page.route('**/system',route=>route.fulfill({status:503,body:'Unavailable'}));
 await page.route('**/dashboard?*',route=>route.fulfill({status:503,body:'Unavailable'}));
 await page.reload();
 await page.locator('#initial-loader').waitFor({state:'hidden'});
 assert.equal(await page.locator('#main-content').isVisible(),true);
 assert.match(await page.locator('#refresh-status').innerText(),/supporting data/);
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({passed:true,errors,checks:['slow initial','mobile','reduced motion','visible score metrics','clean target cards','refresh retains data','failure','retry','no overflow']}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
