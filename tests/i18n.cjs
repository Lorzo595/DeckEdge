const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const context=await browser.newContext({viewport:{width:390,height:700},locale:'fr-FR'});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[{id:'a',label:'A',icon:'⌘',type:'key',target:'playpause'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  await page.goto(base+'/?lang=en');await page.locator('#phone-language').waitFor();
  assert.equal(await page.evaluate(()=>I18n.lang),'en');
  assert.equal(await page.locator('#phone-shortcut summary').innerText(),'Keep this Deck on your phone');
  assert.equal(await page.locator('#phone-language').innerText(),'FR');

  await page.locator('#phone-language').click();
  await page.waitForFunction(()=>I18n.lang==='fr');
  assert.equal(await page.locator('#phone-shortcut summary').innerText(),'Garder ce Deck sur mon téléphone');
  assert.equal(await page.locator('#phone-language').innerText(),'EN');

  await page.reload();await page.locator('#phone-language').waitFor();
  assert.equal(await page.evaluate(()=>I18n.lang),'fr');
  assert.equal(await page.locator('#phone-shortcut summary').innerText(),'Garder ce Deck sur mon téléphone');
  await page.locator('#phone-language').click();
  await page.waitForFunction(()=>I18n.lang==='en');
  assert.deepEqual(errors,[]);
  console.log('OK : bascule FR/EN, traduction des textes statiques et persistance après rechargement. Profils simulés.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
