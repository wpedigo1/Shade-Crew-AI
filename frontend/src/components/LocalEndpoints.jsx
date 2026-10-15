import { useEffect, useState } from 'react';
import { api } from '../api';
import { updateSettings } from '../modelmixApi';

export default function LocalEndpoints({ settings, onSaved }) {
  const [endpoints, setEndpoints] = useState(settings.local_endpoints || []);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { setEndpoints(settings.local_endpoints || []); }, [settings]);

  const change = (index, key, value) => {
    setEndpoints(current => current.map((endpoint, i) => i === index ? { ...endpoint, [key]: value } : endpoint));
    setResult('');
    setError('');
  };
  const save = async () => {
    setBusy(true);
    setResult('');
    setError('');
    try {
      await updateSettings({ local_endpoints: endpoints });
      await onSaved();
      const discovery = await api.getLocalEndpointModels();
      const failures = discovery.errors || [];
      setResult(`Saved. Found ${(discovery.models || []).length} local models. Reload the console to refresh seat selectors.`);
      if (failures.length) setError(failures.map(e => `${e.id}: ${e.message}`).join('; '));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Local endpoint update failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Local OpenAI-compatible endpoints" className="modelmix-local-endpoints">
      <h3>Local servers (llama.cpp / FOB)</h3>
      <p>Use the API base URL, including /v1. No Ollama or API key is required. For authenticated servers, use Custom endpoint below.</p>
      {endpoints.map((endpoint, index) => (
        <fieldset key={index} disabled={busy} className="modelmix-credential-row">
          <legend>Local server {index + 1}</legend>
          <label>Stable ID <input aria-label={`Local server ${index + 1} ID`} value={endpoint.id} onChange={e => change(index, 'id', e.target.value)} placeholder="fob-a" /></label>
          <label>Name <input aria-label={`Local server ${index + 1} name`} value={endpoint.name} onChange={e => change(index, 'name', e.target.value)} placeholder="FOB Gearhead" /></label>
          <label>API base URL <input aria-label={`Local server ${index + 1} URL`} value={endpoint.url} onChange={e => change(index, 'url', e.target.value)} placeholder="http://127.0.0.1:8080/v1" /></label>
          <label><input type="checkbox" checked={endpoint.enabled !== false} onChange={e => change(index, 'enabled', e.target.checked)} /> Enabled</label>
          <button type="button" onClick={() => setEndpoints(current => current.filter((_, i) => i !== index))}>Remove server {index + 1}</button>
        </fieldset>
      ))}
      <p>Keep IDs stable: saved seats and sessions refer to them. Removing or disabling a selected server causes an explicit failure.</p>
      <button type="button" disabled={busy || endpoints.length >= 20} onClick={() => setEndpoints(current => [...current, { id: '', name: '', url: '', enabled: true }])}>Add local server</button>
      <button type="button" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save and discover local models'}</button>
      {result && <p role="status">{result}</p>}
      {error && <p role="alert" className="modelmix-settings-error">{error}</p>}
    </section>
  );
}
