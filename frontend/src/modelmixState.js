export const createModelMixState = () => ({
  sessionId: null,
  runId: null,
  lastSeq: 0,
  overall: 'idle',
  message: 'Ready',
  history: [],
  worker_a: { text: '', status: 'idle', error: null, finishReason: null, usage: null, costUsd: null, startedAt: null, completedAt: null },
  moderator: {
    text: '',
    status: 'waiting',
    error: null,
    started: false,
    finishReason: null,
    usage: null,
    costUsd: null,
    startedAt: null,
    completedAt: null,
  },
  worker_b: { text: '', status: 'idle', error: null, finishReason: null, usage: null, costUsd: null, startedAt: null, completedAt: null },
});

const terminalOverall = new Set(['completed', 'partial', 'failed', 'cancelled', 'replay_gap', 'expired']);

export const isTerminalOverall = (status) => terminalOverall.has(status);

export function controlState(status) {
  const running = ['connecting', 'running', 'reconnecting', 'cancelling'].includes(status);
  return { sendDisabled: running, stopDisabled: status === 'connecting' || !running };
}

export function modelSelectorsDisabled(status) {
  return controlState(status).sendDisabled;
}

export function applyReplayError(state, status, message = '') {
  if (status === 409) {
    return {
      ...state,
      overall: 'replay_gap',
      message: `Replay gap: ${message}. Start a new run to recover.`,
    };
  }
  if (status === 404) {
    return { ...state, overall: 'expired', message: 'Run expired or was not found. Start a new run.' };
  }
  return { ...state, overall: 'failed', message: message || 'Connection failed' };
}

