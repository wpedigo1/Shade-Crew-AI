// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, beforeEach, test, vi } from 'vitest';
import pkg from '../../package.json';
import { DEFAULT_SAVED_MODELS_KEY, loadSavedSeatModels } from '../defaultSeatModels';
import { GUARDRAIL_STORAGE_KEY, loadGuardrailOverride } from '../guardrailSettings';

const { mockSettings, mockDiscovered, mockHydrate, mockSessions, mockDelete, mockUpdate, mockTest, mockOauth } = vi.hoisted(() => ({
  mockSettings: {},
  mockDiscovered: [],
  mockHydrate: { value: null, shouldThrow: true },
  mockSessions: { value: [] },
  mockDelete: { error: null, called: [] },
  mockUpdate: { calls: [] },
  mockTest: { calls: [], results: {} },
  mockOauth: {
    start: { calls: [], error: null, response: null },
    status: { calls: [], status: 'pending', error: null, once: null },
    disconnect: { calls: [], error: null },
  },
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
      if (mockHydrate.shouldThrow) throw new ModelMixHttpError('no session found', 404);
      return mockHydrate.value;
    },
    listModelMixSessions: async () => mockSessions.value,
    deleteModelMixSession: async (sessionId) => {
      if (mockDelete.error) {
        throw new ModelMixHttpError(mockDelete.error.message, mockDelete.error.status);
      }
      mockDelete.called.push(sessionId);
      return {};
    },
    replayModelMixRun: async () => { throw new Error('not used in render test'); },
    startModelMixRun: async () => { throw new Error('not used in render test'); },
    updateSettings: async (body) => { mockUpdate.calls.push(body); return {}; },
    testProvider: async (providerId, apiKey) => {
      mockTest.calls.push({ endpoint: 'provider', providerId, apiKey });
      return mockTest.results.provider || { success: true, message: 'Provider key is valid' };
    },
    testOpenrouter: async (apiKey) => {
      mockTest.calls.push({ endpoint: 'openrouter', apiKey });
      return mockTest.results.openrouter || { success: true, message: 'OpenRouter key is valid' };
    },
    testOpencode: async (apiKey) => {
      mockTest.calls.push({ endpoint: 'opencode', apiKey });
      return mockTest.results.opencode || { success: true, message: 'OpenCode key is valid' };
    },
    testOllama: async (baseUrl) => {
      mockTest.calls.push({ endpoint: 'ollama', baseUrl });
      return mockTest.results.ollama || { success: true, message: 'Connected to Ollama' };
    },
    testCustomEndpoint: async (name, url, apiKey) => {
      mockTest.calls.push({ endpoint: 'custom', name, url, apiKey });
      return mockTest.results.custom || { success: true, message: 'Endpoint is reachable' };
    },
    startOAuthConnection: async (providerId) => {
      if (mockOauth.start.error) throw mockOauth.start.error;
      mockOauth.start.calls.push(providerId);
      if (mockOauth.start.response) return mockOauth.start.response(providerId);
      return {
        session_id: `session-${providerId}`,
        provider_id: providerId,
        user_code: 'CODE-1234',
        verification_uri: 'https://verify.example.com/device',
        verification_uri_complete: `https://verify.example.com/device?code=CODE`,
        expires_in: 300,
        status: 'pending',
      };
    },
    getOAuthConnectionStatus: async (providerId, sessionId) => {
      mockOauth.status.calls.push({ providerId, sessionId });
      if (mockOauth.status.once) {
        const once = mockOauth.status.once;
        mockOauth.status.once = null;
        return once;
      }
      return { status: mockOauth.status.status, error: mockOauth.status.error, provider_id: providerId, session_id: sessionId };
    },
    disconnectOAuthProvider: async (providerId) => {
      if (mockOauth.disconnect.error) throw mockOauth.disconnect.error;
      mockOauth.disconnect.calls.push(providerId);
      return { status: 'disconnected', provider_id: providerId };
    },
  };
});

import ModelMixObserver from './ModelMixObserver.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const DISCOVERED = [
  { id: 'openai-oauth:gpt-5', name: 'gpt-5 (ChatGPT)', provider: 'OpenAI' },
  { id: 'ollama:llama3', name: 'llama3', provider: 'Ollama' },
  { id: 'openai-oauth:alt', name: 'Alt model', provider: 'OpenAI' },
];

