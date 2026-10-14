import assert from 'node:assert/strict';
import { test } from 'vitest';

import {
  cancelModelMixRun,
  consumeModelMixSSE,
  replayModelMixRun,
  startModelMixRun,
} from './modelmixApi.js';
import {
  applyModelMixEvent,
  applyReplayError,
  archiveCurrentRun,
  controlState,
  createModelMixState,
  describeUsage,
  hydrateModelMixState,
  modelSelectorsDisabled,
  startNewSession,
} from './modelmixState.js';

globalThis.window = { location: { hostname: 'localhost' } };

test('model selectors freeze for every active lifecycle state only', () => {
  for (const status of ['connecting', 'running', 'reconnecting', 'cancelling']) {
    assert.equal(modelSelectorsDisabled(status), true, status);
  }
  for (const status of ['idle', 'completed', 'partial', 'failed', 'cancelled', 'replay_gap', 'expired']) {
    assert.equal(modelSelectorsDisabled(status), false, status);
  }
});

test('durable hydration places canonical content by seat and replay remains deduplicated', () => {
  const document = {
    schema_version: 1,
    session: {
      session_id: 'session-1',
      runs: [{
        run_id: 'run-1', latest_seq: 8, status: 'partial',
        prompt: 'Persisted question',
        models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
      }],
      messages: [
        { run_id: 'run-1', seat: 'worker_a', content: 'A', status: 'completed' },
        { run_id: 'run-1', seat: 'moderator', content: 'M', status: 'completed' },
        { run_id: 'run-1', seat: 'worker_b', content: 'B partial', status: 'failed', error: 'stopped' },
      ],
    },
  };
  let state = hydrateModelMixState(document);
  assert.equal(state.worker_a.text, 'A');
  assert.equal(state.moderator.text, 'M');
  assert.equal(state.worker_b.text, 'B partial');
  assert.equal(state.moderator.status, 'partial');
  assert.equal(state.lastSeq, 8);
  assert.equal(state.prompt, 'Persisted question');
  state = applyModelMixEvent(state, {
    run_id: 'run-1', seq: 8, type: 'seat_delta', seat_id: 'worker_b', delta: ' duplicate',
  });
  assert.equal(state.worker_b.text, 'B partial');
});

test('seat deltas route independently and duplicate or replayed seq is ignored', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'seat_delta', seat_id: 'worker_b', delta: 'B' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'seat_delta', seat_id: 'worker_b', delta: 'B' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 3, type: 'seat_delta', seat_id: 'worker_a', delta: '2' });
  assert.equal(state.worker_a.text, 'A2');
  assert.equal(state.worker_b.text, 'B');
  assert.equal(state.moderator.text, '');
  assert.equal(state.lastSeq, 3);
});

test('late events from another run cannot contaminate hydrated state', () => {
  const state = {
    ...createModelMixState(),
    runId: 'current-run',
    lastSeq: 4,
    worker_a: { text: 'kept', status: 'completed', error: null },
  };
  const unchanged = applyModelMixEvent(state, {
    run_id: 'old-run', seq: 99, type: 'seat_delta', seat_id: 'worker_a', delta: ' leaked',
  });
  assert.equal(unchanged, state);
  assert.equal(unchanged.worker_a.text, 'kept');
});

test('Moderator waits, starts, streams once, and completes with finish reason', () => {
  let state = createModelMixState();
  assert.equal(state.moderator.status, 'waiting');
  assert.equal(state.moderator.started, false);

  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'moderator_started' });
  assert.equal(state.moderator.status, 'running');
  assert.equal(state.moderator.started, true);
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'moderator_delta', delta: 'final ' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'moderator_delta', delta: 'duplicate' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 3, type: 'moderator_delta', delta: 'answer' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 4, type: 'moderator_completed', finish_reason: 'stop',
  });
  assert.equal(state.moderator.text, 'final answer');
  assert.equal(state.moderator.status, 'completed');
  assert.equal(state.moderator.finishReason, 'stop');
  assert.equal(state.worker_a.text, '');
  assert.equal(state.worker_b.text, '');
});

test('Worker events never contaminate Moderator or peer panels', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'only A',
  });
  assert.equal(state.worker_a.text, 'only A');
  assert.equal(state.worker_b.text, '');
  assert.equal(state.moderator.text, '');
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_delta', seat_id: 'worker_b', delta: 'only B',
  });
  assert.equal(state.worker_a.text, 'only A');
  assert.equal(state.worker_b.text, 'only B');
  assert.equal(state.moderator.text, '');
});

