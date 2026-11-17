const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAgElEQVR4nNXOQREAIAzAsFLpiMILbhCxB9coyNrnUiZxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEufvwNQD9ogCkYIBwWcAAAAASUVORK5CYII=','base64');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({locale:'fr-FR',viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',buttons:[{id:'test',label:'Enregistrement',icon:'🔴',type:'hotkey',target:'ctrl,f9',is_toggle:true,color:'#444444'},{id:'volume',label:'Volume',icon:'♫',type:'slider',target:'master',color:'#557080'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load'}]};
  if(process.env.DECKEDGE_TEST_DOWNLOADS==='1'){
   for(const id of ['pc-apps','gaming']){const response=await fetch(base+'/api/media/catalog/'+id,{method:'POST'});assert.equal(response.status,200);const result=await response.json();assert.equal(result.items.length,6);}
  }
  let writes=0;
  await page.route('**/api/config',r=>{if(r.request().method()!=='GET')writes++;return r.fulfill({json:fixture})});
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady);
  await page.getByRole('button',{name:'Bibliothèque',exact:true}).click();
  await page.getByRole('tab',{name:'Packs à installer',exact:true}).click();
  const offline=page.locator('.media-pack').filter({hasText:'Commandes animées'});
  await offline.getByRole('button').click();
  await page.waitForFunction(()=>document.querySelector('.media-status').textContent.includes('terminé'));
  await page.getByRole('tab',{name:'Mes visuels',exact:true}).click();
  await page.locator('#media-files').setInputFiles({name:'Mon icone.png',mimeType:'image/png',buffer:png});
  await page.waitForFunction(()=>document.querySelector('.media-status').textContent.includes('ajoutés'));
  const downloaded=await fetch(base+'/api/media/packs/animated-controls/export');
  await page.locator('#media-pack-file').setInputFiles({name:'Mes animations.zip',mimeType:'application/zip',buffer:Buffer.from(await downloaded.arrayBuffer())});
  await page.waitForFunction(()=>document.querySelector('.media-status').textContent.includes('ajoutés'));
  await page.locator('#icon-library-search').fill('Enregistrement');
  await page.locator('.media-choice').filter({hasText:'Enregistrement'}).first().click();
  const normal=await page.evaluate(()=>getCurrentPage().buttons[0].image);
  assert.match(normal,/\.gif$/);
  await page.locator('.preview-btn .key-artwork').first().waitFor();
  await page.waitForFunction(()=>document.querySelector('.preview-btn .key-artwork').naturalWidth>0);
  const samples=[];for(let index=0;index<4;index++){samples.push((await page.locator('.preview-btn .key-artwork').first().screenshot()).toString('base64'));await page.waitForTimeout(90);}
  assert.ok(new Set(samples).size>1,'GIF must animate in the browser');
  await page.locator('#studio-undo').click();assert.equal(await page.evaluate(()=>getCurrentPage().buttons[0].image||''),'');
  await page.locator('#studio-redo').click();assert.equal(await page.evaluate(()=>getCurrentPage().buttons[0].image),normal);
  await page.getByRole('button',{name:'Bibliothèque',exact:true}).click();
  await page.getByRole('combobox',{name:'État de la touche'}).selectOption('active_image');
  await page.locator('#icon-library-search').fill('Chargement');
  await page.locator('.media-choice').click();
  const active=await page.evaluate(()=>getCurrentPage().buttons[0].active_image);assert.match(active,/\.gif$/);assert.notEqual(normal,active);
  const phone=await browser.newPage({viewport:{width:390,height:844}});
  const configured=await page.evaluate(()=>studioClone(config));
  configured.pages[0].buttons[1].image=normal;
  await phone.route('**/api/config',r=>r.fulfill({json:configured}));await phone.routeWebSocket(/\/ws$/,socket=>socket.onMessage(()=>{}));
  await phone.goto(base+'/');await phone.locator('#btn-dom-test .key-artwork').waitFor();
  assert.equal(await phone.locator('#btn-dom-test img').getAttribute('src'),'/media/'+normal);
  assert.equal(await phone.locator('#mute-btn-volume img').getAttribute('src'),'/media/'+normal);
  await phone.evaluate(()=>updateButtonDOM({btn_id:'test',state:true}));
  assert.equal(await phone.locator('#btn-dom-test img').getAttribute('src'),'/media/'+active);
  await page.evaluate(()=>{window.__mediaExport={};const create=URL.createObjectURL.bind(URL);URL.createObjectURL=blob=>{window.__mediaExport.blob=blob;return create(blob)};HTMLAnchorElement.prototype.click=function(){if(this.download)window.__mediaExport.name=this.download};});
  await page.evaluate(()=>exportProfiles());
  await page.waitForFunction(()=>window.__mediaExport.name);
  const exported=await page.evaluate(async()=>JSON.parse(await window.__mediaExport.blob.text()));assert.ok(exported.media[normal]);assert.ok(exported.media[active]);
  page.on('dialog',dialog=>dialog.accept());
  await page.locator('#import-config-file').setInputFiles({name:'media-profiles.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(exported))});
  await page.waitForFunction(()=>/Profils importés|Import impossible/.test(document.getElementById('studio-toast').textContent));
  assert.match(await page.locator('#studio-toast').textContent(),/Profils importés/);
  assert.equal(await page.evaluate(()=>getCurrentPage().buttons[0].image),normal);
  await page.getByRole('button',{name:'Bibliothèque',exact:true}).click();
  await page.getByRole('tab',{name:'Mes visuels',exact:true}).click();
  await page.locator('#icon-library-search').fill('');
  await page.locator('.media-choice img').first().waitFor();
  await page.evaluate(()=>document.getElementById('studio-toast').hidden=true);
  await page.screenshot({path:'previews/bibliotheque-visuelle.png',fullPage:true});
  for(const width of [800,390]){await page.setViewportSize({width,height:844});await page.waitForTimeout(150);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);}
  await page.keyboard.press('Escape');
  await page.evaluate(()=>I18n.setLanguage('en'));
  await page.evaluate(()=>openIconLibrary());
  await page.getByRole('tab',{name:'My artwork',exact:true}).waitFor();
  assert.equal(await page.getByRole('combobox',{name:'Key state'}).inputValue(),'image');
  await page.getByRole('button',{name:'Remove key artwork',exact:true}).waitFor();
  await page.keyboard.press('Escape');
  assert.equal(writes,0);assert.deepEqual(errors,[]);
  console.log('OK : pack GIF, import image et ZIP, recherche, visuel normal/actif, annuler/rétablir, rendu téléphone, export/import avec images et fenêtre 390–1280 px. Profils simulés.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
