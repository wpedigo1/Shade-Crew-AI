export const BEHAVIOR_STORAGE_KEY = 'modelmix.behavior';
export const SPEND_LIMIT_STORAGE_KEY = 'modelmix.spendLimit';

export const MIN_TEMPERATURE = 0.0;
export const MAX_TEMPERATURE = 2.0;
export const MAX_MODERATOR_GUIDANCE_LENGTH = 2000;

const defaultStorage = () => {
  if (typeof window === 'undefined' || !window.localStorage) return null;
  return window.localStorage;
};

function isValidTemperature(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= MIN_TEMPERATURE && value <= MAX_TEMPERATURE;
}

function isValidModeratorGuidance(value) {
  return typeof value === 'string' && value.length <= MAX_MODERATOR_GUIDANCE_LENGTH;
}

export function validateBehavior({ temperature, moderator_guidance } = {}) {
  const errors = {};
  if (temperature !== undefined && temperature !== null) {
    if (!isValidTemperature(temperature)) {
      errors.temperature = 'Temperature must be between 0.0 and 2.0';
    }
  }
  if (moderator_guidance !== undefined && moderator_guidance !== null) {
    if (!isValidModeratorGuidance(moderator_guidance)) {
      errors.moderator_guidance = `Guidance must be ${MAX_MODERATOR_GUIDANCE_LENGTH} characters or fewer`;
    }
  }
  const valid = Object.keys(errors).length === 0;
  return valid ? { valid: true } : { valid: false, errors };
}

export function loadBehavior(storage = defaultStorage()) {
  let raw;
  try {
    raw = storage?.getItem?.(BEHAVIOR_STORAGE_KEY);
  } catch {
    return null;
  }
  if (typeof raw !== 'string' || raw === '') return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    const values = {};
    if (parsed.temperature !== undefined && parsed.temperature !== null) {
      if (!isValidTemperature(parsed.temperature)) return null;
      values.temperature = parsed.temperature;
    }
    if (parsed.moderator_guidance !== undefined && parsed.moderator_guidance !== null) {
      if (!isValidModeratorGuidance(parsed.moderator_guidance)) return null;
      values.moderator_guidance = parsed.moderator_guidance;
    }
    if (Object.keys(values).length === 0) return null;
    return values;
  } catch {
    return null;
  }
}

export function saveBehavior(values, storage = defaultStorage()) {
  if (!storage?.setItem) return false;
  const trimmed = {};
  if (values && values.temperature !== undefined && values.temperature !== null) {
    if (!isValidTemperature(values.temperature)) return false;
    trimmed.temperature = values.temperature;
  }
  if (values && values.moderator_guidance !== undefined && values.moderator_guidance !== null) {
    if (!isValidModeratorGuidance(values.moderator_guidance)) return false;
    trimmed.moderator_guidance = values.moderator_guidance;
  }
  if (Object.keys(trimmed).length === 0) return false;
  try {
    storage.setItem(BEHAVIOR_STORAGE_KEY, JSON.stringify(trimmed));
    return true;
  } catch {
    return false;
  }
}

export function clearBehavior(storage = defaultStorage()) {
  if (!storage?.removeItem) return false;
  try {
    storage.removeItem(BEHAVIOR_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

function isValidSpendLimit(value) {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

export function loadSpendLimit(storage = defaultStorage()) {
  let raw;
  try {
    raw = storage?.getItem?.(SPEND_LIMIT_STORAGE_KEY);
  } catch {
    return null;
  }
  if (typeof raw !== 'string' || raw === '') return null;
  try {
    const parsed = JSON.parse(raw);
    if (!isValidSpendLimit(parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveSpendLimit(value, storage = defaultStorage()) {
  if (!storage?.setItem) return false;
  if (!isValidSpendLimit(value)) return false;
  try {
    storage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function clearSpendLimit(storage = defaultStorage()) {
  if (!storage?.removeItem) return false;
  try {
    storage.removeItem(SPEND_LIMIT_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}
