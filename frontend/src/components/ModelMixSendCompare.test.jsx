// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, test, vi } from 'vitest';
import { DEFAULT_SAVED_MODELS_KEY } from '../defaultSeatModels';
import { MODE_STORAGE_KEY } from '../modelmixMode';

const { captured } = vi.hoisted(() => ({
  captured: { payload: null, events: [], response: null },
}));

vi.mock('../api', () => ({
  api: { getSettings: async () => ({}) },
  buildAvailableSearchProviders: () => [],
  DEFAULT_EXECUTION_MODE: 'full',
}));

vi.mock('../configuredModels', () => ({
  discoverConfiguredModels: async () => [
    { id: 'openai-oauth:gpt-5', name: 'gpt-5 (ChatGPT)', provider: 'OpenAI' },
    { id: 'openai-oauth:alt', name: 'Alt model', provider: 'OpenAI' },
    { id: 'ollama:llama3', name: 'llama3', provider: 'Ollama' },
  ],
}));

vi.mock('../modelmixApi', () => {
  class ModelMixHttpError extends Error {
    constructor(message, status = 0) {
      super(message);
      this.status = status;
    }
  }
  return {
    ModelMixHttpError,
    cancelModelMixRun: async () => {},
    consumeModelMixSSE: async (_response, handleEvent) => {
      for (const event of captured.events) {
        handleEvent(event);
      }
    },
    hydrateModelMixSession: async () => { throw new ModelMixHttpError('no session', 404); },
    replayModelMixRun: async () => { throw new Error('not used in this test'); },
    startModelMixRun: async (payload) => {
      captured.payload = payload;
      return captured.response;
    },
  };
});

import ModelMixObserver from './ModelMixObserver.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mounted = [];

afterEach(() => {
  captured.payload = null;
  captured.events = [];
  captured.response = null;
  for (const { root, container } of mounted.splice(0)) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  window.localStorage.clear();
});

async function renderObserver() {
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

function setMode(select, value) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
  act(() => {
    setter.call(select, value);
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

function setPrompt(textarea, value) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  act(() => {
    setter.call(textarea, value);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

async function sendNow() {
  click(document.querySelector('.modelmix-actions button[type="submit"]'));
  await act(async () => {});
}

function seatModels() {
  return JSON.stringify({
    worker_a: 'openai-oauth:gpt-5',
    moderator: 'openai-oauth:alt',
    worker_b: 'ollama:llama3',
  });
}

test('selecting Compare mode hides the Moderator selector and hides-but-keeps-mounted the Moderator panel', async () => {
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model') != null, true);
  assert.equal(modeSelect.value, 'mix');

  setMode(modeSelect, 'compare');
  assert.equal(modeSelect.value, 'compare');
  assert.equal(window.localStorage.getItem(MODE_STORAGE_KEY), 'compare');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model'), null);
  assert.ok(document.querySelector('.modelmix-models').classList.contains('modelmix-models--compare'));

  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  const moderator = articles[1];
  assert.ok(moderator.classList.contains('modelmix-panel-hidden'));
  assert.equal(moderator.querySelectorAll('.modelmix-transcript').length, 1);
});

test('Mix mode behavior is unchanged: moderator selector is present and panels all render', async () => {
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'mix');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model') != null, true);
  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  assert.ok(!document.querySelector('.modelmix-models').classList.contains('modelmix-models--compare'));
  for (const article of articles) {
    assert.deepEqual(
      [...article.classList].filter((name) => name.startsWith('modelmix-panel-')),
      [],
    );
  }
});

test('mode control is disabled during an active run via the existing disabled-state helper', async () => {
  window.localStorage.setItem(MODE_STORAGE_KEY, 'compare');
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  captured.response = {
    headers: { get: (name) => (name === 'X-ModelMix-Run-ID' ? 'run-compare' : name === 'X-ModelMix-Session-ID' ? 'session-compare' : null) },
  };
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.disabled, false);
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Start a compare run.');
  await sendNow();
  const selectAfterSend = document.querySelector('.modelmix-mode-select');
  assert.equal(selectAfterSend.disabled, true);
  assert.equal(document.querySelector('.modelmix-actions button[type="submit"]').disabled, true);
  assert.equal(document.querySelector('.modelmix-actions button.stop').disabled, false);
});

test('Compare mode send omits the moderator_model key entirely', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  window.localStorage.setItem(MODE_STORAGE_KEY, 'compare');
  captured.response = {
    headers: { get: (name) => (name === 'X-ModelMix-Run-ID' ? 'run-compare' : name === 'X-ModelMix-Session-ID' ? 'session-compare' : null) },
  };
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'compare');
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Compare two witnesses.');
  await sendNow();
  assert.ok(captured.payload);
  assert.equal('moderator_model' in captured.payload, false);
  assert.equal(captured.payload.worker_a_model, 'openai-oauth:gpt-5');
  assert.equal(captured.payload.worker_b_model, 'ollama:llama3');
  assert.equal(captured.payload.prompt, 'Compare two witnesses.');
});

test('Mix mode send still includes the moderator_model key', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  window.localStorage.setItem(MODE_STORAGE_KEY, 'mix');
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'mix');
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Mix both witnesses.');
  await sendNow();
  assert.ok(captured.payload);
  assert.equal(captured.payload.moderator_model, 'openai-oauth:alt');
});

test('a Compare-mode run renders cleanly with worker content and no moderator-shaped content', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  window.localStorage.setItem(MODE_STORAGE_KEY, 'compare');
  captured.response = {
    headers: { get: (name) => (name === 'X-ModelMix-Run-ID' ? 'run-compare' : name === 'X-ModelMix-Session-ID' ? 'session-compare' : null) },
  };
  captured.events = [
    { run_id: 'run-compare', seq: 1, type: 'run_started', seats: ['worker_a', 'worker_b'] },
    { run_id: 'run-compare', seq: 2, type: 'seat_started', seat_id: 'worker_a', model: 'gpt-5' },
    { run_id: 'run-compare', seq: 3, type: 'seat_delta', seat_id: 'worker_a', delta: 'Alice speaks first.' },
    { run_id: 'run-compare', seq: 4, type: 'seat_completed', seat_id: 'worker_a', ts: 1 },
    { run_id: 'run-compare', seq: 5, type: 'seat_started', seat_id: 'worker_b', model: 'llama3' },
    { run_id: 'run-compare', seq: 6, type: 'seat_delta', seat_id: 'worker_b', delta: 'Bob speaks second.' },
    { run_id: 'run-compare', seq: 7, type: 'seat_completed', seat_id: 'worker_b', ts: 2 },
    { run_id: 'run-compare', seq: 8, type: 'run_completed', status: 'completed' },
  ];
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'compare');
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Compare both.');
  await sendNow();

  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  assert.equal(articles[0].textContent.includes('Alice speaks first.'), true);
  assert.equal(articles[2].textContent.includes('Bob speaks second.'), true);

  const moderator = articles[1];
  assert.ok(moderator.classList.contains('modelmix-panel-hidden'));
  assert.equal(moderator.textContent.includes('Moderator synthesis'), false);
  assert.equal(moderator.textContent.includes('Alice speaks first.'), false);
  assert.equal(moderator.textContent.includes('Bob speaks second.'), false);
  assert.equal(document.body.textContent.includes('Moderator synthesis'), false);
});
