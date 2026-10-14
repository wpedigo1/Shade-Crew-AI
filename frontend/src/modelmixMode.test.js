import assert from 'node:assert/strict';
import { test } from 'vitest';
import {
  DEFAULT_MODE,
  loadSavedMode,
  MODE_STORAGE_KEY,
  MODES,
  saveMode,
} from './modelmixMode.js';

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

test('only mix, compare, and solo are valid modes', () => {
  assert.deepEqual(MODES, ['mix', 'compare', 'solo']);
  assert.equal(DEFAULT_MODE, 'mix');
});

test('loadSavedMode defaults to mix when nothing is saved or storage is broken', () => {
  assert.equal(loadSavedMode(memoryStorage()), 'mix');
  assert.equal(loadSavedMode(undefined), 'mix');
  assert.equal(loadSavedMode({}), 'mix');

  const throwing = { getItem() { throw new Error('nope'); } };
  assert.equal(loadSavedMode(throwing), 'mix');
});

test('loadSavedMode rejects an invalid or missing stored value and defaults to mix', () => {
  const storage = memoryStorage();
  storage.setItem(MODE_STORAGE_KEY, 'not-a-mode');
  assert.equal(loadSavedMode(storage), 'mix');
  storage.setItem(MODE_STORAGE_KEY, 'five-worker');
  assert.equal(loadSavedMode(storage), 'mix');
  storage.setItem(MODE_STORAGE_KEY, '  ');
  assert.equal(loadSavedMode(storage), 'mix');
});

test('loadSavedMode is a valid stored mode, trimming whitespace', () => {
  const storage = memoryStorage();
  storage.setItem(MODE_STORAGE_KEY, 'compare');
  assert.equal(loadSavedMode(storage), 'compare');
  storage.setItem(MODE_STORAGE_KEY, '  mix  ');
  assert.equal(loadSavedMode(storage), 'mix');
  storage.setItem(MODE_STORAGE_KEY, ' solo ');
  assert.equal(loadSavedMode(storage), 'solo');
});

test('saveMode writes and round-trips a valid mode, rejects invalid ones', () => {
  const storage = memoryStorage();
  assert.equal(saveMode('compare', storage), true);
  assert.equal(loadSavedMode(storage), 'compare');
  assert.equal(saveMode('solo', storage), true);
  assert.equal(loadSavedMode(storage), 'solo');
  assert.equal(saveMode('five-worker', storage), false);
  assert.equal(saveMode({}, storage), false);
});

test('saveMode tolerates throttled or broken storage without throwing', () => {
  const throwing = { setItem() { throw new Error('nope'); } };
  assert.equal(saveMode('mix', throwing), false);
  assert.equal(saveMode('mix', {}), false);
});
