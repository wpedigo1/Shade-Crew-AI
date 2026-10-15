// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, test, vi } from 'vitest';
const mock = vi.hoisted(() => ({ list: vi.fn(), create: vi.fn(), get: vi.fn(), rename: vi.fn(), fact: vi.fn(), import: vi.fn() }));
vi.mock('../casesApi', () => ({ listCases: mock.list, createCase: mock.create, getCase: mock.get, renameCase: mock.rename, addCaseFact: mock.fact, importLegacyCase: mock.import }));
import CasePanel from './CasePanel';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root;
afterEach(() => { if (root) act(() => root.unmount()); document.body.innerHTML = ''; vi.resetAllMocks(); });
const doc = { schema_version: 1, case: { case_id: 'c1', name: 'Truck', facts: [] }, session: { session_id: 'c1', runs: [], messages: [] } };
async function render(props = {}) {
  mock.list.mockResolvedValue([{ case_id: 'c1', name: 'Truck' }]);
  const node = document.createElement('div'); document.body.appendChild(node); root = createRoot(node);
  await act(async () => root.render(<CasePanel onSelect={() => {}} onMetadata={() => {}} {...props} />));
  return node;
}
async function input(node, label, value) {
  await act(async () => {
    const target = node.querySelector(`[aria-label="${label}"]`);
    const proto = target.tagName === 'SELECT' ? window.HTMLSelectElement.prototype : window.HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(target, value);
    target.dispatchEvent(new Event(target.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
  });
}
async function click(node, label) { await act(async () => [...node.querySelectorAll('button')].find((button) => button.textContent === label).click()); }
test('named creation and reopening select canonical documents', async () => {
  const select = vi.fn(); mock.create.mockResolvedValue(doc); mock.get.mockResolvedValue(doc);
  const node = await render({ onSelect: select });
  await input(node, 'Case name', 'Truck'); await click(node, 'New Case');
  assert.deepEqual(mock.create.mock.calls[0], ['Truck']); assert.equal(select.mock.calls[0][0], doc);
  await input(node, 'Open Case', 'c1'); assert.equal(mock.get.mock.calls[0][0], 'c1');
});
test('legacy import is explicit and preserves original identity as import input', async () => {
  mock.get.mockRejectedValue(Object.assign(new Error('legacy'), { status: 404 })); mock.import.mockResolvedValue(doc);
  const select = vi.fn(); const node = await render({ sessionId: 'legacy-id', onSelect: select });
  assert.equal(mock.import.mock.calls.length, 0);
  await click(node, 'Import legacy session as Case');
  assert.deepEqual(mock.import.mock.calls[0], ['legacy-id']); assert.equal(select.mock.calls[0][0].case.case_id, 'c1');
});
test('rename and measured facts update metadata without rehydrating live seats', async () => {
  const metadata = vi.fn(); const select = vi.fn(); mock.rename.mockResolvedValue(doc); mock.fact.mockResolvedValue(doc);
  const node = await render({ sessionId: 'c1', caseData: doc.case, onMetadata: metadata, onSelect: select });
  await input(node, 'Case name', 'Pickup'); await click(node, 'Rename Case');
  assert.deepEqual(mock.rename.mock.calls[0], ['c1', 'Pickup']);
  await input(node, 'Fact or measurement subject', 'Battery voltage'); await input(node, 'Fact or measurement value', '12.4 V');
  await input(node, 'Evidence status', 'measured'); await input(node, 'Evidence provenance', 'User DMM test'); await click(node, 'Save fact / measurement');
  assert.deepEqual(mock.fact.mock.calls[0], ['c1', { subject: 'Battery voltage', value: '12.4 V', status: 'measured', category: 'measurements', provenance: { kind: 'user_measurement', reference: 'User DMM test' } }]);
  assert.equal(select.mock.calls.length, 0); assert.equal(metadata.mock.calls.length, 2);
});
test('mutation errors remain visible and busy Cases cannot switch', async () => {
  mock.create.mockRejectedValue(new Error('disk unavailable'));
  const node = await render(); await input(node, 'Case name', 'Truck'); await click(node, 'New Case');
  assert.match(node.querySelector('[role="alert"]').textContent, /disk unavailable/);
  await act(async () => root.render(<CasePanel caseData={doc.case} sessionId="c1" busy onSelect={() => {}} onMetadata={() => {}} />));
  assert.equal(node.querySelector('[aria-label="Open Case"]').disabled, true);
});
