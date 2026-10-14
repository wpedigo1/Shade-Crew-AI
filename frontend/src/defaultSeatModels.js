export const DEFAULT_SAVED_MODELS_KEY = 'modelmix.defaultSeatModels';

export const FALLBACK_SEAT_MODELS = Object.freeze({
  worker_a: 'openai-oauth:gpt-5',
  moderator: '',
  worker_b: 'ollama:llama3',
});

const SEAT_KEYS = ['worker_a', 'moderator', 'worker_b'];

export function loadSavedSeatModels(storage) {
  let raw;
  try {
    raw = storage?.getItem?.(DEFAULT_SAVED_MODELS_KEY);
  } catch {
    return null;
  }
  if (typeof raw !== 'string' || raw === '') return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    if (!SEAT_KEYS.every((key) => typeof parsed[key] === 'string')) return null;
    return { worker_a: parsed.worker_a, moderator: parsed.moderator, worker_b: parsed.worker_b };
  } catch {
    return null;
  }
}

export function saveSeatModels(storage, models) {
  if (!storage?.setItem) return false;
  try {
    storage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
      worker_a: String(models?.worker_a ?? ''),
      moderator: String(models?.moderator ?? ''),
      worker_b: String(models?.worker_b ?? ''),
    }));
    return true;
  } catch {
    return false;
  }
}

export function clearSavedSeatModels(storage) {
  if (!storage?.removeItem) return false;
  try {
    storage.removeItem(DEFAULT_SAVED_MODELS_KEY);
    return true;
  } catch {
    return false;
  }
}