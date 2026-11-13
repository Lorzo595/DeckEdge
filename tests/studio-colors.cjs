const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   window.colorMessages=[];window.nativeCallbacks=[];window.chrome ||= {};
   window.chrome.webview={postMessage:message=>colorMessages.push(message),addEventListener:(kind,listener)=>{if(kind==='message')nativeCallbacks.push(listener)}};
   window.replyColor=data=>nativeCallbacks.forEach(listener=>listener({data}));
  });
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[
   {id:'a',label:'A',icon:'⌘',type:'key',target:'playpause',color:'#161c2e',is_toggle:true,active_color:'#991b1b'},
   {id:'b',label:'B',icon:'⌘',type:'key',target:'playpause',color:'#123456'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  await page.goto('http://127.0.0.1:5000/admin');await page.waitForFunction(()=>studioReady);
  const latest=()=>page.evaluate(()=>colorMessages.filter(m=>m.type==='pickColor').at(-1));
  const read=()=>page.evaluate(()=>studioClone(config.pages[0].buttons));
  const reply=(request,extra)=>page.evaluate(data=>replyColor(data),{type:'colorPicked',requestId:request.requestId,...extra});
  assert.equal(await page.locator('#hex-color').inputValue(),'#161c2e');
  await page.locator('#pick-color').click();let request=await latest();
  assert.equal(request.mode,'screen');assert.equal(request.field,'color');
  await reply({...request,requestId:'wrong-id'},{color:'#abcdef'});assert.equal((await read())[0].color,'#161c2e');
  await reply(request,{color:'#38BDF8'});assert.equal((await read())[0].color,'#38bdf8');
  assert.equal(await page.locator('#hex-color').inputValue(),'#38bdf8');
  await page.locator('#studio-undo').click();assert.equal((await read())[0].color,'#161c2e');
  await page.locator('#pick-color').click();request=await latest();await reply(request,{color:null});
  assert.equal(await page.evaluate(()=>studioDirty()),false);
  await page.getByText('Taille et comportement',{exact:true}).click();
  await page.locator('#pick-active-color').click();request=await latest();assert.equal(request.field,'active_color');
  await reply(request,{color:'#00AA33'});assert.equal((await read())[0].active_color,'#00aa33');assert.equal((await read())[0].color,'#161c2e');
  await page.locator('#studio-undo').click();
  await page.locator('#pick-color').click();request=await latest();
  await page.locator('.preview-btn').nth(1).click();await reply(request,{color:'#abcdef'});
  assert.equal((await read())[0].color,'#abcdef');assert.equal((await read())[1].color,'#123456');
  assert.equal(await page.locator('#hex-color').inputValue(),'#123456');
  await page.locator('#studio-undo').click();await page.locator('.preview-btn').first().click();
  await page.locator('#hex-color').fill('#abc');await page.locator('#hex-color').press('Tab');
  assert.equal((await read())[0].color,'#aabbcc');
  await page.locator('#studio-undo').click();
  await page.locator('#hex-color').fill('#oops');await page.locator('#hex-color').press('Tab');
  assert.equal((await read())[0].color,'#161c2e');assert.equal(await page.locator('#hex-color').inputValue(),'#161c2e');
  await page.locator('#inp-color').click();request=await latest();assert.equal(request.mode,'palette');
  await reply(request,{color:'#112233'});assert.equal((await read())[0].color,'#112233');
  assert.deepEqual(errors,[]);
  console.log('OK : pipette et palette natives, couleur normale/active, annulation, codes hexadécimaux, réponse tardive appliquée au bon widget et annuler/rétablir. Profils simulés.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
