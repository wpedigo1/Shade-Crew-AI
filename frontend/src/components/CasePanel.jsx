import { useEffect, useState } from 'react';
import { addCaseFact, createCase, getCase, importLegacyCase, listCases, renameCase } from '../casesApi';

export default function CasePanel({ sessionId, caseData, onSelect, onMetadata, busy }) {
  const [cases, setCases] = useState([]);
  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [value, setValue] = useState('');
  const [status, setStatus] = useState('user_reported');
  const [reference, setReference] = useState('User entry');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    listCases(controller.signal).then(setCases).catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    if (sessionId && !caseData) getCase(sessionId, controller.signal).then(onMetadata).catch((err) => { if (!controller.signal.aborted && err.status !== 404) setError(err.message); });
    return () => controller.abort();
  }, [sessionId, caseData, onMetadata]);
  const perform = async (operation, select = true) => {
    setSaving(true); setError('');
    try {
      const doc = await operation();
      if (select) onSelect(doc); else onMetadata(doc);
      setCases(await listCases());
      setName('');
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  };
  const disabled = busy || saving;
  return <section className="modelmix-case" aria-label="Case">
    <div className="modelmix-case-row">
      <strong>{caseData?.name || (sessionId ? 'Legacy session' : 'No Case selected')}</strong>
      <select aria-label="Open Case" value={caseData?.case_id || ''} disabled={disabled} onChange={(event) => event.target.value && perform(() => getCase(event.target.value))}>
        <option value="">Open Case…</option>
        {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.name}</option>)}
      </select>
      <input aria-label="Case name" placeholder="Case name" value={name} onChange={(event) => setName(event.target.value)} disabled={disabled} />
      <button type="button" disabled={disabled || !name.trim()} onClick={() => perform(() => createCase(name.trim()))}>New Case</button>
      {caseData && <button type="button" disabled={disabled || !name.trim()} onClick={() => perform(() => renameCase(caseData.case_id, name.trim()), false)}>Rename Case</button>}
      {sessionId && !caseData && <button type="button" disabled={disabled} onClick={() => perform(() => importLegacyCase(sessionId))}>Import legacy session as Case</button>}
      {caseData && <details>
        <summary>Case details</summary>
        <div className="modelmix-case-details">
          <p>Machine: {typeof caseData.machine === 'string' ? caseData.machine : JSON.stringify(caseData.machine || {})}</p>
          {[...(caseData.facts || []), ...(caseData.observations || []), ...(caseData.measurements || []), ...(caseData.repair_history || [])].map((item, index) => <p key={item.fact_id || index}><strong>{item.subject}</strong>: {typeof item.value === 'string' ? item.value : JSON.stringify(item.value)} · {item.status} · {item.provenance?.reference || item.provenance?.kind || 'provenance unavailable'}</p>)}
          <input aria-label="Fact or measurement subject" placeholder="Subject (e.g. battery voltage)" value={subject} onChange={(event) => setSubject(event.target.value)} />
          <input aria-label="Fact or measurement value" placeholder="Value including units" value={value} onChange={(event) => setValue(event.target.value)} />
          <select aria-label="Evidence status" value={status} onChange={(event) => setStatus(event.target.value)}>{['user_reported', 'observed', 'measured', 'verified', 'disputed', 'unresolved', 'hypothesis', 'rejected'].map((item) => <option key={item}>{item}</option>)}</select>
          <input aria-label="Evidence provenance" value={reference} onChange={(event) => setReference(event.target.value)} />
          <button type="button" disabled={disabled || !subject.trim() || !value.trim() || !reference.trim()} onClick={() => perform(() => addCaseFact(caseData.case_id, { subject: subject.trim(), value: value.trim(), status, category: status === 'measured' ? 'measurements' : status === 'observed' ? 'observations' : 'facts', provenance: { kind: status === 'measured' ? 'user_measurement' : status === 'observed' ? 'direct_observation' : status === 'verified' ? 'official_reference' : 'user', reference: reference.trim() } }), false)}>Save fact / measurement</button>
        </div>
      </details>}
    </div>
    {error && <p role="alert">{error}</p>}
  </section>;
}
