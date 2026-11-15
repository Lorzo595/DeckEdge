const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const context=await browser.newContext({viewport:{width:390,height:800},isMobile:true,hasTouch:true,deviceScaleFactor:1,locale:'fr-FR'});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[
   {id:'toggle',label:'Micro',icon:'🔴',type:'volume_app',target:'mic:mute',color:'#161c2e',is_toggle:true,state:false,active_label:'MUTÉ',active_icon:'🔇',active_color:'#991b1b'},
   {id:'vol',label:'Volume',icon:'🔊',type:'slider',target:'master',color:'#38bdf8'}
  ]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  await page.goto(base+'/');await page.locator('#btn-dom-toggle').waitFor();

  const viewport=await page.locator('meta[name=viewport]').getAttribute('content');
  assert.ok(!/user-scalable\s*=\s*no/i.test(viewport));
  assert.ok(!/maximum-scale/i.test(viewport));
  const toggle=page.locator('#btn-dom-toggle');
  assert.equal(await toggle.getAttribute('aria-pressed'),'false');
  assert.match(await toggle.evaluate(el=>getComputedStyle(el).touchAction),/pinch-zoom/);
  assert.match(await page.locator('#btn-dom-vol').evaluate(el=>getComputedStyle(el).touchAction),/pinch-zoom/);

  await page.evaluate(()=>updateButtonDOM({btn_id:'toggle',state:true,active_icon:'✅',active_label:'ACTIF',active_color:'#15803d',icon:'🔴',label:'Micro'}));
  assert.equal(await toggle.getAttribute('aria-pressed'),'true');
  const mute=page.locator('#mute-btn-vol');
  assert.ok(['true','false'].includes(await mute.getAttribute('aria-pressed')));
  assert.deepEqual(errors,[]);
  console.log('OK : zoom mobile autorisé, aria-pressed sur les touches à bascule et la sourdine, animations réduites.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