const ALL_CONFIGURED = {
  enabled_providers: {
    openrouter: true,
    ollama: true,
    direct: true,
    custom: true,
    'xai-oauth': true,
    'openai-oauth': true,
    'github-copilot': true,
  },
  openrouter_api_key_set: true,
  ollama_base_url: 'http://localhost:11434',
  openai_api_key_set: true,
  custom_endpoint_url: 'http://localhost:8765',
  xai_oauth_connected: true,
  openai_oauth_connected: true,
  github_copilot_connected: true,
};

const mounted = [];

beforeEach(() => {
  mockSettings.value = {};
  mockDiscovered.value = DISCOVERED;
  mockHydrate.value = null;
  mockHydrate.shouldThrow = true;
  mockSessions.value = [];
  mockDelete.error = null;
  mockDelete.called = [];
  mockUpdate.calls = [];
  mockTest.calls = [];
  mockTest.results = {};
  mockOauth.start.calls = [];
  mockOauth.start.error = null;
  mockOauth.start.response = null;
  mockOauth.status.calls = [];
  mockOauth.status.status = 'pending';
  mockOauth.status.error = null;
  mockOauth.status.once = null;
  mockOauth.disconnect.calls = [];
  mockOauth.disconnect.error = null;
});

afterEach(() => {
  mockSettings.value = {};
  mockDiscovered.value = [];
  mockHydrate.value = null;
  mockHydrate.shouldThrow = true;
  mockSessions.value = [];
  mockDelete.error = null;
  mockDelete.called = [];
  mockUpdate.calls = [];
  mockTest.calls = [];
  mockTest.results = {};
  mockOauth.start.calls = [];
  mockOauth.start.error = null;
  mockOauth.start.response = null;
  mockOauth.status.calls = [];
  mockOauth.status.status = 'pending';
  mockOauth.status.error = null;
  mockOauth.status.once = null;
  mockOauth.disconnect.calls = [];
  mockOauth.disconnect.error = null;
  for (const { root, container } of mounted.splice(0)) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  vi.useRealTimers();
  window.localStorage.clear();
});

// Do NOT clear localStorage here: saved-defaults tests seed before rendering.
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

function openSettings() {
  click(document.querySelector('.modelmix-settings-toggle'));
}

function navButton(label) {
  return [...document.querySelectorAll('.modelmix-settings-nav-item')].find((button) => button.textContent === label);
}

function selectedLabel(inputId) {
  const control = document.getElementById(inputId).closest('.model-select__control');
  const single = control.querySelector('.model-select__single-value');
  return single ? single.textContent : null;
}

