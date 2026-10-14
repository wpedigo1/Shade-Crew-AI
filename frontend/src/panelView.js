export const PANEL_SEATS = ['worker_a', 'moderator', 'worker_b'];

export const DEFAULT_PANEL_VIEW = Object.freeze({ maximized: '', collapsed: [] });

export function getPanelViewClasses(seatKey, maximized, collapsed = []) {
  const classes = [];
  if (collapsed.includes(seatKey)) classes.push('modelmix-panel-collapsed');
  if (maximized) classes.push(maximized === seatKey ? 'modelmix-panel-maximized' : 'modelmix-panel-hidden');
  return classes;
}

export function panelLayoutNeedsReset(maximized, collapsed = []) {
  return Boolean(maximized) || collapsed.length > 0;
}