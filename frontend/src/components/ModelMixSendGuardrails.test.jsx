// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, test, vi } from 'vitest';
import { DEFAULT_SAVED_MODELS_KEY } from '../defaultSeatModels';
import { GUARDRAIL_STORAGE_KEY } from '../guardrailSettings';

const { captured } = vi.hoisted(() => ({ captured: { payload: null } }));

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

vi.mock('../modelmixApi', () => ({
  ModelMixHttpError: class ModelMixHttpError extends Error {
    constructor(message, status = 0) {
      super(message);
      this.status = status;
    }
  },
  cancelModelMixRun: async () => {},
  consumeModelMixSSE: async () => { throw new Error('not used in this render test'); },
  hydrateModelMixSession: async () => { throw new Error('no session'); },
  replayModelMixRun: async () => { throw new Error('not used in this render test'); },
  startModelMixRun: async (payload) => {
    captured.payload = payload;
    const error = new Error('server rejected');
    error.status = 503;
    throw error;
  },
}));

import ModelMixObserver from './ModelMixObserver.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mounted = [];

afterEach(() => {
  captured.payload = null;
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

async function sendWithPrompt() {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  await renderObserver();
  const textarea = document.querySelector('.modelmix-composer textarea');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  act(() => {
    setter.call(textarea, 'Why do independent witnesses matter?');
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  });
  click(document.querySelector('.modelmix-actions button[type="submit"]'));
  await act(async () => {});
}

test('send omits guardrail override fields when nothing is saved', async () => {
  await sendWithPrompt();
  assert.ok(captured.payload);
  assert.equal(captured.payload.prompt, 'Why do independent witnesses matter?');
  assert.equal('warning_threshold_chars' in captured.payload, false);
  assert.equal('hard_cap_chars' in captured.payload, false);
});

test('send includes both override fields when a valid override is saved', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify({
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  }));
  await sendWithPrompt();
  assert.equal(captured.payload.warning_threshold_chars, 5000);
  assert.equal(captured.payload.hard_cap_chars, 10000);
  assert.equal(captured.payload.worker_a_model, 'openai-oauth:alt');
});

test('send omits both fields when the saved override fails validation', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(GUARDRAIL_STORAGE_KEY, 'definitely-not-json{{{');
  await sendWithPrompt();
  assert.equal('warning_threshold_chars' in captured.payload, false);
  assert.equal('hard_cap_chars' in captured.payload, false);
});