const getApiBase = () => window.__AI_COUNSEL_CONFIG__?.apiUrl || import.meta.env?.VITE_API_URL || `http://${window.location.hostname}:8001`;
async function request(path = '', method = 'GET', body, signal) {
  const response = await fetch(`${getApiBase()}/api/modelmix/cases${path}`, {
    method, signal,
    ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    let message = `Case request failed (${response.status})`;
    try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail : message; } catch { /* Use HTTP status. */ }
    const error = new Error(message); error.status = response.status; throw error;
  }
  return response.json();
}
const path = (id) => `/${encodeURIComponent(id)}`;
export const listCases = (signal) => request('', 'GET', undefined, signal);
export const getCase = (id, signal) => request(path(id), 'GET', undefined, signal);
export const createCase = (name) => request('', 'POST', { name });
export const renameCase = (id, name) => request(path(id), 'PATCH', { name });
export const importLegacyCase = (id) => request(`/import${path(id)}`, 'POST');
export const addCaseFact = (id, fact) => request(`${path(id)}/facts`, 'POST', fact);
export const acceptCasePromotion = (id, runId, candidateId) => request(`${path(id)}/promotions`, 'POST', { run_id: runId, candidate_id: candidateId });