function typeInput(element, value) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  act(() => {
    setter.call(element, value);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

test('gear button opens a settings dialog and the close control dismisses it', async () => {
  await renderObserver();
  assert.equal(document.querySelector('.modelmix-settings'), null);
  assert.ok(!document.body.textContent.includes('Settings'));

  openSettings();
  const dialog = document.querySelector('.modelmix-settings');
  assert.ok(dialog);
  assert.equal(dialog.getAttribute('role'), 'dialog');
  assert.equal(dialog.getAttribute('aria-modal'), 'true');
  assert.ok(dialog.textContent.includes('Settings'));
  assert.equal(document.querySelector('.modelmix-settings-toggle').getAttribute('aria-expanded'), 'true');

  click(document.querySelector('.modelmix-settings-close'));
  assert.equal(document.querySelector('.modelmix-settings'), null);
  assert.ok(!document.body.textContent.includes('Settings'));
});

test('About section renders the version from package.json with license and attribution', async () => {
  await renderObserver();
  openSettings();
  const section = document.querySelector('.modelmix-settings-section');
  assert.ok(section.textContent.includes(`Version ${pkg.version}`));
  assert.ok(section.textContent.includes('Jacob Ben David'));
  assert.ok(section.textContent.includes('The AI Counsel'));

  click(navButton('Defaults'));
  click(navButton('About'));
  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes(`Version ${pkg.version}`));
});

test('Providers section lists every source as connected for all-configured settings with no credential values', async () => {
  mockSettings.value = ALL_CONFIGURED;
  await renderObserver();
  openSettings();
  click(navButton('Providers'));

  const statuses = [...document.querySelectorAll('.modelmix-provider-status')];
  assert.deepEqual(statuses.map((node) => node.textContent), [
    'Connected', 'Connected', 'Connected', 'Connected', 'Connected',
  ]);
  assert.ok(statuses.every((node) => node.getAttribute('data-connected') === 'true'));
  assert.deepEqual(
    [...document.querySelectorAll('.modelmix-provider-name')].map((node) => node.textContent),
    ['OpenRouter', 'Ollama (local)', 'Direct API keys', 'Custom endpoint', 'OAuth accounts'],
  );

  const listText = document.querySelector('.modelmix-provider-list').textContent;
  assert.ok(!listText.includes('sk-'));
  assert.ok(!listText.includes('11434'));
  assert.ok(!listText.includes('8765'));
});

test('Providers section lists every source as not connected when nothing is configured', async () => {
  mockSettings.value = {};
  await renderObserver();
  openSettings();
  click(navButton('Providers'));

  const statuses = [...document.querySelectorAll('.modelmix-provider-status')];
  assert.deepEqual(statuses.map((node) => node.textContent), [
    'Not connected', 'Not connected', 'Not connected', 'Not connected', 'Not connected',
  ]);
  assert.ok(statuses.every((node) => node.getAttribute('data-connected') === 'false'));
});

test('without saved defaults the hardcoded built-in seat selections win on mount', async () => {
  await renderObserver();
  assert.equal(selectedLabel('modelmix-worker-a-model'), 'gpt-5 (ChatGPT)');
  assert.equal(selectedLabel('modelmix-worker-b-model'), 'llama3');
  assert.equal(selectedLabel('modelmix-moderator-model'), null);
});

test('saved defaults win over the hardcoded selections on mount', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({
    worker_a: 'openai-oauth:alt',
    moderator: 'openai-oauth:gpt-5',
    worker_b: 'ollama:llama3',
  }));
  await renderObserver();
  assert.equal(selectedLabel('modelmix-worker-a-model'), 'Alt model');
  assert.equal(selectedLabel('modelmix-moderator-model'), 'gpt-5 (ChatGPT)');
  assert.equal(selectedLabel('modelmix-worker-b-model'), 'llama3');

  openSettings();
  click(navButton('Defaults'));
  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes('Saved defaults will be applied on the next load.'));
});

test('a corrupted saved value falls back to the built-in defaults without throwing', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, 'definitely-not-json{{{');
  await renderObserver();
  assert.equal(selectedLabel('modelmix-worker-a-model'), 'gpt-5 (ChatGPT)');
  assert.equal(selectedLabel('modelmix-worker-b-model'), 'llama3');
  assert.equal(selectedLabel('modelmix-moderator-model'), null);
});

test('Defaults section saves the current selections and Clear removes them', async () => {
  await renderObserver();
  openSettings();
  click(navButton('Defaults'));

  const section = document.querySelector('.modelmix-settings-section');
  assert.ok(section.textContent.includes('No saved defaults — built-in defaults apply.'));
  assert.ok(section.textContent.includes('openai-oauth:gpt-5'));
  assert.ok(section.textContent.includes('None'));
  assert.ok(section.textContent.includes('ollama:llama3'));
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, true);

  click(document.querySelector('.modelmix-settings-save'));
  assert.deepEqual(loadSavedSeatModels(window.localStorage), {
    worker_a: 'openai-oauth:gpt-5',
    moderator: '',
    worker_b: 'ollama:llama3',
  });
  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes('Saved defaults will be applied on the next load.'));
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, false);

  click(document.querySelector('.modelmix-settings-clear'));
  assert.equal(loadSavedSeatModels(window.localStorage), null);
  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes('No saved defaults — built-in defaults apply.'));
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, true);
});

test('Guardrails section starts empty with Save and Clear disabled and static default help text', async () => {
  await renderObserver();
  openSettings();
  click(navButton('Guardrails'));

  const warning = document.getElementById('modelmix-guardrail-warning');
  const cap = document.getElementById('modelmix-guardrail-cap');
  assert.ok(warning);
  assert.ok(cap);
  assert.equal(warning.value, '');
  assert.equal(cap.value, '');

  const sectionText = document.querySelector('.modelmix-settings-section').textContent;
  assert.ok(sectionText.includes('ModelMix\'s built-in default'));
  assert.ok(sectionText.includes('20,000'));
  assert.ok(sectionText.includes('40,000'));
  assert.ok(sectionText.includes('not a live-fetched server value'));
  assert.ok(sectionText.includes('No saved override — server defaults apply.'));

  assert.equal(document.querySelector('.modelmix-settings-save').disabled, true);
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, true);
});