test('Moderator failure preserves both worker transcripts', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A evidence',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_delta', seat_id: 'worker_b', delta: 'B evidence',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 3, type: 'moderator_failed', error: 'synthesis failed',
  });
  assert.equal(state.moderator.status, 'failed');
  assert.equal(state.moderator.error, 'synthesis failed');
  assert.equal(state.moderator.started, false);
  assert.equal(state.worker_a.text, 'A evidence');
  assert.equal(state.worker_b.text, 'B evidence');
});

test('Worker failure plus Moderator completion remains honestly partial', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'seat_failed', seat_id: 'worker_a', error: 'A failed',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_delta', seat_id: 'worker_b', delta: 'B evidence',
  });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 3, type: 'moderator_started' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 4, type: 'moderator_delta', delta: 'degraded answer',
  });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 5, type: 'moderator_completed' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 6, type: 'run_completed', status: 'partial',
  });
  assert.equal(state.overall, 'partial');
  assert.equal(state.worker_a.status, 'failed');
  assert.equal(state.worker_b.text, 'B evidence');
  assert.equal(state.moderator.text, 'degraded answer');
  assert.equal(state.moderator.status, 'partial');
});

test('Cancellation during Moderator is terminal and resets controls', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'moderator_started' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'run_cancel_requested' });
  assert.deepEqual(controlState(state.overall), { sendDisabled: true, stopDisabled: false });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 3, type: 'run_cancelled' });
  assert.equal(state.moderator.status, 'cancelled');
  assert.deepEqual(controlState(state.overall), { sendDisabled: false, stopDisabled: true });
});

test('Starting a new run intentionally resets all three transcripts', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'old', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'old A',
  });
  state = applyModelMixEvent(state, {
    run_id: 'old', seq: 2, type: 'moderator_delta', delta: 'old M',
  });
  state = applyModelMixEvent(state, {
    run_id: 'old', seq: 3, type: 'seat_delta', seat_id: 'worker_b', delta: 'old B',
  });
  state = createModelMixState();
  assert.equal(state.worker_a.text, '');
  assert.equal(state.moderator.text, '');
  assert.equal(state.worker_b.text, '');
  assert.equal(state.lastSeq, 0);
});

test('Moderator-phase reconnect uses the last global sequence', async () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'moderated-run', seq: 41, type: 'moderator_started' });
  state = applyModelMixEvent(state, {
    run_id: 'moderated-run', seq: 42, type: 'moderator_delta', delta: 'partial',
  });
  let requestedUrl = '';
  globalThis.fetch = async (url) => {
    requestedUrl = url;
    return new Response('', { status: 200 });
  };
  await replayModelMixRun(state.runId, state.lastSeq);
  assert.equal(
    requestedUrl,
    'http://localhost:8001/api/modelmix/runs/moderated-run/events?after_seq=42',
  );
});

test('failed seat preserves successful peer output', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_b', delta: 'kept' });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'seat_failed', seat_id: 'worker_a', error: 'broken' });
  assert.equal(state.worker_a.status, 'failed');
  assert.equal(state.worker_a.error, 'broken');
  assert.equal(state.worker_b.text, 'kept');
});

test('Send and Stop enablement follows lifecycle state', () => {
  assert.deepEqual(controlState('idle'), { sendDisabled: false, stopDisabled: true });
  assert.deepEqual(controlState('connecting'), { sendDisabled: true, stopDisabled: true });
  assert.deepEqual(controlState('running'), { sendDisabled: true, stopDisabled: false });
  assert.deepEqual(controlState('reconnecting'), { sendDisabled: true, stopDisabled: false });
  assert.deepEqual(controlState('completed'), { sendDisabled: false, stopDisabled: true });
  assert.deepEqual(controlState('cancelled'), { sendDisabled: false, stopDisabled: true });
});

test('replay request uses the run ID and last processed sequence', async () => {
  let requestedUrl = '';
  globalThis.fetch = async (url) => {
    requestedUrl = url;
    return new Response('', { status: 200 });
  };
  await replayModelMixRun('run/id', 17);
  assert.equal(requestedUrl, 'http://localhost:8001/api/modelmix/runs/run%2Fid/events?after_seq=17');
});

test('run creation sends the explicit Moderator model unchanged', async () => {
  let requestBody = null;
  globalThis.fetch = async (_url, options) => {
    requestBody = JSON.parse(options.body);
    return new Response('', { status: 200 });
  };
  await startModelMixRun({
    prompt: 'question',
    worker_a_model: 'provider:a',
    moderator_model: 'custom:moderator',
    worker_b_model: 'provider:b',
  });
  assert.equal(requestBody.moderator_model, 'custom:moderator');
});

