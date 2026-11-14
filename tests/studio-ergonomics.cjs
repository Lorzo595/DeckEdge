const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{window.hostMessages=[];window.chrome ||= {};window.chrome.webview={postMessage:m=>window.hostMessages.push(m)}});
  const fixture={active_page_id:'p1',pages:[
   {id:'p1',name:'Profil test',icon:'⌘',buttons:[{id:'b1',label:'Touche test',type:'hotkey',target:'ctrl,m',icon:'⌘',color:'#161c2e'}, {id:'b2',label:'Volume test',type:'slider',target:'master',icon:'🔊',color:'#161c2e'}]},
   {id:'p2',name:'Autre profil',icon:'⌘',buttons:[{id:'b3',label:'Autre touche',type:'key',target:'playpause',icon:'⏯️',color:'#161c2e'}]}
  ],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:'cpu_temp'}]};
  let saved,failSave=false,releaseSave,holdSave=false;
  await page.route('**/api/config',async route=>{
   if(route.request().method()==='GET')return route.fulfill({json:fixture});
   saved=route.request().postDataJSON();
   if(holdSave)await new Promise(resolve=>releaseSave=resolve);
   return route.fulfill({status:failSave?500:200,json:failSave?{detail:'Test de panne'}:{status:'ok'}});
  });
  let promptText='Profil renommé';page.on('dialog',d=>d.type()==='prompt'?d.accept(promptText):d.accept());
  await page.goto(base+'/admin');
  await page.waitForFunction(()=>studioReady);
  const count=()=>page.locator('.preview-btn').count();
  const state=()=>page.evaluate(()=>({dirty:studioDirty(),config:studioClone(config),undo:studioHistoryIndex}));
  assert.equal((await state()).dirty,false);
  await page.locator('.preview-btn').nth(1).click();
  assert.equal((await state()).dirty,false,'Sélectionner un curseur doit préserver sa couleur et rester propre');
  assert.equal((await state()).config.pages[0].buttons[1].color,'#161c2e');
  await page.locator('.preview-btn').first().click({button:'right'});
  await page.getByRole('menuitem',{name:'Dupliquer',exact:false}).click();
  assert.equal(await count(),3);assert.equal((await state()).dirty,true);
  const duplicated=(await state()).config.pages[0].buttons;assert.equal(new Set(duplicated.map(b=>b.id)).size,3);
  await page.locator('#studio-undo').click();assert.equal(await count(),2);assert.equal((await state()).dirty,false);
  await page.locator('#studio-redo').click();assert.equal(await count(),3);
  await page.locator('#studio-undo').click();
  await page.locator('.preview-btn').first().click();
  await page.locator('#inp-label').fill('Nouveau nom');
  await page.keyboard.press('Control+s');
  await page.waitForFunction(()=>!studioSaving);
  assert.equal(saved.pages[0].buttons[0].label,'Nouveau nom');assert.equal((await state()).dirty,false);
  await page.locator('#studio-undo').click();assert.equal((await state()).dirty,true);
  await page.locator('#studio-redo').click();assert.equal((await state()).dirty,false);
  for(let i=0;i<2;i++){
   await page.locator('.preview-btn').first().click({button:'right'});
   await page.getByRole('menuitem',{name:'Supprimer',exact:false}).click();
  }
  assert.equal(await count(),0);assert.equal(await page.locator('#inp-label').isDisabled(),true);
  await page.locator('#studio-undo').click();assert.equal(await count(),1);
  await page.locator('#studio-undo').click();assert.equal(await count(),2);
  assert.equal(await page.locator('#inp-label').isDisabled(),false);
  await page.locator('.preview-btn').first().click({button:'right'});
  await page.getByRole('menuitem',{name:'Déplacer vers un profil…'}).click();
  await page.getByRole('menuitem',{name:'Autre profil',exact:true}).click();
  assert.equal((await state()).config.pages[0].buttons.length,1);assert.equal((await state()).config.pages[1].buttons.length,2);
  await page.locator('#studio-undo').click();assert.equal(await count(),2);
  await page.locator('[data-page-id=p1]').click({button:'right'});
  await page.getByRole('menuitem',{name:'Dupliquer le profil'}).click();
  assert.equal((await state()).config.pages.length,3);
  const ids=(await state()).config.pages.flatMap(p=>p.buttons.map(b=>b.id));assert.equal(new Set(ids).size,ids.length);
  await page.locator('#studio-undo').click();
  await page.locator('[data-page-id=p1]').focus();await page.keyboard.press('F2');
  assert.equal((await state()).config.pages[0].name,promptText);
  await page.locator('#studio-undo').click();
  await page.locator('.preview-btn').first().click();await page.locator('#inp-label').fill('<img src=x onerror=alert(1)>');
  assert.equal(await page.locator('.preview-btn img').count(),0);
  await page.locator('#studio-undo').click();
  await page.locator('[onclick="openAddMenu(event)"]').first().click();
  await page.getByRole('menuitem',{name:'Curseur de volume',exact:true}).click();
  assert.equal((await state()).config.pages[0].buttons.at(-1).type,'slider');
  await page.locator('#studio-undo').click();
  await page.locator('#app-settings-button').click();
  assert.ok((await page.evaluate(()=>hostMessages)).some(m=>m.type==='openSettings'));
  failSave=true;await page.locator('#inp-label').fill('Échec simulé');
  await page.locator('#studio-save').click();await page.waitForFunction(()=>!studioSaving);
  assert.equal((await state()).dirty,true);assert.match(await page.locator('#studio-toast').innerText(),/refusé/);
  failSave=false;holdSave=true;
  await page.locator('#studio-save').click();
  await page.waitForTimeout(100);
  await page.locator('#inp-label').fill('Modifié pendant la sauvegarde');
  releaseSave();holdSave=false;
  await page.waitForFunction(()=>!studioSaving);
  assert.equal((await state()).dirty,true,'Une modification pendant la requête doit rester non enregistrée');
  await page.getByRole('button',{name:'Recharger',exact:true}).click();
  assert.equal((await state()).dirty,false);
  await page.locator('.preview-btn').first().locator('.tile-more').click();
  await page.screenshot({path:path.resolve(__dirname,'../previews/studio-actions-rapides.png'),fullPage:true});
  await page.keyboard.press('Escape');assert.equal(await page.locator('#studio-menu').isVisible(),false);
  await page.setViewportSize({width:390,height:844});
  await page.locator('.preview-btn').first().locator('.tile-more').click();
  const bounds=await page.locator('#studio-menu').boundingBox();assert.ok(bounds.x>=0&&bounds.x+bounds.width<=390);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);
  console.log('OK : clic droit, menu tactile, duplication et déplacement, profils, suppression de la dernière touche, annuler/rétablir, Ctrl+S, noms échappés, échec et sauvegarde concurrente, liaison paramètres, rendu mobile. Aucun profil réel modifié.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