export function applyModelMixEvent(state, event) {
  if (state.runId && event?.run_id && event.run_id !== state.runId) return state;
  if (!event || !Number.isInteger(event.seq) || event.seq <= state.lastSeq) return state;
  const next = { ...state, lastSeq: event.seq, runId: event.run_id || state.runId };
  const seatId = event.seat_id;

  if (seatId === 'worker_a' || seatId === 'worker_b') {
    const seat = { ...state[seatId] };
    if (event.type === 'seat_started') {
      seat.status = 'running';
      seat.startedAt = event.ts ?? null;
    }
    if (event.type === 'seat_evidence' && event.evidence?.claim_id) {
      seat.evidence = [...(seat.evidence || []).filter((item) => item.claim_id !== event.evidence.claim_id), { ...event.evidence, updated_at: event.ts }];
    }
    if (event.type === 'seat_delta') seat.text += String(event.delta || '');
    if (event.type === 'seat_output_warning') {
      seat.outputWarning = { chars: event.chars, threshold: event.threshold };
    }
    if (event.type === 'seat_cost_warning') {
      seat.costWarning = { cost_usd: event.cost_usd, threshold: event.threshold };
    }
    if (event.type === 'seat_completed') {
      seat.status = 'completed';
      seat.finishReason = event.finish_reason || null;
      seat.usage = event.usage ?? seat.usage;
      seat.costUsd = event.cost_usd ?? seat.costUsd;
      seat.completedAt = event.ts ?? null;
    }
    if (event.type === 'seat_failed') {
      seat.status = 'failed';
      seat.error = event.error || 'Worker failed';
      seat.finishReason = event.finish_reason ?? seat.finishReason;
      seat.usage = event.usage ?? seat.usage;
      seat.costUsd = event.cost_usd ?? seat.costUsd;
      seat.completedAt = event.ts ?? null;
    }
    if (event.type === 'seat_cancelled') {
      seat.status = 'cancelled';
      seat.completedAt = event.ts ?? null;
    }
    next[seatId] = seat;
  }

  if (event.type?.startsWith('moderator_')) {
    const moderator = { ...state.moderator };
    if (event.type === 'moderator_promotion_proposed' && event.candidate?.candidate_id) {
      moderator.promotions = [...(moderator.promotions || []).filter((item) => item.candidate_id !== event.candidate.candidate_id), event.candidate];
    } else if (event.type === 'moderator_evidence') {
      moderator.evidence = [...(moderator.evidence || []).filter((item) => item.claim_id !== event.evidence.claim_id), { ...event.evidence, updated_at: event.ts }];
    } else if (event.type === 'moderator_verification_started') {
      moderator.status = 'verifying';
      moderator.started = true;
    } else if (event.type === 'moderator_verification_completed') {
      moderator.status = 'running';
    } else if (event.type === 'moderator_verification_usage') {
      moderator.verificationUsage = [...(moderator.verificationUsage || []), event.usage ?? null];
      if (event.cost_usd != null) moderator.verificationCostUsd = (moderator.verificationCostUsd ?? 0) + event.cost_usd;
    } else if (event.type === 'moderator_started') {
      moderator.started = true;
      moderator.status = 'running';
      moderator.error = null;
      moderator.startedAt = event.ts ?? null;
    } else if (event.type === 'moderator_delta') {
      moderator.text += String(event.delta || '');
    } else if (event.type === 'moderator_output_warning') {
      moderator.outputWarning = { chars: event.chars, threshold: event.threshold };
    } else if (event.type === 'moderator_cost_warning') {
      moderator.costWarning = { cost_usd: event.cost_usd, threshold: event.threshold };
    } else if (event.type === 'moderator_completed') {
      moderator.started = true;
      moderator.status = 'completed';
      moderator.finishReason = event.finish_reason || null;
      moderator.usage = event.usage ?? moderator.usage;
      moderator.costUsd = event.cost_usd ?? moderator.costUsd;
      moderator.completedAt = event.ts ?? null;
    } else if (event.type === 'moderator_failed') {
      moderator.status = 'failed';
      moderator.error = event.error || 'Crew Chief failed';
      moderator.finishReason = event.finish_reason ?? moderator.finishReason;
      moderator.usage = event.usage ?? moderator.usage;
      moderator.costUsd = event.cost_usd ?? moderator.costUsd;
      moderator.completedAt = event.ts ?? null;
    }
    next.moderator = moderator;
  }

  if (['worker_a', 'moderator', 'worker_b'].includes(seatId) &&
      ['research_started', 'tool_started', 'tool_completed', 'research_usage', 'research_completed', 'research_limited'].includes(event.type)) {
    const seat = { ...next[seatId] };
    if (event.type === 'research_started') seat.researchActive = true;
    if (['research_completed', 'research_limited'].includes(event.type)) seat.researchActive = false;
    if (event.type === 'research_limited') seat.researchLimited = event.reason || event.error || 'Research limit reached';
    if (event.tool?.tool_id) {
      const previous = (seat.research || []).find((item) => item.tool_id === event.tool.tool_id);
      const tool = { ...previous, ...event.tool, model: event.model, run_id: event.run_id, updated_at: event.ts };
      seat.research = previous ? seat.research.map((item) => item.tool_id === tool.tool_id ? tool : item) : [...(seat.research || []), tool];
    }
    if (event.type === 'research_usage') {
      seat.researchUsage = [...(seat.researchUsage || []), event.usage ?? null];
      if (event.cost_usd != null) seat.researchCostUsd = (seat.researchCostUsd ?? 0) + event.cost_usd;
    }
    next[seatId] = seat;
  }

  if (event.type === 'run_started') {
    next.overall = 'running';
    next.message = 'Both workers are running';
  } else if (event.type === 'run_cancel_requested') {
    next.overall = 'cancelling';
    next.message = 'Cancellation requested';
  } else if (event.type === 'run_cancelled') {
    next.overall = 'cancelled';
    next.message = 'Run cancelled';
    for (const id of ['worker_a', 'worker_b']) {
      if (next[id].status === 'running') next[id] = { ...next[id], status: 'cancelled' };
    }
    if (next.moderator.status === 'waiting' || next.moderator.status === 'running') {
      next.moderator = { ...next.moderator, status: 'cancelled' };
    }
  } else if (event.type === 'run_failed') {
    next.overall = 'failed';
    next.message = event.error || 'Run failed';
  } else if (event.type === 'run_completed') {
    next.overall = event.status === 'partial' ? 'partial' : 'completed';
    next.message = event.status === 'partial' ? 'Run completed with a worker failure' : 'Run completed';
    if (event.status === 'partial' && next.moderator.status === 'completed') {
      next.moderator = { ...next.moderator, status: 'partial' };
    }
  }
  if (['run_cancelled', 'run_failed', 'run_completed'].includes(event.type)) {
    for (const id of ['worker_a', 'moderator', 'worker_b']) {
      if (next[id].researchActive) next[id] = { ...next[id], researchActive: false };
    }
  }
  if (['run_cancelled', 'run_failed'].includes(event.type) && next.moderator.status === 'verifying') {
    next.moderator = { ...next.moderator, status: event.type === 'run_cancelled' ? 'cancelled' : 'failed' };
  }
  return next;
}

