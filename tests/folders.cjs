const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');

const fixture={active_page_id:'page_main',pages:[
 {id:'page_main',name:'Principal',icon:'🏠',buttons:[{id:'home',label:'Accueil',icon:'🏠',type:'key',target:'playpause',color:'#161c2e'}]},
 {id:'folder_games',name:'Jeux',icon:'📁',is_folder:true,parent_id:null,buttons:[]},
 {id:'page_steam',name:'Steam',icon:'🎮',parent_id:'folder_games',buttons:[{id:'steam',label:'Steam',icon:'🎮',type:'launch',target:'start steam://',color:'#171a21'}]},
 {id:'page_discord',name:'Discord',icon:'💬',parent_id:'folder_games',buttons:[{id:'discord',label:'Discord',icon:'💬',type:'launch',target:'start discord:',color:'#5865f2'}]},
 {id:'folder_empty',name:'Vide',icon:'📁',is_folder:true,parent_id:null,buttons:[]}
],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};

(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({locale:'fr-FR',viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let saved=null;
  await page.route('**/api/config',route=>{
   if(route.request().method()==='POST'){saved=route.request().postDataJSON();return route.fulfill({json:{status:'ok'}});}
   return route.fulfill({json:fixture});
  });
  await page.goto(base+'/admin?lang=fr');await page.waitForFunction(()=>studioReady);
  const topTabs=page.locator('#pages-bar .page-tab');
  assert.equal(await topTabs.count(),3);
  assert.match(await page.locator('#pages-bar').innerText(),/Jeux/);
  assert.match(await page.locator('#pages-bar').innerText(),/Vide/);
  assert.doesNotMatch(await page.locator('#pages-bar').innerText(),/Steam/);

  await page.locator('#pages-bar .page-tab').filter({hasText:'Jeux'}).click();
  await page.waitForFunction(()=>getCurrentPage().id==='folder_games');
  assert.equal(await page.locator('#subpages-bar').isVisible(),true);
  assert.match(await page.locator('#subpages-bar').innerText(),/Steam/);
  assert.match(await page.locator('#subpages-bar').innerText(),/Discord/);
  assert.match(await page.locator('#grid-preview').innerText(),/Dossier de navigation/);

  await page.locator('#subpages-bar .page-tab').filter({hasText:'Steam'}).click();
  await page.waitForFunction(()=>getCurrentPage().id==='page_steam');
  assert.equal(await page.locator('#inp-page-name').inputValue(),'Steam');
  assert.match(await page.locator('#grid-preview').innerText(),/Steam/);

  await page.selectOption('#inp-page-parent','folder_empty');
  await page.waitForFunction(()=>getCurrentPage().parent_id==='folder_empty');
  await page.locator('#studio-save').click();
  await page.waitForFunction(()=>!studioSaving&&!!studioSavedJSON);
  assert.ok(saved);
  assert.equal(saved.pages.find(page=>page.id==='page_steam').parent_id,'folder_empty');

  page.once('dialog',dialog=>dialog.accept('Musique'));
  await page.getByRole('button',{name:'+ Dossier',exact:true}).click();
  await page.waitForFunction(()=>config.pages.some(page=>page.is_folder&&page.name==='Musique'));
  assert.equal(await page.evaluate(()=>getCurrentPage().is_folder),true);
  const copiedFolder=await page.evaluate(()=>{
   const steam=config.pages.find(p=>p.id==='page_steam');
   steam.parent_id='folder_games';
   steam.buttons=[{id:'folder_gate',label:'Gate',type:'key',target:'a',is_toggle:true,state:true}];
   const discord=config.pages.find(p=>p.id==='page_discord');
   discord.buttons=[{id:'folder_seq',type:'sequence',steps:[
    {type:'key',target:'b',condition:'button_on',condition_target:'folder_gate'},
    {type:'key',target:'c',condition:'button_off',condition_target:'home'}
   ]}];
   duplicateStudioPage('folder_games');
   const folder=getCurrentPage();
   return {folder,children:config.pages.filter(p=>p.parent_id===folder.id),original:steam.buttons[0]};
  });
  assert.equal(copiedFolder.children.length,2);
  const gate=copiedFolder.children.find(p=>p.name==='Steam').buttons[0];
  const seq=copiedFolder.children.find(p=>p.name==='Discord').buttons[0];
  assert.notEqual(gate.id,'folder_gate');
  assert.equal(gate.state,false);
  assert.equal(seq.steps[0].condition_target,gate.id);
  assert.equal(seq.steps[1].condition_target,'home');
  assert.equal(copiedFolder.original.id,'folder_gate');
  assert.equal(copiedFolder.original.state,true);
  assert.deepEqual(errors,[]);

  const phone=await browser.newPage({locale:'fr-FR',viewport:{width:390,height:800}});
  const phoneErrors=[];phone.on('pageerror',e=>phoneErrors.push(e.message));
  await phone.route('**/api/config',route=>route.fulfill({json:fixture}));
  await phone.goto(base+'/');await phone.locator('#pages-bar .page-tab').filter({hasText:'Jeux'}).waitFor();
  assert.doesNotMatch(await phone.locator('#pages-bar').innerText(),/Steam/);
  await phone.locator('#pages-bar .page-tab').filter({hasText:'Jeux'}).click();
  await phone.waitForFunction(()=>document.getElementById('subpages-bar').hidden===false);
  assert.match(await phone.locator('#subpages-bar').innerText(),/Steam/);
  assert.match(await phone.locator('#subpages-bar').innerText(),/Discord/);
  assert.match(await phone.locator('#deck-grid').innerText(),/Steam/);

  await phone.locator('#subpages-bar .page-tab').filter({hasText:'Discord'}).click();
  await phone.waitForFunction(()=>currentActivePageId==='page_discord');
  assert.match(await phone.locator('#deck-grid').innerText(),/Discord/);

  await phone.locator('#pages-bar .page-tab').filter({hasText:'Vide'}).click();
  await phone.waitForFunction(()=>currentActivePageId==='folder_empty');
  assert.equal(await phone.locator('#subpages-bar').isVisible(),false);
  assert.match(await phone.locator('#deck-grid').innerText(),/Ce dossier est vide/);
  assert.deepEqual(phoneErrors,[]);
  console.log('OK : dossiers et sous-pages dans le Studio et sur le mobile, déplacement, création et dossier vide.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
