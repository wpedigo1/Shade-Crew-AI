import assert from 'node:assert/strict';
import { test } from 'vitest';
import {
  clearGuardrailOverride,
  GUARDRAIL_STORAGE_KEY,
  loadGuardrailOverride,
  MAX_OUTPUT_CHARS_BOUND,
  MIN_OUTPUT_CHARS_BOUND,
  saveGuardrailOverride,
  validateGuardrailOverride,
} from './guardrailSettings.js';

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

test('guardrail bound constants match the backend contract', () => {
  assert.equal(MIN_OUTPUT_CHARS_BOUND, 100);
  assert.equal(MAX_OUTPUT_CHARS_BOUND, 200_000);
});

test('validateGuardrailOverride accepts a valid pair', () => {
  assert.deepEqual(validateGuardrailOverride({
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  }), { valid: true });
  assert.deepEqual(validateGuardrailOverride({
    warning_threshold_chars: MIN_OUTPUT_CHARS_BOUND,
    hard_cap_chars: MAX_OUTPUT_CHARS_BOUND,
  }), { valid: true });
});

test('validateGuardrailOverride rejects non-integers', () => {
  for (const bad of [12.5, '5000', NaN, null, undefined, {}, []]) {
    const result = validateGuardrailOverride({
      warning_threshold_chars: bad,
      hard_cap_chars: 10000,
    });
    assert.equal(result.valid, false, `warning=${String(bad)}`);
    assert.match(result.error, /warning_threshold_chars/);
  }
  const capResult = validateGuardrailOverride({
    warning_threshold_chars: 5000,
    hard_cap_chars: 7500.5,
  });
  assert.equal(capResult.valid, false);
  assert.match(capResult.error, /hard_cap_chars/);
});

test('validateGuardrailOverride rejects out-of-bounds values', () => {
  for (const bad of [MIN_OUTPUT_CHARS_BOUND - 1, MAX_OUTPUT_CHARS_BOUND + 1]) {
    const warningResult = validateGuardrailOverride({
      warning_threshold_chars: bad,
      hard_cap_chars: 10000,
    });
    assert.equal(warningResult.valid, false, `warning=${bad}`);
    const capResult = validateGuardrailOverride({
      warning_threshold_chars: 5000,
      hard_cap_chars: bad,
    });
    assert.equal(capResult.valid, false, `cap=${bad}`);
  }
});

test('validateGuardrailOverride rejects cap below warning', () => {
  const result = validateGuardrailOverride({
    warning_threshold_chars: 20000,
    hard_cap_chars: 19999,
  });
  assert.equal(result.valid, false);
  assert.match(result.error, /Hard cap/);
});

test('validateGuardrailOverride accepts warning equal to cap', () => {
  assert.deepEqual(validateGuardrailOverride({
    warning_threshold_chars: 40000,
    hard_cap_chars: 40000,
  }), { valid: true });
});

test('loadGuardrailOverride returns null when nothing is saved', () => {
  assert.equal(loadGuardrailOverride(memoryStorage()), null);
  assert.equal(loadGuardrailOverride(undefined), null);
  assert.equal(loadGuardrailOverride({}), null);
});

test('loadGuardrailOverride parses a valid saved pair and rejects corrupt shapes without throwing', () => {
  const storage = memoryStorage();
  storage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify({
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  }));
  assert.deepEqual(loadGuardrailOverride(storage), {
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  });

  storage.setItem(GUARDRAIL_STORAGE_KEY, 'not-json{{');
  assert.equal(loadGuardrailOverride(storage), null);

  storage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify({ warning_threshold_chars: 5000 }));
  assert.equal(loadGuardrailOverride(storage), null);

  storage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify([5000, 10000]));
  assert.equal(loadGuardrailOverride(storage), null);

  storage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify({
    warning_threshold_chars: 150000,
    hard_cap_chars: 10000,
  }));
  assert.equal(loadGuardrailOverride(storage), null);
});

test('saveGuardrailOverride writes a validated pair and clearGuardrailOverride removes it', () => {
  const storage = memoryStorage();
  assert.equal(saveGuardrailOverride({ warning_threshold_chars: 5000, hard_cap_chars: 10000 }, storage), true);
  assert.deepEqual(loadGuardrailOverride(storage), {
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  });
  assert.equal(clearGuardrailOverride(storage), true);
  assert.equal(loadGuardrailOverride(storage), null);
});

test('saveGuardrailOverride refuses an invalid pair without writing', () => {
  const storage = memoryStorage();
  assert.equal(saveGuardrailOverride({ warning_threshold_chars: 500, hard_cap_chars: 100 }, storage), false);
  assert.equal(loadGuardrailOverride(storage), null);
});

test('helpers tolerate broken or throwing storage without throwing', () => {
  assert.equal(saveGuardrailOverride({ warning_threshold_chars: 5000, hard_cap_chars: 10000 }, {}), false);
  assert.equal(clearGuardrailOverride({}), false);
  assert.equal(loadGuardrailOverride({}), null);

  const throwing = {
    getItem() { throw new Error('nope'); },
    setItem() { throw new Error('nope'); },
    removeItem() { throw new Error('nope'); },
  };
  assert.equal(loadGuardrailOverride(throwing), null);
  assert.equal(saveGuardrailOverride({ warning_threshold_chars: 5000, hard_cap_chars: 10000 }, throwing), false);
  assert.equal(clearGuardrailOverride(throwing), false);
});