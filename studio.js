/* Ergonomie du Studio : actions locales, historique et liaison à l'application. */
let studioReady = false;
let studioRestoring = false;
let studioHistory = [];
let studioHistoryIndex = -1;
let studioSavedJSON = '';
let studioCheckpointPending = false;
let studioInputGroup = null;
let studioLastGroup = null;
let studioLastEditAt = 0;
let studioLastDirty = null;
let studioToastTimer;
let studioMenuReturnFocus;
let studioSaving = false;
let studioMenuIgnoreScrollUntil = 0;
let previewOrientation = 'portrait';
let previewResizePending = false;

function renderPhoneChrome() {
  const screen = document.getElementById('phone-screen'); if (!screen) return;
  DeckLayout.orient(document.getElementById('grid-preview'), previewOrientation);
  const bar = document.getElementById('preview-monitoring'); bar.replaceChildren();
  const widgets = config.monitoring || [];
  bar.style.gridTemplateColumns = `repeat(${Math.max(1,Math.min(widgets.length,previewOrientation === 'portrait' ? 3 : 6))},minmax(0,1fr))`;
  widgets.forEach(widget => {
    const gauge = document.createElement('div'); gauge.className = 'preview-gauge';
    for (const [className,text] of [['preview-gauge-title',widget.label],['preview-gauge-val','--'],['preview-gauge-sub',widget.secondary_sensor_id ? '--' : '\u00a0']]) {
      const line = document.createElement('div'); line.className = className; line.textContent = text; gauge.append(line);
    }
    bar.append(gauge);
  });
  const tabs = document.getElementById('preview-phone-pages'); tabs.replaceChildren();
  (config.pages || []).forEach(page => {
    const tab = document.createElement('button'); tab.type = 'button'; tab.className = 'phone-tab';
    tab.classList.toggle('active',page.id === currentActivePageId); tab.textContent = `${page.icon || '📄'} ${page.name}`;
    tab.onclick = () => switchPage(page.id); tabs.append(tab);
  });
}

function updatePhonePreview() {
  if (previewResizePending) return; previewResizePending = true;
  requestAnimationFrame(() => {
    previewResizePending = false;
    const stage = document.getElementById('preview-stage'); if (!stage) return;
    const size = document.getElementById('preview-size').value;
    const [short,long] = size.split('x').map(Number);
    const [width,height] = previewOrientation === 'portrait' ? [short,long] : [long,short];
    const zoom = document.getElementById('preview-zoom').value;
    const availableWidth = Math.max(160,stage.clientWidth - 24);
    const top = stage.getBoundingClientRect().top + window.scrollY;
    const availableHeight = Math.max(300, Math.min(446,innerHeight - 280));
    const scale = Math.min(1,availableWidth/(width+20),zoom === 'fit' ? availableHeight/(height+20) : 1);
    const device = document.getElementById('phone-device');
    device.style.width = width+20+'px'; device.style.height = height+20+'px'; device.style.transform = `scale(${scale})`;
    const wrapper = document.getElementById('phone-wrapper');
    wrapper.style.width = (width+20)*scale+'px'; wrapper.style.height = (height+20)*scale+'px';
    stage.style.height = (height+20)*scale+24+'px';
    document.getElementById('phone-screen').dataset.orientation = previewOrientation;
    document.getElementById('preview-rotate').textContent = previewOrientation === 'portrait' ? '↻ Portrait' : '↻ Paysage';
    document.getElementById('preview-dimensions').textContent = `${width} × ${height} · ${Math.round(scale*100)} %`;
    renderPhoneChrome();
    try { localStorage.setItem('deckedge.preview',JSON.stringify({size,zoom,orientation:previewOrientation})); } catch {}
  });
}

function rotatePhonePreview() { previewOrientation = previewOrientation === 'portrait' ? 'landscape' : 'portrait'; updatePhonePreview(); }

function setupPhonePreview() {
  const preview = document.getElementById('mobile-preview');
  const metadata = document.querySelector('.page-header-row');
  const monitoring = document.getElementById('monitoring-settings');
  preview.insertAdjacentElement('afterend',metadata); metadata.insertAdjacentElement('afterend',monitoring);
  try {
    const saved = JSON.parse(localStorage.getItem('deckedge.preview'));
    if (saved) {
      if (['390x844','320x568','430x932'].includes(saved.size)) document.getElementById('preview-size').value = saved.size;
      if (['fit','actual'].includes(saved.zoom)) document.getElementById('preview-zoom').value = saved.zoom;
      if (['portrait','landscape'].includes(saved.orientation)) previewOrientation = saved.orientation;
    }
  } catch {}
  new ResizeObserver(updatePhonePreview).observe(document.getElementById('preview-stage'));
  window.addEventListener('resize',updatePhonePreview);
  updatePhonePreview();
}

