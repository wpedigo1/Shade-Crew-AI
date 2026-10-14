import assert from 'node:assert/strict';
import { test } from 'vitest';

import { buildSeatTelemetry, formatElapsed, formatTimestamp } from './seatTelemetry.js';

const pad = (value) => String(value).padStart(2, '0');
const localClock = (ts) => {
  const date = new Date(ts * 1000);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

test('formatTimestamp returns local HH:MM:SS for a finite timestamp', () => {
  assert.equal(formatTimestamp(0), localClock(0));
  assert.equal(formatTimestamp(1750000000), localClock(1750000000));
});

test('formatTimestamp returns null for missing or non-finite input', () => {
  assert.equal(formatTimestamp(null), null);
  assert.equal(formatTimestamp(undefined), null);
  assert.equal(formatTimestamp('x'), null);
  assert.equal(formatTimestamp(Number.NaN), null);
  assert.equal(formatTimestamp(Number.POSITIVE_INFINITY), null);
});

test('formatElapsed renders seconds, minutes, and hours', () => {
  assert.equal(formatElapsed(100, 112.4), '12.4s');
  assert.equal(formatElapsed(100, 160), '1m 0s');
  assert.equal(formatElapsed(100, 3760), '1h 1m');
});

test('formatElapsed returns null for missing, inverted, or zero duration', () => {
  assert.equal(formatElapsed(null, 112.4), null);
  assert.equal(formatElapsed(100, null), null);
  assert.equal(formatElapsed(100, 99), null);
  assert.equal(formatElapsed(100, 100), null);
});

test('idle seats produce no telemetry items', () => {
  const idleWorker = { text: '', status: 'idle', error: null, usage: null, startedAt: null, completedAt: null };
  const waitingModerator = {
    text: '',
    status: 'waiting',
    error: null,
    started: false,
    finishReason: null,
    usage: null,
    startedAt: null,
    completedAt: null,
  };
  assert.deepEqual(buildSeatTelemetry(idleWorker), []);
  assert.deepEqual(buildSeatTelemetry(waitingModerator), []);
});

test('a completed seat with usage shows authoritative provider-reported usage', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    usage: { prompt_tokens: 12, completion_tokens: 34, total_tokens: 46 },
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  assert.equal(items.length, 3);
  const usage = items.find((item) => item.key === 'usage');
  assert.equal(usage.label, 'Usage');
  assert.equal(usage.value, 'authoritative (provider-reported)');
  assert.equal(usage.detail, '46 tokens');
});

test('a usage object without total_tokens falls back to totalTokenCount', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    usage: { prompt_tokens: 5, totalTokenCount: 77 },
    startedAt: 100,
    completedAt: 112.4,
  };
  const usage = buildSeatTelemetry(seat).find((item) => item.key === 'usage');
  assert.equal(usage.value, 'authoritative (provider-reported)');
  assert.equal(usage.detail, '77 tokens');
});

test('a completed seat without usage shows honest unavailable', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  const usage = items.find((item) => item.key === 'usage');
  assert.equal(usage.value, 'unavailable');
  assert.equal(usage.detail, null);
});

test('elapsed timing is labeled calculated with a time range detail', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const timing = buildSeatTelemetry(seat).find((item) => item.key === 'timing');
  assert.equal(timing.label, 'Elapsed');
  assert.equal(timing.value, '12.4s (calculated)');
  assert.equal(timing.detail, `${localClock(100)} → ${localClock(112.4)}`);
});

test('a started but not completed seat shows a Started item without fabricating duration', () => {
  const seat = {
    text: 'partial',
    status: 'running',
    error: null,
    usage: null,
    startedAt: 100,
    completedAt: null,
  };
  const items = buildSeatTelemetry(seat);
  assert.equal(items.length, 3);
  const timing = items.find((item) => item.key === 'timing');
  assert.equal(timing.label, 'Started');
  assert.equal(timing.value, localClock(100));
});

