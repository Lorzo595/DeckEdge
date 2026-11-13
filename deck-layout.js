/* Disposition commune au pupitre et à son aperçu dans le Studio. */
window.DeckLayout = Object.freeze({
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
