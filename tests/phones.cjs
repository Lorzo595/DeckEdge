const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=require('./ui-base.cjs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({locale:'fr-FR',viewport:{width:1200,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture={active_page_id:'page_main',pages:[{id:'page_main',name:'Principal',icon:'⌘',buttons:[{id:'a',label:'Ma touche',icon:'⌘',type:'key',target:'playpause'}]}],monitoring:[{label:'CPU',sensor_id:'cpu_load',secondary_sensor_id:''}]};
  let phones=[
   {id:'phone1',name:'iPhone · Safari',created_at:'2026-11-15T10:00:00Z',last_seen:'2026-11-15T12:00:00Z',last_ip:'192.168.1.20'},
   {id:'phone2',name:'Android · Chrome',created_at:'2026-11-15T11:00:00Z',last_seen:'2026-11-15T13:00:00Z',last_ip:'192.168.1.21'}
  ];
  let patched=null,revokedAll=false;
  await page.route('**/api/config',route=>route.fulfill({json:fixture}));
  await page.route('**/api/phones**',route=>{
   const req=route.request(), url=new URL(req.url());
   if(url.pathname==='/api/phones'&&req.method()==='GET') return route.fulfill({json:{phones}});
   if(url.pathname==='/api/phones/revoke-all'){revokedAll=true;const count=phones.length;phones=[];return route.fulfill({json:{status:'ok',revoked:count}});}
   const id=url.pathname.split('/').pop();
   if(req.method()==='PATCH'){patched=req.postDataJSON();phones=phones.map(phone=>phone.id===id?{...phone,name:patched.name}:phone);return route.fulfill({json:{status:'ok'}});}
   if(req.method()==='DELETE'){phones=phones.filter(phone=>phone.id!==id);return route.fulfill({json:{status:'ok'}});}
   return route.fulfill({status:404,json:{detail:'not found'}});
  });
  await page.goto(base+'/admin?lang=fr');await page.waitForFunction(()=>studioReady);
  await page.locator('#phones-button').click();
  await page.waitForFunction(()=>document.getElementById('phones-modal').style.display==='flex');
  await page.waitForFunction(()=>document.querySelectorAll('.phone-library-row').length===2);
  assert.match(await page.locator('#phones-list').innerText(),/iPhone · Safari/);
  assert.match(await page.locator('#phones-list').innerText(),/Android · Chrome/);
  assert.match(await page.locator('#phones-list').innerText(),/192\.168\.1\.20/);

  page.once('dialog',dialog=>dialog.accept('Téléphone salon'));
  await page.getByRole('button',{name:'Renommer',exact:true}).first().click();
  await page.waitForFunction(()=>document.querySelector('.phone-library-row .phone-library-name')?.textContent==='Téléphone salon');
  assert.deepEqual(patched,{name:'Téléphone salon'});

  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Révoquer',exact:true}).first().click();
  await page.waitForFunction(()=>document.querySelectorAll('.phone-library-row').length===1);
  assert.match(await page.locator('#phones-list').innerText(),/Android · Chrome/);

  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Révoquer tous',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.phone-library-row').length===0);
  assert.equal(revokedAll,true);
  assert.match(await page.locator('#phones-list').innerText(),/Aucun téléphone associé/);
  assert.deepEqual(errors,[]);
  console.log('OK : liste, renommage, révocation individuelle et révocation totale des téléphones. Serveur simulé.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
