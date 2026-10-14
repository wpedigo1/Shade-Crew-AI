// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, test, vi } from 'vitest';
import LocalEndpoints from './LocalEndpoints';

const mocks = vi.hoisted(() => ({ update: vi.fn(), discover: vi.fn() }));
vi.mock('../modelmixApi', () => ({ updateSettings: (...args) => mocks.update(...args) }));
vi.mock('../api', () => ({ api: { getLocalEndpointModels: (...args) => mocks.discover(...args) } }));
let root;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { act(() => root?.unmount()); document.body.innerHTML = ''; vi.resetAllMocks(); });

function render(endpoints, onSaved = async () => {}) {
  const container = document.createElement('div'); document.body.append(container);
  root = createRoot(container);
  act(() => root.render(<LocalEndpoints settings={{ local_endpoints: endpoints }} onSaved={onSaved} />));
}
async function click(text) {
  const button = [...document.querySelectorAll('button')].find(b => b.textContent === text);
  await act(async () => button.click());
}

test('saves named endpoint list, reports per-server discovery failure and preserves other models', async () => {
  mocks.update.mockResolvedValue({});
  mocks.discover.mockResolvedValue({ models: [{ id: 'local:a:qwen' }], errors: [{ id: 'b', message: 'Connection failed' }] });
  const onSaved = vi.fn().mockResolvedValue();
  const endpoints = [{ id: 'a', name: 'FOB A', url: 'http://localhost:8080/v1', enabled: true }];
  render(endpoints, onSaved);
  await click('Save and discover local models');
  assert.deepEqual(mocks.update.mock.calls[0][0], { local_endpoints: endpoints });
  assert.equal(onSaved.mock.calls.length, 1);
  assert.ok(document.querySelector('[role="status"]').textContent.includes('Found 1 local models'));
  assert.equal(document.querySelector('[role="alert"]').textContent, 'b: Connection failed');
  assert.equal(document.querySelectorAll('input[type="password"]').length, 0);
});

test('remove last endpoint sends an empty list, and a rejected save is visible', async () => {
  mocks.update.mockRejectedValue(new Error('IDs must be unique'));
  render([{ id: 'a', name: 'FOB', url: 'http://localhost:8080/v1' }]);
  await click('Remove server 1');
  await click('Save and discover local models');
  assert.deepEqual(mocks.update.mock.calls[0][0], { local_endpoints: [] });
  assert.equal(document.querySelector('[role="alert"]').textContent, 'IDs must be unique');
  assert.equal(mocks.discover.mock.calls.length, 0);
});

test('add server exposes name, stable ID, URL and enabled control', async () => {
  render([]);
  await click('Add local server');
  assert.ok(document.querySelector('[aria-label="Local server 1 ID"]'));
  assert.ok(document.querySelector('[aria-label="Local server 1 name"]'));
  assert.ok(document.querySelector('[aria-label="Local server 1 URL"]'));
  assert.ok(document.querySelector('input[type="checkbox"]').checked);
});
