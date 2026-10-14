import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import { configuredSources, discoverConfiguredModels } from '../configuredModels';
import MarkdownContent from './MarkdownContent';
import SearchableModelSelect from './SearchableModelSelect';
import { DEFAULT_PANEL_VIEW, getPanelViewClasses, panelLayoutNeedsReset } from '../panelView';
import { buildSeatTelemetry } from '../seatTelemetry';
import {
  clearSavedSeatModels,
  FALLBACK_SEAT_MODELS,
  loadSavedSeatModels,
  saveSeatModels,
} from '../defaultSeatModels';
import {
  clearGuardrailOverride,
  loadGuardrailOverride,
  MAX_OUTPUT_CHARS_BOUND,
  MIN_OUTPUT_CHARS_BOUND,
  saveGuardrailOverride,
  validateGuardrailOverride,
} from '../guardrailSettings';
import { loadSavedMode, MODES, saveMode } from '../modelmixMode';
import {
  clearBehavior,
  clearSpendLimit,
  loadBehavior,
  loadSpendLimit,
  saveBehavior,
  saveSpendLimit,
  validateBehavior,
  MAX_MODERATOR_GUIDANCE_LENGTH,
} from '../modelmixBehavior';
import pkg from '../../package.json';
import {
  cancelModelMixRun,
  consumeModelMixSSE,
  deleteModelMixSession,
  disconnectOAuthProvider,
  getOAuthConnectionStatus,
  hydrateModelMixSession,
  listModelMixSessions,
  ModelMixHttpError,
  replayModelMixRun,
  startModelMixRun,
  startOAuthConnection,
  testCustomEndpoint,
  testOllama,
  testOpencode,
  testOpenrouter,
  testProvider,
  updateSettings,
} from '../modelmixApi';
import {
  applyModelMixEvent,
  applyReplayError,
  archiveCurrentRun,
  controlState,
  createModelMixState,
  isTerminalOverall,
  hydrateModelMixState,
  modelSelectorsDisabled,
  startNewSession,
} from '../modelmixState';
import './ModelMixObserver.css';

const reconnectDelay = () => new Promise((resolve) => setTimeout(resolve, 500));

