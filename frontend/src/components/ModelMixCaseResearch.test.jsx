// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, test, vi } from 'vitest';
const mock = vi.hoisted(() => ({ accept: vi.fn(), replay: vi.fn(), get: vi.fn() }));
vi.mock('../api', () => ({ api: { getSettings: async () => ({}) } }));
vi.mock('../configuredModels', () => ({ discoverConfiguredModels: async () => [] }));
vi.mock('../casesApi', () => ({ listCases: async () => [{ case_id: 'c', name: 'Pickup' }], getCase: mock.get, acceptCasePromotion: mock.accept, createCase: vi.fn(), renameCase: vi.fn(), importLegacyCase: vi.fn(), addCaseFact: vi.fn() }));
vi.mock('../modelmixApi', () => ({
  ModelMixHttpError: class ModelMixHttpError extends Error {},
  hydrateModelMixSession: async () => ({ schema_version: 1, case: { case_id: 'c', name: 'Pickup' }, session: {
    session_id: 'c', runs: [{ run_id: 'r', latest_seq: 9, status: 'completed', models: { worker_a: 'exact:a', moderator: 'exact:m', worker_b: 'exact:b' } }],
    messages: ['worker_a', 'moderator', 'worker_b'].map((seat) => ({
      run_id: 'r', seat, content: `${seat} answer`, status: 'completed', research_usage: [{ total_tokens: 4 }], research_cost_usd: 0.02,
      research: [{ tool_id: `${seat}-search`, name: 'bing_search', arguments: { query: `${seat} query` }, result: { sources: [{ title: 'Manual', url: 'https://example.org/manual' }] }, status: 'completed' }],
      ...(seat === 'moderator' ? { promotions: [{ candidate_id: 'p', subject: 'Voltage', value: '12 V', provenance: { kind: 'official_reference', reference: 'Manual' } }] } : {}),
    })),
  } }),
  replayModelMixRun: mock.replay, cancelModelMixRun: vi.fn(), consumeModelMixSSE: vi.fn(), startModelMixRun: vi.fn(),
}));
import ModelMixObserver from './ModelMixObserver';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root;
afterEach(() => { if (root) act(() => root.unmount()); document.body.innerHTML = ''; localStorage.clear(); vi.clearAllMocks(); });
test('persisted research appears in all seats and only explicit Chief acceptance mutates Case', async () => {
  mock.accept.mockResolvedValue({ case: { case_id: 'c', name: 'Pickup', accepted_promotions: [{ run_id: 'r', candidate_id: 'p' }] } });
  const node = document.createElement('div'); document.body.appendChild(node); root = createRoot(node);
  await act(async () => root.render(<ModelMixObserver />));
  assert.equal(node.querySelectorAll('.modelmix-worker').length, 3);
  for (const pane of node.querySelectorAll('.modelmix-worker')) assert.match(pane.textContent, /bing_search/);
  assert.equal(mock.accept.mock.calls.length, 0);
  const button = [...node.querySelectorAll('button')].find((item) => item.textContent === 'Accept into Case');
  assert.ok(button.closest('.modelmix-moderator'));
  await act(async () => button.click());
  assert.deepEqual(mock.accept.mock.calls[0], ['c', 'r', 'p']);
  assert.match(node.textContent, /Accepted into Case/);
  assert.equal([...node.querySelectorAll('button')].some((item) => item.textContent === 'Accept into Case'), false);
  assert.equal(mock.replay.mock.calls.length, 0);
  assert.equal(localStorage.getItem('modelmix.sessionId'), 'c');
});