test('a completed seat with only completedAt shows a Completed item', () => {
  const seat = {
    text: 'answer',
    status: 'partial',
    error: null,
    usage: null,
    startedAt: null,
    completedAt: 112.4,
  };
  const timing = buildSeatTelemetry(seat).find((item) => item.key === 'timing');
  assert.equal(timing.label, 'Completed');
  assert.equal(timing.value, localClock(112.4));
});

test('finish reason is rendered identically for every seat and passes provider values verbatim', () => {
  const seat = {
    text: 'synthesis',
    status: 'completed',
    error: null,
    started: true,
    finishReason: 'stop',
    usage: { total_tokens: 5 },
    startedAt: 100,
    completedAt: 112.4,
  };
  const modFinish = buildSeatTelemetry(seat).find((item) => item.key === 'finish');
  assert.equal(modFinish.value, 'stop');

  const workerFinish = buildSeatTelemetry({ ...seat }).find((item) => item.key === 'finish');
  assert.equal(workerFinish.label, 'Finish');
  assert.equal(workerFinish.value, 'stop');

  const otherWorkerFinish = buildSeatTelemetry({ ...seat, finishReason: 'tool-calls' }).find((item) => item.key === 'finish');
  assert.equal(otherWorkerFinish.value, 'tool-calls');
});

test('worker finish reason verbatim render applies only to values ModelMix does not own', () => {
  const seat = {
    text: 'stop',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  const finish = items.find((item) => item.key === 'finish');
  assert.equal(finish.value, 'stop');
});

test('worker finish reason modelmix_output_cap renders as readable ModelMix copy', () => {
  const seat = {
    text: 'output',
    status: 'completed',
    error: null,
    finishReason: 'modelmix_output_cap',
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const finish = buildSeatTelemetry(seat).find((item) => item.key === 'finish');
  assert.equal(finish.value, 'Output capped by ModelMix');
});

test('finish reason for a worker without a reported reason stays known-unknown', () => {
  const worker = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: null,
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const finish = buildSeatTelemetry(worker).find((item) => item.key === 'finish');
  assert.equal(finish.value, 'not reported');
});

test('a seat with a real sub-cent cost renders a Cost row that is not $0.00', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: { prompt_tokens: 1000, completion_tokens: 500 },
    costUsd: 0.0045,
    startedAt: 100,
    completedAt: 112.4,
  };
  const cost = buildSeatTelemetry(seat).find((item) => item.key === 'cost');
  assert.equal(cost.label, 'Cost');
  assert.equal(cost.value, '$0.0045');
  assert.notEqual(cost.value, '$0.00');
});

test('a seat with a cost over a cent renders standard two-decimal currency', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    costUsd: 0.125,
    startedAt: 100,
    completedAt: 112.4,
  };
  const cost = buildSeatTelemetry(seat).find((item) => item.key === 'cost');
  assert.equal(cost.value, '$0.13');
});

test('a seat without a cost renders no Cost row at all', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: { total_tokens: 5 },
    costUsd: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  assert.equal(buildSeatTelemetry(seat).find((item) => item.key === 'cost'), undefined);
});

test('a seat with the cost field absent entirely renders no Cost row', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: { total_tokens: 5 },
    startedAt: 100,
    completedAt: 112.4,
  };
  assert.equal(buildSeatTelemetry(seat).find((item) => item.key === 'cost'), undefined);
});

test('non-finite cost values never render', () => {
  for (const bad of [NaN, Infinity, '0.0045', null, undefined]) {
    const seat = {
      text: 'answer',
      status: 'completed',
      error: null,
      finishReason: 'stop',
      usage: null,
      costUsd: bad,
      startedAt: 100,
      completedAt: 112.4,
    };
    assert.equal(buildSeatTelemetry(seat).find((item) => item.key === 'cost'), undefined);
  }
});

