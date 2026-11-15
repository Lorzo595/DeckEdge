const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({locale:'fr-FR',viewport:{width:1200,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[{
   id:'seq',label:'Ma séquence',icon:'🔗',type:'sequence',target:'',color:'#161c2e',is_toggle:false,state:false,
   steps:[{type:'hotkey',target:'ctrl,shift,m',delay:0.2},{type:'launch',target:'calc.exe',delay:0}]
  }]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  let saved=null;
  await page.route('**/api/config',route=>{
   if(route.request().method()==='POST'){saved=route.request().postDataJSON();return route.fulfill({json:{status:'ok'}});}
   return route.fulfill({json:fixture});
  });
  await page.goto(base+'/admin');await page.waitForFunction(()=>studioReady);
  await page.locator('.preview-btn').first().click();
  await page.waitForFunction(()=>document.getElementById('box-sequence-setup').style.display==='flex');
  assert.equal(await page.locator('#sequence-steps .sequence-step').count(),2);
  assert.equal(await page.locator('#sequence-steps .sequence-step').nth(0).locator('select').first().inputValue(),'hotkey');
  assert.equal(await page.locator('#sequence-steps .sequence-step').nth(0).locator('input[type=text]').inputValue(),'ctrl,shift,m');
  assert.equal(await page.locator('#sequence-steps .sequence-step').nth(0).locator('input[type=number]').inputValue(),'0.2');

  await page.locator('#sequence-steps .sequence-step').nth(0).locator('input[type=text]').fill('ctrl,shift,d');
  await page.getByRole('button',{name:'+ Ajouter une étape'}).click();
  await page.waitForFunction(()=>document.querySelectorAll('#sequence-steps .sequence-step').length===3);
  const third=page.locator('#sequence-steps .sequence-step').nth(2);
  await third.locator('select').first().selectOption('launch');
  await third.locator('input[type=text]').fill('calc.exe');
  await third.locator('input[type=number]').fill('0.5');
  await page.locator('#studio-save').click();
  await page.waitForFunction(()=>!studioSaving);
  assert.ok(saved);
  const steps=saved.pages[0].buttons[0].steps;
  assert.equal(steps.length,3);
  assert.equal(steps[0].target,'ctrl,shift,d');
  assert.equal(steps[2].type,'launch');
  assert.equal(steps[2].target,'calc.exe');
  assert.equal(steps[2].delay,0.5);

  await page.getByRole('button',{name:'Ajouter : Séquence'}).click();
  await page.waitForFunction(()=>getCurrentPage().buttons.at(-1).type==='sequence');
  assert.equal(await page.evaluate(()=>getCurrentPage().buttons.at(-1).steps.length),1);
  assert.deepEqual(errors,[]);
  console.log('OK : éditeur de séquence, ajout d’étapes, sauvegarde et modèle de bibliothèque. Profils simulés.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