test('Stop uses the explicit cancel endpoint', async () => {
  let request = null;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return new Response(JSON.stringify({ status: 'active' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  await cancelModelMixRun('run-1');
  assert.equal(request.url, 'http://localhost:8001/api/modelmix/runs/run-1/cancel');
  assert.equal(request.options.method, 'POST');
});

test('stream ending alone never calls the cancellation endpoint', async () => {
  let fetchCalls = 0;
  globalThis.fetch = async () => { fetchCalls += 1; };
  const response = new Response('data: {"run_id":"r","seq":1,"type":"run_started"}\n\n');
  const events = [];
  await consumeModelMixSSE(response, (event) => events.push(event));
  assert.equal(events.length, 1);
  assert.equal(fetchCalls, 0);
});

test('409 and 404 replay errors have clear recovery states', () => {
  const state = createModelMixState();
  const gap = applyReplayError(state, 409, 'events through seq 4 are no longer retained');
  const expired = applyReplayError(state, 404, 'not found');
  assert.equal(gap.overall, 'replay_gap');
  assert.match(gap.message, /Start a new run/);
  assert.equal(expired.overall, 'expired');
  assert.match(expired.message, /expired or was not found/i);
});

function persistedDocument(runCount) {
  const runs = [];
  const messages = [];
  for (let index = 0; index < runCount; index += 1) {
    const runId = `run-${index}`;
    runs.push({
      run_id: runId,
      prompt: `PROMPT_${index}`,
      models: { worker_a: `m:a${index}`, moderator: `m:m${index}`, worker_b: `m:b${index}` },
      status: 'completed',
      latest_seq: 10 + index,
    });
    messages.push(
      { run_id: runId, seat: 'worker_a', content: `A_${index}`, status: 'completed' },
      { run_id: runId, seat: 'moderator', content: `M_${index}`, status: 'completed' },
      { run_id: runId, seat: 'worker_b', content: `B_${index}`, status: 'completed' },
    );
  }
  return { schema_version: 1, session: { session_id: 'session-1', runs, messages } };
}

test('hydrating three runs archives the two prior runs in chronological order', () => {
  const state = hydrateModelMixState(persistedDocument(3));

  assert.equal(state.history.length, 2);
  assert.equal(state.history[0].runId, 'run-0');
  assert.equal(state.history[1].runId, 'run-1');
  assert.equal(state.history[0].prompt, 'PROMPT_0');
  assert.equal(state.history[1].worker_a.text, 'A_1');
  assert.equal(state.history[0].moderator.finishReason, null);
  assert.equal(state.runId, 'run-2');
  assert.equal(state.lastSeq, 12);
  assert.equal(state.overall, 'completed');
  assert.equal(state.worker_a.text, 'A_2');
  assert.equal(state.moderator.text, 'M_2');
  assert.equal(state.worker_b.text, 'B_2');
});

test('hydrating a single run leaves history empty and fills the live slots', () => {
  const state = hydrateModelMixState(persistedDocument(1));

  assert.deepEqual(state.history, []);
  assert.equal(state.sessionId, 'session-1');
  assert.equal(state.runId, 'run-0');
  assert.equal(state.lastSeq, 10);
  assert.equal(state.overall, 'completed');
  assert.equal(state.worker_a.text, 'A_0');
  assert.equal(state.moderator.text, 'M_0');
  assert.equal(state.moderator.started, true);
  assert.equal(state.worker_b.text, 'B_0');
});

test('hydrating an empty session returns the fresh initialState', () => {
  const document = { schema_version: 1, session: { session_id: 'session-1', runs: [], messages: [] } };
  assert.deepEqual(hydrateModelMixState(document), createModelMixState());
});

test('archiveCurrentRun appends the outgoing run, resets live slots, and keeps sessionId', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-9',
    runId: 'run-9',
    prompt: 'Outgoing question',
    models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
    overall: 'completed',
    lastSeq: 42,
  };
  state.worker_a = { text: 'A evidence', status: 'completed', error: null };
  state.moderator = { text: 'M synthesis', status: 'completed', error: null, started: true, finishReason: 'stop' };
  state.worker_b = { text: 'B evidence', status: 'completed', error: null };

  const archived = archiveCurrentRun(state);

  assert.equal(state.history.length, 0);
  assert.equal(archived.sessionId, 'session-9');
  assert.equal(archived.history.length, 1);
  assert.equal(archived.history[0].runId, 'run-9');
  assert.equal(archived.history[0].prompt, 'Outgoing question');
  assert.equal(archived.history[0].status, 'completed');
  assert.deepEqual(archived.history[0].worker_a, {
    text: 'A evidence',
    status: 'completed',
    error: null,
    finishReason: null,
    usage: null,
    costUsd: null,
    startedAt: null,
    completedAt: null,
  });
  assert.deepEqual(archived.history[0].moderator, {
    text: 'M synthesis',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    costUsd: null,
    startedAt: null,
    completedAt: null,
  });
  assert.deepEqual(archived.history[0].worker_b, {
    text: 'B evidence',
    status: 'completed',
    error: null,
    finishReason: null,
    usage: null,
    costUsd: null,
    startedAt: null,
    completedAt: null,
  });
  assert.equal(archived.runId, null);
  assert.equal(archived.lastSeq, 0);
  assert.equal(archived.overall, 'idle');
  assert.equal(archived.worker_a.text, '');
  assert.equal(archived.moderator.text, '');
  assert.equal(archived.moderator.started, false);
  assert.equal(archived.worker_b.text, '');
});

test('archiveCurrentRun appends nothing when the outgoing run has no seat content', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-9',
    runId: 'run-9',
    prompt: 'A question with no output',
    overall: 'failed',
    lastSeq: 3,
  };

  const archived = archiveCurrentRun(state);

  assert.equal(archived.history.length, 0);
  assert.equal(archived.sessionId, 'session-9');
  assert.equal(archived.overall, 'idle');
  assert.equal(archived.runId, null);
});