test('moderator without a reported finish reason stays known-unknown', () => {
  const moderator = {
    text: 'synthesis',
    status: 'partial',
    error: null,
    started: true,
    finishReason: null,
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const finish = buildSeatTelemetry(moderator).find((item) => item.key === 'finish');
  assert.equal(finish.value, 'not reported');
});

test('an oversized usage object is summarized by field count, never merged', () => {
  const usage = {};
  for (let index = 0; index < 10; index += 1) usage[`field_${index}`] = index;
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    usage,
    startedAt: 100,
    completedAt: 112.4,
  };
  const usageItem = buildSeatTelemetry(seat).find((item) => item.key === 'usage');
  assert.equal(usageItem.value, 'authoritative (provider-reported)');
  assert.equal(usageItem.detail, '10 fields');
});

test('a crossed output warning renders as a plain informational footer line with formatted counts', () => {
  const seat = {
    text: 'long answer',
    status: 'running',
    error: null,
    finishReason: null,
    usage: null,
    outputWarning: { chars: 22451, threshold: 20000 },
    startedAt: 100,
    completedAt: null,
  };
  const items = buildSeatTelemetry(seat);
  const warning = items.find((item) => item.key === 'output-warning');
  assert.equal(warning.label, 'Approaching output limit');
  assert.equal(warning.value, '22,451 / 20,000 chars');
  const finish = items.find((item) => item.key === 'finish');
  assert.equal(finish.value, 'not reported');
});

test('a crossed output warning stays visible alongside a capped completion', () => {
  const seat = {
    text: 'long answer',
    status: 'completed',
    error: null,
    finishReason: 'modelmix_output_cap',
    usage: null,
    outputWarning: { chars: 22451, threshold: 20000 },
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  assert.equal(items.find((item) => item.key === 'output-warning').value, '22,451 / 20,000 chars');
  assert.equal(items.find((item) => item.key === 'finish').value, 'Output capped by ModelMix');
});

test('no output-warning line is rendered when the seat never crossed a threshold', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  assert.equal(items.some((item) => item.key === 'output-warning'), false);
});

test('a valid costWarning renders a Cost notice row with sub-cent precision (never $0.00)', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    costWarning: { cost_usd: 0.1234, threshold: 0.1 },
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  const notice = items.find((item) => item.key === 'cost-warning');
  assert.equal(notice.label, 'Cost notice');
  assert.ok(notice.value.includes('$0.12'));
  assert.ok(notice.value.includes('$0.10'));
  assert.notEqual(notice.value, '$0.00');
});

test('a sub-cent cost warning value renders with four decimals, not $0.00', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    costWarning: { cost_usd: 0.0045, threshold: 0.001 },
    startedAt: 100,
    completedAt: 112.4,
  };
  const items = buildSeatTelemetry(seat);
  const notice = items.find((item) => item.key === 'cost-warning');
  assert.ok(notice.value.includes('$0.0045'));
  assert.notEqual(notice.value, '$0.00');
});

test('a seat with no costWarning renders no Cost notice row', () => {
  const seat = {
    text: 'answer',
    status: 'completed',
    error: null,
    finishReason: 'stop',
    usage: null,
    startedAt: 100,
    completedAt: 112.4,
  };
  assert.equal(buildSeatTelemetry(seat).find((item) => item.key === 'cost-warning'), undefined);
});

test('a costWarning with non-finite or missing values renders no Cost notice row', () => {
  for (const costWarning of [
    null,
    { cost_usd: '0.25', threshold: 0.1 },
    { cost_usd: 0.25, threshold: '0.1' },
    { cost_usd: 0.25 },
    { threshold: 0.1 },
  ]) {
    const seat = {
      text: 'answer',
      status: 'completed',
      error: null,
      finishReason: 'stop',
      usage: null,
      costWarning,
      startedAt: 100,
      completedAt: 112.4,
    };
    assert.equal(buildSeatTelemetry(seat).find((item) => item.key === 'cost-warning'), undefined);
  }
});