test('Guardrails section shows an inline error and keeps Save disabled for an invalid pair', async () => {
  await renderObserver();
  openSettings();
  click(navButton('Guardrails'));

  const cap = document.getElementById('modelmix-guardrail-cap');
  typeInput(cap, '100');
  const warning = document.getElementById('modelmix-guardrail-warning');
  typeInput(warning, '500');
  const section = document.querySelector('.modelmix-settings-section');
  assert.ok(section.textContent.includes('Hard cap must be at least the warning threshold'));
  assert.equal(document.querySelector('.modelmix-settings-error').getAttribute('role'), 'alert');
  assert.equal(document.querySelector('.modelmix-settings-save').disabled, true);

  typeInput(cap, '250000');
  assert.ok(section.textContent.includes('must be between 100 and 200000 characters'));
  assert.equal(document.querySelector('.modelmix-settings-save').disabled, true);
});

test('Guardrails section saving a valid pair enables Clear and writes the override', async () => {
  await renderObserver();
  openSettings();
  click(navButton('Guardrails'));

  typeInput(document.getElementById('modelmix-guardrail-warning'), '5000');
  typeInput(document.getElementById('modelmix-guardrail-cap'), '10000');
  assert.equal(document.querySelector('.modelmix-settings-save').disabled, false);

  click(document.querySelector('.modelmix-settings-save'));
  assert.deepEqual(loadGuardrailOverride(window.localStorage), {
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  });
  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes('Saved override will be sent with each request.'));
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, false);
});

test('Guardrails section Clear removes the override and resets both inputs', async () => {
  window.localStorage.setItem(GUARDRAIL_STORAGE_KEY, JSON.stringify({
    warning_threshold_chars: 5000,
    hard_cap_chars: 10000,
  }));
  await renderObserver();
  openSettings();
  click(navButton('Guardrails'));

  assert.equal(document.getElementById('modelmix-guardrail-warning').value, '5000');
  assert.equal(document.getElementById('modelmix-guardrail-cap').value, '10000');
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, false);

  click(document.querySelector('.modelmix-settings-clear'));
  assert.equal(loadGuardrailOverride(window.localStorage), null);
  assert.equal(document.getElementById('modelmix-guardrail-warning').value, '');
  assert.equal(document.getElementById('modelmix-guardrail-cap').value, '');
  assert.equal(document.querySelector('.modelmix-settings-clear').disabled, true);
  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes('No saved override — server defaults apply.'));
});

function openSessionsSection() {
  openSettings();
  click(navButton('Sessions'));
}

const flush = async () => {
  await act(async () => {});
};

test('Sessions section renders the fetched list with friendly details and an empty state', async () => {
  mockSessions.value = [
    { session_id: 'session-alpha', created_at: 1700000000, updated_at: 1700003600, message_count: 3 },
    { session_id: 'session-beta', created_at: 1690000000, updated_at: 1690000100, message_count: 0 },
  ];
  await renderObserver();
  openSessionsSection();
  await flush();

  const section = document.querySelector('.modelmix-settings-section');
  assert.ok(section.textContent.includes('session-alpha'));
  assert.ok(section.textContent.includes('3 messages'));
  assert.ok(section.textContent.includes('session-beta'));
  assert.ok(section.textContent.includes('0 messages'));
  assert.ok(section.textContent.includes('Deleting a session is permanent and cannot be undone.'));
  const rows = document.querySelectorAll('.modelmix-session-row');
  assert.equal(rows.length, 2);
});

test('Sessions section shows an honest empty state when there are no sessions', async () => {
  mockSessions.value = [];
  await renderObserver();
  openSessionsSection();
  await flush();

  assert.ok(document.querySelector('.modelmix-settings-section').textContent.includes('No sessions yet.'));
});

