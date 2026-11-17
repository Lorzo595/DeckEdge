const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:900},locale:'fr-FR'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[
   {id:'page_main',name:'Principal',icon:'⌘',buttons:[
    {id:'volume',label:'Volume',icon:'♫',type:'slider',target:'master',color:'#536a77',width:'half'},
    {id:'music',label:'Lecture / Pause',icon:'▷',type:'key',target:'playpause',color:'#444444',width:'half'},
    {id:'mic',label:'Micro',icon:'🎙️',type:'hotkey',target:'ctrl,shift,m',color:'#454545',width:'third'},
    {id:'next',label:'Suivant',icon:'»',type:'key',target:'nexttrack',color:'#454545',width:'third'},
    {id:'desktop',label:'Bureau',icon:'▣',type:'hotkey',target:'win,d',color:'#454545',width:'third'}]},
   {id:'folder',name:'Applications',icon:'📁',is_folder:true,buttons:[]},
   {id:'child',name:'Jeux',icon:'🎮',parent_id:'folder',buttons:[]}
  ],monitoring:[{label:'CPU',sensor_id:'cpu_load'},{label:'GPU',sensor_id:'gpu_load'},{label:'RAM',sensor_id:'ram_used'}]};
  let writes=0;
  await page.route('**/api/config',r=>{if(r.request().method()!=='GET')writes++;return r.fulfill({json:fixture})});
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady);
  await page.locator('#pages-bar > .page-tab').filter({hasText:'Applications'}).click();
  assert.equal(await page.locator('#subpages-bar').evaluate(e=>e.previousElementSibling.dataset.pageId),'folder');
  const before=await page.evaluate(()=>JSON.stringify(config));
  await page.getByRole('button',{name:'Ajouter : Volume',exact:true}).click();
  assert.equal(await page.evaluate(()=>JSON.stringify(config)),before,'A folder must never receive an invisible key');
  assert.equal(await page.evaluate(()=>studioDirty()),false);
  await page.locator('#subpages-bar .page-tab').click();
  assert.equal(await page.evaluate(()=>getCurrentPage().id),'child');
  await page.locator('#pages-bar > .page-tab').filter({hasText:'Principal'}).click();
  await page.locator('.preview-btn').nth(1).click();
  for(const [width,height] of [[1440,900],[1200,829],[1024,768],[800,600],[390,844]]){
   await page.setViewportSize({width,height});await page.waitForTimeout(180);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`Overflow at ${width}`);
   const save=await page.locator('#studio-save').boundingBox();assert.ok(save.x>=0&&save.x+save.width<=width+1);
   for(const zoom of ['fit','actual']){
    await page.locator('#preview-zoom').selectOption(zoom);await page.waitForTimeout(100);
    if(width>=1100&&height>=700){
     const panel=await page.locator('#editor-panel').boundingBox();
     assert.ok(panel.y<height-190,'Inspector must remain visible at either zoom');
    }
   }
  }
  await page.setViewportSize({width:1280,height:900});
  await page.locator('#preview-zoom').selectOption('actual');
  await page.evaluate(()=>{document.getElementById('editor-panel').scrollTop=0;document.getElementById('studio-toast').hidden=true});
  await page.screenshot({path:'previews/studio-redesign.png',fullPage:true});
  assert.equal(writes,0);assert.deepEqual(errors,[]);
  console.log('OK : dossier sans touche invisible, sous-pages dans la navigation, barre de sauvegarde accessible, aucun débordement 390–1440 px, inspecteur accessible aux deux zooms.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
