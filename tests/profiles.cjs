const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1200,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',dialog=>dialog.accept());
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Original',icon:'⌘',buttons:[{id:'a',label:'Touche originale',icon:'⌘',type:'key',target:'playpause',color:'#161c2e'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  const imported={active_page_id:'page_main',pages:[{id:'page_main',name:'Importé',icon:'⌘',buttons:[{id:'b',label:'Touche importée',icon:'⌘',type:'key',target:'nexttrack',color:'#161c2e'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  const restored={active_page_id:'page_main',pages:[{id:'page_main',name:'Restauré',icon:'⌘',buttons:[{id:'a',label:'Touche restaurée',icon:'⌘',type:'key',target:'playpause',color:'#161c2e'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  const backups=[{name:'deckedge-20260101-120000-000.json',size:2048,modified:'2026-01-01 12:00:00'}];
  let saveGate=null, restoreGate=null, saves=0, restores=0, restoreError=false;
  let disk=fixture;
  await page.route('**/api/config/validate',route=>route.fulfill({json:{status:'ok',config:imported}}));
  await page.route('**/api/config/backups',route=>route.fulfill({json:{status:'ok',backups}}));
  await page.route('**/api/config/restore',async route=>{
    restores++;
    if(restoreError) return route.fulfill({status:500,json:{detail:'Restauration annulée : sauvegarde de sécurité impossible.'}});
    if(restoreGate) await restoreGate;
    disk=restored;
    return route.fulfill({json:{status:'ok',config:restored}});
  });
  await page.route('**/api/config',async route=>{
    if(route.request().method()==='POST'){
      saves++;
      const pending=route.request().postDataJSON();
      if(saveGate) await saveGate;
      disk=pending;
      return route.fulfill({json:{status:'ok'}});
    }
    return route.fulfill({json:disk});
  });
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady);
  assert.equal(await page.locator('.preview-btn .label').first().innerText(),'Touche originale');

  await page.evaluate(()=>{
    window.__deckExport={};
    const create=URL.createObjectURL.bind(URL);
    URL.createObjectURL=blob=>{window.__deckExport.blob=blob;return create(blob);};
    HTMLAnchorElement.prototype.click=function(){if(this.download){window.__deckExport.name=this.download;return;}};
  });
  await page.locator('#profiles-button').click();
  await page.getByRole('menuitem',{name:'Exporter les profils…'}).click();
  await page.waitForFunction(()=>window.__deckExport && window.__deckExport.name);
  const exportName=await page.evaluate(()=>window.__deckExport.name);
  assert.match(exportName,/^deckedge-profils-\d{4}-\d{2}-\d{2}\.json$/);
  const exported=await page.evaluate(async()=>JSON.parse(await window.__deckExport.blob.text()));
  assert.equal(exported.format,'deckedge-profiles');
  assert.equal(exported.config.pages[0].name,'Original');

  await page.locator('#profiles-button').click();
  const chooserPromise=page.waitForEvent('filechooser');
  await page.getByRole('menuitem',{name:'Importer des profils…'}).click();
  const chooser=await chooserPromise;
  await chooser.setFiles({name:'profils.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({format:'deckedge-profiles',config:imported}))});
  await page.waitForFunction(()=>studioDirty() && getCurrentPage().name==='Importé');
  assert.equal(await page.locator('.preview-btn .label').first().innerText(),'Touche importée');

  let releaseSave;
  saveGate=new Promise(resolve=>{releaseSave=resolve});
  await page.locator('#studio-save').click();
  await page.waitForFunction(()=>studioSaving);

  await page.locator('#profiles-button').click();
  await page.getByRole('menuitem',{name:'Sauvegardes locales…'}).click();
  await page.locator('#backups-modal').waitFor({state:'visible'});
  await page.getByText('2026-01-01 12:00:00').waitFor();
  await page.getByRole('button',{name:'Restaurer'}).click();
  await page.waitForFunction(()=>document.getElementById('studio-toast').textContent.includes('Attendez la fin'));
  assert.equal(restores,0,'Ne pas envoyer une restauration pendant un enregistrement');
  releaseSave(); saveGate=null;
  await page.waitForFunction(()=>!studioSaving);

  let releaseRestore;
  restoreGate=new Promise(resolve=>{releaseRestore=resolve});
  await page.getByRole('button',{name:'Restaurer'}).click();
  await page.waitForFunction(()=>studioRestoringBackup);
  assert.equal(await page.locator('#studio-save').isDisabled(),true);
  const savesBefore=saves;
  await page.evaluate(async()=>{await saveData();await restoreBackup('deckedge-20260101-120000-000.json')});
  assert.equal(saves,savesBefore,'Ne pas enregistrer pendant une restauration');
  releaseRestore(); restoreGate=null;
  await page.waitForFunction(()=>!studioDirty() && getCurrentPage().name==='Restauré');
  await page.waitForFunction(()=>!studioRestoringBackup);
  assert.equal(restores,1,'Une seule restauration doit être envoyée');
  assert.equal(disk.pages[0].name,'Restauré');
  assert.equal(await page.locator('#studio-save').isDisabled(),false);
  assert.equal(await page.locator('#backups-modal').isVisible(),false);

  restoreError=true;
  await page.locator('#profiles-button').click();
  await page.getByRole('menuitem',{name:'Sauvegardes locales…'}).click();
  await page.getByRole('button',{name:'Restaurer'}).click();
  await page.waitForFunction(()=>!studioRestoringBackup && document.getElementById('studio-toast').textContent.includes('Restauration impossible'));
  assert.equal(await page.locator('#studio-save').isDisabled(),false,'Libérer les commandes après un échec');
  assert.equal(await page.evaluate(()=>getCurrentPage().name),'Restauré');
  await page.getByRole('button',{name:'Fermer les sauvegardes',exact:true}).click();

  assert.deepEqual(errors,[]);
  console.log('OK : export, import et restauration d’une sauvegarde de profils, annulation et rendu. Profils simulés.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