test('a single Delete click does not delete; the confirm click does', async () => {
  mockSessions.value = [{ session_id: 'session-alpha', created_at: 1, updated_at: 2, message_count: 1 }];
  await renderObserver();
  openSessionsSection();
  await flush();

  click(document.querySelector('.modelmix-session-delete'));
  await flush();
  assert.deepEqual(mockDelete.called, []);
  assert.ok(document.querySelector('.modelmix-session-confirm'));

  click(document.querySelector('.modelmix-session-delete-confirm'));
  await flush();
  assert.deepEqual(mockDelete.called, ['session-alpha']);
  assert.equal(document.querySelectorAll('.modelmix-session-row').length, 0);
});

test('a 409 delete response renders the real backend error message', async () => {
  mockSessions.value = [{ session_id: 'busy', created_at: 1, updated_at: 2, message_count: 1 }];
  mockDelete.error = { status: 409, message: 'Session has an active run (run-7); cancel it first' };
  await renderObserver();
  openSessionsSection();
  await flush();

  click(document.querySelector('.modelmix-session-delete'));
  await flush();
  click(document.querySelector('.modelmix-session-delete-confirm'));
  await flush();

  const section = document.querySelector('.modelmix-settings-section');
  assert.ok(section.textContent.includes('Session has an active run (run-7); cancel it first'));
  assert.equal(document.querySelector('.modelmix-settings-error').getAttribute('role'), 'alert');
  // The failed row stays visible.
  assert.equal(document.querySelectorAll('.modelmix-session-row').length, 1);
});

test('deleting the currently-open session resets to a fresh session', async () => {
  mockHydrate.value = {
    schema_version: 1,
    session: {
      session_id: 'sess-current',
      created_at: 1,
      updated_at: 2,
      runs: [{
        run_id: 'run-1', prompt: 'p', models: { worker_a: 'a' },
        status: 'completed', latest_seq: 1, events: [],
      }],
      messages: [],
    },
  };
  mockHydrate.shouldThrow = false;
  mockSessions.value = [{ session_id: 'sess-current', created_at: 1, updated_at: 2, message_count: 1 }];
  await renderObserver();
  window.localStorage.setItem('modelmix.sessionId', 'sess-current');
  openSessionsSection();
  await flush();

  click(document.querySelector('.modelmix-session-delete'));
  await flush();
  click(document.querySelector('.modelmix-session-delete-confirm'));
  await flush();

  assert.deepEqual(mockDelete.called, ['sess-current']);
  // The live cockpit reset to a fresh session: no persisted session id remains.
  assert.equal(window.localStorage.getItem('modelmix.sessionId'), null);
});

test('deleting a different session leaves the live cockpit state unchanged', async () => {
  mockHydrate.value = {
    schema_version: 1,
    session: {
      session_id: 'sess-current',
      created_at: 1,
      updated_at: 2,
      runs: [{
        run_id: 'run-1', prompt: 'p', models: { worker_a: 'a' },
        status: 'completed', latest_seq: 1, events: [],
      }],
      messages: [],
    },
  };
  mockHydrate.shouldThrow = false;
  mockSessions.value = [
    { session_id: 'sess-current', created_at: 1, updated_at: 2, message_count: 1 },
    { session_id: 'sess-other', created_at: 1, updated_at: 2, message_count: 2 },
  ];
  await renderObserver();
  window.localStorage.setItem('modelmix.sessionId', 'sess-current');
  openSessionsSection();
  await flush();

  const rows = [...document.querySelectorAll('.modelmix-session-row')];
  const otherRow = rows.find((row) => row.textContent.includes('sess-other'));
  click(otherRow.querySelector('.modelmix-session-delete'));
  await flush();
  click(otherRow.querySelector('.modelmix-session-delete-confirm'));
  await flush();

  assert.deepEqual(mockDelete.called, ['sess-other']);
  // The currently-open session is untouched.
  assert.equal(window.localStorage.getItem('modelmix.sessionId'), 'sess-current');
  assert.equal(document.querySelector('.modelmix-session-status').getAttribute('data-status'), 'completed');
});

function credRow(name) {
  return [...document.querySelectorAll('.modelmix-credential-row')].find(
    (row) => row.querySelector('.modelmix-cred-name')?.textContent === name,
  );
}

function openProviders() {
  openSettings();
  click(navButton('Providers'));
}

