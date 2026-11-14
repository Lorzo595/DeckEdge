const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const context=await browser.newContext({viewport:{width:390,height:700},isMobile:true,hasTouch:true,deviceScaleFactor:1});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const buttons=[
   {id:'tap',label:'Commande 1',type:'hotkey',target:'ctrl,m',icon:'⌘'},
   {id:'tap2',label:'Commande 2',type:'hotkey',target:'ctrl,m',icon:'⌘'},
   {id:'slider',label:'Volume',type:'slider',target:'master',icon:'🔊',color:'#38bdf8'},
   ...Array.from({length:20},(_,i)=>({id:'more'+i,label:'Commande '+(i+3),type:'hotkey',target:'ctrl,m',icon:'⌘'}))
  ];
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:'cpu_temp'}]};
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  let messages=[];
  await page.routeWebSocket(/\/ws$/,socket=>socket.onMessage(message=>messages.push(message)));
  const cdp=await context.newCDPSession(page);
  const point=(x,y)=>({x,y,id:1,radiusX:2,radiusY:2,force:1});
  async function gesture(x,y,dx,dy,cancel=false){
   await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point(x,y)]});
   for(let step=1;step<=10;step++){
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[point(x+dx*step/10,y+dy*step/10)]});
    await page.waitForTimeout(20);
   }
   await cdp.send('Input.dispatchTouchEvent',{type:cancel?'touchCancel':'touchEnd',touchPoints:[]});
   await page.waitForTimeout(150);
  }
  async function fresh(){await page.goto(base+'/');await page.locator('#btn-dom-slider').waitFor();await page.waitForFunction(()=>ws?.readyState===WebSocket.OPEN);messages=[];}
  await fresh();
  let rect=await page.locator('#btn-dom-tap').boundingBox();
  await gesture(rect.x+rect.width/2,rect.y+rect.height/2,0,-120);
  assert.ok(await page.locator('#deck-grid').evaluate(el=>el.scrollTop)>0,'Le glissement sur une touche doit défiler');
  assert.deepEqual(messages,[],'Un défilement sur une touche ne doit envoyer aucune commande');
  await fresh();rect=await page.locator('#btn-dom-slider').boundingBox();
  await gesture(rect.x+rect.width/2,rect.y+rect.height/2,0,-120);
  assert.ok(await page.locator('#deck-grid').evaluate(el=>el.scrollTop)>0,'Le curseur doit autoriser le défilement vertical');
  assert.deepEqual(messages,[],'Le défilement vertical ne doit pas modifier le volume');
  await fresh();rect=await page.locator('#mute-btn-slider').boundingBox();
  await gesture(rect.x+rect.width/2,rect.y+rect.height/2,0,-100);
  assert.deepEqual(messages,[],'Défiler depuis la sourdine ne doit pas couper le son');
  await fresh();await page.locator('#btn-dom-tap').tap();assert.deepEqual(messages,['tap']);
  await fresh();await page.locator('#mute-btn-slider').tap();
  assert.equal(messages.length,1);assert.equal(JSON.parse(messages[0]).action,'toggle_mute');
  await fresh();rect=await page.locator('#btn-dom-slider').boundingBox();
  await gesture(rect.x+rect.width*.35,rect.y+rect.height/2,rect.width*.45,0);
  const volumeMessages=messages.map(m=>JSON.parse(m));
  assert.ok(volumeMessages.length>0);assert.ok(volumeMessages.every(m=>m.action==='set_volume'));
  assert.ok(Math.abs(volumeMessages.at(-1).value-80)<=1);
  assert.equal(await page.locator('#deck-grid').evaluate(el=>el.scrollTop),0);
  await fresh();rect=await page.locator('#btn-dom-tap').boundingBox();
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point(rect.x+30,rect.y+30)]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]});
  assert.deepEqual(messages,[]);assert.equal(await page.locator('.pressed').count(),0);
  for(const viewport of [{width:390,height:700},{width:844,height:390},{width:320,height:568}]){
   await page.setViewportSize(viewport);
   await page.waitForTimeout(150);
   await page.evaluate(()=>{document.documentElement.style.setProperty('--safe-bottom','34px');updateViewportHeight();document.getElementById('deck-grid').scrollTop=1e6});
   await page.waitForTimeout(80);
   const metrics=await page.evaluate(()=>{
    const grid=document.getElementById('deck-grid'),last=grid.lastElementChild;
    return {gridBottom:grid.getBoundingClientRect().bottom,lastBottom:last.getBoundingClientRect().bottom,padding:parseFloat(getComputedStyle(grid).paddingBottom),bodyBottom:document.body.getBoundingClientRect().bottom,visibleHeight:visualViewport.height,overflow:document.documentElement.scrollWidth>innerWidth,scrollTop:grid.scrollTop,scrollHeight:grid.scrollHeight,clientHeight:grid.clientHeight};
   });
   assert.ok(metrics.lastBottom<=metrics.gridBottom-metrics.padding+2,'La dernière touche doit être entièrement au-dessus de la zone système : '+JSON.stringify({viewport,metrics}));
   assert.ok(metrics.bodyBottom<=metrics.visibleHeight+1,'Le contenu doit suivre la hauteur réellement visible');
   assert.equal(metrics.overflow,false);
  }
  await page.setViewportSize({width:390,height:700});
  await page.locator('#deck-grid').evaluate(el=>el.scrollTop=el.scrollHeight);
  await page.screenshot({path:path.resolve(__dirname,'../previews/mobile-defilement-bas.png')});
  const desktop=await browser.newPage({viewport:{width:1000,height:700}});
  await desktop.route('**/api/config',route=>route.fulfill({json:fixture}));
  const desktopMessages=[];
  await desktop.routeWebSocket(/\/ws$/,socket=>socket.onMessage(message=>desktopMessages.push(message)));
  await desktop.goto(base+'/');
  await desktop.locator('#btn-dom-slider').waitFor();
  const desktopSlider=await desktop.locator('#btn-dom-slider').boundingBox();
  await desktop.mouse.move(desktopSlider.x+desktopSlider.width*.3,desktopSlider.y+desktopSlider.height/2);
  await desktop.mouse.down();
  await desktop.mouse.move(desktopSlider.x+desktopSlider.width*.75,desktopSlider.y+desktopSlider.height/2,{steps:5});
  await desktop.mouse.up();
  assert.ok(desktopMessages.some(message=>JSON.parse(message).action==='set_volume'),'Le réglage à la souris doit fonctionner également');
  assert.deepEqual(errors,[]);
  console.log('OK : défilement tactile depuis touches, curseur et sourdine sans action ; appuis simples uniques ; réglage horizontal tactile et souris ; annulation du geste ; dernières touches visibles avec zone système de 34 px en portrait, paysage et petit écran. Commandes audio simulées.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
