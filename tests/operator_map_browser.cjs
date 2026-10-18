// Isolated headless Chrome; synthetic localhost fixture, no persistent profile.
// Start tests/serve_import_plan_fixture.py first. No external traffic is allowed.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const base = 'http://127.0.0.1:8107';
const origin = {name:'Synthetic Phoenix',latitude:33.4,longitude:-112};
const sites = [{id:1,name:'Synthetic saved site',latitude:34,longitude:-112.5,bortle_class:3,visited_at:null}];
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64');
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const results = [];
  try {
    for (const width of [1440,390]) {
      const context = await browser.newContext({viewport:{width,height:900}});
      const page = await context.newPage();
      const errors = []; page.on('pageerror', error => errors.push(error.message));
      let local = false, mode = 'hold', requests = 0, held;
      await page.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin !== base) return route.fulfill({contentType:'image/png',body:png});
        if (/^\/operator(?:\/.*)?$/.test(url.pathname)) {
          const response = await route.fetch({url:base+'/operator'});
          let body = await response.text();
          if (local) body = body.replace('"mode": "supabase"','"mode": "local"');
          body = body.replace('<script>window.supabase','<script nonce="synthetic">window.supabase');
          return route.fulfill({response,body,headers:{...response.headers(),
            'content-security-policy':"default-src 'self'; script-src 'self' 'nonce-synthetic'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src 'self'; font-src 'self' data:"}});
        }
        if (url.pathname === '/operator-assets/leaflet.js') {
          requests++;
          if (mode === 'fail') return route.abort();
          if (mode === 'hold') return new Promise(resolve => { held = async (abort=false) => { await (abort ? route.abort() : route.continue()).catch(()=>{}); resolve(); }; });
        }
        if (url.pathname === '/candidate-sites') return route.fulfill({json:sites});
        if (url.pathname === '/tonight') {
          const response = await route.fetch();
          const plan = await response.json();
          plan.observatory = {...plan.observatory, ...origin};
          return route.fulfill({response,json:plan});
        }
        if (url.pathname === '/system' || url.pathname === '/dashboard') return route.fulfill({status:503,body:'Synthetic unavailable supporting data'});
        return route.continue();
      });
      await page.goto(base+'/operator');
      await page.locator('#initial-loader').waitFor({state:'hidden'});
      assert.equal(await page.locator('#hosted-tonight-panel').isVisible(),true);
      assert.equal(requests,0, 'Hosted startup must not request the held optional map library');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await page.screenshot({path:`../map-hosted-${width}.png`,fullPage:true});

      // A failed optional map must leave fetched sites available.
      local = true; mode = 'fail';
      await page.goto(base+'/operator/locations');
      await page.locator('#initial-loader').waitFor({state:'hidden'});
      assert.match(await page.locator('#candidate-site-list').innerText(),/Synthetic saved site/);
      assert.match(await page.locator('#candidate-site-map').innerText(),/unavailable/);
      mode = 'success';
      await page.locator('#refresh-button').click();
      await page.locator('#candidate-site-map.leaflet-container').waitFor();
      assert.equal(await page.locator('#candidate-site-map .leaflet-tile').count()>0,true);
      await page.locator('#candidate-site-map').click({position:{x:90,y:90}});
      assert.notEqual(await page.locator('#candidate-site-latitude').inputValue(),'');
      await page.evaluate(async()=>renderCaptureLocations({capture_locations:[{location:'Synthetic capture',latitude:33.4,longitude:-112,capture_count:2,bortle_class:4}]}));
      assert.equal(await page.locator('#capture-location-map.leaflet-container').count(),1);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await page.screenshot({path:`../map-local-${width}.png`,fullPage:true});
      await page.locator('[data-view-link="tonight"]').click();
      await page.locator('#initial-loader').waitFor({state:'hidden'});
      assert.equal(await page.locator('#candidate-site-map').isVisible(),false);
      await page.locator('[data-view-link="locations"]').click();
      await page.locator('#initial-loader').waitFor({state:'hidden'});
      assert.equal(await page.locator('#candidate-site-map.leaflet-container').isVisible(),true);

      // A map response held across a load-generation change must not render stale sites.
      local = false; mode = 'hold'; held = null;
      await page.goto(base+'/operator');
      await page.locator('#initial-loader').waitFor({state:'hidden'});
      await page.evaluate(origin=>{window.mapAttempt=loadCandidateSites(origin);},origin);
      await page.waitForFunction(()=>!!document.querySelector('script[src="/operator-assets/leaflet.js"]'));
      while (!held) await new Promise(resolve=>setTimeout(resolve,10));
      await page.evaluate(()=>{loadingRun=loadingCoordinator.begin({});});
      await held(); await page.evaluate(()=>window.mapAttempt);
      assert.doesNotMatch(await page.locator('#candidate-site-list').innerText(),/Synthetic saved site/);

      // Actual browser timer expires; retry creates a fresh library request.
      held = null;
      await page.reload(); await page.locator('#initial-loader').waitFor({state:'hidden'});
      await page.evaluate(origin=>{window.mapAttempt=loadCandidateSites(origin);},origin);
      await page.waitForFunction(()=>document.querySelector('#candidate-site-list').textContent.includes('Synthetic saved site'),null,{timeout:20000});
      assert.match(await page.locator('#candidate-site-map').innerText(),/unavailable/);
      const releaseExpired = held;
      mode = 'success';
      // End the simulated dead connection before restoring network service.
      if (releaseExpired) await releaseExpired(true);
      await page.evaluate(origin=>loadCandidateSites(origin),origin);
      assert.equal(await page.locator('#candidate-site-map.leaflet-container').count(),1);
      assert.deepEqual(errors,[]);
      results.push({width,passed:true,requests,checks:['hosted startup without Leaflet','CSP','failure preserves sites','retry','map clicks','capture map','open close reopen','no overflow','stale generation','15-second timeout and retry'],pageErrors:errors});
      await context.close();
    }
    console.log(JSON.stringify({browser:await browser.version(),results},null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
