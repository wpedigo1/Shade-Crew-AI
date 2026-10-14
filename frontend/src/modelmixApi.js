const getApiBase = () => {
  if (window.__AI_COUNSEL_CONFIG__?.apiUrl) return window.__AI_COUNSEL_CONFIG__.apiUrl;
  if (import.meta.env?.VITE_API_URL) return import.meta.env.VITE_API_URL;
  return `http://${window.location.hostname}:8001`;
};

export class ModelMixHttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function checkedFetch(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `ModelMix request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Keep the status-based message for a non-JSON error response.
    }
    throw new ModelMixHttpError(response.status, message);
  }
  return response;
}

export function startModelMixRun(payload, signal) {
  return checkedFetch(`${getApiBase()}/api/modelmix/runs/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });
}

export async function hydrateModelMixSession(sessionId, signal) {
  const path = sessionId
    ? `/api/modelmix/sessions/${encodeURIComponent(sessionId)}`
    : '/api/modelmix/sessions/latest';
  const response = await checkedFetch(`${getApiBase()}${path}`, { signal });
  return response.json();
}

export function replayModelMixRun(runId, afterSeq, signal) {
  return checkedFetch(
    `${getApiBase()}/api/modelmix/runs/${encodeURIComponent(runId)}/events?after_seq=${afterSeq}`,
    { signal },
  );
}

export async function cancelModelMixRun(runId) {
  const response = await checkedFetch(
    `${getApiBase()}/api/modelmix/runs/${encodeURIComponent(runId)}/cancel`,
    { method: 'POST' },
  );
  return response.json();
}

export async function listModelMixSessions(signal) {
  const response = await checkedFetch(`${getApiBase()}/api/modelmix/sessions`, { signal });
  return response.json();
}

export async function deleteModelMixSession(sessionId) {
  return checkedFetch(
    `${getApiBase()}/api/modelmix/sessions/${encodeURIComponent(sessionId)}`,
    { method: 'DELETE' },
  );
}

export async function updateSettings(body) {
  const response = await checkedFetch(`${getApiBase()}/api/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}

export async function testProvider(providerId, apiKey) {
  const response = await checkedFetch(`${getApiBase()}/api/settings/test-provider`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider_id: providerId, api_key: apiKey || undefined }),
  });
  return response.json();
}

export async function testOpenrouter(apiKey) {
  const response = await checkedFetch(`${getApiBase()}/api/settings/test-openrouter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey || undefined }),
  });
  return response.json();
}

export async function testOpencode(apiKey) {
  const response = await checkedFetch(`${getApiBase()}/api/settings/test-opencode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey || undefined }),
  });
  return response.json();
}

export async function testOllama(baseUrl) {
  const response = await checkedFetch(`${getApiBase()}/api/settings/test-ollama`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_url: baseUrl }),
  });
  return response.json();
}

export async function testCustomEndpoint(name, url, apiKey) {
  const response = await checkedFetch(`${getApiBase()}/api/settings/test-custom-endpoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, url, api_key: apiKey || undefined }),
  });
  return response.json();
}

export async function startOAuthConnection(providerId) {
  const response = await checkedFetch(
    `${getApiBase()}/api/oauth/${encodeURIComponent(providerId)}/start`,
    { method: 'POST' },
  );
  return response.json();
}

export async function getOAuthConnectionStatus(providerId, sessionId) {
  const response = await checkedFetch(
    `${getApiBase()}/api/oauth/${encodeURIComponent(providerId)}/status?session_id=${encodeURIComponent(sessionId)}`,
  );
  return response.json();
}

export async function disconnectOAuthProvider(providerId) {
  const response = await checkedFetch(
    `${getApiBase()}/api/oauth/${encodeURIComponent(providerId)}`,
    { method: 'DELETE' },
  );
  return response.json();
}

export async function consumeModelMixSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';
      for (const block of blocks) {
        const dataLine = block.split('\n').find((line) => line.startsWith('data: '));
        if (dataLine) onEvent(JSON.parse(dataLine.slice(6)));
      }
    }
  } finally {
    reader.releaseLock();
  }
}
