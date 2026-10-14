import assert from 'node:assert/strict';
import { test } from 'vitest';

import {
  DEFAULT_PANEL_VIEW,
  getPanelViewClasses,
  PANEL_SEATS,
  panelLayoutNeedsReset,
} from './panelView.js';
import { applyModelMixEvent, createModelMixState } from './modelmixState.js';

test('panel class computation stays CSS-driven and mounted-safe', () => {
  assert.deepEqual(getPanelViewClasses('moderator', '', []), []);
  assert.deepEqual(getPanelViewClasses('moderator', 'moderator', []), ['modelmix-panel-maximized']);
  assert.deepEqual(getPanelViewClasses('worker_a', 'moderator', []), ['modelmix-panel-hidden']);
  assert.deepEqual(getPanelViewClasses('worker_b', 'worker_b', []), ['modelmix-panel-maximized']);
  assert.deepEqual(getPanelViewClasses('moderator', '', ['worker_a', 'moderator']), ['modelmix-panel-collapsed']);
  assert.deepEqual(
    getPanelViewClasses('moderator', 'moderator', ['moderator']),
    ['modelmix-panel-collapsed', 'modelmix-panel-maximized'],
  );
  assert.deepEqual(
    getPanelViewClasses('worker_a', 'moderator', ['worker_a']),
    ['modelmix-panel-collapsed', 'modelmix-panel-hidden'],
  );
});

test('reset is offered whenever any panel is collapsed or maximized', () => {
  assert.equal(panelLayoutNeedsReset('', []), false);
  assert.equal(panelLayoutNeedsReset('worker_a', []), true);
  assert.equal(panelLayoutNeedsReset('', ['moderator']), true);
  assert.equal(panelLayoutNeedsReset('worker_a', ['worker_b']), true);
});

test('default panel view is an empty layout that needs no reset', () => {
  assert.deepEqual(DEFAULT_PANEL_VIEW, { maximized: '', collapsed: [] });
  assert.equal(panelLayoutNeedsReset(DEFAULT_PANEL_VIEW.maximized, DEFAULT_PANEL_VIEW.collapsed), false);
  assert.deepEqual(PANEL_SEATS, ['worker_a', 'moderator', 'worker_b']);
});

test('panel view state never leaks into observable server-backed state', () => {
  const viewKeys = ['maximized', 'collapsed', 'hidden', 'detailsOpen', 'panelLayout'];
  const state = createModelMixState();
  for (const stateKey of viewKeys) {
    assert.equal(Object.hasOwn(state, stateKey), false, stateKey);
    assert.equal(Object.hasOwn(state.worker_a, stateKey), false, stateKey);
    assert.equal(Object.hasOwn(state.moderator, stateKey), false, stateKey);
    assert.equal(Object.hasOwn(state.worker_b, stateKey), false, stateKey);
  }
  const applied = applyModelMixEvent(state, {
    run_id: 'run-1', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'x',
  });
  for (const stateKey of viewKeys) {
    assert.equal(Object.hasOwn(applied, stateKey), false, stateKey);
    assert.equal(Object.hasOwn(applied.worker_a, stateKey), false, stateKey);
  }
});