export function describeUsage(usage) {
  return usage !== null && typeof usage === 'object' ? 'authoritative' : 'unavailable';
}

function researchMetadata(message) {
  return {
    ...(message.research ? { research: message.research } : {}),
    ...(message.research_usage ? { researchUsage: message.research_usage } : {}),
    ...(message.research_cost_usd != null ? { researchCostUsd: message.research_cost_usd } : {}),
    ...(message.research_active != null ? { researchActive: message.research_active } : {}),
    ...(message.promotions ? { promotions: message.promotions } : {}),
  };
}

function buildHistoryEntry(run, messages) {
  const entry = {
    runId: run.run_id,
    prompt: run.prompt,
    models: run.models,
    status: run.status,
    worker_a: { text: '', status: 'idle', error: null, finishReason: null, usage: null, costUsd: null, startedAt: null, completedAt: null },
    moderator: {
      text: '',
      status: 'waiting',
      error: null,
      finishReason: null,
      usage: null,
      costUsd: null,
      startedAt: null,
      completedAt: null,
    },
    worker_b: { text: '', status: 'idle', error: null, finishReason: null, usage: null, costUsd: null, startedAt: null, completedAt: null },
  };
  for (const message of messages) {
    if (message.run_id !== run.run_id || !['worker_a', 'worker_b', 'moderator'].includes(message.seat)) continue;
    entry[message.seat] = {
      ...entry[message.seat],
      ...researchMetadata(message),
      ...(message.research_active != null && isTerminalOverall(run.status) ? { researchActive: false } : {}),
      ...(message.evidence ? { evidence: message.evidence } : {}),
      ...(message.verification_usage ? { verificationUsage: message.verification_usage } : {}),
      ...(message.verification_cost_usd != null ? { verificationCostUsd: message.verification_cost_usd } : {}),
      text: String(message.content || ''),
      status: message.status || entry[message.seat].status,
      error: message.error || null,
      finishReason: message.finish_reason || null,
      usage: message.usage ?? null,
      costUsd: message.cost_usd ?? null,
      startedAt: message.started_at ?? null,
      completedAt: message.completed_at ?? null,
    };
  }
  return entry;
}

