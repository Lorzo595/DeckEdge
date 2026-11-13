/* Sélecteur natif dans l'application, EyeDropper dans les navigateurs compatibles. */
let studioColorRequest = null;

function syncStudioColorFields() {
  const widget = getCurrentPage()?.buttons?.[selectedIndex]; if (!widget) return;
  for (const [field,id,fallback] of [['color','color','#161c2e'],['active_color','active-color','#991b1b']]) {
    const text = document.getElementById('hex-'+id);
    if (text && document.activeElement !== text) text.value = widget[field] || fallback;
  }
}

function applyStudioPickedColor(color) {
  const request = studioColorRequest;
  if (!request || !/^#[0-9a-f]{6}$/i.test(color)) return;
  const page = config.pages.find(p => p.id === request.page);
  const widget = page?.buttons.find(w => w.id === request.widget);
  if (!widget) return;
  studioInputGroup = null; studioLastGroup = null;
  widget[request.field] = color.toLowerCase(); renderGrid();
  if (currentActivePageId === page.id && page.buttons[selectedIndex]?.id === widget.id) {
    document.getElementById(request.field === 'color' ? 'inp-color' : 'inp-active-color').value = color;
    syncStudioColorFields();
  }
  studioScheduleCheckpoint(); studioNotify('Couleur appliquée.');
}

async function chooseStudioColor(field, mode = 'screen') {
  if (studioColorRequest || !['color','active_color'].includes(field)) return;
  const widget = getCurrentPage()?.buttons?.[selectedIndex]; if (!widget) return;
  studioColorRequest = {id:studioId('color'),widget:widget.id,page:currentActivePageId,field};
  if (window.chrome?.webview) {
    window.chrome.webview.postMessage({type:'pickColor',requestId:studioColorRequest.id,field,mode,color:widget[field] || (field === 'active_color' ? '#991b1b' : '#161c2e')});
    return;
  }
  try {
    if (!window.EyeDropper) { studioNotify('La pipette est disponible dans l’application Windows. Vous pouvez aussi saisir un code couleur.'); return; }
    const result = await new EyeDropper().open();
    applyStudioPickedColor(result.sRGBHex);
  } catch (error) {
    if (error.name !== 'AbortError') studioNotify('Impossible d’ouvrir la pipette. Essayez dans l’application Windows.');
  } finally { studioColorRequest = null; }
}

function setStudioHexColor(field, value, input) {
  let color = value.trim();
  if (/^#?[0-9a-f]{3}$/i.test(color)) color = '#'+color.replace('#','').split('').map(c=>c+c).join('');
  else if (/^#?[0-9a-f]{6}$/i.test(color)) color = '#'+color.replace('#','');
  else {
    studioNotify('Utilisez un code couleur comme #38BDF8.');
    input.value = getCurrentPage()?.buttons?.[selectedIndex]?.[field] || (field === 'color' ? '#161c2e' : '#991b1b');
    return;
  }
  liveUpdate(field,color.toLowerCase());
  document.getElementById(field === 'color' ? 'inp-color' : 'inp-active-color').value = color;
  input.value = color.toLowerCase();
}

function setupStudioColorPicker() {
  for (const [field,id] of [['color','color'],['active_color','active-color']]) {
    document.getElementById('inp-'+id).addEventListener('click',event => {
      if (window.chrome?.webview) { event.preventDefault(); chooseStudioColor(field,'palette'); }
    });
  }
  window.chrome?.webview?.addEventListener?.('message',event => {
    const data = event.data;
    if (data?.type !== 'colorPicked' || data.requestId !== studioColorRequest?.id) return;
    if (data.color) applyStudioPickedColor(data.color);
    if (data.error) studioNotify(data.error);
    studioColorRequest = null;
  });
}