test('archived history preserves per-seat isolation with distinctive sentinels', () => {
  const document = persistedDocument(2);
  document.session.messages[0].content = 'PURE_A_CONTENT_SENTINEL';
  document.session.messages[1].content = 'PURE_M_CONTENT_SENTINEL';
  document.session.messages[2].content = 'PURE_B_CONTENT_SENTINEL';

  const state = hydrateModelMixState(document);
  const entry = state.history[0];

  assert.equal(entry.worker_a.text, 'PURE_A_CONTENT_SENTINEL');
  assert.equal(entry.worker_b.text, 'PURE_B_CONTENT_SENTINEL');
  assert.ok(!entry.worker_a.text.includes('PURE_B_CONTENT_SENTINEL'));
  assert.ok(!entry.worker_a.text.includes('PURE_M_CONTENT_SENTINEL'));
  assert.ok(!entry.worker_b.text.includes('PURE_A_CONTENT_SENTINEL'));
  assert.equal(state.worker_a.text, 'A_1');
});

test('archiveCurrentRun preserves prompt and models into the history entry', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-12',
    runId: 'run-12',
    prompt: 'Why do witnesses differ?',
    models: { worker_a: 'prov:a', moderator: 'prov:m', worker_b: 'prov:b' },
    overall: 'completed',
    lastSeq: 7,
  };
  state.worker_a = { text: 'A evidence', status: 'completed', error: null };
  state.moderator = { text: 'M synthesis', status: 'completed', error: null, started: true, finishReason: 'stop' };
  state.worker_b = { text: 'B evidence', status: 'completed', error: null };

  const archived = archiveCurrentRun(state);

  assert.equal(archived.history.length, 1);
  assert.equal(archived.history[0].runId, 'run-12');
  assert.equal(archived.history[0].prompt, 'Why do witnesses differ?');
  assert.deepEqual(archived.history[0].models, { worker_a: 'prov:a', moderator: 'prov:m', worker_b: 'prov:b' });
  assert.equal(archived.history[0].status, 'completed');
});

test('archiveCurrentRun with no prompt archives an entry whose prompt is undefined', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-12',
    runId: 'run-12',
    overall: 'completed',
  };
  state.worker_a = { text: 'A evidence', status: 'completed', error: null };

  const archived = archiveCurrentRun(state);

  assert.equal(archived.history.length, 1);
  assert.equal(archived.history[0].prompt, undefined);
});

test('startNewSession resets cockpit state while preserving model selections', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-12',
    runId: 'run-12',
    overall: 'completed',
    models: { worker_a: 'prov:a', moderator: 'prov:m', worker_b: 'prov:b' },
  };
  state.worker_a = { text: 'A evidence', status: 'completed', error: null };

  const fresh = startNewSession(state);

  assert.deepEqual(fresh, {
    ...createModelMixState(),
    models: { worker_a: 'prov:a', moderator: 'prov:m', worker_b: 'prov:b' },
  });
  assert.equal(fresh.sessionId, null);
  assert.equal(fresh.runId, null);
  assert.equal(fresh.lastSeq, 0);
  assert.equal(fresh.overall, 'idle');
  assert.deepEqual(fresh.history, []);
  assert.equal(fresh.worker_a.text, '');
  assert.equal(state.sessionId, 'session-12');
  assert.equal(state.worker_a.text, 'A evidence');
});