test('Providers credential UI shows write-only password inputs that start empty even when a key is already saved', async () => {
  mockSettings.value = { openai_api_key_set: true, enabled_providers: { direct: true } };
  await renderObserver();
  openProviders();

  const row = credRow('OpenAI');
  assert.ok(row);
  const input = row.querySelector('input');
  assert.equal(input.type, 'password');
  assert.equal(input.value, '');
  // No saved credential value is ever echoed into the document.
  assert.ok(!document.body.textContent.includes('sk-'));
  assert.ok(!input.getAttribute('placeholder').includes('sk-'));
  assert.match(input.getAttribute('placeholder'), /New key/);
  // The connected READ status reflects the saved state independently.
  const statuses = [...document.querySelectorAll('.modelmix-provider-status')];
  assert.equal(statuses.find((s) => s.parentElement.textContent.includes('Direct API keys')).getAttribute('data-connected'), 'true');
});

test('Providers saves a plain API-key provider by PUTting only that field', async () => {
  await renderObserver();
  openProviders();

  const input = credRow('OpenAI').querySelector('input');
  typeInput(input, 'sk-openai-123');
  click(credRow('OpenAI').querySelector('.modelmix-cred-save'));
  await flush();

  assert.deepEqual(mockUpdate.calls, [{ openai_api_key: 'sk-openai-123' }]);
  // A successful save clears the write-only input.
  assert.equal(input.value, '');
});

test('Providers saves the ollama base URL by PUTting only that field', async () => {
  await renderObserver();
  openProviders();

  const input = document.querySelector('input[aria-label="Ollama base URL"]');
  typeInput(input, 'http://localhost:11434');
  click(credRow('Ollama (local)').querySelector('.modelmix-cred-save'));
  await flush();

  assert.deepEqual(mockUpdate.calls, [{ ollama_base_url: 'http://localhost:11434' }]);
});

test('Providers saves a custom endpoint by PUTting only the entered fields (no api_key when blank)', async () => {
  await renderObserver();
  openProviders();

  typeInput(document.querySelector('input[aria-label="Custom endpoint name"]'), 'My vLLM');
  typeInput(document.querySelector('input[aria-label="Custom endpoint URL"]'), 'http://localhost:8000/v1');
  // Leave the API key blank for a local server.
  click(credRow('Custom endpoint').querySelector('.modelmix-cred-save'));
  await flush();

  assert.deepEqual(mockUpdate.calls, [
    { custom_endpoint_name: 'My vLLM', custom_endpoint_url: 'http://localhost:8000/v1' },
  ]);
});

test('Providers custom endpoint save includes api_key when the user provided one', async () => {
  await renderObserver();
  openProviders();

  typeInput(document.querySelector('input[aria-label="Custom endpoint name"]'), 'Together');
  typeInput(document.querySelector('input[aria-label="Custom endpoint URL"]'), 'https://api.together.xyz/v1');
  typeInput(document.querySelector('input[aria-label="Custom endpoint API key"]'), 'tk-456');
  click(credRow('Custom endpoint').querySelector('.modelmix-cred-save'));
  await flush();

  assert.deepEqual(mockUpdate.calls, [
    { custom_endpoint_name: 'Together', custom_endpoint_url: 'https://api.together.xyz/v1', custom_endpoint_api_key: 'tk-456' },
  ]);
});

test('Providers Test calls the correct existing endpoint and shows the real returned message', async () => {
  mockTest.results.provider = { success: true, message: 'Valid OpenAI key' };
  await renderObserver();
  openProviders();

  const row = credRow('OpenAI');
  typeInput(row.querySelector('input'), 'sk-openai-xyz');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();

  assert.deepEqual(mockTest.calls, [{ endpoint: 'provider', providerId: 'openai', apiKey: 'sk-openai-xyz' }]);
  const result = row.querySelector('.modelmix-cred-result');
  assert.ok(result);
  assert.ok(result.textContent.includes('Valid OpenAI key'));
  assert.ok(result.classList.contains('modelmix-cred-result--ok'));
});

test('Providers OpenRouter Test hits the dedicated test-openrouter endpoint and renders a failure message', async () => {
  mockTest.results.openrouter = { success: false, message: 'Invalid OpenRouter key' };
  await renderObserver();
  openProviders();

  const row = credRow('OpenRouter');
  typeInput(row.querySelector('input'), 'bad-key');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();

  assert.deepEqual(mockTest.calls, [{ endpoint: 'openrouter', apiKey: 'bad-key' }]);
  const result = row.querySelector('.modelmix-cred-result');
  assert.ok(result.textContent.includes('Invalid OpenRouter key'));
  assert.ok(result.classList.contains('modelmix-cred-result--err'));
});

