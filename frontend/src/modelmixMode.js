export const MODE_STORAGE_KEY = 'modelmix.mode';

export const MODES = ['mix', 'compare', 'solo'];

export const DEFAULT_MODE = 'mix';

function defaultStorage() {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  return window.localStorage;
}

export function loadSavedMode(storage = defaultStorage()) {
  let raw;
  try {
    raw = storage?.getItem?.(MODE_STORAGE_KEY);
  } catch {
    return DEFAULT_MODE;
  }
  if (typeof raw !== 'string') return DEFAULT_MODE;
  const value = raw.trim();
  return MODES.includes(value) ? value : DEFAULT_MODE;
}

export function saveMode(mode, storage = defaultStorage()) {
  if (!MODES.includes(mode)) return false;
  if (!storage?.setItem) return false;
  try {
    storage.setItem(MODE_STORAGE_KEY, mode);
    return true;
  } catch {
    return false;
  }
}
