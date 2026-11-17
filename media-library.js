/* Media stay on the PC. Keys contain a content ID, never a third-party URL. */
function setupMediaLibrary() {
  const modal=document.getElementById('icon-library-modal');
  const dialog=modal.querySelector('.icon-library');
  const search=document.getElementById('icon-library-search');
  const categories=document.getElementById('icon-library-categories');
  const emojiScroll=dialog.querySelector('.icon-library-scroll');
  const state={tab:'emoji',items:[],packs:[],catalog:[],target:null,busy:false,loaded:false};
  const text=(fr,en)=>I18n.lang==='en'?en:fr;
  const tabs=document.createElement('div');tabs.className='media-tabs';tabs.setAttribute('role','tablist');
  const area=document.createElement('section');area.className='media-area';area.hidden=true;
  const status=document.createElement('p');status.className='media-status';status.setAttribute('role','status');
  const controls=document.createElement('div');controls.className='media-controls';
  const mode=document.createElement('select');mode.setAttribute('aria-label',text('État de la touche','Key state'));
  for(const [value,label] of [['image',text('Visuel normal','Normal artwork')],['active_image',text('Visuel actif / sourdine','Active / muted artwork')]]){const option=new Option(label,value);mode.append(option);}
  const clear=document.createElement('button');clear.type='button';clear.className='btn btn-secondary';clear.textContent=text('Retirer le visuel de la touche','Remove key artwork');
  clear.onclick=()=>apply('');controls.append(mode,clear);
  dialog.querySelector('.icon-library-head').after(tabs,controls);
  dialog.append(area,status);
  const files=document.createElement('input');files.type='file';files.multiple=true;files.accept='.png,.jpg,.jpeg,.webp,.gif,.svg,.ico';files.hidden=true;files.id='media-files';
  const packFile=document.createElement('input');packFile.type='file';packFile.accept='.zip,.deckedge-pack';packFile.hidden=true;packFile.id='media-pack-file';dialog.append(files,packFile);
  const targetButton=()=>{const target=state.target;return target&&config.pages.find(page=>page.id===target.page)?.buttons.find(button=>button.id===target.button);};

  async function request(url,options){const response=await fetch(url,options);const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'HTTP '+response.status);return data;}
  function message(value){status.textContent=value;}
  function button(label,action){const node=document.createElement('button');node.type='button';node.className='btn btn-secondary';node.textContent=label;node.onclick=action;return node;}
  async function refresh(){const [library,catalog]=await Promise.all([request('/api/media'),request('/api/media/catalog')]);state.items=library.items;state.packs=library.packs;state.catalog=catalog.packs;state.loaded=true;}
  async function task(action,success){if(state.busy)return;state.busy=true;area.setAttribute('aria-busy','true');message(text('Import en cours…','Importing…'));render();try{await action();await refresh();message(success||text('Ajout terminé. Choisissez un visuel pour votre touche.','Import complete. Choose artwork for your key.'));}catch(error){message(error.message);}finally{state.busy=false;area.removeAttribute('aria-busy');render();}}
  async function importFiles(input){const selected=[...input.files];input.value='';if(!selected.length)return;let done=0;await task(async()=>{for(const file of selected){if(file.size>32*1024*1024)throw new Error(text('Fichier trop volumineux (32 Mo maximum).','File too large (32 MB maximum).'));await request('/api/media/import?filename='+encodeURIComponent(file.name),{method:'POST',body:file});done++;}},text('Visuels ajoutés à la bibliothèque.','Artwork added to the library.'));if(done){state.tab='media';render();}}
  files.onchange=()=>importFiles(files);packFile.onchange=()=>importFiles(packFile);
  function apply(identifier){const current=targetButton();if(!current){message(text('La touche sélectionnée n’existe plus.','The selected key no longer exists.'));return;}current[mode.value]=identifier;studioLastGroup=null;renderGrid();studioCheckpoint();if(getCurrentPage().id===state.target.page){const index=getCurrentPage().buttons.findIndex(button=>button.id===current.id);if(index>=0)selectButton(index);}closeIconLibrary();}
  function render(){
    mode.setAttribute('aria-label',text('État de la touche','Key state'));
    mode.options[0].textContent=text('Visuel normal','Normal artwork');
    mode.options[1].textContent=text('Visuel actif / sourdine','Active / muted artwork');
    clear.textContent=text('Retirer le visuel de la touche','Remove key artwork');
    tabs.replaceChildren();
    for(const [id,label] of [['emoji',text('Émojis','Emoji')],['media',text('Mes visuels','My artwork')],['packs',text('Packs à installer','Available packs')]]){
      const tab=button(label,()=>{state.tab=id;render();});tab.setAttribute('role','tab');tab.setAttribute('aria-selected',String(state.tab===id));tabs.append(tab);
    }
    const emoji=state.tab==='emoji';categories.hidden=!emoji;emojiScroll.hidden=!emoji;area.hidden=emoji;mode.disabled=!targetButton();clear.disabled=!targetButton()?.[mode.value];
    if(emoji)return;
    area.replaceChildren();
    const toolbar=document.createElement('div');toolbar.className='media-toolbar';
    toolbar.append(button(text('Importer des images / GIF','Import images / GIFs'),()=>files.click()),button(text('Importer un pack ZIP','Import ZIP pack'),()=>packFile.click()));area.append(toolbar);
    const query=studioIconSearchText(search.value);
    if(state.tab==='packs'){
      const hint=document.createElement('p');hint.className='media-hint';hint.textContent=text('Installez une banque ci-dessous, ou importez un ZIP téléchargé ailleurs. Les GIF peuvent être importés seuls ou en pack.','Install a collection below, or import a ZIP downloaded elsewhere. Import GIFs individually or in packs.');area.append(hint);
      for(const pack of state.catalog.filter(pack=>studioIconSearchText(pack.name+' '+pack.description).includes(query))){
        const card=document.createElement('article');card.className='media-pack';
        const heading=document.createElement('h4');heading.textContent=pack.name;
        const description=document.createElement('p');description.textContent=pack.description;
        const credit=document.createElement('small');credit.textContent=`${pack.count} ${text('visuels','items')} · ${pack.source} · ${pack.license}`;
        const installed=state.packs.some(item=>item.id===pack.id);
        card.append(heading,description,credit,button(installed?text('Réinstaller','Reinstall'):text('Installer le pack','Install pack'),()=>task(()=>request('/api/media/catalog/'+encodeURIComponent(pack.id),{method:'POST'}))));area.append(card);
      }
    }else{
      const filter=document.createElement('select');filter.setAttribute('aria-label',text('Filtrer par pack','Filter by pack'));filter.append(new Option(text('Tous les packs','All packs'),''));
      state.packs.forEach(pack=>filter.append(new Option(pack.name,pack.id)));filter.value=state.pack||'';
      const animated=document.createElement('label');animated.className='media-animated';const check=document.createElement('input');check.type='checkbox';check.checked=!!state.animated;animated.append(check,document.createTextNode(text('GIF / animations','GIF / animation')));
      filter.onchange=()=>{state.pack=filter.value;render();};check.onchange=()=>{state.animated=check.checked;render();};toolbar.append(filter,animated);
      const pack=state.packs.find(item=>item.id===state.pack);
      if(pack){const exportButton=document.createElement('a');exportButton.className='btn btn-secondary';exportButton.textContent=text('Exporter ce pack','Export this pack');exportButton.href='/api/media/packs/'+encodeURIComponent(pack.id)+'/export';exportButton.download='deckedge-pack.zip';toolbar.append(exportButton);}
      const grid=document.createElement('div');grid.className='media-grid';
      const items=state.items.filter(item=>(!pack||pack.items.includes(item.id))&&(!state.animated||item.animated)&&studioIconSearchText(item.name).includes(query));
      for(const item of items){const tile=document.createElement('div');tile.className='media-tile';const choose=button(item.name,()=>apply(item.id));choose.className='media-choice';choose.title=item.name;
        const image=document.createElement('img');image.src='/media/'+item.id;image.alt='';image.loading='lazy';image.draggable=false;choose.prepend(image);
        const remove=button(text('Retirer de la bibliothèque','Remove from library'),()=>task(()=>request('/api/media/'+item.id,{method:'DELETE'}),text('Visuel retiré. Les touches qui l’utilisent sont conservées.','Artwork removed. Existing keys keep their artwork.')));remove.className='media-remove';remove.setAttribute('aria-label',text('Retirer ','Remove ')+item.name);remove.textContent='×';tile.append(choose,remove);grid.append(tile);}
      area.append(grid);
      if(!items.length){const empty=document.createElement('p');empty.className='media-hint';empty.textContent=state.loaded?text('Aucun visuel ici. Importez vos fichiers ou choisissez un pack.','No artwork here. Import files or choose a pack.'):text('Chargement de la bibliothèque…','Loading library…');area.append(empty);}
    }
    area.querySelectorAll('button,input,select').forEach(node=>node.disabled=state.busy);
  }
  const originalOpen=openIconLibrary;
  openIconLibrary=function(){const current=getCurrentPage()?.buttons?.[selectedIndex];state.target=current?{page:getCurrentPage().id,button:current.id}:null;mode.value='image';originalOpen();message('');render();refresh().then(()=>render()).catch(error=>message(error.message));};
  const originalRender=renderIconLibrary;
  renderIconLibrary=function(){originalRender();render();};
  const originalSet=setIconFromLibrary;
  setIconFromLibrary=function(icon){if(mode.value==='active_image'){const current=targetButton();if(!current)return;current.active_image='';current.active_icon=icon;renderGrid();studioCheckpoint();selectButton(selectedIndex);studioRememberIcon(icon);closeIconLibrary();}else originalSet(icon);};
  mode.onchange=()=>render();
}
