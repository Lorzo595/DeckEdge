const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({locale:'fr-FR',viewport:{width:1200,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[{id:'a',label:'A',icon:'⌘',type:'key',target:'playpause',color:'#161c2e'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  const report={generated_at:'2026-11-14 12:00:00',app:{name:'DeckEdge',version:'0.1.2',pages:1,buttons:1},system:{platform:'Windows test'},network:{port:5011},audio:{devices:[],apps:[]},monitoring:{connected:false},discord:{is_authenticated:false},logs:{deckedge:['ligne de journal'],desktop:[]}};
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  await page.route('**/api/diagnostics',route=>route.fulfill({json:report}));
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady);
  await page.locator('#diagnostics-button').click();
  await page.locator('#diagnostics-modal').waitFor({state:'visible'});
  await page.waitForFunction(()=>document.getElementById('diagnostics-output').textContent.includes('"version"'));
  const text=await page.locator('#diagnostics-output').textContent();
  assert.match(text,/"version": "0.1.2"/);
  assert.match(text,/"deckedge": \[/);
  await page.locator('#diagnostics-modal button[aria-label="Fermer le diagnostic"]').click();
  await page.waitForFunction(()=>document.getElementById('diagnostics-modal').style.display==='none');
  assert.deepEqual(errors,[]);
  console.log('OK : panneau de diagnostic, rapport local et fermeture du modal. Profils simulés.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
