const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({locale:'fr-FR',viewport:{width:1200,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[
   {id:'toggle',label:'Micro',icon:'🔴',type:'volume_app',target:'mic:mute',color:'#161c2e',is_toggle:true,state:false,active_label:'MUTÉ',active_icon:'🔇',active_color:'#991b1b'},
   {id:'seq',label:'Ma séquence',icon:'🔗',type:'sequence',target:'',color:'#161c2e',is_toggle:false,state:false,
    steps:[{type:'hotkey',target:'ctrl,shift,m',delay:0,condition:'button_on',condition_target:'toggle'}]}
  ]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  let saved=null;
  await page.route('**/api/config',route=>{
   if(route.request().method()==='POST'){saved=route.request().postDataJSON();return route.fulfill({json:{status:'ok'}});}
   return route.fulfill({json:fixture});
  });
  await page.goto(base+'/admin?lang=fr');await page.waitForFunction(()=>studioReady);
  await page.locator('.preview-btn').nth(1).click();
  await page.waitForFunction(()=>document.getElementById('box-sequence-setup').style.display==='flex');

  const firstStep=page.locator('#sequence-steps .sequence-step').nth(0);
  const condition=firstStep.locator('.sequence-condition select').first();
  const conditionTarget=firstStep.locator('.sequence-condition select').nth(1);
  assert.equal(await condition.inputValue(),'button_on');
  assert.equal(await conditionTarget.inputValue(),'toggle');
  await condition.selectOption('app_running');
  const appTarget=firstStep.locator('.sequence-condition input[type=text]');
  await appTarget.fill('spotify');
  await page.locator('#studio-save').click();
  await page.waitForFunction(()=>!studioSaving&&!!studioSavedJSON);
  assert.ok(saved);
  assert.equal(saved.pages[0].buttons[1].steps[0].condition,'app_running');
  assert.equal(saved.pages[0].buttons[1].steps[0].condition_target,'spotify');

  await firstStep.locator('.sequence-condition select').first().selectOption('always');
  await page.locator('#action-test-button').click();
  await page.waitForFunction(()=>document.getElementById('action-test-status').textContent==='Action prête');
  assert.equal(await page.locator('#action-test-result').isVisible(),true);
  assert.ok(await page.locator('#action-test-result .action-test-check').count()>=2);

  await firstStep.locator('input[type=text]').first().fill('not-a-key');
  await page.locator('#action-test-button').click();
  await page.waitForFunction(()=>document.getElementById('action-test-status').textContent==='Action incomplète');
  assert.match(await page.locator('#action-test-result').innerText(),/Raccourci inconnu|Touche inconnue/);

  await page.getByRole('button',{name:'Bibliothèque',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('icon-library-modal').style.display==='flex');
  await page.locator('#icon-library-search').fill('micro');
  await page.locator('#icon-library-grid .icon-library-item').first().click();
  await page.waitForFunction(()=>document.getElementById('icon-library-modal').style.display==='none');
  assert.equal(await page.locator('#inp-icon').inputValue(),'🎙️');
  assert.ok((await page.evaluate(()=>JSON.parse(localStorage.getItem('deckedge.recentIcons')||'[]'))).includes('🎙️'));
  const cloneCheck=await page.evaluate(()=>{
   const original=config.pages[0];
   original.buttons[1].steps=[
    {type:'key',target:'a',condition:'button_on',condition_target:'toggle'},
    {type:'key',target:'b',condition:'button_off',condition_target:'external'},
    {type:'key',target:'c',condition:'app_running',condition_target:'toggle'}
   ];
   duplicateStudioPage(original.id);
   return {original:original.buttons,copy:getCurrentPage().buttons};
  });
  assert.notEqual(cloneCheck.copy[0].id,'toggle');
  assert.equal(cloneCheck.copy[1].steps[0].condition_target,cloneCheck.copy[0].id);
  assert.equal(cloneCheck.copy[1].steps[1].condition_target,'external');
  assert.equal(cloneCheck.copy[1].steps[2].condition_target,'toggle');
  assert.equal(cloneCheck.original[1].steps[0].condition_target,'toggle');
  assert.equal(cloneCheck.copy[0].state,false);
  assert.deepEqual(errors,[]);
  console.log('OK : test d’action, conditions de séquence et bibliothèque d’icônes. Commandes simulées, aucune action exécutée.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
