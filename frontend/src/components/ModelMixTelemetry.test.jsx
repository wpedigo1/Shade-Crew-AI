// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, beforeEach, test, vi } from 'vitest';

const { mockSettings, mockDiscovered, mockHydrate } = vi.hoisted(() => ({
  mockSettings: {},
  mockDiscovered: [],
  mockHydrate: { document: null },
}));

vi.mock('../api', () => ({
  api: { getSettings: async () => mockSettings.value },
  buildAvailableSearchProviders: () => [],
  DEFAULT_EXECUTION_MODE: 'full',
}));

vi.mock('../configuredModels', async (importOriginal) => ({
  ...(await importOriginal()),
  discoverConfiguredModels: async () => mockDiscovered.value,
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
    consumeModelMixSSE: async () => { throw new Error('not used in render test'); },
    hydrateModelMixSession: async () => {
      if (!mockHydrate.document) throw new ModelMixHttpError('no session found', 404);
      return mockHydrate.document;
    },
    replayModelMixRun: async () => { throw new Error('not used in render test'); },
    startModelMixRun: async () => { throw new Error('not used in render test'); },
  };
});

import ModelMixObserver from './ModelMixObserver.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const DISCOVERED = [
  { id: 'openai-oauth:gpt-5', name: 'gpt-5 (ChatGPT)', provider: 'OpenAI' },
  { id: 'ollama:llama3', name: 'llama3', provider: 'Ollama' },
  { id: 'openai-oauth:alt', name: 'Alt model', provider: 'OpenAI' },
];

const MODELS = { worker_a: 'openai-oauth:gpt-5', moderator: 'openai-oauth:gpt-5', worker_b: 'ollama:llama3' };

function message(runId, seat, overrides = {}) {
  return {
    run_id: runId,
    seat,
    content: '',
    status: 'completed',
    usage: null,
    started_at: null,
    completed_at: null,
    finish_reason: null,
    ...overrides,
  };
}

function documentWith({ runs, messages }) {
  return {
    schema_version: 1,
    session: { session_id: 'sess-telemetry', runs, messages },
  };
}

const mounted = [];

beforeEach(() => {
  mockSettings.value = {};
  mockDiscovered.value = DISCOVERED;
  mockHydrate.document = null;
});

afterEach(() => {
  mockSettings.value = {};
  mockDiscovered.value = [];
  mockHydrate.document = null;
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

function panel(title) {
  return [...document.querySelectorAll('article.modelmix-worker')]
    .find((article) => article.querySelector('h2').textContent === title);
}

function panelFooter(title) {
  return panel(title).querySelector('.modelmix-telemetry');
}

test('with no session the cockpit renders no telemetry footers', async () => {
  await renderObserver();
  assert.equal(document.querySelectorAll('.modelmix-telemetry').length, 0);
});

test('completed seats render authoritative provider-reported usage, finish reason, and calculated timing', async () => {
  mockHydrate.document = documentWith({
    runs: [{ run_id: 'run-1', latest_seq: 12, status: 'completed', prompt: 'prompt 1', models: MODELS }],
    messages: [
      message('run-1', 'worker_a', {
        content: 'Live A evidence',
        usage: { prompt_tokens: 12, completion_tokens: 34, total_tokens: 46 },
        started_at: 100,
        completed_at: 112.4,
      }),
      message('run-1', 'moderator', {
        content: 'Live M synthesis',
        usage: { total_tokens: 99 },
        started_at: 120,
        completed_at: 200.5,
        finish_reason: 'stop',
      }),
      message('run-1', 'worker_b', {
        content: 'Live B evidence',
        usage: null,
        started_at: 400,
        completed_at: 401,
      }),
    ],
  });
  await renderObserver();

  assert.equal(document.querySelectorAll('.modelmix-telemetry').length, 3);

  const workerAFooter = panelFooter('Worker A');
  assert.ok(workerAFooter.textContent.includes('Usage'));
  assert.ok(workerAFooter.textContent.includes('authoritative (provider-reported)'));
  assert.ok(workerAFooter.textContent.includes('46 tokens'));
  assert.ok(workerAFooter.textContent.includes('Elapsed'));
  assert.ok(workerAFooter.textContent.includes('(calculated)'));
  assert.ok(workerAFooter.textContent.includes('→'));

  const moderatorFooter = panelFooter('Moderator');
  assert.ok(moderatorFooter.textContent.includes('Finish'));
  assert.ok(moderatorFooter.textContent.includes('stop'));
  assert.ok(moderatorFooter.textContent.includes('99 tokens'));

  const workerBFooter = panelFooter('Worker B');
  assert.ok(workerBFooter.textContent.includes('unavailable'));
});

test('prior-turn archives keep their telemetry hidden while live seats still render footers', async () => {
  mockHydrate.document = documentWith({
    runs: [
      { run_id: 'run-0', latest_seq: 6, status: 'completed', prompt: 'prior prompt', models: MODELS },
      { run_id: 'run-1', latest_seq: 12, status: 'completed', prompt: 'prompt 1', models: MODELS },
    ],
    messages: [
      message('run-0', 'worker_a', {
        content: 'Prior A evidence',
        usage: { total_tokens: 7 },
        started_at: 1,
        completed_at: 2,
      }),
      message('run-0', 'moderator', { content: 'Prior M synthesis', usage: { total_tokens: 8 } }),
      message('run-0', 'worker_b', { content: 'Prior B evidence', usage: null }),
      message('run-1', 'worker_a', {
        content: 'Live A evidence',
        usage: null,
        started_at: 100,
        completed_at: 112.4,
      }),
      message('run-1', 'moderator', {
        content: 'Live M synthesis',
        usage: { total_tokens: 99 },
        started_at: 120,
        completed_at: 200.5,
      }),
      message('run-1', 'worker_b', {
        content: 'Live B evidence',
        usage: null,
        started_at: 400,
        completed_at: 401,
      }),
    ],
  });
  await renderObserver();

  assert.equal(document.querySelectorAll('.modelmix-prior-turn .modelmix-telemetry').length, 0);
  assert.equal(document.querySelectorAll('.modelmix-telemetry').length, 3);
  assert.ok(document.body.textContent.includes('Prior A evidence'));

  const workerAFooter = panelFooter('Worker A');
  assert.ok(workerAFooter.textContent.includes('unavailable'));
  assert.ok(!workerAFooter.textContent.includes('total_tokens'));

  const moderatorFooter = panelFooter('Moderator');
  assert.ok(moderatorFooter.textContent.includes('not reported'));
});