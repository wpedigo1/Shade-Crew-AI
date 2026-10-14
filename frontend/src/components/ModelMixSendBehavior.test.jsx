// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, test, vi } from 'vitest';
import { DEFAULT_SAVED_MODELS_KEY } from '../defaultSeatModels';
import { BEHAVIOR_STORAGE_KEY, SPEND_LIMIT_STORAGE_KEY } from '../modelmixBehavior';

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

test('send omits temperature and moderator_guidance when nothing is saved', async () => {
  await sendWithPrompt();
  assert.ok(captured.payload);
  assert.equal(captured.payload.prompt, 'Why do independent witnesses matter?');
  assert.equal('temperature' in captured.payload, false);
  assert.equal('moderator_guidance' in captured.payload, false);
});

test('send includes both temperature and moderator_guidance when both are saved', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(BEHAVIOR_STORAGE_KEY, JSON.stringify({
    temperature: 0.7,
    moderator_guidance: 'Emphasize numeric claims.',
  }));
  await sendWithPrompt();
  assert.equal(captured.payload.temperature, 0.7);
  assert.equal(captured.payload.moderator_guidance, 'Emphasize numeric claims.');
  assert.equal(captured.payload.worker_a_model, 'openai-oauth:alt');
});

test('send includes only the saved field when just one is set', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(BEHAVIOR_STORAGE_KEY, JSON.stringify({
    temperature: 1.25,
  }));
  await sendWithPrompt();
  assert.equal(captured.payload.temperature, 1.25);
  assert.equal('moderator_guidance' in captured.payload, false);
});

test('send includes only the saved guidance when just guidance is set', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(BEHAVIOR_STORAGE_KEY, JSON.stringify({
    moderator_guidance: 'Flag any unsupported conclusions.',
  }));
  await sendWithPrompt();
  assert.equal(captured.payload.moderator_guidance, 'Flag any unsupported conclusions.');
  assert.equal('temperature' in captured.payload, false);
});

test('send omits both fields when the saved behavior fails validation', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(BEHAVIOR_STORAGE_KEY, 'definitely-not-json{{{');
  await sendWithPrompt();
  assert.equal('temperature' in captured.payload, false);
  assert.equal('moderator_guidance' in captured.payload, false);
});

test('send includes spend_limit_usd when a spend limit is saved', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(3.0));
  await sendWithPrompt();
  assert.equal(captured.payload.spend_limit_usd, 3.0);
});

test('send omits spend_limit_usd when no spend limit is saved', async () => {
  await sendWithPrompt();
  assert.equal('spend_limit_usd' in captured.payload, false);
});

test('confirm_over_budget is never present on the initial request', async () => {
  window.localStorage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(1.5));
  await sendWithPrompt();
  assert.equal('confirm_over_budget' in captured.payload, false);
});
