export const GUARDRAIL_STORAGE_KEY = 'modelmix.guardrails';

export const MIN_OUTPUT_CHARS_BOUND = 100;
export const MAX_OUTPUT_CHARS_BOUND = 200_000;

const defaultStorage = () => {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  return window.localStorage;
};

export function validateGuardrailOverride({ warning_threshold_chars, hard_cap_chars } = {}) {
  const fields = {
    warning_threshold_chars,
    hard_cap_chars,
  };
  for (const [key, value] of Object.entries(fields)) {
    if (!Number.isInteger(value)) {
      return { valid: false, error: `${key} must be a whole number of characters` };
    }
    if (value < MIN_OUTPUT_CHARS_BOUND || value > MAX_OUTPUT_CHARS_BOUND) {
      return {
        valid: false,
        error: `${key} must be between ${MIN_OUTPUT_CHARS_BOUND} and ${MAX_OUTPUT_CHARS_BOUND} characters`,
      };
    }
  }
  if (hard_cap_chars < warning_threshold_chars) {
    return { valid: false, error: 'Hard cap must be at least the warning threshold' };
  }
  return { valid: true };
}

export function loadGuardrailOverride(storage = defaultStorage()) {
  let raw;
  try {
    raw = storage?.getItem?.(GUARDRAIL_STORAGE_KEY);
  } catch {
    return null;
  }
  if (typeof raw !== 'string' || raw === '') return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    const values = {
      warning_threshold_chars: parsed.warning_threshold_chars,
      hard_cap_chars: parsed.hard_cap_chars,
    };
    if (!validateGuardrailOverride(values).valid) return null;
    return values;
  } catch {
    return null;
  }
}

export function saveGuardrailOverride(values, storage = defaultStorage()) {
  if (!storage?.setItem) return false;
  if (!validateGuardrailOverride(values ?? {}).valid) return false;
  try {
    storage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify({
      warning_threshold_chars: values.warning_threshold_chars,
      hard_cap_chars: values.hard_cap_chars,
    }));
    return true;
  } catch {
    return false;
  }
}

export function clearGuardrailOverride(storage = defaultStorage()) {
  if (!storage?.removeItem) return false;
  try {
    storage.removeItem(GUARDRAIL_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}