test('startNewSession of a default cockpit exactly equals createModelMixState', () => {
  assert.deepEqual(startNewSession(createModelMixState()), createModelMixState());
});

test('New Session gating matches the frozen-selector predicate for every lifecycle state', () => {
  for (const status of ['connecting', 'running', 'reconnecting', 'cancelling']) {
    assert.equal(modelSelectorsDisabled(status), true, `${status} must disable New Session`);
  }
  for (const status of ['idle', 'completed', 'partial', 'failed', 'cancelled', 'replay_gap', 'expired']) {
    assert.equal(modelSelectorsDisabled(status), false, `${status} must enable New Session`);
  }
});

test('seat_completed usage is stored unchanged and never clobbered by an empty event', () => {
  const usage = { total_tokens: 42, completion_tokens: 17, custom: { nested: [1, 2, 3] } };
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_completed', seat_id: 'worker_a', usage, ts: 101 });
  assert.deepEqual(state.worker_a.usage, usage);
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_completed', seat_id: 'worker_a', ts: 102,
  });
  assert.deepEqual(state.worker_a.usage, usage);
});

test('seat_completed cost_usd is stored and never clobbered by an event without it', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'seat_completed', seat_id: 'worker_a', cost_usd: 0.0045, ts: 101,
  });
  assert.equal(state.worker_a.costUsd, 0.0045);
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_completed', seat_id: 'worker_a', ts: 102,
  });
  assert.equal(state.worker_a.costUsd, 0.0045);
});

test('moderator_completed cost_usd is stored and never clobbered by an event without it', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'moderator_completed', cost_usd: 0.009, ts: 101,
  });
  assert.equal(state.moderator.costUsd, 0.009);
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'moderator_completed', ts: 102 });
  assert.equal(state.moderator.costUsd, 0.009);
});

test('seats without a reported cost keep costUsd null', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_completed', seat_id: 'worker_b', ts: 101 });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'moderator_completed', ts: 102 });
  assert.equal(state.worker_b.costUsd, null);
  assert.equal(state.moderator.costUsd, null);
});

test('startedAt and completedAt populate from event ts for both workers and moderator', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_started', seat_id: 'worker_b', ts: 101 });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'seat_completed', seat_id: 'worker_b', ts: 202 });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 3, type: 'moderator_started', ts: 303 });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 4, type: 'moderator_completed', ts: 404, finish_reason: 'stop' });
  assert.equal(state.worker_b.startedAt, 101);
  assert.equal(state.worker_b.completedAt, 202);
  assert.equal(state.moderator.startedAt, 303);
  assert.equal(state.moderator.completedAt, 404);
  assert.equal(state.worker_b.usage, null);
  assert.equal(state.moderator.usage, null);
});

test('failure and cancellation record a completedAt but never invent usage', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_failed', seat_id: 'worker_a', error: 'boom', ts: 55 });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 2, type: 'seat_cancelled', seat_id: 'worker_b', ts: 56 });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 3, type: 'moderator_failed', error: 'splat', ts: 57 });
  assert.equal(state.worker_a.completedAt, 55);
  assert.equal(state.worker_a.usage, null);
  assert.equal(state.worker_b.completedAt, 56);
  assert.equal(state.moderator.completedAt, 57);
});