export default function ModelMixObserver() {
  const [prompt, setPrompt] = useState('Explain why independent answers can improve reliability.');
  const savedSeatModels = useMemo(() => loadSavedSeatModels(window.localStorage), []);
  const [workerAModel, setWorkerAModel] = useState(savedSeatModels?.worker_a ?? FALLBACK_SEAT_MODELS.worker_a);
  const [moderatorModel, setModeratorModel] = useState(savedSeatModels?.moderator ?? FALLBACK_SEAT_MODELS.moderator);
  const [workerBModel, setWorkerBModel] = useState(savedSeatModels?.worker_b ?? FALLBACK_SEAT_MODELS.worker_b);
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState('');
  const [observer, setObserver] = useState(createModelMixState);
  const observerRef = useRef(observer);
  const connectionRef = useRef(null);
  const historicalModelsRef = useRef(new Set());
  const lastRequestBodyRef = useRef(null);
  const [panelView, setPanelView] = useState(DEFAULT_PANEL_VIEW);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsSection, setSettingsSection] = useState('about');
  const [settingsSnapshot, setSettingsSnapshot] = useState(null);
  const [defaultsRevision, setDefaultsRevision] = useState(0);
  const [guardrailsRevision, setGuardrailsRevision] = useState(0);
  const [behaviorRevision, setBehaviorRevision] = useState(0);
  const [mode, setMode] = useState(() => loadSavedMode(window.localStorage));

  const updateObserver = useCallback((updater) => {
    setObserver((current) => {
      const next = typeof updater === 'function' ? updater(current) : updater;
      observerRef.current = next;
      return next;
    });
  }, []);

  const toggleCollapsed = useCallback((seatKey) => {
    setPanelView((current) => ({
      ...current,
      collapsed: current.collapsed.includes(seatKey)
        ? current.collapsed.filter((key) => key !== seatKey)
        : [...current.collapsed, seatKey],
    }));
  }, []);

  const toggleMaximize = useCallback((seatKey) => {
    setPanelView((current) => ({ ...current, maximized: current.maximized === seatKey ? '' : seatKey }));
  }, []);

  const resetPanelLayout = useCallback(() => setPanelView(DEFAULT_PANEL_VIEW), []);

  useEffect(() => {
    let cancelled = false;
    const loadModels = async () => {
      try {
        const settings = await api.getSettings();
        if (!cancelled) setSettingsSnapshot(settings);
        const discovered = await discoverConfiguredModels(api, settings);
        if (cancelled) return;
        const historical = Array.from(historicalModelsRef.current)
          .filter((id) => !discovered.some((model) => model.id === id))
          .map((id) => ({ id, name: `${id} (historical)`, provider: 'Historical' }));
        setModels([...discovered, ...historical]);
        const discoveredIds = new Set(discovered.map((model) => model.id));
        setWorkerAModel((current) => discoveredIds.has(current) || historicalModelsRef.current.has(current) ? current : '');
        setModeratorModel((current) => discoveredIds.has(current) || historicalModelsRef.current.has(current) ? current : '');
        setWorkerBModel((current) => discoveredIds.has(current) || historicalModelsRef.current.has(current) ? current : '');
        if (discovered.length === 0) {
          setModelsError('No models were discovered from configured providers.');
        }
      } catch (error) {
        if (!cancelled) {
          setModelsError(error instanceof Error ? error.message : 'Failed to discover configured models.');
        }
      } finally {
        if (!cancelled) setModelsLoading(false);
      }
    };
    loadModels();
    return () => {
      cancelled = true;
      connectionRef.current?.abort();
    };
  }, []);

  const handleEvent = useCallback((event) => {
    updateObserver((current) => applyModelMixEvent(current, event));
  }, [updateObserver]);

  const showConnectionError = useCallback((error) => {
    const status = error instanceof ModelMixHttpError ? error.status : 0;
    updateObserver((current) => applyReplayError(current, status, error.message));
  }, [updateObserver]);

  const observe = useCallback(async (initialResponse, controller) => {
    let response = initialResponse;
    while (!controller.signal.aborted) {
      try {
        await consumeModelMixSSE(response, handleEvent);
        if (isTerminalOverall(observerRef.current.overall)) return;
        updateObserver((current) => ({ ...current, overall: 'reconnecting', message: 'Reconnecting…' }));
        await reconnectDelay();
        if (controller.signal.aborted) return;
        response = await replayModelMixRun(
          observerRef.current.runId,
          observerRef.current.lastSeq,
          controller.signal,
        );
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ModelMixHttpError && (error.status === 409 || error.status === 404)) {
          showConnectionError(error);
          return;
        }
        updateObserver((current) => ({ ...current, overall: 'reconnecting', message: 'Connection lost. Reconnecting…' }));
        await reconnectDelay();
        if (controller.signal.aborted) return;
        try {
          response = await replayModelMixRun(
            observerRef.current.runId,
            observerRef.current.lastSeq,
            controller.signal,
          );
        } catch (replayError) {
          if (replayError instanceof ModelMixHttpError && [404, 409].includes(replayError.status)) {
            showConnectionError(replayError);
            return;
          }
        }
      }
    }
  }, [handleEvent, showConnectionError, updateObserver]);

  useEffect(() => {
    const controller = new AbortController();
    connectionRef.current = controller;
    const sessionId = window.localStorage?.getItem('modelmix.sessionId');
    hydrateModelMixSession(sessionId, controller.signal)
      .then(async (document) => {
        const hydrated = hydrateModelMixState(document);
        updateObserver(hydrated);
        window.localStorage?.setItem('modelmix.sessionId', hydrated.sessionId);
        if (hydrated.prompt) setPrompt(hydrated.prompt);
        if (hydrated.models) {
          const historicalIds = Object.values(hydrated.models).filter(Boolean);
          historicalModelsRef.current = new Set(historicalIds);
          setModels((current) => {
            const missing = historicalIds
              .filter((id) => !current.some((model) => model.id === id))
              .map((id) => ({ id, name: `${id} (historical)`, provider: 'Historical' }));
            return [...current, ...missing];
          });
          setWorkerAModel(hydrated.models.worker_a || '');
          setModeratorModel(hydrated.models.moderator || '');
          setWorkerBModel(hydrated.models.worker_b || '');
        }
        if (!isTerminalOverall(hydrated.overall)) {
          const response = await replayModelMixRun(hydrated.runId, hydrated.lastSeq, controller.signal);
          await observe(response, controller);
        }
      })
      .catch((error) => {
        if (!(error instanceof ModelMixHttpError && error.status === 404) && !controller.signal.aborted) {
          showConnectionError(error);
        }
      });
    return () => controller.abort();
  }, [observe, showConnectionError, updateObserver]);

  const send = async (event) => {
    event.preventDefault();
    if (!prompt.trim() || !workerAModel.trim()) return;
    if (!isSolo && !workerBModel.trim()) return;
    if (mode === 'mix' && !moderatorModel.trim()) return;
    connectionRef.current?.abort();
    const controller = new AbortController();
    connectionRef.current = controller;
    const starting = {
      ...archiveCurrentRun(observerRef.current),
      overall: 'connecting',
      message: 'Connecting…',
      prompt: prompt.trim(),
      models: {
        worker_a: workerAModel.trim(),
        moderator: mode === 'mix' ? moderatorModel.trim() : '',
        worker_b: isSolo ? '' : workerBModel.trim(),
      },
    };
    updateObserver(starting);
    const requestBody = {
      prompt: prompt.trim(),
      worker_a_model: workerAModel.trim(),
      session_id: observerRef.current.sessionId || undefined,
    };
    if (!isSolo) requestBody.worker_b_model = workerBModel.trim();
    if (mode === 'mix') requestBody.moderator_model = moderatorModel.trim();
    const guardrailOverride = loadGuardrailOverride();
    if (guardrailOverride) {
      requestBody.warning_threshold_chars = guardrailOverride.warning_threshold_chars;
      requestBody.hard_cap_chars = guardrailOverride.hard_cap_chars;
    }
    const behaviorSettings = loadBehavior();
    if (behaviorSettings) {
      if (behaviorSettings.temperature !== undefined) requestBody.temperature = behaviorSettings.temperature;
      if (behaviorSettings.moderator_guidance !== undefined) requestBody.moderator_guidance = behaviorSettings.moderator_guidance;
    }
    const spendLimit = loadSpendLimit();
    if (spendLimit !== null && spendLimit !== undefined) requestBody.spend_limit_usd = spendLimit;
    lastRequestBodyRef.current = requestBody;
    try {
      const response = await startModelMixRun(requestBody, controller.signal);
      const runId = response.headers.get('X-ModelMix-Run-ID');
      const sessionId = response.headers.get('X-ModelMix-Session-ID');
      if (sessionId) window.localStorage?.setItem('modelmix.sessionId', sessionId);
      updateObserver((current) => ({ ...current, runId, sessionId, overall: 'running', message: 'Streaming…' }));
      await observe(response, controller);
    } catch (error) {
      if (!controller.signal.aborted) {
        if (error instanceof ModelMixHttpError && error.status === 402) {
          setPendingSpendConfirmation({ requestBody, message: error.message });
        } else {
          showConnectionError(error);
        }
      }
    }
  };

  const [pendingSpendConfirmation, setPendingSpendConfirmation] = useState(null);

  const confirmOverBudget = useCallback(async () => {
    if (!pendingSpendConfirmation) return;
    const { requestBody } = pendingSpendConfirmation;
    setPendingSpendConfirmation(null);
    connectionRef.current?.abort();
    const controller = new AbortController();
    connectionRef.current = controller;
    updateObserver((current) => ({
      ...archiveCurrentRun(current),
      overall: 'connecting',
      message: 'Connecting…',
      prompt: requestBody.prompt,
      models: {
        worker_a: requestBody.worker_a_model,
        moderator: requestBody.moderator_model || '',
        worker_b: requestBody.worker_b_model || '',
      },
    }));
    try {
      const confirmedBody = { ...requestBody, confirm_over_budget: true };
      const response = await startModelMixRun(confirmedBody, controller.signal);
      const runId = response.headers.get('X-ModelMix-Run-ID');
      const sessionId = response.headers.get('X-ModelMix-Session-ID');
      if (sessionId) window.localStorage?.setItem('modelmix.sessionId', sessionId);
      updateObserver((current) => ({ ...current, runId, sessionId, overall: 'running', message: 'Streaming…' }));
      await observe(response, controller);
    } catch (error) {
      if (!controller.signal.aborted) showConnectionError(error);
    }
  }, [pendingSpendConfirmation, observe, updateObserver, showConnectionError]);

  const stop = async () => {
    if (!observerRef.current.runId) return;
    updateObserver((current) => ({ ...current, overall: 'cancelling', message: 'Cancellation requested…' }));
    try {
      await cancelModelMixRun(observerRef.current.runId);
    } catch (error) {
      showConnectionError(error);
    }
  };

  const newSession = () => {
    if (modelSelectorsDisabled(observerRef.current.overall)) return;
    window.localStorage?.removeItem('modelmix.sessionId');
    updateObserver((current) => startNewSession(current));
  };

  const resetToFreshSession = useCallback(() => {
    window.localStorage?.removeItem('modelmix.sessionId');
    updateObserver((current) => startNewSession(current));
  }, [updateObserver]);

  const saveDefaults = () => {
    saveSeatModels(window.localStorage, {
      worker_a: workerAModel,
      moderator: moderatorModel,
      worker_b: workerBModel,
    });
    setDefaultsRevision((revision) => revision + 1);
  };

  const clearDefaults = () => {
    clearSavedSeatModels(window.localStorage);
    setDefaultsRevision((revision) => revision + 1);
  };

  const saveGuardrails = (values) => {
    if (!saveGuardrailOverride(values)) return;
    setGuardrailsRevision((revision) => revision + 1);
  };

  const clearGuardrails = () => {
    clearGuardrailOverride();
    setGuardrailsRevision((revision) => revision + 1);
  };

  const saveBehaviorSettings = (values) => {
    if (!saveBehavior(values)) return;
    setBehaviorRevision((revision) => revision + 1);
  };

  const clearBehaviorSettings = () => {
    clearBehavior();
    setBehaviorRevision((revision) => revision + 1);
  };

  const saveSpendLimitSetting = (value) => {
    if (!saveSpendLimit(value)) return;
    setBehaviorRevision((revision) => revision + 1);
  };

  const clearSpendLimitSetting = () => {
    clearSpendLimit();
    setBehaviorRevision((revision) => revision + 1);
  };

  const controls = controlState(observer.overall);
  const selectorsDisabled = modelsLoading || modelSelectorsDisabled(observer.overall);
  const isSolo = mode === 'solo';
  const sendDisabled = controls.sendDisabled
    || modelsLoading
    || !prompt.trim()
    || !workerAModel
    || (!isSolo && !workerBModel)
    || (mode === 'mix' && !moderatorModel);
  const modeDisabled = modelsLoading || modelSelectorsDisabled(observer.overall);
  return (
    <main className="modelmix-observer">
      <header className="modelmix-topbar">
        <h1>ModelMix</h1>
        <label className="modelmix-mode">
          <span className="modelmix-mode-label">Mode</span>
          <select
            className="modelmix-mode-select"
            aria-label="Mode"
            value={mode}
            disabled={modeDisabled}
            onChange={(event) => {
              const next = event.target.value;
              saveMode(next, window.localStorage);
              setMode(next);
            }}
          >
            {MODES.map((value) => (
              <option key={value} value={value}>{value === 'mix' ? 'Mix' : value === 'compare' ? 'Compare' : 'Solo'}</option>
            ))}
          </select>
        </label>
        <div className="modelmix-session">
          <span className="modelmix-session-status" data-status={observer.overall}>{observer.overall}</span>
          <button type="button" className="new-session" disabled={modelSelectorsDisabled(observer.overall)} onClick={newSession}>New Session</button>
        </div>
        <button type="button" className="modelmix-details-toggle" aria-expanded={detailsOpen} onClick={() => setDetailsOpen((open) => !open)}>Details</button>
        <a href="/">Back to Council</a>
        <button type="button" className="modelmix-settings-toggle" aria-label="Settings" title="Settings" aria-expanded={settingsOpen} onClick={() => setSettingsOpen((open) => !open)}>⚙</button>
      </header>

      <div className="modelmix-run-meta" data-open={detailsOpen} aria-hidden={!detailsOpen}>
        <span>Run: {observer.runId || '—'}</span><span>Last sequence: {observer.lastSeq}</span>
      </div>

      {settingsOpen && (
        <ModelMixSettings
          section={settingsSection}
          onSectionChange={setSettingsSection}
          onClose={() => setSettingsOpen(false)}
          settings={settingsSnapshot}
          currentModels={{
            worker_a: workerAModel,
            moderator: moderatorModel,
            worker_b: workerBModel,
          }}
          defaultsRevision={defaultsRevision}
          onSaveDefaults={saveDefaults}
          onClearDefaults={clearDefaults}
          guardrailsRevision={guardrailsRevision}
          onSaveGuardrails={saveGuardrails}
          onClearGuardrails={clearGuardrails}
          behaviorRevision={behaviorRevision}
          onSaveBehavior={saveBehaviorSettings}
          onClearBehavior={clearBehaviorSettings}
          onSaveSpendLimit={saveSpendLimitSetting}
          onClearSpendLimit={clearSpendLimitSetting}
          currentSessionId={observer.sessionId}
          onCurrentSessionDeleted={resetToFreshSession}
        />
      )}

      <form className="modelmix-composer" onSubmit={send}>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="Prompt" rows="3" required />
        <div className={`modelmix-models${mode === 'compare' ? ' modelmix-models--compare' : ''}`}>
          <label htmlFor="modelmix-worker-a-model">
            Worker A model
            <SearchableModelSelect
              inputId="modelmix-worker-a-model"
              ariaLabel="Worker A model"
              models={models}
              allModels={models}
              value={workerAModel}
              onChange={setWorkerAModel}
              isDisabled={selectorsDisabled}
              isLoading={modelsLoading}
            />
          </label>
          {mode === 'mix' && (
            <label htmlFor="modelmix-moderator-model">
              Moderator model
              <SearchableModelSelect
                inputId="modelmix-moderator-model"
                ariaLabel="Moderator model"
                models={models}
                allModels={models}
                value={moderatorModel}
                onChange={setModeratorModel}
                isDisabled={selectorsDisabled}
                isLoading={modelsLoading}
              />
            </label>
          )}
          {!isSolo && (
            <label htmlFor="modelmix-worker-b-model">
              Worker B model
              <SearchableModelSelect
                inputId="modelmix-worker-b-model"
                ariaLabel="Worker B model"
                models={models}
                allModels={models}
                value={workerBModel}
                onChange={setWorkerBModel}
                isDisabled={selectorsDisabled}
                isLoading={modelsLoading}
              />
            </label>
          )}
        </div>
        {modelsError && <p className="modelmix-model-error" role="alert">{modelsError}</p>}
        <div className="modelmix-actions">
          <button type="submit" disabled={sendDisabled}>Send</button>
          <button type="button" className="stop" disabled={controls.stopDisabled} onClick={stop}>Stop</button>
          <span role="status">{observer.message}</span>
        </div>
        {pendingSpendConfirmation && (
          <div className="modelmix-spend-confirmation" role="alert">
            <p className="modelmix-spend-confirmation-message">{pendingSpendConfirmation.message}</p>
            <button type="button" className="modelmix-spend-confirm" onClick={confirmOverBudget}>
              Proceed anyway
            </button>
          </div>
        )}
      </form>

      {panelLayoutNeedsReset(panelView.maximized, panelView.collapsed) && (
        <div className="modelmix-panel-toolbar">
          <button type="button" className="modelmix-reset-layout" onClick={resetPanelLayout}>Reset panel layout</button>
        </div>
      )}

      <section
        className={`modelmix-workers${panelView.maximized || isSolo ? ' modelmix-workers--maximized' : ''}`}
        aria-label="ModelMix cockpit"
      >
        {[
          { seatKey: 'worker_a', title: 'Worker A', className: '', emptyText: 'Waiting for visible output…' },
          { seatKey: 'moderator', title: 'Moderator', className: 'modelmix-moderator', emptyText: 'Waiting for workers…' },
          { seatKey: 'worker_b', title: 'Worker B', className: '', emptyText: 'Waiting for visible output…' },
        ].map(({ seatKey, title, className, emptyText }) => {
          const hiddenByMode = (mode === 'compare' && seatKey === 'moderator')
            || (mode === 'solo' && (seatKey === 'moderator' || seatKey === 'worker_b'));
          // In Solo mode the mode owns the layout: worker_a always renders and
          // fills the width, so any panelView.maximized targeting another seat
          // is neutralized (otherwise a maximize on a mode-hidden panel would
          // blank the cockpit).
          const effectiveMaximized = isSolo ? '' : panelView.maximized;
          const viewClasses = `${className} ${getPanelViewClasses(seatKey, effectiveMaximized, panelView.collapsed).join(' ')}${hiddenByMode ? ' modelmix-panel-hidden' : ''}`.trim();
          return (
            <TranscriptPane
              key={seatKey}
              title={title}
              seatKey={seatKey}
              participant={observer[seatKey]}
              history={observer.history}
              emptyText={emptyText}
              className={viewClasses}
              statusOverride={seatKey === 'moderator' && observer.overall === 'reconnecting' ? 'reconnecting' : null}
              collapsed={panelView.collapsed.includes(seatKey)}
              maximized={panelView.maximized === seatKey}
              onToggleCollapse={() => toggleCollapsed(seatKey)}
              onToggleMaximize={() => toggleMaximize(seatKey)}
            />
          );
        })}
      </section>
    </main>
  );
}

