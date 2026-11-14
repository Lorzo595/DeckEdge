const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_music',pages:[
   {id:'page_music',name:'Musique',icon:'🎵',buttons:[{id:'m',label:'Musique',type:'hotkey',target:''}]},
   {id:'page_main',name:'Principal',icon:'⌘',buttons:[{id:'p',label:'Principal',type:'hotkey',target:''}]}
  ],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  let saved;
  await page.route('**/api/config',route=>route.request().method()==='POST'
   ? (saved=route.request().postDataJSON(),route.fulfill({json:{status:'ok'}}))
   : route.fulfill({json:fixture}));
  await page.routeWebSocket(/\/ws$/,()=>{});
  await page.goto(base+'/admin'); await page.waitForFunction(()=>studioReady);
  assert.equal(await page.evaluate(()=>currentActivePageId),'page_main');
  await page.locator('[data-page-id=page_music]').click();
  assert.equal(await page.evaluate(()=>studioDirty()),false,'Parcourir les onglets ne doit pas modifier la configuration');
  assert.equal(await page.evaluate(()=>config.active_page_id),'page_music','La navigation doit laisser intacte la valeur chargée, même ancienne');
  await page.locator('#studio-save').click(); await page.waitForFunction(()=>!studioSaving);
  assert.ok(saved);
  await page.reload(); await page.waitForFunction(()=>studioReady);
  assert.equal(await page.evaluate(()=>currentActivePageId),'page_main');
  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/'); await page.locator('.deck-btn').first().waitFor();
  assert.equal(await page.evaluate(()=>currentActivePageId),'page_main');
  await page.locator('.page-tab').filter({hasText:'Musique'}).click();
  await page.evaluate(()=>loadConfig());
  assert.equal(await page.evaluate(()=>currentActivePageId),'page_music','Actualiser une session ouverte ne doit pas interrompre la navigation');
  await page.reload(); await page.locator('.deck-btn').first().waitFor();
  assert.equal(await page.evaluate(()=>currentActivePageId),'page_main');
  assert.deepEqual(errors,[]);
  console.log('OK : Principal à chaque nouvelle ouverture du Studio et du mobile, même avec une ancienne configuration Musique et un ordre différent ; navigation locale et session ouverte conservées.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
