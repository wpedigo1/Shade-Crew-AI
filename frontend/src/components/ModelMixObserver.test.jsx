// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, test, vi } from 'vitest';

vi.mock('../api', () => ({
  api: { getSettings: async () => ({}) },
  buildAvailableSearchProviders: () => [],
  DEFAULT_EXECUTION_MODE: 'full',
}));

vi.mock('../configuredModels', () => ({
  discoverConfiguredModels: async () => [],
}));

vi.mock('../modelmixApi', () => ({
  ModelMixHttpError: class ModelMixHttpError extends Error {},
  cancelModelMixRun: async () => { throw new Error('not used in this render test'); },
  consumeModelMixSSE: async () => { throw new Error('not used in this render test'); },
  hydrateModelMixSession: async () => ({
    schema_version: 1,
    session: {
      session_id: 'session-001',
      runs: [{
        run_id: 'run-001',
        latest_seq: 6,
        status: 'completed',
        prompt: 'Explain two independent answers.',
        models: { worker_a: 'mod:a', moderator: 'mod:m', worker_b: 'mod:b' },
      }],
      messages: [
        { run_id: 'run-001', seat: 'worker_a', content: 'Worker A evidence', status: 'completed' },
        { run_id: 'run-001', seat: 'moderator', content: 'Moderator synthesis', status: 'completed', finish_reason: 'stop' },
        { run_id: 'run-001', seat: 'worker_b', content: 'Worker B evidence', status: 'completed' },
      ],
    },
  }),
  replayModelMixRun: async () => { throw new Error('not used in this render test'); },
  startModelMixRun: async () => { throw new Error('not used in this render test'); },
}));

import ModelMixObserver from './ModelMixObserver.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mounted = [];

afterEach(() => {
  for (const { root, container } of mounted.splice(0)) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  window.localStorage.clear();
});

async function renderObserver() {
  window.localStorage.clear();
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(<ModelMixObserver />);
  });
  await act(async () => {});
  mounted.push({ root, container });
  return { container, root };
}