function TranscriptPane({
  title,
  participant,
  history = [],
  seatKey,
  emptyText,
  className = '',
  statusOverride = null,
  collapsed = false,
  maximized = false,
  onToggleCollapse,
  onToggleMaximize,
}) {
  const status = statusOverride || participant.status;
  const priorTurns = history.filter((entry) => entry[seatKey]?.text);
  const collapseLabel = `${collapsed ? 'Expand' : 'Collapse'} ${title}`;
  const maximizeLabel = `${maximized ? 'Restore' : 'Maximize'} ${title}`;
  const telemetry = buildSeatTelemetry(participant);
  return (
    <article className={`modelmix-worker ${className}`.trim()}>
      <header>
        <h2>{title}</h2>
        <div className="modelmix-panel-head">
          <span data-status={status}>{status}</span>
          <div className="modelmix-panel-controls">
            <button type="button" className="modelmix-panel-control" aria-label={collapseLabel} aria-expanded={!collapsed} title={collapseLabel} onClick={onToggleCollapse}>{collapsed ? 'Expand' : 'Collapse'}</button>
            <button type="button" className="modelmix-panel-control" aria-label={maximizeLabel} aria-pressed={maximized} title={maximizeLabel} onClick={onToggleMaximize}>{maximized ? 'Restore' : 'Maximize'}</button>
          </div>
        </div>
      </header>
      <div className="modelmix-transcript">
        {priorTurns.map((entry) => (
          <div key={entry.runId} className="modelmix-prior-turn">
            {entry.prompt ? <p className="modelmix-prior-prompt">{entry.prompt}</p> : null}
            <MarkdownContent>{entry[seatKey].text}</MarkdownContent>
            {entry[seatKey].error && <p className="modelmix-worker-error">{entry[seatKey].error}</p>}
          </div>
        ))}
        {participant.text ? <MarkdownContent>{participant.text}</MarkdownContent>
          : priorTurns.length === 0 ? <p className="modelmix-empty">{emptyText}</p> : null}
        {participant.error && <p className="modelmix-worker-error">{participant.error}</p>}
        {telemetry.length > 0 && (
          <footer className="modelmix-telemetry" aria-label="Seat telemetry">
            {telemetry.map((item) => (
              <span className="modelmix-telemetry-item" key={item.key}>
                <span className="modelmix-telemetry-label">{item.label}</span>: {item.value}
                {item.detail && <span className="modelmix-telemetry-detail"> · {item.detail}</span>}
              </span>
            ))}
          </footer>
        )}
      </div>
    </article>
  );
}

