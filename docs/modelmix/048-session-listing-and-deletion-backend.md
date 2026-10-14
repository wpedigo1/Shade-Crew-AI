# Mission 048 — Session Listing and Deletion (Backend)

Date: 2026-09-02 CT · Base: main @ `e1a0398` (Mission 047)

## What changed

Manual session listing and deletion in the backend persistence layer and HTTP
surface. No automatic retention, no frontend, no schema bump.

### `backend/modelmix/persistence.py`

- `ModelMixPersistence` (abstract): two new methods —
  `list_sessions() -> List[Dict[str, Any]]` and
  `delete_session(session_id: str) -> bool`.
- `AtomicJsonModelMixPersistence`:
  - `list_sessions()`: `self.root.glob("*.json")`, sorted newest-first by
    `path.stat().st_mtime` (the exact `latest_session()` pattern), all inside
    `self._lock`. Returns lightweight summaries only — `session_id`,
    `created_at`, `updated_at`, `message_count` (length of the messages
    array). Full message/run content is never returned.
  - `delete_session()`: reuses the existing `_path()` for id validation (no
    reimplementation, no unvalidated filesystem access), unlinks the file
    inside `self._lock`, returns `True` if it existed / `False` if not.

### `backend/modelmix/registry.py`

- `active_run_for_session(session_id) -> Optional[str]`: returns the run_id of
  any in-process, non-terminal run (`run.session_id == session_id` and
  `run.status not in TERMINAL_STATUSES`), guarded by `self._lock`, pruning
  first. Uses the existing `_runs` map and journal `TERMINAL_STATUSES` — no new
  run-execution logic.

### `backend/modelmix/routes.py`

- `GET /api/modelmix/sessions` → `list_sessions()` summaries.
- `DELETE /api/modelmix/sessions/{session_id}`:
  - 409 if `active_run_for_session` finds a live run (checked before any
    delete, so a streaming run's file is never removed out from under it);
  - 422 on invalid id (`_path()` `PersistenceError`, same as other routes);
  - 404 if `delete_session()` returns `False`;
  - 204 on success.

## Boundaries honored

- No automatic/scheduled retention policy (a separate product decision).
- `create_session`/`load_session`/`latest_session`/`find_run`/`create_run`/
  `append_event` and all run-execution logic untouched.
- Frontend untouched.
- `_path()` validation reused exactly; no `schema_version` bump.

## Tests

`test_modelmix_persistence.py` (+6): empty-dir listing returns `[]`;
multi-session summary newest-first with `message_count` and no message/run
content; `message_count` reflects a created run's user message;
delete-existing returns `True` and `load_session` then returns `None`;
delete-nonexistent returns `False` without raising; invalid ids
(`../`, empty, >128 chars) raise the same `PersistenceError` `_path()` always
raises.

`test_modelmix_sessions_routes.py` (+4, real HTTP via `httpx.AsyncClient` +
`ASGITransport`): list route empty-then-populated; delete success 204 then
session 404; delete nonexistent 404 and bad id 422 (space-encoded `bad%20id`
— a literal `..` path is normalized away by the HTTP client before routing);
409 while a real (hanging) run is active, then 204 after cancelling it.

## Validation (observed)

- `uv run pytest backend/tests/test_modelmix_persistence.py
  backend/tests/test_modelmix_streaming.py -v --basetemp=...` → **39 passed**.
- `uv run pytest backend/tests -q --basetemp=...` → **517 passed** (507 prior +
  10 new).
- `cd frontend && npm test` → **148 passed**; `npm run build` → clean;
  `npm run lint` → clean. (Nothing frontend changed; run as required.)

The literal `--basetemp`-less commands reproduce the known pre-existing
`pytest-of-wpedigo` system-temp ACL `WinError 5`; the workspace `--basetemp`
override is the established workaround.

## Doc updates

- `PUNCH-BOARD.md` item 29 → Mission 048 added; retention/delete basics in
  place, automatic retention + session-manager UI still open.
- `MISSION-INDEX.md` (row + result), `ENGINEERING-PROGRESS.md` (result).

## Remaining risks / open items

- The 409 guard only protects runs live in this process (`run_registry`);
  a session whose run is terminal here is deletable, which is the intended
  contract.
- Automatic/scheduled retention and the session-manager frontend remain open
  (item 29 tail and future mission respectively).