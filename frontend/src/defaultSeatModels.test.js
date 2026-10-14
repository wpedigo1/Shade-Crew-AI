import assert from 'node:assert/strict';
import { test } from 'vitest';
import {
  clearSavedSeatModels,
  DEFAULT_SAVED_MODELS_KEY,
  FALLBACK_SEAT_MODELS,
  loadSavedSeatModels,
  saveSeatModels,
} from './defaultSeatModels.js';

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

test('fallback seat models match the built-in default selections', () => {
  assert.equal(FALLBACK_SEAT_MODELS.worker_a, 'openai-oauth:gpt-5');
  assert.equal(FALLBACK_SEAT_MODELS.moderator, '');
  assert.equal(FALLBACK_SEAT_MODELS.worker_b, 'ollama:llama3');
  assert.ok(Object.isFrozen(FALLBACK_SEAT_MODELS));
});

test('loadSavedSeatModels returns null when nothing is saved', () => {
  assert.equal(loadSavedSeatModels(memoryStorage()), null);
  assert.equal(loadSavedSeatModels(undefined), null);
  assert.equal(loadSavedSeatModels({}), null);
});

test('loadSavedSeatModels parses a saved trio and rejects corrupt shapes without throwing', () => {
  const storage = memoryStorage();
  storage.setItem(
    DEFAULT_SAVED_MODELS_KEY,
    JSON.stringify({ worker_a: 'mod:a', moderator: 'mod:m', worker_b: 'mod:b' }),
  );
  assert.deepEqual(loadSavedSeatModels(storage), { worker_a: 'mod:a', moderator: 'mod:m', worker_b: 'mod:b' });

  storage.setItem(DEFAULT_SAVED_MODELS_KEY, 'not-json{{');
  assert.equal(loadSavedSeatModels(storage), null);

  storage.setItem(DEFAULT_SAVED_MODELS_KEY, '{"worker_a":"only-one"}');
  assert.equal(loadSavedSeatModels(storage), null);

  storage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({ worker_a: 'x', moderator: 7, worker_b: 'y' }));
  assert.equal(loadSavedSeatModels(storage), null);

  storage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify(['a', 'b', null]));
  assert.equal(loadSavedSeatModels(storage), null);

  storage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({ worker_a: 'x', moderator: '', worker_b: 'y', extra: 1 }));
  assert.deepEqual(loadSavedSeatModels(storage), { worker_a: 'x', moderator: '', worker_b: 'y' });
});

test('saveSeatModels writes the trio and clearSavedSeatModels removes it', () => {
  const storage = memoryStorage();
  assert.equal(saveSeatModels(storage, { worker_a: 'a', moderator: '', worker_b: 'b' }), true);
  assert.deepEqual(loadSavedSeatModels(storage), { worker_a: 'a', moderator: '', worker_b: 'b' });
  assert.equal(clearSavedSeatModels(storage), true);
  assert.equal(loadSavedSeatModels(storage), null);
});

test('helpers tolerate broken or throwing storage without throwing', () => {
  assert.equal(saveSeatModels({}, {}), false);
  assert.equal(clearSavedSeatModels({}), false);
  assert.equal(loadSavedSeatModels({}), null);

  const throwing = {
    getItem() { throw new Error('nope'); },
    setItem() { throw new Error('nope'); },
    removeItem() { throw new Error('nope'); },
  };
  assert.equal(loadSavedSeatModels(throwing), null);
  assert.equal(saveSeatModels(throwing, { worker_a: 'a', moderator: '', worker_b: 'b' }), false);
  assert.equal(clearSavedSeatModels(throwing), false);
});