const SETTINGS_SECTIONS = [
  { id: 'about', label: 'About' },
  { id: 'providers', label: 'Providers' },
  { id: 'defaults', label: 'Defaults' },
  { id: 'guardrails', label: 'Guardrails' },
  { id: 'behavior', label: 'Behavior' },
  { id: 'sessions', label: 'Sessions' },
];

function ModelMixSettings({
  section,
  onSectionChange,
  onClose,
  settings,
  currentModels,
  defaultsRevision,
  onSaveDefaults,
  onClearDefaults,
  guardrailsRevision,
  onSaveGuardrails,
  onClearGuardrails,
  behaviorRevision,
  onSaveBehavior,
  onClearBehavior,
  onSaveSpendLimit,
  onClearSpendLimit,
  currentSessionId,
  onCurrentSessionDeleted,
}) {
  return (
    <div className="modelmix-settings-backdrop" onClick={onClose}>
      <section
        className="modelmix-settings"
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modelmix-settings-head">
          <h2>Settings</h2>
          <button type="button" className="modelmix-settings-close" aria-label="Close Settings" onClick={onClose}>✕</button>
        </header>
        <nav className="modelmix-settings-nav" aria-label="Settings sections">
          {SETTINGS_SECTIONS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              className={section === id ? 'modelmix-settings-nav-item is-active' : 'modelmix-settings-nav-item'}
              aria-pressed={section === id}
              onClick={() => onSectionChange(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="modelmix-settings-body">
          {section === 'about' && <AboutSection version={pkg.version} />}
          {section === 'providers' && <ProvidersSection settings={settings} />}
          {section === 'defaults' && (
            <DefaultsSection
              currentModels={currentModels}
              revision={defaultsRevision}
              onSave={onSaveDefaults}
              onClear={onClearDefaults}
            />
          )}
          {section === 'guardrails' && (
            <GuardrailsSection
              key={guardrailsRevision}
              onSave={onSaveGuardrails}
              onClear={onClearGuardrails}
            />
          )}
          {section === 'behavior' && (
            <BehaviorSection
              key={behaviorRevision}
              onSave={onSaveBehavior}
              onClear={onClearBehavior}
              onSaveSpendLimit={onSaveSpendLimit}
              onClearSpendLimit={onClearSpendLimit}
            />
          )}
          {section === 'sessions' && (
            <SessionsSection
              currentSessionId={currentSessionId}
              onCurrentSessionDeleted={onCurrentSessionDeleted}
            />
          )}
        </div>
      </section>
    </div>
  );
}

function AboutSection({ version }) {
  return (
    <div className="modelmix-settings-section">
      <p className="modelmix-settings-line">
        <strong>ModelMix</strong> — a local-first multi-model app to reduce single-model bias and unsupported conclusions.
      </p>
      <p className="modelmix-settings-line"><strong>Version</strong> {version}</p>
      <p className="modelmix-settings-line"><strong>License</strong> MIT — Copyright (c) 2025 Jacob Ben David.</p>
      <p className="modelmix-settings-line">
        Origin: ModelMix began as a fork/evolution of The AI Counsel, an open-source multi-model AI project.
      </p>
      <p className="modelmix-settings-line"><a href="https://github.com/wpedigo1/ModelMix">github.com/wpedigo1/ModelMix</a></p>
      <p className="modelmix-settings-line"><a href="https://github.com/wpedigo1/ModelMix/blob/main/OPEN_SOURCE_CREDITS.md">OPEN_SOURCE_CREDITS.md — open-source credits and dependency licenses</a></p>
    </div>
  );
}

const PROVIDER_ROWS = [
  ['OpenRouter', (sources) => sources.openrouter],
  ['Ollama (local)', (sources) => sources.ollama],
  ['Direct API keys', (sources) => sources.direct],
  ['Custom endpoint', (sources) => sources.custom],
  ['OAuth accounts', (sources) => sources.oauth],
];

const KEY_PROVIDERS = [
  { id: 'openrouter', name: 'OpenRouter', saveField: 'openrouter_api_key', statusFlag: 'openrouter_api_key_set', testKind: 'openrouter' },
  { id: 'openai', name: 'OpenAI', saveField: 'openai_api_key', statusFlag: 'openai_api_key_set', testKind: 'provider' },
  { id: 'anthropic', name: 'Anthropic', saveField: 'anthropic_api_key', statusFlag: 'anthropic_api_key_set', testKind: 'provider' },
  { id: 'google', name: 'Google', saveField: 'google_api_key', statusFlag: 'google_api_key_set', testKind: 'provider' },
  { id: 'mistral', name: 'Mistral', saveField: 'mistral_api_key', statusFlag: 'mistral_api_key_set', testKind: 'provider' },
  { id: 'deepseek', name: 'DeepSeek', saveField: 'deepseek_api_key', statusFlag: 'deepseek_api_key_set', testKind: 'provider' },
  { id: 'groq', name: 'Groq', saveField: 'groq_api_key', statusFlag: 'groq_api_key_set', testKind: 'provider' },
  { id: 'nvidia', name: 'NVIDIA Build', saveField: 'nvidia_api_key', statusFlag: 'nvidia_api_key_set', testKind: 'provider' },
  { id: 'opencode', name: 'OpenCode (Zen + Go)', saveField: 'opencode_api_key', statusFlag: 'opencode_api_key_set', testKind: 'opencode' },
];

const OAUTH_PROVIDERS = [
  { id: 'xai-oauth', name: 'xAI (Grok)', connectedFlag: 'xai_oauth_connected' },
  { id: 'openai-oauth', name: 'ChatGPT (OpenAI)', connectedFlag: 'openai_oauth_connected' },
  { id: 'github-copilot', name: 'GitHub Copilot', connectedFlag: 'github_copilot_connected' },
];

function ProvidersSection({ settings }) {
  const [currentSettings, setCurrentSettings] = useState(settings);
  const [keys, setKeys] = useState({});
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [customName, setCustomName] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [customKey, setCustomKey] = useState('');
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});
  const [saving, setSaving] = useState({});
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [oauth, setOauth] = useState({});
  const oauthTimersRef = useRef({});

  const refreshSettings = useCallback(async () => {
    try {
      const updated = await api.getSettings();
      if (updated) setCurrentSettings(updated);
    } catch {
      // Keep the last known snapshot; status stays as-is rather than guessing.
    }
  }, []);

  useEffect(() => {
    setCurrentSettings(settings);
  }, [settings]);

  const runTest = useCallback(async (provider) => {
    const key = (keys[provider.id] || '').trim();
    setTesting((current) => ({ ...current, [provider.id]: true }));
    setTestResults((current) => ({ ...current, [provider.id]: undefined }));
    setError('');
    try {
      let result;
      if (provider.testKind === 'openrouter') {
        result = await testOpenrouter(key || undefined);
      } else if (provider.testKind === 'opencode') {
        result = await testOpencode(key || undefined);
      } else {
        result = await testProvider(provider.id, key || undefined);
      }
      setTestResults((current) => ({ ...current, [provider.id]: result }));
    } catch (err) {
      setTestResults((current) => ({
        ...current,
        [provider.id]: { success: false, message: err instanceof Error ? err.message : 'Test failed' },
      }));
    } finally {
      setTesting((current) => ({ ...current, [provider.id]: false }));
    }
  }, [keys]);

  const saveKey = useCallback(async (provider) => {
    const value = (keys[provider.id] || '').trim();
    if (!value) return;
    setSaving((current) => ({ ...current, [provider.id]: true }));
    setError('');
    setMessage('');
    try {
      await updateSettings({ [provider.saveField]: value });
      setKeys((current) => ({ ...current, [provider.id]: '' }));
      setTestResults((current) => ({ ...current, [provider.id]: undefined }));
      await refreshSettings();
      setMessage(`${provider.name} saved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to save ${provider.name}.`);
    } finally {
      setSaving((current) => ({ ...current, [provider.id]: false }));
    }
  }, [keys, refreshSettings]);

  const saveOllama = useCallback(async () => {
    const value = ollamaUrl.trim();
    if (!value) return;
    setSaving((current) => ({ ...current, ollama: true }));
    setError('');
    setMessage('');
    try {
      await updateSettings({ ollama_base_url: value });
      setOllamaUrl('');
      await refreshSettings();
      setMessage('Ollama saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save Ollama.');
    } finally {
      setSaving((current) => ({ ...current, ollama: false }));
    }
  }, [ollamaUrl, refreshSettings]);

  const saveCustom = useCallback(async () => {
    const body = {};
    if (customName.trim()) body.custom_endpoint_name = customName.trim();
    if (customUrl.trim()) body.custom_endpoint_url = customUrl.trim();
    if (customKey.trim()) body.custom_endpoint_api_key = customKey.trim();
    if (Object.keys(body).length === 0) return;
    setSaving((current) => ({ ...current, custom: true }));
    setError('');
    setMessage('');
    try {
      await updateSettings(body);
      setCustomName('');
      setCustomUrl('');
      setCustomKey('');
      await refreshSettings();
      setMessage('Custom endpoint saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save custom endpoint.');
    } finally {
      setSaving((current) => ({ ...current, custom: false }));
    }
  }, [customName, customUrl, customKey, refreshSettings]);

  const testOllamaNow = useCallback(async () => {
    if (!ollamaUrl.trim()) return;
    setTesting((current) => ({ ...current, ollama: true }));
    setTestResults((current) => ({ ...current, ollama: undefined }));
    setError('');
    try {
      const result = await testOllama(ollamaUrl.trim());
      setTestResults((current) => ({ ...current, ollama: result }));
    } catch (err) {
      setTestResults((current) => ({
        ...current,
        ollama: { success: false, message: err instanceof Error ? err.message : 'Test failed' },
      }));
    } finally {
      setTesting((current) => ({ ...current, ollama: false }));
    }
  }, [ollamaUrl]);

  const testCustomNow = useCallback(async () => {
    if (!customName.trim() || !customUrl.trim()) return;
    setTesting((current) => ({ ...current, custom: true }));
    setTestResults((current) => ({ ...current, custom: undefined }));
    setError('');
    try {
      const result = await testCustomEndpoint(customName.trim(), customUrl.trim(), customKey.trim() || undefined);
      setTestResults((current) => ({ ...current, custom: result }));
    } catch (err) {
      setTestResults((current) => ({
        ...current,
        custom: { success: false, message: err instanceof Error ? err.message : 'Test failed' },
      }));
    } finally {
      setTesting((current) => ({ ...current, custom: false }));
    }
  }, [customName, customUrl, customKey]);

  const connectOAuth = useCallback(async (provider) => {
    setError('');
    setMessage('');
    try {
      const session = await startOAuthConnection(provider.id);
      setOauth((current) => ({
        ...current,
        [provider.id]: {
          state: 'awaiting',
          sessionId: session.session_id,
          userCode: session.user_code,
          verificationUri: session.verification_uri_complete || session.verification_uri,
          expiresIn: Number(session.expires_in) || 300,
          message: session.error || '',
        },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to start ${provider.name} connection.`);
    }
  }, []);

  const disconnectOAuth = useCallback(async (provider) => {
    setError('');
    setMessage('');
    try {
      await disconnectOAuthProvider(provider.id);
      setOauth((current) => ({ ...current, [provider.id]: undefined }));
      await refreshSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to disconnect ${provider.name}.`);
    }
  }, [refreshSettings]);

  useEffect(() => {
    const timers = oauthTimersRef.current;
    const started = new Map();
    const deadline = new Map();
    const poll = async (provider, entry) => {
      try {
        const status = await getOAuthConnectionStatus(provider.id, entry.sessionId);
        if (status.status === 'complete') {
          clearInterval(timers[entry.sessionId]);
          delete timers[entry.sessionId];
          setOauth((current) => ({ ...current, [provider.id]: { ...current[provider.id], state: 'connected' } }));
          await refreshSettings();
        } else if (status.status === 'error' || status.status === 'expired') {
          clearInterval(timers[entry.sessionId]);
          delete timers[entry.sessionId];
          setOauth((current) => ({
            ...current,
            [provider.id]: {
              ...current[provider.id],
              state: 'terminated',
              message: status.error || (status.status === 'expired' ? 'Connection expired.' : 'Connection failed.'),
            },
          }));
        } else if (entry.expiresIn > 0 && Date.now() - started.get(entry.sessionId) >= deadline.get(entry.sessionId)) {
          clearInterval(timers[entry.sessionId]);
          delete timers[entry.sessionId];
          setOauth((current) => ({
            ...current,
            [provider.id]: { ...current[provider.id], state: 'terminated', message: 'Connection timed out.' },
          }));
        }
      } catch {
        // Transient poll error: keep polling until the deadline rather than guessing.
      }
    };

    OAUTH_PROVIDERS.forEach((provider) => {
      const entry = oauth[provider.id];
      if (!entry || entry.state === 'terminated' || entry.state === 'connected') return;
      if (timers[entry.sessionId]) return;
      started.set(entry.sessionId, Date.now());
      deadline.set(entry.sessionId, (Number(entry.expiresIn) || 300) * 1000);
      poll(provider, entry);
      timers[entry.sessionId] = setInterval(() => poll(provider, entry), 2500);
    });

    return () => {
      Object.keys(timers).forEach((sessionId) => {
        clearInterval(timers[sessionId]);
        delete timers[sessionId];
      });
    };
  }, [oauth, refreshSettings]);

  if (!currentSettings) {
    return (
      <div className="modelmix-settings-section">
        <p className="modelmix-settings-line">Provider status is unavailable right now.</p>
      </div>
    );
  }
  const sources = configuredSources(currentSettings);
  return (
    <div className="modelmix-settings-section">
      <p className="modelmix-settings-line">
        Enter a credential below to connect a provider from here. Fields are write-only — a saved value is never shown back.
      </p>
      <ul className="modelmix-provider-list">
        {PROVIDER_ROWS.map(([name, status]) => {
          const connected = status(sources);
          return (
            <li key={name}>
              <span className="modelmix-provider-name">{name}</span>
              <span className="modelmix-provider-status" data-connected={connected}>
                {connected ? 'Connected' : 'Not connected'}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="modelmix-credential-editors">
        {KEY_PROVIDERS.map((provider) => (
          <CredentialRow
            key={provider.id}
            provider={provider}
            settings={currentSettings}
            value={keys[provider.id] || ''}
            testResult={testResults[provider.id]}
            testing={testing[provider.id]}
            saving={saving[provider.id]}
            onChange={(next) => setKeys((current) => ({ ...current, [provider.id]: next }))}
            onTest={() => runTest(provider)}
            onSave={() => saveKey(provider)}
          />
        ))}
        <div className="modelmix-credential-row">
          <span className="modelmix-cred-name">Ollama (local)</span>
          <span className="modelmix-cred-hint">Base URL — a local server address, not a key</span>
          <div className="modelmix-cred-controls">
            <input
              type="text"
              className="modelmix-settings-input"
              placeholder="http://localhost:11434"
              aria-label="Ollama base URL"
              value={ollamaUrl}
              onChange={(event) => setOllamaUrl(event.target.value)}
            />
            <button type="button" className="modelmix-cred-test" disabled={testing.ollama || !ollamaUrl.trim()} onClick={testOllamaNow}>
              {testing.ollama ? 'Testing…' : 'Test'}
            </button>
            <button type="button" className="modelmix-cred-save" disabled={saving.ollama || !ollamaUrl.trim()} onClick={saveOllama}>
              {saving.ollama ? 'Saving…' : 'Save'}
            </button>
          </div>
          <ResultLine result={testResults.ollama} />
        </div>
        <div className="modelmix-credential-row">
          <span className="modelmix-cred-name">Custom endpoint</span>
          <span className="modelmix-cred-hint">Display name, base URL, and optional API key (blank for local servers)</span>
          <input
            type="text"
            className="modelmix-settings-input"
            placeholder="Display name"
            aria-label="Custom endpoint name"
            value={customName}
            onChange={(event) => setCustomName(event.target.value)}
          />
          <input
            type="text"
            className="modelmix-settings-input"
            placeholder="https://api.example.com/v1"
            aria-label="Custom endpoint URL"
            value={customUrl}
            onChange={(event) => setCustomUrl(event.target.value)}
          />
          <input
            type="password"
            className="modelmix-settings-input"
            placeholder="API key (optional)"
            aria-label="Custom endpoint API key"
            value={customKey}
            onChange={(event) => setCustomKey(event.target.value)}
          />
          <div className="modelmix-cred-controls">
            <button type="button" className="modelmix-cred-test" disabled={testing.custom || !customName.trim() || !customUrl.trim()} onClick={testCustomNow}>
              {testing.custom ? 'Testing…' : 'Test'}
            </button>
            <button type="button" className="modelmix-cred-save" disabled={saving.custom || (!customName.trim() && !customUrl.trim() && !customKey.trim())} onClick={saveCustom}>
              {saving.custom ? 'Saving…' : 'Save'}
            </button>
          </div>
          <ResultLine result={testResults.custom} />
        </div>
        {OAUTH_PROVIDERS.map((provider) => (
          <OAuthRow
            key={provider.id}
            provider={provider}
            settings={currentSettings}
            entry={oauth[provider.id]}
            onConnect={() => connectOAuth(provider)}
            onDisconnect={() => disconnectOAuth(provider)}
          />
        ))}
      </div>
      {error && <p className="modelmix-settings-error" role="alert">{error}</p>}
      {message && <p className="modelmix-settings-line" role="status">{message}</p>}
      <p className="modelmix-settings-line">Credentials stay in secure storage and never appear here.</p>
    </div>
  );
}

function CredentialRow({ provider, settings, value, testResult, testing, saving, onChange, onTest, onSave }) {
  const configured = !!settings[provider.statusFlag];
  return (
    <div className="modelmix-credential-row">
      <span className="modelmix-cred-name">{provider.name}</span>
      <div className="modelmix-cred-controls">
        <input
          type="password"
          className="modelmix-settings-input"
          placeholder={configured ? 'New key (saved key not shown)' : 'Enter API key'}
          aria-label={`${provider.name} API key`}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="button" className="modelmix-cred-test" disabled={testing || !value.trim()} onClick={onTest}>
          {testing ? 'Testing…' : 'Test'}
        </button>
        <button type="button" className="modelmix-cred-save" disabled={saving || !value.trim()} onClick={onSave}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
      <ResultLine result={testResult} />
    </div>
  );
}

function ResultLine({ result }) {
  if (!result) return null;
  const success = result.success === true;
  const text = result.message || (success ? 'Success' : 'Failed');
  return (
    <p className={`modelmix-cred-result ${success ? 'modelmix-cred-result--ok' : 'modelmix-cred-result--err'}`} role="status">
      {text}
    </p>
  );
}

function OAuthRow({ provider, settings, entry, onConnect, onDisconnect }) {
  const connected = !!settings[provider.connectedFlag];
  const awaiting = entry && (entry.state === 'awaiting');
  return (
    <div className="modelmix-credential-row">
      <span className="modelmix-cred-name">{provider.name}</span>
      <span className="modelmix-cred-hint">
        {connected ? 'Connected' : 'Not connected'}
      </span>
      {awaiting ? (
        <div className="modelmix-oauth-pending">
          <p className="modelmix-oauth-code">
            Enter code <strong>{entry.userCode}</strong>
          </p>
          <a
            className="modelmix-oauth-link"
            href={entry.verificationUri}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open approval page
          </a>
          <p className="modelmix-oauth-note">Waiting for approval…</p>
        </div>
      ) : (
        <div className="modelmix-cred-controls">
          {connected ? (
            <button type="button" className="modelmix-cred-save" onClick={onDisconnect}>
              Disconnect
            </button>
          ) : (
            <button type="button" className="modelmix-cred-test" onClick={onConnect}>
              Connect
            </button>
          )}
        </div>
      )}
      {entry && entry.state === 'terminated' && entry.message && (
        <ResultLine result={{ success: false, message: entry.message }} />
      )}
    </div>
  );
}

function DefaultsSection({ currentModels, onSave, onClear }) {
  const saved = loadSavedSeatModels(window.localStorage);
  const rows = [
    ['Worker A', currentModels.worker_a],
    ['Moderator', currentModels.moderator],
    ['Worker B', currentModels.worker_b],
  ];
  return (
    <div className="modelmix-settings-section">
      <p className="modelmix-settings-line">
        When no defaults are saved, ModelMix starts each session with its built-in default seats.
      </p>
      <ul className="modelmix-provider-list">
        {rows.map(([seat, model]) => (
          <li key={seat}>
            <span className="modelmix-provider-name">{seat}</span>
            <span>{model || 'None'}</span>
          </li>
        ))}
      </ul>
      {saved ? (
        <p className="modelmix-settings-line">Saved defaults will be applied on the next load.</p>
      ) : (
        <p className="modelmix-settings-line">No saved defaults — built-in defaults apply.</p>
      )}
      <div className="modelmix-settings-actions">
        <button type="button" className="modelmix-settings-save" onClick={onSave}>Save current selections as defaults</button>
        <button type="button" className="modelmix-settings-clear" disabled={!saved} onClick={onClear}>Clear saved defaults</button>
      </div>
    </div>
  );
}

function GuardrailsSection({ onSave, onClear }) {
  const [fields, setFields] = useState(() => {
    const saved = loadGuardrailOverride();
    return {
      warning: saved ? String(saved.warning_threshold_chars) : '',
      cap: saved ? String(saved.hard_cap_chars) : '',
    };
  });

  const parsed = {
    warning_threshold_chars: fields.warning === '' ? NaN : Number(fields.warning),
    hard_cap_chars: fields.cap === '' ? NaN : Number(fields.cap),
  };
  const validation = validateGuardrailOverride(parsed);
  const edited = fields.warning !== '' || fields.cap !== '';
  const saved = loadGuardrailOverride();
  return (
    <div className="modelmix-settings-section">
      <p className="modelmix-settings-line">
        Save both thresholds as character counts — these are not token counts. When saved, both are sent with every request and the server validates them again.
      </p>
      <label className="modelmix-settings-line" htmlFor="modelmix-guardrail-warning">
        Warning threshold (characters)
      </label>
      <input
        id="modelmix-guardrail-warning"
        className="modelmix-settings-input"
        type="number"
        min={MIN_OUTPUT_CHARS_BOUND}
        max={MAX_OUTPUT_CHARS_BOUND}
        step="1"
        value={fields.warning}
        onChange={(event) => setFields((current) => ({ ...current, warning: event.target.value }))}
        aria-label="Warning threshold in characters"
      />
      <label className="modelmix-settings-line" htmlFor="modelmix-guardrail-cap">
        Hard cap (characters)
      </label>
      <input
        id="modelmix-guardrail-cap"
        className="modelmix-settings-input"
        type="number"
        min={MIN_OUTPUT_CHARS_BOUND}
        max={MAX_OUTPUT_CHARS_BOUND}
        step="1"
        value={fields.cap}
        onChange={(event) => setFields((current) => ({ ...current, cap: event.target.value }))}
        aria-label="Hard cap in characters"
      />
      {!validation.valid && edited && (
        <p className="modelmix-settings-error" role="alert">{validation.error}</p>
      )}
      <p className="modelmix-settings-line">
        ModelMix's built-in default: warning 20,000 chars and hard cap 40,000 chars. This is a static default value, not a live-fetched server value — requests that omit both thresholds use it.
      </p>
      {saved ? (
        <p className="modelmix-settings-line">Saved override will be sent with each request.</p>
      ) : (
        <p className="modelmix-settings-line">No saved override — server defaults apply.</p>
      )}
      <div className="modelmix-settings-actions">
        <button
          type="button"
          className="modelmix-settings-save"
          disabled={!validation.valid}
          onClick={() => onSave(parsed)}
        >
          Save as the default override
        </button>
        <button type="button" className="modelmix-settings-clear" disabled={!saved} onClick={onClear}>
          Clear saved override
        </button>
      </div>
    </div>
  );
}

function BehaviorSection({ onSave, onClear, onSaveSpendLimit, onClearSpendLimit }) {
  const saved = loadBehavior();
  const [temperature, setTemperature] = useState(
    saved && saved.temperature !== undefined ? String(saved.temperature) : ''
  );
  const [guidance, setGuidance] = useState(
    saved && saved.moderator_guidance !== undefined ? saved.moderator_guidance : ''
  );
  const [spendLimit, setSpendLimit] = useState(() => {
    const savedLimit = loadSpendLimit();
    return savedLimit !== null ? String(savedLimit) : '';
  });

  const parsedTemperature = temperature === '' ? NaN : Number(temperature);
  const parsedGuidance = guidance;
  const validation = validateBehavior({
    temperature: parsedTemperature,
    moderator_guidance: parsedGuidance,
  });
  const edited = temperature !== '' || guidance !== '';
  const guidanceRemaining = MAX_MODERATOR_GUIDANCE_LENGTH - guidance.length;

  const parsedSpendLimit = spendLimit === '' ? NaN : Number(spendLimit);
  const spendLimitValid = spendLimit === '' || (Number.isFinite(parsedSpendLimit) && parsedSpendLimit > 0);
  const spendLimitSaved = loadSpendLimit();

  const handleSave = () => {
    const values = {};
    if (temperature !== '') values.temperature = parsedTemperature;
    if (guidance !== '') values.moderator_guidance = guidance;
    onSave(values);
  };

  const handleSaveSpendLimit = () => {
    if (!Number.isFinite(parsedSpendLimit) || parsedSpendLimit <= 0) return;
    onSaveSpendLimit(parsedSpendLimit);
  };

  const handleClearSpendLimit = () => {
    onClearSpendLimit();
    setSpendLimit('');
  };

  return (
    <div className="modelmix-settings-section">
      <p className="modelmix-settings-line">
        Optionally set per-run model behavior. Each value is independent — set one, the other, or neither. Saved values are sent with every request and the server validates them again.
      </p>
      <label className="modelmix-settings-line" htmlFor="modelmix-behavior-temperature">
        Temperature (0.0–2.0)
      </label>
      <input
        id="modelmix-behavior-temperature"
        className="modelmix-settings-input"
        type="number"
        min={0.0}
        max={2.0}
        step="0.1"
        value={temperature}
        onChange={(event) => setTemperature(event.target.value)}
        aria-label="Temperature"
      />
      <label className="modelmix-settings-line" htmlFor="modelmix-behavior-guidance">
        Moderator guidance (how the Moderator should synthesize)
      </label>
      <textarea
        id="modelmix-behavior-guidance"
        className="modelmix-settings-input"
        rows="4"
        maxLength={MAX_MODERATOR_GUIDANCE_LENGTH}
        value={guidance}
        onChange={(event) => setGuidance(event.target.value)}
        aria-label="Moderator guidance"
      />
      <p className="modelmix-settings-line">
        {guidanceRemaining} characters remaining (limit {MAX_MODERATOR_GUIDANCE_LENGTH}). Guidance is appended to the Moderator's instructions, never replacing them.
      </p>
      {!validation.valid && edited && (
        <p className="modelmix-settings-error" role="alert">
          {Object.values(validation.errors).join(' ')}
        </p>
      )}
      {saved ? (
        <p className="modelmix-settings-line">Saved behavior will be sent with each request.</p>
      ) : (
        <p className="modelmix-settings-line">No saved behavior — no temperature or guidance is sent.</p>
      )}
      <div className="modelmix-settings-actions">
        <button
          type="button"
          className="modelmix-settings-save"
          disabled={!validation.valid || !edited}
          onClick={handleSave}
        >
          Save behavior
        </button>
        <button type="button" className="modelmix-settings-clear" disabled={!saved} onClick={onClear}>
          Clear saved behavior
        </button>
      </div>
      <hr className="modelmix-settings-divider" />
      <label className="modelmix-settings-line" htmlFor="modelmix-behavior-spend-limit">
        Spend limit (USD)
      </label>
      <input
        id="modelmix-behavior-spend-limit"
        className="modelmix-settings-input"
        type="number"
        min={0.01}
        step="0.01"
        value={spendLimit}
        onChange={(event) => setSpendLimit(event.target.value)}
        aria-label="Spend limit in USD"
      />
      {!spendLimitValid && spendLimit !== '' && (
        <p className="modelmix-settings-error" role="alert">
          Spend limit must be greater than 0
        </p>
      )}
      {spendLimitSaved !== null ? (
        <p className="modelmix-settings-line">Saved spend limit: ${spendLimitSaved} USD. Runs exceeding this are rejected.</p>
      ) : (
        <p className="modelmix-settings-line">No spend limit — runs are not gated by cost.</p>
      )}
      <div className="modelmix-settings-actions">
        <button
          type="button"
          className="modelmix-settings-save"
          disabled={!spendLimitValid || spendLimit === ''}
          onClick={handleSaveSpendLimit}
        >
          Save spend limit
        </button>
        <button type="button" className="modelmix-settings-clear" disabled={spendLimitSaved === null} onClick={handleClearSpendLimit}>
          Clear spend limit
        </button>
      </div>
    </div>
  );
}

function formatSessionTime(ts) {
  if (typeof ts !== 'number' || !Number.isFinite(ts)) return 'unknown';
  return new Date(ts * 1000).toLocaleString();
}
function SessionRow({ session, current, confirming, busy, onConfirm, onDelete }) {
  const displayId = session.session_id.length > 40 ? `${session.session_id.slice(0, 37)}…` : session.session_id;
  const isCurrent = current != null && session.session_id === current;
  return (
    <li className="modelmix-session-row">
      <div className="modelmix-session-info">
        <span className="modelmix-session-id" title={session.session_id}>{displayId}</span>
        {isCurrent && <span className="modelmix-session-current">current</span>}
        <span className="modelmix-session-time">
          created {formatSessionTime(session.created_at)} · updated {formatSessionTime(session.updated_at)}
        </span>
        <span className="modelmix-session-count">{session.message_count} messages</span>
      </div>
      {confirming === session.session_id ? (
        <span className="modelmix-session-confirm">
          <span className="modelmix-session-confirm-text">Delete this session?</span>
          <button type="button" className="modelmix-session-delete-confirm" disabled={busy} onClick={() => onDelete(session.session_id)}>Confirm</button>
          <button type="button" className="modelmix-session-delete-cancel" disabled={busy} onClick={() => onConfirm(null)}>Cancel</button>
        </span>
      ) : (
        <button type="button" className="modelmix-session-delete" onClick={() => onConfirm(session.session_id)}>Delete</button>
      )}
    </li>
  );
}

function SessionsSection({ currentSessionId, onCurrentSessionDeleted }) {
  const [sessions, setSessions] = useState(null);
  const [error, setError] = useState('');
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      const list = await listModelMixSessions();
      setSessions(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions.');
      setSessions(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (sessionId) => {
    setBusy(true);
    setError('');
    try {
      await deleteModelMixSession(sessionId);
      setSessions((current) => (current || []).filter((s) => s.session_id !== sessionId));
      setConfirming(null);
      if (currentSessionId != null && sessionId === currentSessionId) {
        onCurrentSessionDeleted();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session.');
      setConfirming(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modelmix-settings-section">
      <p className="modelmix-settings-line">
        Sessions are stored locally on this device. Deleting a session is permanent and cannot be undone.
      </p>
      {error && <p className="modelmix-settings-error" role="alert">{error}</p>}
      {sessions === null ? (
        <p className="modelmix-settings-line">Loading sessions…</p>
      ) : sessions.length === 0 ? (
        <p className="modelmix-settings-line">No sessions yet.</p>
      ) : (
        <ul className="modelmix-session-list">
          {sessions.map((session) => (
            <SessionRow
              key={session.session_id}
              session={session}
              current={currentSessionId}
              confirming={confirming}
              busy={busy}
              onConfirm={setConfirming}
              onDelete={handleDelete}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
