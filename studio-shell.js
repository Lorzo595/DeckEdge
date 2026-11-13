/* L'organisation du Studio ne modifie jamais les profils au chargement. */
function setupStudioShell() {
  const layout = document.querySelector('.main-layout');
  const deck = document.querySelector('.deck-section');
  document.querySelector('.workspace-heading h2').textContent = 'Votre Deck';
  document.querySelector('.workspace-heading p').textContent = 'Sélectionnez une touche pour la personnaliser.';
  const rail = document.createElement('nav'); rail.className = 'profile-sidebar'; rail.setAttribute('aria-label','Profils du Deck');
  rail.innerHTML = '<div class="rail-title">Mes profils</div>';
  rail.append(document.getElementById('pages-bar')); layout.prepend(rail);
  const panel = document.getElementById('editor-panel'); deck.append(panel);
  const actionSidebar = document.createElement('aside'); actionSidebar.className = 'action-sidebar';
  actionSidebar.setAttribute('aria-label', 'Bibliothèque d’actions');
  actionSidebar.innerHTML = '<h2>Actions</h2><p>Ajoutez une action à votre Deck en un clic ou en la glissant sur l’aperçu.</p><input class="action-search" type="search" aria-label="Rechercher une action" placeholder="Rechercher une action…"><div class="action-list"></div><div class="library-tip"><strong>Un Deck à votre image</strong>Glissez les touches pour les réorganiser. Le clic droit permet de dupliquer, déplacer ou supprimer.</div>';
  layout.append(actionSidebar);
  const templates = [
    {group:'Audio',icon:'♫',name:'Volume',description:'Régler le son d’une application',type:'slider',target:'master',label:'Volume'},
    {group:'Audio',icon:'▷',name:'Lecture / Pause',description:'Contrôler la musique',type:'key',target:'playpause',label:'Lecture / Pause'},
    {group:'Audio',icon:'»',name:'Piste suivante',description:'Passer au morceau suivant',type:'key',target:'nexttrack',label:'Suivant'},
    {group:'Audio',icon:'♩',name:'Couper le son',description:'Activer ou couper le son du PC',type:'key',target:'volumemute',label:'Son',toggle:true},
    {group:'Applications',icon:'↗',name:'Ouvrir une application',description:'Application, jeu ou fichier',type:'launch',target:'',label:'Mon application',picker:true},
    {group:'Applications',icon:'◎',name:'Ouvrir un site',description:'Accéder à une adresse web',type:'launch',target:'https://',label:'Mon site'},
    {group:'Clavier',icon:'⌘',name:'Raccourci clavier',description:'Combiner plusieurs touches',type:'hotkey',target:'',label:'Mon raccourci'},
    {group:'Clavier',icon:'▣',name:'Afficher le bureau',description:'Retrouver le bureau Windows',type:'hotkey',target:'win,d',label:'Bureau'}
  ];
  const list = actionSidebar.querySelector('.action-list');
  function renderActions(filter='') {
    list.replaceChildren(); let count=0;
    for (const group of [...new Set(templates.map(t=>t.group))]) {
      const entries = templates.map((t,index)=>({t,index})).filter(({t})=>t.group===group && `${t.name} ${t.description} ${t.group}`.toLocaleLowerCase('fr').includes(filter.toLocaleLowerCase('fr')));
      if(!entries.length) continue;
      const section=document.createElement('section'); section.className='action-group';
      const title=document.createElement('h3');title.className='action-category';title.textContent=group;section.append(title);
      entries.forEach(({t,index})=>{
        const button=document.createElement('button');button.type='button';button.className='action-card';button.draggable=true;
        button.innerHTML=`<span class="action-symbol">${t.icon}</span><span><strong>${t.name}</strong><small>${t.description}</small></span><span class="add-mark">＋</span>`;
        button.setAttribute('aria-label',`Ajouter : ${t.name}`); button.onclick=()=>addTemplate(index);
        button.ondragstart=e=>{e.dataTransfer.setData('application/deckedge-action',String(index));e.dataTransfer.effectAllowed='copy';};
        section.append(button);count++;
      });list.append(section);
    }
    if(!count){const empty=document.createElement('p');empty.className='library-empty';empty.textContent='Aucune action trouvée. Essayez « volume » ou « clavier ».';list.append(empty);}
  }
  function addTemplate(index) {
    const template=templates[index]; if(!template || !studioReady)return;
    const page=getCurrentPage();
    page.buttons.push({id:studioId('b'),label:template.label,icon:template.icon,type:template.type,target:template.target,color:template.type==='slider'?'#6188e8':'#30394f',is_toggle:!!template.toggle,state:false});
    renderGrid();selectButton(page.buttons.length-1);studioCheckpoint();
    document.getElementById('editor-panel').scrollIntoView({behavior:'smooth',block:'nearest'});
    studioNotify(`${template.name} ajouté`);
    if(template.picker)openAppPickerModal();else studioFocusLabel();
  }
  actionSidebar.querySelector('input').oninput=e=>renderActions(e.target.value); renderActions();
  const stage=document.getElementById('preview-stage');
  stage.addEventListener('dragover',e=>{if(e.dataTransfer.types.includes('application/deckedge-action')){e.preventDefault();e.dataTransfer.dropEffect='copy';}});
  stage.addEventListener('drop',e=>{const value=e.dataTransfer.getData('application/deckedge-action');if(value!==''){e.preventDefault();e.stopPropagation();addTemplate(Number(value));}},true);
  function disclosure(label,nodes){const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent=label;details.append(summary);nodes.filter(Boolean).forEach(node=>details.append(node));panel.append(details);return details;}
  const labelGroup=document.getElementById('inp-label').closest('.field-group');panel.insertBefore(labelGroup,panel.children[1]);
  const size=panel.querySelector('.widget-size-fields');
  const toggle=document.getElementById('box-toggle');
  disclosure('Taille et comportement',[size,toggle]);
  const typeGroup=document.getElementById('inp-type').closest('.field-group');
  disclosure('Options avancées',[typeGroup]);
  const metadata=document.querySelector('.page-header-row');const monitoring=document.getElementById('monitoring-settings');
  deck.append(metadata,monitoring);
  document.querySelector('#grp-target label').textContent='Action';
  document.querySelector('#grp-target button span').textContent='Choisir une application ou un outil…';
  const raw=document.getElementById('inp-target'); raw.setAttribute('aria-label','Commande, raccourci ou adresse');
  const help=document.createElement('p');help.className='action-field-help';raw.after(help);
  const record=document.createElement('button');record.type='button';record.className='btn btn-secondary';record.textContent='Enregistrer un raccourci';raw.before(record);
  let recording=false;
  record.onclick=()=>{recording=!recording;record.textContent=recording?'Appuyez sur votre combinaison · Échap pour annuler':'Enregistrer un raccourci';if(recording)record.focus();};
  record.addEventListener('keydown',event=>{
    if(!recording)return;event.preventDefault();event.stopPropagation();
    if(event.key==='Escape'){recording=false;record.textContent='Enregistrer un raccourci';return;}
    if(['Control','Shift','Alt','Meta'].includes(event.key))return;
    const keys=[];if(event.ctrlKey)keys.push('ctrl');if(event.altKey)keys.push('alt');if(event.shiftKey)keys.push('shift');if(event.metaKey)keys.push('win');
    const names={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',' ':'space',Delete:'delete',Backspace:'backspace',Enter:'enter',Tab:'tab'};
    keys.push(names[event.key]||event.key.toLowerCase());raw.value=keys.join(',');liveUpdate('target',raw.value);
    recording=false;record.textContent='Enregistrer un raccourci';
  });
  function simplifyFields(){
    const btn=getCurrentPage()?.buttons?.[selectedIndex];if(!btn)return;
    const type=btn.type||'hotkey',slider=type==='slider';
    document.getElementById('grp-target').hidden=slider;
    const picker=document.querySelector('#grp-target>button');picker.hidden=!['launch','volume_app'].includes(type);
    picker.style.display=picker.hidden?'none':'flex';record.hidden=type!=='hotkey';
    help.textContent=type==='hotkey'?'Cliquez sur « Enregistrer un raccourci », puis pressez les touches ensemble.':type==='launch'?'Choisissez une application ou saisissez l’adresse complète d’un site.':type==='key'?'Choisissez une commande rapide ci-dessous.':'Choisissez une application et le pas de volume.';
    raw.placeholder=type==='launch'?'https://exemple.fr':type==='hotkey'?'Votre raccourci apparaîtra ici':'Commande';
    recording=false;record.textContent='Enregistrer un raccourci';
  }
  const nativeSelect=selectButton;
  selectButton=function(index){const result=nativeSelect(index);const btn=getCurrentPage()?.buttons?.[selectedIndex];if(btn)document.getElementById('editor-title').textContent=`${btn.label || 'Sans nom'} · Personnaliser`;simplifyFields();return result;};
  const nativeTypeChange=onTypeChange;
  onTypeChange=function(...args){const result=nativeTypeChange(...args);simplifyFields();return result;};
}