test('hydration reads usage, startedAt, completedAt, and moderator finish reason off persisted messages', () => {
  const document = {
    schema_version: 1,
    session: {
      session_id: 'session-1',
      runs: [
        {
          run_id: 'run-old', latest_seq: 4, status: 'completed',
          prompt: 'Prior question',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
        {
          run_id: 'run-live', latest_seq: 4, status: 'completed',
          prompt: 'Live question',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
      ],
      messages: [
        {
          run_id: 'run-old', seat: 'worker_a', content: 'old A', status: 'completed',
          usage: { total_tokens: 7 }, started_at: 100, completed_at: 101, finish_reason: 'stop',
        },
        {
          run_id: 'run-live', seat: 'worker_a', content: 'live A', status: 'completed',
          usage: { total_tokens: 11 }, started_at: 200, completed_at: 201, finish_reason: 'stop',
        },
        {
          run_id: 'run-live', seat: 'moderator', content: 'live M', status: 'completed',
          usage: { usageMetadata: { totalTokenCount: 5 } }, started_at: 300, completed_at: 301,
          finish_reason: 'tool-calls',
        },
        {
          run_id: 'run-live', seat: 'worker_b', content: 'live B', status: 'completed',
          usage: { total_tokens: 9 }, started_at: 400, completed_at: 401,
        },
      ],
    },
  };
  const state = hydrateModelMixState(document);
  assert.deepEqual(state.worker_a.usage, { total_tokens: 11 });
  assert.equal(state.worker_a.startedAt, 200);
  assert.equal(state.worker_a.completedAt, 201);
  assert.deepEqual(state.moderator.usage, { usageMetadata: { totalTokenCount: 5 } });
  assert.equal(state.moderator.startedAt, 300);
  assert.equal(state.moderator.completedAt, 301);
  assert.equal(state.moderator.finishReason, 'tool-calls');
  assert.deepEqual(state.worker_b.usage, { total_tokens: 9 });
  assert.equal(state.worker_b.startedAt, 400);
  assert.equal(state.worker_b.completedAt, 401);

  const entry = state.history[0];
  assert.deepEqual(entry.worker_a.usage, { total_tokens: 7 });
  assert.equal(entry.worker_a.startedAt, 100);
  assert.equal(entry.worker_a.completedAt, 101);
});

test('hydration reads cost_usd off persisted messages and leaves absence null', () => {
  const document = {
    schema_version: 1,
    session: {
      session_id: 'session-1',
      runs: [
        {
          run_id: 'run-live', latest_seq: 4, status: 'completed',
          prompt: 'Live question',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
      ],
      messages: [
        {
          run_id: 'run-live', seat: 'worker_a', content: 'A', status: 'completed',
          usage: { prompt_tokens: 1000, completion_tokens: 500 }, started_at: 200, completed_at: 201,
          finish_reason: 'stop', cost_usd: 0.0045,
        },
        {
          run_id: 'run-live', seat: 'moderator', content: 'M', status: 'completed',
          usage: { total_tokens: 5 }, started_at: 300, completed_at: 301,
          finish_reason: 'stop', cost_usd: 0.009,
        },
        {
          run_id: 'run-live', seat: 'worker_b', content: 'B', status: 'completed',
          usage: { total_tokens: 9 }, started_at: 400, completed_at: 401,
        },
      ],
    },
  };
  const state = hydrateModelMixState(document);
  assert.equal(state.worker_a.costUsd, 0.0045);
  assert.equal(state.moderator.costUsd, 0.009);
  assert.equal(state.worker_b.costUsd, null);
});

test('archiveCurrentRun carries costUsd into the history entry', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-9',
    runId: 'run-9',
    prompt: 'Outgoing question',
    models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
    overall: 'completed',
    lastSeq: 42,
  };
  state.worker_a = {
    text: 'A evidence', status: 'completed', error: null, costUsd: 0.0045,
    usage: { total_tokens: 3 }, startedAt: 10, completedAt: 11,
  };
  state.worker_b = {
    text: 'B evidence', status: 'failed', error: 'stopped',
    usage: null, startedAt: 14, completedAt: 15,
  };

  const archived = archiveCurrentRun(state);
  assert.equal(archived.history[0].worker_a.costUsd, 0.0045);
  assert.equal(archived.history[0].moderator.costUsd, null);
  assert.equal(archived.history[0].worker_b.costUsd, null);
});

test('archiveCurrentRun carries usage, startedAt, and completedAt into the history entry', () => {
  const state = {
    ...createModelMixState(),
    sessionId: 'session-9',
    runId: 'run-9',
    prompt: 'Outgoing question',
    models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
    overall: 'completed',
    lastSeq: 42,
  };
  state.worker_a = {
    text: 'A evidence', status: 'completed', error: null,
    usage: { total_tokens: 3 }, startedAt: 10, completedAt: 11,
  };
  state.moderator = {
    text: 'M synthesis', status: 'completed', error: null, started: true, finishReason: 'stop',
    usage: { total_tokens: 4 }, costUsd: null, startedAt: 12, completedAt: 13,
  };
  state.worker_b = {
    text: 'B evidence', status: 'failed', error: 'stopped',
    usage: null, startedAt: 14, completedAt: 15,
  };

  const archived = archiveCurrentRun(state);
  assert.deepEqual(archived.history[0].worker_a, {
    text: 'A evidence', status: 'completed', error: null, finishReason: null, usage: { total_tokens: 3 }, costUsd: null, startedAt: 10, completedAt: 11,
  });
  assert.deepEqual(archived.history[0].moderator, {
    text: 'M synthesis', status: 'completed', error: null, finishReason: 'stop',
    usage: { total_tokens: 4 }, costUsd: null, startedAt: 12, completedAt: 13,
  });
  assert.deepEqual(archived.history[0].worker_b, {
    text: 'B evidence', status: 'failed', error: 'stopped', finishReason: null, usage: null, costUsd: null, startedAt: 14, completedAt: 15,
  });
});

test('describeUsage returns authoritative only for a non-null object', () => {
  assert.equal(describeUsage({ total_tokens: 5 }), 'authoritative');
  assert.equal(describeUsage(null), 'unavailable');
  assert.equal(describeUsage(undefined), 'unavailable');
});

test('worker seats start with a null finishReason plus full moderator parity on completion', () => {
  const initial = createModelMixState();
  assert.equal(initial.worker_a.finishReason, null);
  assert.equal(initial.worker_b.finishReason, null);

  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_completed', seat_id: 'worker_a', finish_reason: 'stop',
    usage: { total_tokens: 5 }, ts: 202,
  });
  assert.equal(state.worker_a.finishReason, 'stop');
  assert.equal(state.worker_a.usage.total_tokens, 5);
  assert.equal(state.worker_a.completedAt, 202);
  assert.equal(state.worker_b.finishReason, null);
});

