// @vitest-environment jsdom
import assert from 'node:assert/strict';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, test, vi } from 'vitest';
import { DEFAULT_SAVED_MODELS_KEY } from '../defaultSeatModels';

const mock = vi.hoisted(() => ({ replay: vi.fn(), ended: null }));
vi.mock('../api', () => ({ api: { getSettings: async () => ({}) } }));
vi.mock('../configuredModels', () => ({ discoverConfiguredModels: async () => [{id:'a',name:'A'}, {id:'b',name:'B'}, {id:'m',name:'M'}] }));
vi.mock('../modelmixApi', () => ({
  ModelMixHttpError: class ModelMixHttpError extends Error {},
  hydrateModelMixSession: async () => { throw new Error('no session'); },
  startModelMixRun: async () => ({headers: {get: name => name.includes('Run') ? 'run' : 'session'}}),
  consumeModelMixSSE: async (_response, handle) => {
    // Resolve after one batched delivery, before React gets a separate render turn.
    handle({run_id:'run',seq:1,type:'run_started'});
    handle({run_id:'run',seq:2,type:'moderator_delta',delta:'final'});
    handle({run_id:'run',seq:3,type:'moderator_completed'});
    handle({run_id:'run',seq:4,type:'run_completed',status:'completed'});
    mock.ended();
  },
  replayModelMixRun: (...args) => mock.replay(...args),
}));
import ModelMixObserver from './ModelMixObserver';
let root;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { act(() => root?.unmount()); window.localStorage.clear(); document.body.innerHTML=''; vi.resetAllMocks(); });

test('batched terminal event ends observation without reconnecting or disabling Send', async () => {
  window.localStorage.setItem(DEFAULT_SAVED_MODELS_KEY, JSON.stringify({worker_a:'a',worker_b:'b',moderator:'m'}));
  const container = document.createElement('div'); document.body.append(container); root=createRoot(container);
  await act(async () => root.render(<ModelMixObserver />));
  const setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
  act(() => {const textarea=document.querySelector('textarea'); setter.call(textarea,'repair'); textarea.dispatchEvent(new Event('input',{bubbles:true}));});
  const ended = new Promise(resolve => { mock.ended=resolve; });
  await act(async () => { document.querySelector('button[type="submit"]').click(); await ended; });
  assert.equal(document.querySelector('.modelmix-session-status').textContent, 'completed');
  assert.equal(document.querySelector('button[type="submit"]').disabled, false);
  assert.equal(mock.replay.mock.calls.length, 0);
});
