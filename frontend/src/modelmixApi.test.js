// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { afterEach, beforeEach, test, vi } from 'vitest';
import { deleteModelMixSession, listModelMixSessions, updateSettings, testProvider, testOpenrouter, testOpencode, testOllama, testCustomEndpoint, startOAuthConnection, getOAuthConnectionStatus, disconnectOAuthProvider } from './modelmixApi';

let fetchCalls = [];

beforeEach(() => {
  fetchCalls = [];
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(ok, status, body) {
  const response = {
    ok,
    status,
    json: async () => body,
  };
  vi.stubGlobal('fetch', async (url, options) => {
    fetchCalls.push({ url, options });
    return response;
  });
  return response;
}

test('listModelMixSessions GETs the sessions endpoint and returns the parsed summaries', async () => {
  const summaries = [
    { session_id: 's1', created_at: 1, updated_at: 2, message_count: 3 },
  ];
  const response = stubFetch(true, 200, summaries);

  const result = await listModelMixSessions();

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/modelmix/sessions'));
  assert.equal(fetchCalls[0].options.method, undefined);
  assert.equal(result, summaries);
  assert.equal(await response.json(), summaries);
});

test('deleteModelMixSession DELETEs the encoded session id and returns the response', async () => {
  const response = stubFetch(true, 204, null);

  const result = await deleteModelMixSession('session abc');

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/modelmix/sessions/session%20abc'));
  assert.equal(fetchCalls[0].options.method, 'DELETE');
  assert.equal(result, response);
});

test('deleteModelMixSession surfaces a 409 with the backend detail message', async () => {
  vi.stubGlobal('fetch', async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: 'Session has an active run (run-1); cancel it first' }),
  }));

    await assert.rejects(
      deleteModelMixSession('busy-session'),
      (err) => err.status === 409 && err.message === 'Session has an active run (run-1); cancel it first',
    );
});

test('updateSettings sends a PUT with only the provided fields', async () => {
  stubFetch(true, 200, {});

  await updateSettings({ openai_api_key: 'sk-test' });

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/settings'));
  assert.equal(fetchCalls[0].options.method, 'PUT');
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { openai_api_key: 'sk-test' });
});

test('updateSettings sends partial merge for ollama base URL only', async () => {
  stubFetch(true, 200, {});

  await updateSettings({ ollama_base_url: 'http://localhost:11434' });

  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { ollama_base_url: 'http://localhost:11434' });
});

test('updateSettings sends custom endpoint fields without api_key when omitted', async () => {
  stubFetch(true, 200, {});

  await updateSettings({ custom_endpoint_name: 'My Server', custom_endpoint_url: 'http://localhost:1234' });

  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), {
    custom_endpoint_name: 'My Server',
    custom_endpoint_url: 'http://localhost:1234',
  });
});

test('testProvider POSTs to test-provider with provider_id and optional api_key', async () => {
  stubFetch(true, 200, { success: true, message: 'Key is valid' });

  const result = await testProvider('openai', 'sk-abc');

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/settings/test-provider'));
  assert.equal(fetchCalls[0].options.method, 'POST');
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { provider_id: 'openai', api_key: 'sk-abc' });
  assert.deepEqual(result, { success: true, message: 'Key is valid' });
});

test('testProvider omits api_key when not provided, relying on server-side stored key', async () => {
  stubFetch(true, 200, { success: true });

  await testProvider('anthropic');

  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { provider_id: 'anthropic' });
});

test('testOpenrouter POSTs to test-openrouter with api_key', async () => {
  stubFetch(true, 200, { success: true, message: 'Valid key' });

  const result = await testOpenrouter('sk-or-key');

  assert.ok(fetchCalls[0].url.endsWith('/api/settings/test-openrouter'));
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { api_key: 'sk-or-key' });
  assert.deepEqual(result, { success: true, message: 'Valid key' });
});

test('testOpenrouter omits api_key when not provided', async () => {
  stubFetch(true, 200, { success: false, message: 'No key' });

  await testOpenrouter();

  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), {});
});

test('testOpencode POSTs to test-opencode with api_key', async () => {
  stubFetch(true, 200, { success: true });

  await testOpencode('oc-key');

  assert.ok(fetchCalls[0].url.endsWith('/api/settings/test-opencode'));
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { api_key: 'oc-key' });
});

test('testOllama POSTs to test-ollama with base_url', async () => {
  stubFetch(true, 200, { success: true, message: 'Connected' });

  const result = await testOllama('http://localhost:11434');

  assert.ok(fetchCalls[0].url.endsWith('/api/settings/test-ollama'));
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), { base_url: 'http://localhost:11434' });
  assert.deepEqual(result, { success: true, message: 'Connected' });
});

test('testCustomEndpoint POSTs to test-custom-endpoint with name, url, and optional api_key', async () => {
  stubFetch(true, 200, { success: true, message: 'Endpoint is reachable' });

  const result = await testCustomEndpoint('Together', 'https://api.together.xyz/v1', 'tk-123');

  assert.ok(fetchCalls[0].url.endsWith('/api/settings/test-custom-endpoint'));
  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), {
    name: 'Together',
    url: 'https://api.together.xyz/v1',
    api_key: 'tk-123',
  });
  assert.deepEqual(result, { success: true, message: 'Endpoint is reachable' });
});

test('testCustomEndpoint omits api_key when not provided (local servers)', async () => {
  stubFetch(true, 200, { success: true });

  await testCustomEndpoint('vLLM', 'http://localhost:8000');

  assert.deepEqual(JSON.parse(fetchCalls[0].options.body), {
    name: 'vLLM',
    url: 'http://localhost:8000',
  });
});

test('startOAuthConnection POSTs the start route and returns the session', async () => {
  const session = {
    session_id: 's1', provider_id: 'xai-oauth', user_code: 'CODE',
    verification_uri: 'https://verify', verification_uri_complete: null, expires_in: 300, status: 'pending',
  };
  stubFetch(true, 200, session);

  const result = await startOAuthConnection('xai-oauth');

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/oauth/xai-oauth/start'));
  assert.equal(fetchCalls[0].options.method, 'POST');
  assert.deepEqual(result, session);
});

test('startOAuthConnection encodes the provider id in the URL', async () => {
  stubFetch(true, 200, {});
  await startOAuthConnection('openai-oauth');
  assert.ok(fetchCalls[0].url.includes('/api/oauth/openai-oauth/start'));
});

test('getOAuthConnectionStatus GETs the status route with the encoded session id', async () => {
  const status = { status: 'pending', error: null, provider_id: 'xai-oauth', session_id: 's1' };
  stubFetch(true, 200, status);

  const result = await getOAuthConnectionStatus('xai-oauth', 's1');

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/oauth/xai-oauth/status?session_id=s1'));
  assert.equal(result, status);
});

test('getOAuthConnectionStatus encodes session id', async () => {
  stubFetch(true, 200, {});
  await getOAuthConnectionStatus('github-copilot', 'session 12');
  assert.ok(fetchCalls[0].url.includes('session_id=session%2012'));
});

test('disconnectOAuthProvider DELETEs the provider route and returns the result', async () => {
  stubFetch(true, 200, { status: 'disconnected', provider_id: 'xai-oauth' });

  const result = await disconnectOAuthProvider('xai-oauth');

  assert.equal(fetchCalls.length, 1);
  assert.ok(fetchCalls[0].url.endsWith('/api/oauth/xai-oauth'));
  assert.equal(fetchCalls[0].options.method, 'DELETE');
  assert.deepEqual(result, { status: 'disconnected', provider_id: 'xai-oauth' });
});