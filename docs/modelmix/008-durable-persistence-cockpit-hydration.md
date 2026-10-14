# Mission 008 — Durable Persistence + Cockpit Hydration

Date: 2026-08-29  
Status: **PASS (local isolated checkout)**

## Delivered

Mission 008 adds a ModelMix-owned `ModelMixPersistence` interface and an alpha
`AtomicJsonModelMixPersistence` implementation. Each session is stored as one
schema-versioned JSON document. Writes use a same-directory temporary file,
file `fsync`, atomic `os.replace`, and directory `fsync`; failed replacement
leaves the prior canonical document readable and removes the temporary file.

Schema version **1** stores:

- session ID and timestamps;
- canonical user and assistant messages with run, seat, audience, and role metadata;
- append-only run snapshots with exact Worker A, Moderator, and Worker B model references;
- the original prompt, ordered canonical events, latest durable `seq`, and terminal status;
- accumulated completed or partial visible output and participant error/status state.

The default location is `data/modelmix/sessions/<session_id>.json`. The backend
may override the root with `MODELMIX_DATA_DIR`; this changes location, not the
schema or persistence contract. The existing repository `data/` exclusion keeps
local conversations and prompts out of Git.

The run registry writes through this boundary and can locate a run across all
persisted sessions, then rebuild a terminal `RunEventJournal` from its ordered
events after process restart. The existing SSE endpoints and cursor contract
remain the replay/live transport. Duplicate or already-durable sequences do not
mutate canonical messages.

The cockpit loads its last session (or its browser-held session ID), hydrates the
latest run, original prompt, and exact seat/model placement, then retains the
persisted `latest_seq` as its replay cursor. Historical model references remain
visible even when they are no longer discovered. Sequence and run-identity
suppression prevent replay or a late prior-run event from appending output already
supplied by hydration.

## Files Changed

- `backend/modelmix/persistence.py`
- `backend/modelmix/journal.py`
- `backend/modelmix/registry.py`
- `backend/modelmix/routes.py`
- `backend/tests/test_modelmix_persistence.py`
- `frontend/src/modelmixApi.js`
- `frontend/src/modelmixState.js`
- `frontend/src/modelmixState.test.js`
- `frontend/src/components/ModelMixObserver.jsx`
- `docs/modelmix/008-durable-persistence-cockpit-hydration.md`
- `docs/modelmix/PUNCH-BOARD.md`
- `docs/modelmix/ENGINEERING-PROGRESS.md`
- `docs/modelmix/MISSION-INDEX.md`
- `docs/modelmix/README.md`

## Verification Observed

- `uv run pytest backend/tests/test_modelmix_persistence.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_streaming.py backend/tests/test_modelmix_moderator.py -q` — **35 passed in 3.66s**.
- `uv run pytest --basetemp=.pytest_temp -q` — **473 passed in 17.83s**.
- `node --test $(find src -name '*.test.js' -print)` — **24 passed, 0 failed**.
- `npx eslint src/modelmixApi.js src/modelmixState.js src/modelmixState.test.js src/components/ModelMixObserver.jsx` — **passed**.
- `npm run build` — **passed; 432 modules transformed; built in 5.14s**.
- `npm run lint` — **did not pass** because of 26 errors and 11 warnings in inherited, unchanged frontend files. The focused lint over every Mission 008 frontend file passed.

## Remaining Scope

Punch Board item 11's direct alpha persistence/restart requirement and item 22's
direct reload/hydration/deduplication requirement are satisfied by this slice.
General multi-turn history management, cross-device/session-library selection,
timeouts/retries, and later packaging remain governed by their separate Punch
Board items and were not pulled into Mission 008.

Remote integration was intentionally unavailable in this isolated checkout. The
Mission 008 commit is local to `work`; remote preservation must be verified by
the integrating environment.
