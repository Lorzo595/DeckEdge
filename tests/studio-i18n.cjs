const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const context=await browser.newContext({viewport:{width:1200,height:900},locale:'en-US'});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[{id:'a',label:'Ma touche',icon:'⌘',type:'key',target:'playpause',color:'#161c2e'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady && typeof I18n!=='undefined');
  await page.waitForFunction(()=>document.body.innerText.includes('Reload'));
  assert.equal(await page.evaluate(()=>I18n.lang),'en');
  assert.equal(await page.locator('#studio-language').inputValue(),'en');
  assert.equal(await page.locator('#studio-save').innerText(),'Save');
  assert.equal(await page.locator('.workspace-heading h2').innerText(),'Your Deck');
  assert.match(await page.locator('#editor-title').innerText(),/Customize$/);
  assert.equal(await page.getByRole('heading',{name:'Actions',exact:true}).innerText(),'Actions');

  await page.locator('#profiles-button').click();
  await page.getByRole('menuitem',{name:'Export profiles…'}).waitFor();
  await page.keyboard.press('Escape');

  await page.selectOption('#studio-language','fr');
  await page.waitForFunction(()=>document.body.innerText.includes('Recharger'));
  assert.equal(await page.evaluate(()=>I18n.lang),'fr');
  assert.equal(await page.locator('#studio-save').innerText(),'Enregistrer');
  assert.equal(await page.locator('.workspace-heading h2').innerText(),'Votre Deck');
  assert.match(await page.locator('#editor-title').innerText(),/Personnaliser$/);

  await page.reload();await page.waitForFunction(()=>studioReady && document.body.innerText.includes('Recharger'));
  assert.equal(await page.evaluate(()=>I18n.lang),'fr');
  assert.deepEqual(errors,[]);
  console.log('OK : Studio bilingue, libellés, sélecteur et persistance après rechargement. Profils simulés.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