test('Providers Ollama Test hits test-ollama with the base URL and renders the real message', async () => {
  mockTest.results.ollama = { success: true, message: 'Successfully connected to Ollama' };
  await renderObserver();
  openProviders();

  typeInput(document.querySelector('input[aria-label="Ollama base URL"]'), 'http://localhost:11434');
  click(credRow('Ollama (local)').querySelector('.modelmix-cred-test'));
  await flush();

  assert.deepEqual(mockTest.calls, [{ endpoint: 'ollama', baseUrl: 'http://localhost:11434' }]);
  const result = credRow('Ollama (local)').querySelector('.modelmix-cred-result');
  assert.ok(result.textContent.includes('Successfully connected to Ollama'));
});

test('Providers Custom endpoint Test hits test-custom-endpoint with name, url, and key', async () => {
  mockTest.results.custom = { success: true, message: 'Endpoint is reachable' };
  await renderObserver();
  openProviders();

  typeInput(document.querySelector('input[aria-label="Custom endpoint name"]'), 'Together');
  typeInput(document.querySelector('input[aria-label="Custom endpoint URL"]'), 'https://api.together.xyz/v1');
  typeInput(document.querySelector('input[aria-label="Custom endpoint API key"]'), 'tk-789');
  click(credRow('Custom endpoint').querySelector('.modelmix-cred-test'));
  await flush();

  assert.deepEqual(mockTest.calls, [{ endpoint: 'custom', name: 'Together', url: 'https://api.together.xyz/v1', apiKey: 'tk-789' }]);
  const result = credRow('Custom endpoint').querySelector('.modelmix-cred-result');
  assert.ok(result.textContent.includes('Endpoint is reachable'));
});

test('Providers READ status updates to Connected after a successful save via refetch', async () => {
  mockSettings.value = {};
  await renderObserver();
  openProviders();

  const row = credRow('OpenAI');
  typeInput(row.querySelector('input'), 'sk-openai-update');
  // Simulate the server having saved the key: the refetch returns new state.
  mockSettings.value = { openai_api_key_set: true, enabled_providers: { direct: true } };
  click(row.querySelector('.modelmix-cred-save'));
  await flush();

  assert.deepEqual(mockUpdate.calls, [{ openai_api_key: 'sk-openai-update' }]);
  const statuses = [...document.querySelectorAll('.modelmix-provider-status')];
  const direct = statuses.find((s) => s.parentElement.textContent.includes('Direct API keys'));
  assert.equal(direct.getAttribute('data-connected'), 'true');
  assert.equal(direct.textContent, 'Connected');
});

test('Providers section scopes the council-settings link to OAuth providers only', async () => {
  await renderObserver();
  openProviders();

  const section = document.querySelector('.modelmix-settings-section');
  assert.ok(!section.textContent.includes('still managed in council settings'), 'OAuth copy should no longer say council-managed');
  assert.ok(!section.textContent.includes('Manage providers in council settings'));
});

test('OAuth Connect starts the device-code flow and renders the real code and verification link', async () => {
  await renderObserver();
  openProviders();

  for (const provider of ['xai-oauth', 'openai-oauth', 'github-copilot']) {
    const names = {
      'xai-oauth': 'xAI (Grok)',
      'openai-oauth': 'ChatGPT (OpenAI)',
      'github-copilot': 'GitHub Copilot',
    };
    const row = credRow(names[provider]);
    click(row.querySelector('.modelmix-cred-test'));
    await flush();
    assert.deepEqual(mockOauth.start.calls, [provider], `start called for ${provider}`);
    const pending = row.querySelector('.modelmix-oauth-pending');
    assert.ok(pending, `pending block for ${provider}`);
    assert.ok(pending.textContent.includes('CODE-1234'), `code shown for ${provider}`);
    const link = pending.querySelector('a');
    assert.equal(link.getAttribute('href'), `https://verify.example.com/device?code=CODE`);
    assert.equal(link.getAttribute('target'), '_blank');
    mockOauth.start.calls = [];
  }
});