function click(element) {
  act(() => {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}

function viewClasses(article) {
  return [...article.classList].filter((name) => name.startsWith('modelmix-panel-'));
}

test('top bar is a single compact strip with brand, mode control, session status, New Session, and Back to Council', async () => {
  await renderObserver();
  const h1 = document.querySelector('.modelmix-topbar h1');
  assert.ok(h1);
  assert.equal(h1.textContent, 'ModelMix');
  const mode = document.querySelector('.modelmix-mode');
  assert.ok(mode);
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.ok(modeSelect);
  assert.equal(modeSelect.nodeName, 'SELECT');
  assert.equal(modeSelect.value, 'mix');
  assert.deepEqual(
    [...modeSelect.options].map((option) => option.textContent),
    ['Mix', 'Compare', 'Solo'],
  );
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model') != null, true);
  assert.ok(document.querySelector('.modelmix-topbar .new-session'));
  assert.equal(document.querySelector('.modelmix-session-status').textContent, 'completed');
  const council = document.querySelector('.modelmix-topbar a');
  assert.equal(council.textContent, 'Back to Council');
  assert.equal(council.getAttribute('href'), '/');
  const actionButtons = [...document.querySelector('.modelmix-actions').querySelectorAll('button')];
  assert.deepEqual(actionButtons.map((button) => button.textContent.trim()), ['Send', 'Stop']);
  assert.ok(document.querySelector('.modelmix-actions span[role="status"]'));
  assert.ok(!document.body.textContent.includes('Settings'));
  assert.ok([...document.querySelectorAll('a')].every((anchor) => !(anchor.getAttribute('href') || '').includes('settings')));
});

test('collapse hides only the transcript body via class while the panel stays mounted', async () => {
  await renderObserver();
  const workerA = document.querySelector('article.modelmix-worker');
  assert.equal(document.querySelectorAll('article.modelmix-worker').length, 3);
  click(workerA.querySelector('[aria-label="Collapse Worker A"]'));
  assert.ok(workerA.classList.contains('modelmix-panel-collapsed'));
  assert.equal(workerA.querySelectorAll('.modelmix-transcript').length, 1);
  assert.equal(workerA.querySelectorAll('h2').length, 1);
  assert.deepEqual(viewClasses(document.querySelectorAll('article.modelmix-worker')[1]), []);
  assert.deepEqual(viewClasses(document.querySelectorAll('article.modelmix-worker')[2]), []);
  assert.ok(document.querySelector('.modelmix-reset-layout'));
  click(document.querySelector('.modelmix-reset-layout'));
  assert.deepEqual(viewClasses(workerA), []);
  assert.equal(document.querySelector('.modelmix-reset-layout'), null);
});

test('maximize keeps all three panels mounted and hides the others from layout via class', async () => {
  await renderObserver();
  const [workerA, moderator, workerB] = document.querySelectorAll('article.modelmix-worker');
  click(workerA.querySelector('[aria-label="Maximize Worker A"]'));
  assert.ok(workerA.classList.contains('modelmix-panel-maximized'));
  assert.ok(moderator.classList.contains('modelmix-panel-hidden'));
  assert.ok(workerB.classList.contains('modelmix-panel-hidden'));
  assert.equal(document.querySelectorAll('article.modelmix-worker').length, 3);
  assert.equal(document.querySelectorAll('.modelmix-transcript').length, 3);
  assert.ok(document.querySelector('.modelmix-workers').classList.contains('modelmix-workers--maximized'));
  assert.ok(document.querySelector('.modelmix-reset-layout'));
  click(workerA.querySelector('[aria-label="Restore Worker A"]'));
  assert.deepEqual(viewClasses(workerA), []);
  assert.deepEqual(viewClasses(moderator), []);
  assert.deepEqual(viewClasses(workerB), []);
  assert.ok(!document.querySelector('.modelmix-workers').classList.contains('modelmix-workers--maximized'));
  assert.equal(document.querySelector('.modelmix-reset-layout'), null);
});

test('maximize switches focus and reset restores the three-up grid from any combination', async () => {
  await renderObserver();
  const [workerA, moderator, workerB] = document.querySelectorAll('article.modelmix-worker');
  click(workerB.querySelector('[aria-label="Maximize Worker B"]'));
  click(moderator.querySelector('[aria-label="Collapse Moderator"]'));
  click(workerA.querySelector('[aria-label="Maximize Worker A"]'));
  assert.ok(workerA.classList.contains('modelmix-panel-maximized'));
  assert.ok(workerB.classList.contains('modelmix-panel-hidden'));
  assert.ok(moderator.classList.contains('modelmix-panel-collapsed'));
  click(document.querySelector('.modelmix-reset-layout'));
  assert.deepEqual(viewClasses(workerA), []);
  assert.deepEqual(viewClasses(moderator), []);
  assert.deepEqual(viewClasses(workerB), []);
  assert.equal(document.querySelector('.modelmix-reset-layout'), null);
});

test('New Session stays in the top bar, clears the persisted session id, and resets transcripts', async () => {
  await renderObserver();
  assert.equal(window.localStorage.getItem('modelmix.sessionId'), 'session-001');
  const newSessionButton = document.querySelector('.modelmix-topbar .new-session');
  assert.ok(newSessionButton);
  assert.equal(newSessionButton.disabled, false);
  click(newSessionButton);
  assert.equal(window.localStorage.getItem('modelmix.sessionId'), null);
  assert.ok(!document.querySelector('article.modelmix-worker').textContent.includes('Worker A evidence'));
  assert.ok(document.querySelector('.modelmix-topbar .new-session'));
});

test('run metadata debug line sits behind Details, hidden by default', async () => {
  await renderObserver();
  const runMeta = document.querySelector('.modelmix-run-meta');
  assert.ok(runMeta);
  assert.equal(runMeta.getAttribute('data-open'), 'false');
  assert.equal(runMeta.getAttribute('aria-hidden'), 'true');
  assert.ok(runMeta.textContent.includes('Run: run-001'));
  assert.ok(runMeta.textContent.includes('Last sequence: 6'));
  const toggle = document.querySelector('.modelmix-details-toggle');
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  click(toggle);
  assert.equal(runMeta.getAttribute('data-open'), 'true');
  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  click(toggle);
  assert.equal(runMeta.getAttribute('data-open'), 'false');
});