function resizeStudioWidget(width,height) {
  const widget = getCurrentPage().buttons[selectedIndex]; if (!widget) return;
  widget.width = width; widget.height = height; renderGrid(); selectButton(selectedIndex);
}

function studioId(prefix) { return `${prefix}_${globalThis.crypto?.randomUUID?.() || Date.now() + '_' + Math.random().toString(36).slice(2)}`; }
function studioClone(value) { return JSON.parse(JSON.stringify(value)); }
function studioEscape(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function studioDirty() { return studioReady && JSON.stringify(config) !== studioSavedJSON; }

function studioResetHistory() {
  studioReady = true;
  studioSavedJSON = JSON.stringify(config);
  studioHistory = [{json: studioSavedJSON, page: currentActivePageId, index: selectedIndex}];
  studioHistoryIndex = 0; studioLastGroup = null; studioUpdateStatus();
}

function studioUpdateStatus() {
  const dirty = studioDirty();
  const status = document.getElementById('save-status');
  status.textContent = dirty ? 'Modifications non enregistrées' : 'À jour';
  status.dataset.dirty = String(dirty);
  document.getElementById('studio-undo').disabled = studioHistoryIndex <= 0;
  document.getElementById('studio-redo').disabled = studioHistoryIndex >= studioHistory.length - 1;
  document.getElementById('studio-save').disabled = studioSaving || !studioReady;
  if (dirty !== studioLastDirty) {
    studioLastDirty = dirty;
    window.chrome?.webview?.postMessage({type:'editorDirty', dirty});
  }
}

function studioCheckpoint() {
  if (!studioReady || studioRestoring) return;
  const json = JSON.stringify(config);
  if (studioHistory[studioHistoryIndex]?.json !== json) {
    const snapshot = {json, page:currentActivePageId, index:selectedIndex};
    const grouped = studioInputGroup && studioInputGroup === studioLastGroup && performance.now() - studioLastEditAt < 800;
    if (grouped && studioHistoryIndex > 0 && studioHistoryIndex === studioHistory.length - 1) studioHistory[studioHistoryIndex] = snapshot;
    else {
      studioHistory.splice(studioHistoryIndex + 1);
      studioHistory.push(snapshot);
      if (studioHistory.length > 50) studioHistory.shift();
      studioHistoryIndex = studioHistory.length - 1;
    }
    studioLastGroup = studioInputGroup; studioLastEditAt = performance.now();
  }
  studioUpdateStatus();
}

function studioScheduleCheckpoint() {
  if (studioCheckpointPending || !studioReady || studioRestoring) return;
  studioCheckpointPending = true;
  queueMicrotask(() => { studioCheckpointPending = false; studioCheckpoint(); });
}

function studioRestoreHistory(offset) {
  studioCheckpoint();
  const next = studioHistoryIndex + offset;
  if (next < 0 || next >= studioHistory.length) return;
  studioRestoring = true;
  try {
    studioHistoryIndex = next;
    const snapshot = studioHistory[next];
    config = JSON.parse(snapshot.json);
    currentActivePageId = config.pages.some(p => p.id === snapshot.page) ? snapshot.page : config.pages[0].id;
    selectedIndex = snapshot.index;
    renderPagesBar(); renderMonitoringEditor(); renderGrid(); selectButton(selectedIndex);
    studioLastGroup = null;
  } finally { studioRestoring = false; studioUpdateStatus(); }
}

function undoStudio() { studioCloseMenu(); studioRestoreHistory(-1); }
function redoStudio() { studioCloseMenu(); studioRestoreHistory(1); }

function studioNotify(text, actionLabel, action) {
  clearTimeout(studioToastTimer);
  const toast = document.getElementById('studio-toast'); toast.replaceChildren();
  const message = document.createElement('span'); message.textContent = text; toast.append(message);
  if (actionLabel) {
    const button = document.createElement('button'); button.type = 'button'; button.textContent = actionLabel;
    button.onclick = () => { action(); toast.hidden = true; }; toast.append(button);
  }
  toast.hidden = false; studioToastTimer = setTimeout(() => { toast.hidden = true; }, 5500);
}

function setEditorAvailability(available) {
  const panel = document.getElementById('editor-panel');
  panel.classList.toggle('editor-empty', !available);
  panel.querySelectorAll('input, select, button').forEach(control => { control.disabled = !available; });
  if (!available) document.getElementById('editor-title').textContent = 'Ajoutez ou sélectionnez une touche';
}

function studioFocusLabel() {
  const input = document.getElementById('inp-label'); input.focus(); input.select();
}

function addStudioButton(type = 'hotkey') {
  const page = getCurrentPage();
  const slider = type === 'slider';
  page.buttons.push({id:studioId('b'), label:slider ? 'Volume' : 'Nouvelle touche', icon:slider ? '🔊' : '⌘',
    type, target:slider ? 'master' : '', color:slider ? '#38bdf8' : '#161c2e', is_toggle:false, state:false});
  renderGrid(); selectButton(page.buttons.length - 1); studioFocusLabel();
}

function duplicateStudioButton() {
  const page = getCurrentPage(), source = page.buttons[selectedIndex];
  if (!source) return;
  const copy = studioClone(source); copy.id = studioId('b'); copy.state = false;
  copy.label = (copy.label || 'Touche').slice(0, 42) + ' (copie)';
  page.buttons.splice(selectedIndex + 1, 0, copy);
  renderGrid(); selectButton(selectedIndex + 1); studioFocusLabel();
  studioNotify('Touche dupliquée.');
}

function moveStudioButton(pageId) {
  const source = getCurrentPage(), destination = config.pages.find(p => p.id === pageId);
  if (!destination || destination === source || !source.buttons[selectedIndex]) return;
  const [button] = source.buttons.splice(selectedIndex, 1); destination.buttons.push(button);
  renderGrid(); selectButton(Math.max(0, selectedIndex - 1));
  studioNotify(`Touche déplacée vers « ${destination.name} ».`, 'Voir', () => switchPage(destination.id));
}

function duplicateStudioPage(pageId) {
  const source = config.pages.find(p => p.id === pageId); if (!source) return;
  const copy = studioClone(source); copy.id = studioId('page'); copy.name = source.name.slice(0,42) + ' (copie)';
  copy.buttons.forEach(button => { button.id = studioId('b'); button.state = false; });
  config.pages.splice(config.pages.indexOf(source) + 1, 0, copy); switchPage(copy.id);
  studioNotify('Profil dupliqué.');
}

function renameStudioPage(pageId) {
  const page = config.pages.find(p => p.id === pageId); if (!page) return;
  const name = prompt('Nom du profil :', page.name);
  if (name?.trim()) { page.name = name.trim().slice(0,50); renderPagesBar(); }
}

function removeStudioPage(pageId) {
  if (config.pages.length <= 1) return;
  const page = config.pages.find(p => p.id === pageId); if (!page) return;
  if (!confirm(`Supprimer le profil « ${page.name} » et ses touches ? Cette action peut être annulée.`)) return;
  config.pages.splice(config.pages.indexOf(page), 1);
  if (!config.pages.some(p => p.id === config.active_page_id))
    config.active_page_id = config.pages.find(p => p.id === 'page_main')?.id || config.pages[0].id;
  if (currentActivePageId === pageId) currentActivePageId = config.pages[0].id;
  switchPage(currentActivePageId); studioNotify('Profil supprimé.', 'Annuler', undoStudio);
}

function studioCloseMenu(restoreFocus = false) {
  document.getElementById('studio-menu').hidden = true;
  if (restoreFocus && studioMenuReturnFocus?.isConnected) studioMenuReturnFocus.focus();
}

function studioMenu(event, title, items) {
  event?.preventDefault();
  const menu = document.getElementById('studio-menu'); menu.replaceChildren();
  const heading = document.createElement('div'); heading.className = 'studio-menu-title'; heading.textContent = title; menu.append(heading);
  items.forEach(item => {
    if (!item) { menu.append(document.createElement('hr')); return; }
    const button = document.createElement('button'); button.type = 'button'; button.setAttribute('role','menuitem');
    button.disabled = !!item.disabled; if (item.danger) button.className = 'danger';
    const label = document.createElement('span'); label.textContent = item.label; button.append(label);
    if (item.key) { const key = document.createElement('kbd'); key.textContent = item.key; button.append(key); }
    button.onclick = () => { studioCloseMenu(); studioInputGroup = null; item.action(); studioScheduleCheckpoint(); };
    menu.append(button);
  });
  menu.hidden = false;
  studioMenuIgnoreScrollUntil = performance.now() + 150;
  const x = event?.clientX || 20, y = event?.clientY || 100;
  menu.style.left = `${Math.max(8, Math.min(x, innerWidth - menu.offsetWidth - 8))}px`;
  menu.style.top = `${Math.max(8, Math.min(y, innerHeight - menu.offsetHeight - 8))}px`;
  menu.querySelector('button:not(:disabled)')?.focus({preventScroll:true});
}

function openAddMenu(event) {
  if (!config?.pages?.length) return;
  const rect = event?.currentTarget?.getBoundingClientRect();
  studioMenu(event?.clientX ? event : {clientX:rect?.left || 20,clientY:rect?.bottom || 100}, 'Ajouter au profil', [
    {label:'Touche / raccourci', key:'Ctrl+N', action:() => addStudioButton('hotkey')},
    {label:'Curseur de volume', action:() => addStudioButton('slider')}
  ]);
}

function openTileMenu(event, index) {
  selectButton(index);
  studioMenuReturnFocus = document.querySelector('.preview-btn.selected');
  const page = getCurrentPage(), button = page.buttons[index];
  studioMenu(event, button.label || 'Touche', [
    {label:'Modifier le nom', key:'F2', action:studioFocusLabel},
    {label:'Dupliquer', key:'Ctrl+D', action:duplicateStudioButton},
    {label:'Redimensionner…', action:() => studioMenu(event,'Taille du widget',[
      {label:'Petit · ¼ de ligne',action:() => resizeStudioWidget('quarter','compact')},
      {label:'⅓ de ligne',action:() => resizeStudioWidget('third','normal')},
      {label:'½ ligne',action:() => resizeStudioWidget('half','normal')},
      {label:'Toute la largeur',action:() => resizeStudioWidget('full','normal')},
      {label:'Grand widget',action:() => resizeStudioWidget('full','tall')},
      {label:'Automatique',action:() => resizeStudioWidget('auto','normal')}
    ])},
    {label:'Déplacer vers un profil…', disabled:config.pages.length < 2, action:() => studioMenu(event, 'Déplacer vers', config.pages.filter(p => p !== page).map(p => ({label:p.name, action:() => moveStudioButton(p.id)})))},
    null,
    {label:'Ajouter une touche après', action:() => { const before = selectedIndex; addStudioButton(); const added = page.buttons.pop(); page.buttons.splice(before + 1,0,added); renderGrid(); selectButton(before + 1); studioFocusLabel(); }},
    {label:'Ajouter un curseur de volume', action:() => addStudioButton('slider')},
    null,
    {label:'Supprimer', key:'Suppr', danger:true, action:deleteCurrentButton}
  ]);
}

function setupStudioErgonomics() {
  setupPhonePreview();
  setupStudioColorPicker();
  for (const name of ['renderGrid','renderPagesBar','renderMonitoringEditor']) {
    const original = window[name];
    window[name] = function(...args) {
      const result = original.apply(this,args);
      if (name === 'renderGrid') {
        document.querySelectorAll('.preview-btn').forEach((tile,index) => {
          tile.tabIndex = index === selectedIndex ? 0 : -1; tile.setAttribute('role','button');
          tile.setAttribute('aria-label', `${getCurrentPage().buttons[index].label || 'Touche'}, modifier`);
          const more = document.createElement('button'); more.type = 'button'; more.className = 'tile-more'; more.textContent = '⋯';
          more.title = 'Actions rapides'; more.setAttribute('aria-label', `Actions de ${getCurrentPage().buttons[index].label || 'la touche'}`);
          more.onclick = event => { event.stopPropagation(); openTileMenu(event,index); }; tile.append(more);
        });
      }
      renderPhoneChrome(); syncStudioColorFields(); studioScheduleCheckpoint(); return result;
    };
  }
  const menu = document.getElementById('studio-menu');
  document.addEventListener('contextmenu', event => {
    if (event.target.closest('input,select,textarea,[contenteditable=true]')) return;
    const tile = event.target.closest('.preview-btn');
    const tab = event.target.closest('.page-tab');
    if (tile) openTileMenu(event, Number(tile.dataset.index));
    else if (tab) {
      const pageId = tab.dataset.pageId; studioMenuReturnFocus = tab;
      studioMenu(event, config.pages.find(p => p.id === pageId)?.name || 'Profil', [
        {label:'Renommer', action:() => renameStudioPage(pageId)},
        {label:'Dupliquer le profil', action:() => duplicateStudioPage(pageId)},
        {label:'Ajouter un profil', action:addNewPage}, null,
        {label:'Supprimer le profil', danger:true, disabled:config.pages.length <= 1, action:() => removeStudioPage(pageId)}
      ]);
    } else if (event.target.closest('#grid-preview')) openAddMenu(event);
  });
  document.addEventListener('pointerdown', event => { studioInputGroup = null; if (!menu.contains(event.target)) studioCloseMenu(); }, true);
  document.addEventListener('input', event => { studioInputGroup = event.target; studioScheduleCheckpoint(); }, true);
  document.addEventListener('change', studioScheduleCheckpoint, true);
  document.addEventListener('click', studioScheduleCheckpoint);
  window.addEventListener('resize', () => studioCloseMenu());
  window.addEventListener('blur', () => studioCloseMenu());
  document.addEventListener('scroll', event => { if (performance.now() > studioMenuIgnoreScrollUntil && !menu.contains(event.target)) studioCloseMenu(); }, true);
  document.addEventListener('keydown', event => {
    const editing = event.target.closest('input,textarea,select,[contenteditable=true]');
    const modal = Array.from(document.querySelectorAll('.modal-overlay')).some(el => getComputedStyle(el).display !== 'none');
    const ctrl = event.ctrlKey || event.metaKey;
    if (!menu.hidden) {
      const buttons = Array.from(menu.querySelectorAll('button:not(:disabled)'));
      if (event.key === 'Escape') { event.preventDefault(); studioCloseMenu(true); return; }
      if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault(); const current = buttons.indexOf(document.activeElement);
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length-1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
        buttons[next]?.focus(); return;
      }
    }
    if (modal) {
      if (event.key === 'Escape') { closeAppPickerModal(); closeDiscordModal(); }
      return;
    }
    if (ctrl && event.key.toLowerCase() === 's') { event.preventDefault(); saveData(); return; }
    if (editing) return;
    const tab = event.target.closest('.page-tab');
    if (tab && (event.key === 'F2' || event.key === 'Delete' || (ctrl && event.key.toLowerCase() === 'd'))) {
      event.preventDefault();
      if (event.key === 'F2') renameStudioPage(tab.dataset.pageId);
      else if (event.key === 'Delete') removeStudioPage(tab.dataset.pageId);
      else duplicateStudioPage(tab.dataset.pageId);
      studioScheduleCheckpoint(); return;
    }
    studioInputGroup = null;
    if (ctrl && event.key.toLowerCase() === 'z') { event.preventDefault(); event.shiftKey ? redoStudio() : undoStudio(); }
    else if (ctrl && event.key.toLowerCase() === 'y') { event.preventDefault(); redoStudio(); }
    else if (ctrl && event.key.toLowerCase() === 'd') { event.preventDefault(); duplicateStudioButton(); }
    else if (ctrl && event.key.toLowerCase() === 'n') { event.preventDefault(); addStudioButton(); }
    else if (event.key === 'Delete' && !event.target.closest('button,summary,a')) { event.preventDefault(); deleteCurrentButton(); }
    else if (event.key === 'F2' && !event.target.closest('button,summary,a')) { event.preventDefault(); studioFocusLabel(); }
    else if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
      const tile = document.querySelector('.preview-btn.selected'); if (!tile) return;
      event.preventDefault(); const rect = tile.getBoundingClientRect(); openTileMenu({clientX:rect.left+12,clientY:rect.top+12},selectedIndex);
    } else if (event.target.closest('.preview-btn') && ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','Enter'].includes(event.key)) {
      event.preventDefault();
      if (event.key === 'Enter') { studioFocusLabel(); return; }
      const columns = getComputedStyle(document.getElementById('grid-preview')).gridTemplateColumns.split(' ').length;
      const count = getCurrentPage().buttons.length;
      const delta = {ArrowLeft:-1,ArrowRight:1,ArrowUp:-columns,ArrowDown:columns}[event.key] || 0;
      const index = event.key === 'Home' ? 0 : event.key === 'End' ? count-1 : Math.max(0,Math.min(count-1,selectedIndex+delta));
      selectButton(index); document.querySelectorAll('.preview-btn')[index]?.focus();
    }
    studioScheduleCheckpoint();
  });
  window.addEventListener('beforeunload', event => { if (studioDirty()) { event.preventDefault(); event.returnValue = ''; } });
  if (window.chrome?.webview) document.getElementById('app-settings-button').hidden = false;
}
