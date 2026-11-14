const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const context=await browser.newContext({viewport:{width:1440,height:1100}});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const buttons=[...Array.from({length:4},(_,i)=>({id:'small'+i,label:['Micro','Pause','Capture','Bureau'][i],type:'hotkey',target:'',icon:['🎙️','⏯️','📸','🖥️'][i],width:'quarter',height:'compact',color:'#2b2e27'})),
   {id:'large',label:'Mode stream',type:'hotkey',target:'',icon:'🎬',width:'full',height:'tall',color:'#3b4930'},
   {id:'vol',label:'Discord',type:'slider',target:'app:discord',icon:'🎙️',width:'half',height:'normal',color:'#c69764'},
   {id:'half',label:'Musique',type:'key',target:'playpause',icon:'🎵',width:'half',height:'normal',color:'#2b2e27'},
   {id:'legacy',label:'Touche classique',type:'key',target:'playpause',icon:'⌘',color:'#2b2e27'},
   {id:'legacy-slider',label:'Général',type:'slider',target:'master',icon:'🔊',color:'#38bdf8'}];
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'🏠',buttons}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:'cpu_temp'},{label:'GPU',sensor_id:'gpu_load',secondary_sensor_id:'gpu_temp'},{label:'RAM',sensor_id:'ram_used',secondary_sensor_id:''}]};
  let saved,unexpectedPosts=[];
  await page.route('**/api/**',route=>{
   if(route.request().url().endsWith('/api/config')){
    if(route.request().method()==='POST'){saved=route.request().postDataJSON();return route.fulfill({json:{status:'ok'}})}
    return route.fulfill({json:fixture});
   }
   if(route.request().method()==='POST'){unexpectedPosts.push(route.request().url());return route.abort()}
   return route.continue();
  });
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady);
  await page.waitForFunction(()=>document.getElementById('phone-screen').offsetWidth===390);
  assert.equal(await page.evaluate(()=>studioDirty()),false);
  const measure=selector=>{
   const grid=document.querySelector(selector),g=grid.getBoundingClientRect(),scale=g.width/grid.offsetWidth;
   return Array.from(grid.children).map(tile=>{const r=tile.getBoundingClientRect();return{x:(r.left-g.left)/scale,y:(r.top-g.top)/scale,width:r.width/scale,height:r.height/scale}});
  };
  const actual=await browser.newPage({viewport:{width:390,height:844}});
  actual.on('pageerror',e=>errors.push(e.message));
  let current=fixture;
  await actual.route('**/api/config',route=>route.fulfill({json:current}));
  const sent=[];await actual.routeWebSocket(/\/ws$/,socket=>socket.onMessage(m=>sent.push(m)));
  async function compare(width,height){
   current=await page.evaluate(()=>studioClone(config));
   await actual.setViewportSize({width,height});await actual.goto(base+'/');await actual.locator('.deck-layout-tile').first().waitFor();
   const preview=await page.evaluate(measure,'#grid-preview'),live=await actual.evaluate(measure,'#deck-grid');
   assert.equal(preview.length,live.length);
   preview.forEach((tile,i)=>{for(const key of ['x','y','width','height'])assert.ok(Math.abs(tile[key]-live[i][key])<1.1,`Aperçu différent du téléphone : widget ${i} ${key}, ${tile[key]} / ${live[i][key]}`)});
   return preview;
  }
  let positions=await compare(390,844);
  assert.ok(positions.slice(0,4).every(p=>p.y===positions[0].y),'Quatre petits widgets doivent tenir sur une ligne');
  assert.ok(positions[4].height>positions[0].height*3,'Le grand bouton doit être nettement plus haut');
  await page.locator('.preview-btn').first().click();
  await page.locator('#inp-label').fill('Micro <test>');
  await compare(390,844);
  assert.equal(await actual.locator('#btn-dom-small0 .label').innerText(),'Micro <test>');
  assert.equal(await actual.locator('#btn-dom-small0 test').count(),0);
  await page.locator('#studio-undo').click();
  await page.locator('.preview-btn').first().click();
  await page.getByText('Taille et comportement',{exact:true}).click();
  await page.locator('#inp-width').selectOption('third');await page.locator('#inp-height').selectOption('tall');
  assert.equal(await page.evaluate(()=>config.pages[0].buttons[0].width),'third');
  await compare(390,844);
  await page.locator('#studio-undo').click();await page.locator('#studio-undo').click();
  assert.equal(await page.evaluate(()=>config.pages[0].buttons[0].width),'quarter');
  assert.equal(await page.evaluate(()=>config.pages[0].buttons[0].height),'compact');
  await page.locator('.preview-btn').first().click({button:'right'});
  await page.getByRole('menuitem',{name:'Redimensionner…'}).click();await page.getByRole('menuitem',{name:'Grand widget',exact:true}).click();
  assert.equal(await page.evaluate(()=>config.pages[0].buttons[0].width),'full');
  assert.equal(await page.locator('#inp-height').inputValue(),'tall');
  await page.locator('#studio-undo').click();
  await page.locator('.preview-btn').first().dragTo(page.locator('.preview-btn').nth(1));
  assert.equal(await page.evaluate(()=>config.pages[0].buttons[1].id),'small0');
  await page.locator('#studio-undo').click();
  await page.locator('.preview-btn.is-slider').first().click();assert.deepEqual(unexpectedPosts,[]);
  await page.locator('#preview-rotate').click();
  await page.waitForFunction(()=>document.getElementById('phone-screen').offsetWidth===844);
  await compare(844,390);assert.equal(await page.evaluate(()=>studioDirty()),false,'Le mode de prévisualisation ne doit pas modifier le pupitre');
  await page.locator('#preview-rotate').click();await page.locator('#preview-size').selectOption('320x568');
  await page.waitForFunction(()=>document.getElementById('phone-screen').offsetWidth===320);
  await compare(320,568);
  await page.locator('#preview-size').selectOption('390x844');await page.locator('#preview-zoom').selectOption('actual');
  await page.locator('.preview-btn').first().click();await page.locator('#inp-width').selectOption('third');
  await page.locator('#studio-save').click();await page.waitForFunction(()=>!studioSaving);
  assert.equal(saved.pages[0].buttons[0].width,'third');
  assert.equal(await page.evaluate(()=>studioDirty()),false);
  await page.locator('#studio-undo').click();
  await page.locator('#preview-zoom').selectOption('fit');
  await page.evaluate(()=>{document.getElementById('grid-preview').scrollTop=0;window.scrollTo(0,0)});
  await page.screenshot({path:path.resolve(__dirname,'../previews/studio-apercu-mobile.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(unexpectedPosts,[]);assert.deepEqual(sent,[]);assert.deepEqual(errors,[]);
  console.log('OK : aperçu fidèle aux positions et dimensions du mobile en 390×844, 320×568 et paysage ; quatre widgets sur une ligne, grand bouton, tailles, annulation, menu rapide, glisser-déposer et sauvegarde simulée ; aucune commande réelle.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