test('worker seat_completed captures the ModelMix-owned modelmix_output_cap finish reason', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_b', delta: 'long output',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_completed', seat_id: 'worker_b', finish_reason: 'modelmix_output_cap',
  });
  assert.equal(state.worker_b.finishReason, 'modelmix_output_cap');
  assert.equal(state.worker_b.status, 'completed');
});

test('seat_output_warning updates only its own seat and never the peers or moderator', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_output_warning', seat_id: 'worker_a', chars: 22451, threshold: 20000,
  });
  assert.deepEqual(state.worker_a.outputWarning, { chars: 22451, threshold: 20000 });
  assert.equal(state.worker_b.outputWarning, undefined);
  assert.equal(state.moderator.outputWarning, undefined);
});

test('moderator_output_warning updates only the moderator seat', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'moderator_started' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'moderator_output_warning', chars: 30000, threshold: 20000,
  });
  assert.deepEqual(state.moderator.outputWarning, { chars: 30000, threshold: 20000 });
  assert.equal(state.worker_a.outputWarning, undefined);
  assert.equal(state.worker_b.outputWarning, undefined);
});

test('outputWarning stays live-only and never leaks into archive or history entries', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_output_warning', seat_id: 'worker_a', chars: 22451, threshold: 20000,
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 3, type: 'seat_completed', seat_id: 'worker_a', finish_reason: 'modelmix_output_cap',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 4, type: 'moderator_delta', delta: 'M',
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 5, type: 'moderator_output_warning', chars: 22000, threshold: 20000,
  });
  assert.deepEqual(state.worker_a.outputWarning, { chars: 22451, threshold: 20000 });
  assert.deepEqual(state.moderator.outputWarning, { chars: 22000, threshold: 20000 });

  const archived = archiveCurrentRun({
    ...state,
    prompt: 'question',
    models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
  });
  assert.equal('outputWarning' in archived.history[0].worker_a, false);
  assert.equal('outputWarning' in archived.history[0].moderator, false);
  assert.equal('outputWarning' in archived.worker_a, false);
});

test('hydration reads worker finish reasons but never invents outputWarning on live seats or history', () => {
  const document = {
    schema_version: 1,
    session: {
      session_id: 'session-1',
      runs: [
        {
          run_id: 'run-old', latest_seq: 4, status: 'completed', prompt: 'Prior',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
        {
          run_id: 'run-live', latest_seq: 4, status: 'completed', prompt: 'Live',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
      ],
      messages: [
        {
          run_id: 'run-old', seat: 'worker_a', content: 'old A', status: 'completed',
          finish_reason: 'modelmix_output_cap',
        },
        {
          run_id: 'run-live', seat: 'worker_a', content: 'live A', status: 'completed',
          finish_reason: 'stop',
        },
        {
          run_id: 'run-live', seat: 'moderator', content: 'live M', status: 'completed',
          finish_reason: 'tool-calls',
        },
      ],
    },
  };
  const state = hydrateModelMixState(document);
  assert.equal(state.worker_a.finishReason, 'stop');
  assert.equal(state.worker_b.finishReason, null);
  assert.equal(state.moderator.finishReason, 'tool-calls');
  assert.equal(state.history[0].worker_a.finishReason, 'modelmix_output_cap');
  assert.equal(state.history[0].moderator.finishReason, null);
  assert.equal('outputWarning' in state.worker_a, false);
  assert.equal('outputWarning' in state.history[0].worker_a, false);
});

test('moderator finishReason behavior is unchanged by worker parity work', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'moderator_started' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'moderator_completed', finish_reason: 'stop', usage: { total_tokens: 7 },
  });
  assert.equal(state.moderator.finishReason, 'stop');
  assert.equal(state.moderator.status, 'completed');
  assert.equal(state.worker_a.finishReason, null);
  assert.equal(state.worker_b.finishReason, null);
  assert.equal(state.worker_a.text, '');
});

