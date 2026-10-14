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

test('selecting Solo hides the Moderator and Worker B selectors and keeps all three panels mounted', async () => {
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'mix');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model') != null, true);
  assert.equal(document.querySelector('.modelmix-models #modelmix-worker-b-model') != null, true);

  setMode(modeSelect, 'solo');
  assert.equal(modeSelect.value, 'solo');
  assert.equal(window.localStorage.getItem(MODE_STORAGE_KEY), 'solo');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model'), null);
  assert.equal(document.querySelector('.modelmix-models #modelmix-worker-b-model'), null);
  assert.ok(document.querySelector('.modelmix-models #modelmix-worker-a-model'));

  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  const moderator = articles[1];
  const workerB = articles[2];
  assert.ok(moderator.classList.contains('modelmix-panel-hidden'));
  assert.ok(workerB.classList.contains('modelmix-panel-hidden'));
  assert.equal(moderator.querySelectorAll('.modelmix-transcript').length, 1);
  assert.equal(workerB.querySelectorAll('.modelmix-transcript').length, 1);
  assert.ok(document.querySelector('.modelmix-workers').classList.contains('modelmix-workers--maximized'));
});

test('Solo mode send omits worker_b_model and moderator_model keys entirely', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  window.localStorage.setItem(MODE_STORAGE_KEY, 'solo');
  captured.response = {
    headers: { get: (name) => (name === 'X-ModelMix-Run-ID' ? 'run-solo' : name === 'X-ModelMix-Session-ID' ? 'session-solo' : null) },
  };
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'solo');
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Solo witness.');
  await sendNow();
  assert.ok(captured.payload);
  assert.equal('worker_b_model' in captured.payload, false);
  assert.equal('moderator_model' in captured.payload, false);
  assert.equal(captured.payload.worker_a_model, 'openai-oauth:gpt-5');
  assert.equal(captured.payload.prompt, 'Solo witness.');
});

test('Solo mode does not require worker_b or moderator to enable Send', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  window.localStorage.setItem(MODE_STORAGE_KEY, 'solo');
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'solo');
  const sendButton = document.querySelector('.modelmix-actions button[type="submit"]');
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'A lone prompt.');
  await act(async () => {});
  assert.equal(sendButton.disabled, false);
});

test('mix mode behavior is unchanged after Solo is added', async () => {
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'mix');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model') != null, true);
  assert.equal(document.querySelector('.modelmix-models #modelmix-worker-b-model') != null, true);
  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  for (const article of articles) {
    assert.deepEqual(
      [...article.classList].filter((name) => name.startsWith('modelmix-panel-')),
      [],
    );
  }
  assert.ok(!document.querySelector('.modelmix-workers').classList.contains('modelmix-workers--maximized'));
});

test('compare mode behavior is unchanged after Solo is added', async () => {
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  setMode(modeSelect, 'compare');
  assert.equal(document.querySelector('.modelmix-models #modelmix-moderator-model'), null);
  assert.equal(document.querySelector('.modelmix-models #modelmix-worker-b-model') != null, true);
  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  assert.ok(articles[1].classList.contains('modelmix-panel-hidden'));
  assert.ok(!articles[2].classList.contains('modelmix-panel-hidden'));
  assert.ok(!document.querySelector('.modelmix-workers').classList.contains('modelmix-workers--maximized'));
});

test('mode control being disabled during an active run also covers Solo as a value', async () => {
  window.localStorage.setItem(MODE_STORAGE_KEY, 'solo');
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  captured.response = {
    headers: { get: (name) => (name === 'X-ModelMix-Run-ID' ? 'run-solo' : name === 'X-ModelMix-Session-ID' ? 'session-solo' : null) },
  };
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'solo');
  assert.equal(modeSelect.disabled, false);
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Start a solo run.');
  await sendNow();
  const selectAfterSend = document.querySelector('.modelmix-mode-select');
  assert.equal(selectAfterSend.disabled, true);
  assert.equal(selectAfterSend.value, 'solo');
  assert.equal(document.querySelector('.modelmix-actions button[type="submit"]').disabled, true);
  assert.equal(document.querySelector('.modelmix-actions button.stop').disabled, false);
});

test('a Solo-mode run renders cleanly with worker_a content and no worker_b or moderator content', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, seatModels());
  window.localStorage.setItem(MODE_STORAGE_KEY, 'solo');
  captured.response = {
    headers: { get: (name) => (name === 'X-ModelMix-Run-ID' ? 'run-solo' : name === 'X-ModelMix-Session-ID' ? 'session-solo' : null) },
  };
  captured.events = [
    { run_id: 'run-solo', seq: 1, type: 'run_started', seats: ['worker_a'] },
    { run_id: 'run-solo', seq: 2, type: 'seat_started', seat_id: 'worker_a', model: 'gpt-5' },
    { run_id: 'run-solo', seq: 3, type: 'seat_delta', seat_id: 'worker_a', delta: 'Alice thinks alone.' },
    { run_id: 'run-solo', seq: 4, type: 'seat_completed', seat_id: 'worker_a', ts: 1 },
    { run_id: 'run-solo', seq: 5, type: 'run_completed', status: 'completed' },
  ];
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  assert.equal(modeSelect.value, 'solo');
  setPrompt(document.querySelector('.modelmix-composer textarea'), 'Run solo.');
  await sendNow();

  const articles = document.querySelectorAll('article.modelmix-worker');
  assert.equal(articles.length, 3);
  assert.equal(articles[0].textContent.includes('Alice thinks alone.'), true);

  const moderator = articles[1];
  const workerB = articles[2];
  assert.ok(moderator.classList.contains('modelmix-panel-hidden'));
  assert.ok(workerB.classList.contains('modelmix-panel-hidden'));
  assert.equal(moderator.textContent.includes('Alice thinks alone.'), false);
  assert.equal(workerB.textContent.includes('Alice thinks alone.'), false);
  assert.equal(document.body.textContent.includes('Bob'), false);
  assert.equal(document.body.querySelectorAll('.modelmix-worker-error').length, 0);
});

test('in Solo mode maximizing a hidden seat is inert and never blanks the cockpit', async () => {
  window.localStorage.setItem(MODE_STORAGE_KEY, 'solo');
  await renderObserver();
  const modeSelect = document.querySelector('.modelmix-mode-select');
  setMode(modeSelect, 'solo');
  const articles = document.querySelectorAll('article.modelmix-worker');
  const workerB = articles[2];
  // Try to maximize the mode-hidden Worker B panel.
  click(workerB.querySelector('[aria-label="Maximize Worker B"]'));
  const [workerA, moderator, workerBAfter] = document.querySelectorAll('article.modelmix-worker');
  assert.ok(workerA.classList.contains('modelmix-panel-hidden') === false);
  assert.ok(moderator.classList.contains('modelmix-panel-hidden'));
  assert.ok(workerBAfter.classList.contains('modelmix-panel-hidden'));
  // Worker A remains visible in the single-column layout: the cockpit is not blank.
  assert.ok(document.querySelector('.modelmix-workers').classList.contains('modelmix-workers--maximized'));
  assert.ok(workerA.querySelector('.modelmix-transcript'));
});