test('OAuth Connect falls back to verification_uri when verification_uri_complete is null', async () => {
  mockOauth.start.response = (providerId) => ({
    session_id: `session-${providerId}`,
    provider_id: providerId,
    user_code: 'CODE-NULL',
    verification_uri: 'https://verify.example.com/device',
    verification_uri_complete: null,
    expires_in: 300,
    status: 'pending',
  });
  await renderObserver();
  openProviders();
  const row = credRow('ChatGPT (OpenAI)');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();
  const link = row.querySelector('a');
  assert.ok(link, 'approval link rendered');
  assert.equal(link.getAttribute('href'), 'https://verify.example.com/device');
  assert.ok(row.querySelector('.modelmix-oauth-pending').textContent.includes('CODE-NULL'));
});

test('OAuth polling transitions to connected display on status complete', async () => {
  vi.useFakeTimers();
  await renderObserver();
  openProviders();
  const row = credRow('xAI (Grok)');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();
  assert.ok(row.querySelector('.modelmix-oauth-pending'));

  mockSettings.value = { xai_oauth_connected: true, enabled_providers: { 'xai-oauth': true } };
  mockOauth.status.once = { status: 'complete', error: null };
  await act(async () => { vi.advanceTimersByTime(2500); });
  await flush();
  assert.ok(mockOauth.status.calls.length >= 1, 'status polled');
  const pending = row.querySelector('.modelmix-oauth-pending');
  assert.ok(pending === null, 'no longer awaiting once connected');
  const afterComplete = mockOauth.status.calls.length;
  await act(async () => { vi.advanceTimersByTime(2500 * 3); });
  await flush();
  assert.equal(mockOauth.status.calls.length, afterComplete, 'no further polling after complete');
  vi.useRealTimers();
});

test('OAuth polling stops and shows the real error message on status error', async () => {
  vi.useFakeTimers();
  await renderObserver();
  openProviders();
  const row = credRow('xAI (Grok)');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();

  mockOauth.status.once = { status: 'error', error: 'approval denied by user' };
  await act(async () => { vi.advanceTimersByTime(2500); });
  await flush();
  const result = row.querySelector('.modelmix-cred-result');
  assert.ok(result, 'error result rendered');
  assert.ok(result.textContent.includes('approval denied by user'));
  const afterError = mockOauth.status.calls.length;
  await act(async () => { vi.advanceTimersByTime(2500 * 3); });
  await flush();
  assert.equal(mockOauth.status.calls.length, afterError, 'no further polling after error');
  vi.useRealTimers();
});

test('OAuth polling stops and shows expired message on status expired', async () => {
  vi.useFakeTimers();
  await renderObserver();
  openProviders();
  const row = credRow('xAI (Grok)');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();

  mockOauth.status.once = { status: 'expired', error: null };
  await act(async () => { vi.advanceTimersByTime(2500); });
  await flush();
  const result = row.querySelector('.modelmix-cred-result');
  assert.ok(result && result.textContent.includes('expired'));
  vi.useRealTimers();
});

test('Closing settings during a poll clears the active interval (no leak)', async () => {
  vi.useFakeTimers();
  await renderObserver();
  openProviders();
  const row = credRow('xAI (Grok)');
  click(row.querySelector('.modelmix-cred-test'));
  await flush();

  const before = mockOauth.status.calls.length;
  assert.ok(before >= 1, 'poll started');
  // Close the settings dialog -> the ProvidersSection unmounts mid-poll.
  click(document.querySelector('.modelmix-settings-close'));
  await flush();
  await act(async () => { vi.advanceTimersByTime(2500 * 3); });
  await flush();
  assert.equal(mockOauth.status.calls.length, before, 'no polling after unmount');
  vi.useRealTimers();
});

test('OAuth Disconnect calls the DELETE route and updates connected status afterward', async () => {
  mockSettings.value = { xai_oauth_connected: true, enabled_providers: { 'xai-oauth': true } };
  await renderObserver();
  openProviders();

  const row = credRow('xAI (Grok)');
  click(row.querySelector('.modelmix-cred-save')); // Disconnect
  mockSettings.value = {};
  await flush();
  assert.deepEqual(mockOauth.disconnect.calls, ['xai-oauth']);
  const button = row.querySelector('.modelmix-cred-test');
  assert.ok(button && button.textContent === 'Connect', 'shows Connect after disconnect');
});