test('a worker seat that crosses the warning and completes normally keeps the truthful warning alongside finish', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_output_warning', seat_id: 'worker_a', chars: 22451, threshold: 20000,
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 3, type: 'seat_completed', seat_id: 'worker_a', finish_reason: 'stop',
  });
  assert.equal(state.worker_a.finishReason, 'stop');
  assert.deepEqual(state.worker_a.outputWarning, { chars: 22451, threshold: 20000 });
});

test('seat_cost_warning updates only its own seat and never the peers or moderator', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_cost_warning', seat_id: 'worker_a', cost_usd: 0.25, threshold: 0.1,
  });
  assert.deepEqual(state.worker_a.costWarning, { cost_usd: 0.25, threshold: 0.1 });
  assert.equal(state.worker_b.costWarning, undefined);
  assert.equal(state.moderator.costWarning, undefined);
});

test('moderator_cost_warning updates only the moderator seat', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'moderator_started' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'moderator_cost_warning', cost_usd: 0.4, threshold: 0.1,
  });
  assert.deepEqual(state.moderator.costWarning, { cost_usd: 0.4, threshold: 0.1 });
  assert.equal(state.worker_a.costWarning, undefined);
  assert.equal(state.worker_b.costWarning, undefined);
});

test('costWarning stays live-only and never leaks into archive or history entries', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_cost_warning', seat_id: 'worker_a', cost_usd: 0.25, threshold: 0.1,
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 3, type: 'seat_completed', seat_id: 'worker_a', finish_reason: 'stop',
  });
  state = applyModelMixEvent(state, { run_id: 'run', seq: 4, type: 'moderator_delta', delta: 'M' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 5, type: 'moderator_cost_warning', cost_usd: 0.4, threshold: 0.1,
  });
  assert.deepEqual(state.worker_a.costWarning, { cost_usd: 0.25, threshold: 0.1 });
  assert.deepEqual(state.moderator.costWarning, { cost_usd: 0.4, threshold: 0.1 });

  const archived = archiveCurrentRun({
    ...state,
    prompt: 'question',
    models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
  });
  assert.equal('costWarning' in archived.history[0].worker_a, false);
  assert.equal('costWarning' in archived.history[0].moderator, false);
  assert.equal('costWarning' in archived.worker_a, false);
});

test('hydration never invents costWarning on live seats or history entries', () => {
  const document = {
    schema_version: 1,
    session: {
      session_id: 'session-1',
      runs: [
        {
          run_id: 'run-old', latest_seq: 4, status: 'completed', prompt: 'Prior',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
        {
          run_id: 'run-live', latest_seq: 4, status: 'completed', prompt: 'Live',
          models: { worker_a: 'p:a', moderator: 'p:m', worker_b: 'p:b' },
        },
      ],
      messages: [
        {
          run_id: 'run-old', seat: 'worker_a', content: 'old A', status: 'completed',
          finish_reason: 'stop', cost_usd: 0.25,
        },
        {
          run_id: 'run-live', seat: 'worker_a', content: 'live A', status: 'completed',
          finish_reason: 'stop', cost_usd: 0.3,
        },
      ],
    },
  };
  const state = hydrateModelMixState(document);
  assert.equal(state.worker_a.costUsd, 0.3);
  assert.equal(state.history[0].worker_a.costUsd, 0.25);
  assert.equal('costWarning' in state.worker_a, false);
  assert.equal('costWarning' in state.history[0].worker_a, false);
});

test('a seat that warns then completes normally keeps the truthful cost warning alongside finish', () => {
  let state = createModelMixState();
  state = applyModelMixEvent(state, { run_id: 'run', seq: 1, type: 'seat_delta', seat_id: 'worker_a', delta: 'A' });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 2, type: 'seat_cost_warning', seat_id: 'worker_a', cost_usd: 0.25, threshold: 0.1,
  });
  state = applyModelMixEvent(state, {
    run_id: 'run', seq: 3, type: 'seat_completed', seat_id: 'worker_a', finish_reason: 'stop', cost_usd: 0.25,
  });
  assert.equal(state.worker_a.finishReason, 'stop');
  assert.equal(state.worker_a.costUsd, 0.25);
  assert.deepEqual(state.worker_a.costWarning, { cost_usd: 0.25, threshold: 0.1 });
});