export function archiveCurrentRun(state) {
  const outgoing = {
    runId: state.runId,
    prompt: state.prompt,
    models: state.models,
    status: state.overall,
    worker_a: {
      ...researchMetadata({ research: state.worker_a.research, research_usage: state.worker_a.researchUsage, research_cost_usd: state.worker_a.researchCostUsd, promotions: state.worker_a.promotions }),
      ...(state.worker_a.evidence ? { evidence: state.worker_a.evidence } : {}),
      text: state.worker_a.text,
      status: state.worker_a.status,
      error: state.worker_a.error,
      finishReason: state.worker_a.finishReason ?? null,
      usage: state.worker_a.usage ?? null,
      costUsd: state.worker_a.costUsd ?? null,
      startedAt: state.worker_a.startedAt ?? null,
      completedAt: state.worker_a.completedAt ?? null,
    },
    moderator: {
      ...researchMetadata({ research: state.moderator.research, research_usage: state.moderator.researchUsage, research_cost_usd: state.moderator.researchCostUsd, promotions: state.moderator.promotions }),
      ...(state.moderator.evidence ? { evidence: state.moderator.evidence } : {}),
      ...(state.moderator.verificationUsage ? { verificationUsage: state.moderator.verificationUsage } : {}),
      ...(state.moderator.verificationCostUsd != null ? { verificationCostUsd: state.moderator.verificationCostUsd } : {}),
      text: state.moderator.text,
      status: state.moderator.status,
      error: state.moderator.error,
      finishReason: state.moderator.finishReason ?? null,
      usage: state.moderator.usage ?? null,
      costUsd: state.moderator.costUsd ?? null,
      startedAt: state.moderator.startedAt ?? null,
      completedAt: state.moderator.completedAt ?? null,
    },
    worker_b: {
      ...researchMetadata({ research: state.worker_b.research, research_usage: state.worker_b.researchUsage, research_cost_usd: state.worker_b.researchCostUsd, promotions: state.worker_b.promotions }),
      ...(state.worker_b.evidence ? { evidence: state.worker_b.evidence } : {}),
      text: state.worker_b.text,
      status: state.worker_b.status,
      error: state.worker_b.error,
      finishReason: state.worker_b.finishReason ?? null,
      usage: state.worker_b.usage ?? null,
      costUsd: state.worker_b.costUsd ?? null,
      startedAt: state.worker_b.startedAt ?? null,
      completedAt: state.worker_b.completedAt ?? null,
    },
  };
  const hasSeatContent = [outgoing.worker_a, outgoing.moderator, outgoing.worker_b].some((seat) => Boolean(seat.text || seat.research?.length || seat.promotions?.length || seat.evidence?.length));
  const history = hasSeatContent ? [...state.history, outgoing] : [...state.history];
  return {
    ...createModelMixState(),
    sessionId: state.sessionId,
    ...(state.case ? { case: state.case } : {}),
    history,
  };
}

export function startNewSession(state) {
  return {
    ...createModelMixState(),
    ...(state.models ? { models: { ...state.models } } : {}),
  };
}

export function hydrateModelMixState(document) {
  if (document?.schema_version !== 1 || !document.session || !Array.isArray(document.session.runs)) {
    throw new Error('Unsupported or malformed ModelMix session');
  }
  const run = document.session.runs.at(-1);
  if (!run) return { ...createModelMixState(), sessionId: document.session.session_id, ...(document.case ? { case: document.case } : {}) };
  const state = {
    ...createModelMixState(),
    runId: run.run_id,
    sessionId: document.session.session_id,
    ...(document.case ? { case: document.case } : {}),
    lastSeq: run.latest_seq,
    overall: run.status === 'active' ? 'running' : run.status,
    message: `Restored ${run.status} run`,
    models: run.models,
    prompt: run.prompt,
    history: document.session.runs
      .slice(0, -1)
      .map((priorRun) => buildHistoryEntry(priorRun, document.session.messages || [])),
  };
  for (const message of document.session.messages || []) {
    if (message.run_id !== run.run_id || !['worker_a', 'worker_b', 'moderator'].includes(message.seat)) continue;
    state[message.seat] = {
      ...state[message.seat],
      ...researchMetadata(message),
      ...(message.research_active != null && isTerminalOverall(run.status) ? { researchActive: false } : {}),
      ...(message.evidence ? { evidence: message.evidence } : {}),
      ...(message.verification_usage ? { verificationUsage: message.verification_usage } : {}),
      ...(message.verification_cost_usd != null ? { verificationCostUsd: message.verification_cost_usd } : {}),
      text: String(message.content || ''),
      status: message.verification_active && !isTerminalOverall(run.status) ? 'verifying' : message.status || state[message.seat].status,
      error: message.error || null,
      finishReason: message.finish_reason || null,
      usage: message.usage ?? null,
      costUsd: message.cost_usd ?? null,
      startedAt: message.started_at ?? null,
      completedAt: message.completed_at ?? null,
    };
    if (message.seat === 'moderator') {
      state.moderator.started = message.status !== 'waiting';
    }
  }
  if (run.status === 'partial' && state.moderator.status === 'completed') state.moderator.status = 'partial';
  return state;
}
