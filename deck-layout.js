/* Disposition commune au pupitre et à son aperçu dans le Studio. */
window.DeckLayout = Object.freeze({
  activeDisplay(widget) {
    const source = widget || {};
    let icon;
    if (source.active_icon) icon = source.active_icon;
    else if (['🎙️','🔊','🎧'].includes(source.icon)) icon = '🔇';
    else if (source.icon === '⏯️') icon = '⏸️';
    else if (source.icon === '🔴') icon = '⏹️';
    else icon = '⚡';

    let label;
    const target = String(source.target || '').toLowerCase();
    if (source.active_label) label = source.active_label;
    else if (target.includes('deaf')) label = 'SOURDINE';
    else if (target.includes('mute')) label = 'MUTÉ';
    else {
      const text = String(source.label || '').toLowerCase();
      if (text.includes('sourdine') || text.includes('deaf')) label = 'SOURDINE';
      else if (text.includes('micro') || text.includes('mute')) label = 'MUTÉ';
      else if (text.includes('discord')) label = 'DISCORD MUTÉ';
      else if (text.includes('rec') || text.includes('obs')) label = 'REC EN COURS';
      else if (text.includes('pause') || text.includes('play')) label = 'EN PAUSE';
      else label = source.label || '';
    }
    return {icon, label};
  },
  apply(element, widget) {
    const widths = {quarter:3, third:4, half:6, full:12};
    const width = Object.prototype.hasOwnProperty.call(widths, widget.width) ? widget.width : 'auto';
    const height = ['compact','normal','tall'].includes(widget.height) ? widget.height : 'normal';
    element.classList.add('deck-layout-tile');
    element.dataset.widgetWidth = width; element.dataset.widgetHeight = height;
    element.style.setProperty('--tile-portrait', widths[width] || (widget.type === 'slider' ? 12 : 6));
    element.style.setProperty('--tile-landscape', widths[width] || 4);
    element.style.setProperty('--tile-rows', {compact:2, normal:3, tall:6}[height]);
  },
  orient(grid, orientation) {
    if (grid) grid.dataset.orientation = orientation || (matchMedia('(orientation: landscape)').matches ? 'landscape' : 'portrait');
  }
});
