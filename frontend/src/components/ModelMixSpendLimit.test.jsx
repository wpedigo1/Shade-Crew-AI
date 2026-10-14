// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, beforeEach, test, vi } from 'vitest';
import { DEFAULT_SAVED_MODELS_KEY } from '../defaultSeatModels';
import { BEHAVIOR_STORAGE_KEY, SPEND_LIMIT_STORAGE_KEY } from '../modelmixBehavior';
import { ModelMixHttpError } from '../modelmixApi';

const { captured } = vi.hoisted(() => ({
  captured: { payloads: [], rejectWith: null },
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
    captured.payloads.push(payload);
    if (captured.rejectWith) {
      throw captured.rejectWith;
    }
    const error = new Error('server rejected');
    error.status = 503;
    throw error;
  },
}));

import ModelMixObserver from './ModelMixObserver.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mounted = [];

beforeEach(() => {
  captured.payloads = [];
  captured.rejectWith = null;
});

afterEach(() => {
  captured.payloads = [];
  captured.rejectWith = null;
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

test('send includes spend_limit_usd when a spend limit is saved', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  window.localStorage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(2.5));
  await sendWithPrompt();
  const payload = captured.payloads[0];
  assert.ok(payload);
  assert.equal(payload.spend_limit_usd, 2.5);
});

test('send omits spend_limit_usd when no spend limit is saved', async () => {
  await sendWithPrompt();
  const payload = captured.payloads[0];
  assert.ok(payload);
  assert.equal('spend_limit_usd' in payload, false);
});

test('confirm_over_budget is never present on the initial request', async () => {
  window.localStorage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(1.0));
  await sendWithPrompt();
  const payload = captured.payloads[0];
  assert.equal('confirm_over_budget' in payload, false);
});

test('a 402 response renders the real backend message and offers confirmation', async () => {
  captured.rejectWith = new ModelMixHttpError(
    'Seat worker_a would cost $3.00, exceeding the $2.50 spend limit.',
    402,
  );
  window.localStorage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(2.5));
  await sendWithPrompt();
  const confirmation = document.querySelector('.modelmix-spend-confirmation');
  assert.ok(confirmation, 'spend confirmation UI should be visible');
  assert.ok(
    confirmation.textContent.includes('worker_a would cost $3.00'),
    'should show the real backend message',
  );
  assert.ok(
    confirmation.querySelector('.modelmix-spend-confirm'),
    'should have a proceed button',
  );
});

test('confirm-and-retry resends the identical original body plus confirm_over_budget', async () => {
  captured.rejectWith = new ModelMixHttpError(
    'Seat worker_a would cost $3.00, exceeding the $2.50 spend limit.',
    402,
  );
  window.localStorage.setItem(SPEND_LIMIT_STORAGE_KEY, JSON.stringify(2.5));
  await sendWithPrompt();
  const originalPayload = captured.payloads[0];
  assert.ok(originalPayload);
  assert.equal('confirm_over_budget' in originalPayload, false);

  captured.rejectWith = null;
  const throwAfterCapture = new Error('server rejected');
  throwAfterCapture.status = 503;
  captured.rejectWith = throwAfterCapture;

  const confirmButton = document.querySelector('.modelmix-spend-confirm');
  assert.ok(confirmButton);
  click(confirmButton);
  await act(async () => {});

  assert.equal(captured.payloads.length, 2);
  const retryPayload = captured.payloads[1];
  assert.equal(retryPayload.prompt, originalPayload.prompt);
  assert.equal(retryPayload.worker_a_model, originalPayload.worker_a_model);
  assert.equal(retryPayload.worker_b_model, originalPayload.worker_b_model);
  assert.equal(retryPayload.moderator_model, originalPayload.moderator_model);
  assert.equal(retryPayload.spend_limit_usd, originalPayload.spend_limit_usd);
  assert.equal(retryPayload.confirm_over_budget, true);
});

test('a non-402 error does not show the spend confirmation UI', async () => {
  captured.rejectWith = new ModelMixHttpError('Service unavailable', 503);
  await sendWithPrompt();
  const confirmation = document.querySelector('.modelmix-spend-confirmation');
  assert.equal(confirmation, null, 'spend confirmation should not appear for non-402 errors');
});
