"""Focused Mission 008 persistence and restart coverage."""

import json
from copy import deepcopy

import pytest

from backend.modelmix.journal import RunEventJournal
from backend.modelmix.persistence import AtomicJsonModelMixPersistence, PersistenceError
from backend.modelmix.registry import RunRegistry


def _history_document(run_count=1):
    runs = [
        {
            "run_id": f"run-{index}",
            "prompt": f"PROMPT_{index}_SENTINEL",
            "models": {},
            "status": "completed",
            "latest_seq": 0,
            "events": [],
        }
        for index in range(run_count)
    ]
    messages = []
    for index in range(run_count):
        messages.extend([
            {
                "run_id": f"run-{index}",
                "seat": "worker_a",
                "content": f"WORKER_A_{index}_SENTINEL",
            },
            {
                "run_id": f"run-{index}",
                "seat": "worker_b",
                "content": f"WORKER_B_{index}_SENTINEL",
            },
            {
                "run_id": f"run-{index}",
                "seat": "moderator",
                "content": f"MODERATOR_{index}_SENTINEL",
            },
        ])
    return {"schema_version": 1, "session": {"runs": runs, "messages": messages}}


def test_build_seat_history_uses_only_own_nonempty_messages_without_mutation():
    from backend.modelmix.history import build_seat_history

    document = _history_document(2)
    document["session"]["messages"][0]["content"] = "WORKER_A_PARTIAL_FAILED_SENTINEL"
    document["session"]["messages"][3]["content"] = ""
    original = deepcopy(document)

    history = build_seat_history(document, "worker_a", exclude_run_id="run-1")

    assert history == [
        {"role": "user", "content": "PROMPT_0_SENTINEL"},
        {"role": "assistant", "content": "WORKER_A_PARTIAL_FAILED_SENTINEL"},
    ]
    assert "WORKER_B_0_SENTINEL" not in str(history)
    assert "MODERATOR_0_SENTINEL" not in str(history)
    assert document == original


def test_build_seat_history_caps_latest_qualifying_turns_and_bounds_each_message():
    from backend.modelmix.history import (
        MAX_HISTORY_MESSAGE_CHARS,
        MAX_SEAT_HISTORY_TURNS,
        build_seat_history,
    )

    document = _history_document(MAX_SEAT_HISTORY_TURNS + 2)
    document["session"]["runs"][-1]["prompt"] = "P" * (MAX_HISTORY_MESSAGE_CHARS + 1)
    document["session"]["messages"][-3]["content"] = "A" * (MAX_HISTORY_MESSAGE_CHARS + 1)

    history = build_seat_history(document, "worker_a", exclude_run_id="current-run")

    assert len(history) == MAX_SEAT_HISTORY_TURNS * 2
    assert history[0]["content"] == "PROMPT_2_SENTINEL"
    assert len(history[-2]["content"]) == MAX_HISTORY_MESSAGE_CHARS
    assert len(history[-1]["content"]) == MAX_HISTORY_MESSAGE_CHARS
    assert "truncated deterministically" in history[-2]["content"]
    assert "truncated deterministically" in history[-1]["content"]


def test_build_seat_history_is_empty_for_fresh_session():
    from backend.modelmix.history import build_seat_history

    document = {"schema_version": 1, "session": {"runs": [], "messages": []}}

    assert build_seat_history(document, "worker_a", exclude_run_id="new-run") == []


def _snapshot():
    return {
        "run_id": "run-1",
        "prompt": "question",
        "models": {"worker_a": "p:a", "moderator": "p:m", "worker_b": "p:b"},
        "status": "created",
        "latest_seq": 0,
        "events": [],
    }


async def _play(store, session_id, events):
    await store.create_session(session_id)
    await store.create_run(session_id, _snapshot())
    for event in events:
        await store.append_event(session_id, "run-1", event, "active")
    return await store.load_session(session_id)


async def persisted_run(store, session_id="session-1", status="completed"):
    await store.create_session(session_id)
    snapshot = {
        "run_id": "run-1",
        "prompt": "question",
        "models": {"worker_a": "p:a", "moderator": "p:m", "worker_b": "p:b"},
        "status": "created",
        "latest_seq": 0,
        "events": [],
    }
    await store.create_run(session_id, snapshot)
    events = [
        {"run_id": "run-1", "seq": 1, "type": "run_started", "ts": 101.0, "seats": ["worker_a", "worker_b"]},
        {"run_id": "run-1", "seq": 2, "type": "seat_started", "ts": 102.0, "seat_id": "worker_a", "model": "p:a"},
        {"run_id": "run-1", "seq": 3, "type": "seat_delta", "ts": 103.0, "seat_id": "worker_a", "delta": "A"},
        {"run_id": "run-1", "seq": 4, "type": "seat_completed", "ts": 104.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 5, "type": "seat_started", "ts": 105.0, "seat_id": "worker_b", "model": "p:b"},
        {"run_id": "run-1", "seq": 6, "type": "seat_delta", "ts": 106.0, "seat_id": "worker_b", "delta": "B"},
        {"run_id": "run-1", "seq": 7, "type": "seat_completed", "ts": 107.0, "seat_id": "worker_b"},
        {"run_id": "run-1", "seq": 8, "type": "moderator_started", "ts": 108.0, "actor": "moderator", "model": "p:m"},
        {"run_id": "run-1", "seq": 9, "type": "moderator_delta", "ts": 109.0, "actor": "moderator", "delta": "M"},
        {"run_id": "run-1", "seq": 10, "type": "moderator_completed", "ts": 110.0, "actor": "moderator"},
    ]
    terminal = (
        {"run_id": "run-1", "seq": 11, "type": "run_completed", "ts": 111.0, "status": status}
        if status in {"completed", "partial"}
        else {"run_id": "run-1", "seq": 11, "type": f"run_{status}", "ts": 111.0}
    )
    for event in [*events, terminal]:
        await store.append_event(session_id, "run-1", event, "active")
    return await store.load_session(session_id)


async def test_completed_session_survives_reload_with_canonical_seat_metadata(tmp_path):
    document = await persisted_run(AtomicJsonModelMixPersistence(tmp_path))
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    assert reloaded == document
    assert reloaded["schema_version"] == 1
    assert reloaded["session"]["runs"][0]["status"] == "completed"
    messages = {message["seat"]: message for message in reloaded["session"]["messages"]}
    assert (messages["worker_a"]["content"], messages["moderator"]["content"], messages["worker_b"]["content"]) == ("A", "M", "B")
    assert messages["worker_a"]["audience"] == ["worker_a"]
    assert messages["worker_b"]["audience"] == ["worker_b"]
    assert messages["moderator"]["audience"] == ["moderator", "user"]


@pytest.mark.parametrize("status", ["partial", "cancelled", "failed"])
async def test_partial_cancelled_and_failed_state_survives(tmp_path, status):
    document = await persisted_run(AtomicJsonModelMixPersistence(tmp_path), status=status)
    run = document["session"]["runs"][0]
    assert run["status"] == status
    assert run["latest_seq"] == 11
    assert next(message for message in document["session"]["messages"] if message["seat"] == "worker_a")["content"] == "A"


async def test_new_registry_restores_replay_without_prior_memory(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    document = await persisted_run(store)
    restarted = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    restored = await restarted.restore("run-1", document)
    assert isinstance(restored, RunEventJournal)
    assert restored.status == "completed"
    assert [event["seq"] for event in await restored.events_after(8)] == [9, 10, 11]


async def test_registry_finds_run_outside_latest_session_after_restart(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await persisted_run(store, session_id="older-session")
    await store.create_session("newer-session")

    restarted = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    restored = await restarted.restore_persisted("run-1")

    assert restored is not None
    assert restored.session_id == "older-session"
    assert restored.status == "completed"


async def test_restart_marks_abandoned_active_run_failed_with_monotonic_event(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await store.create_session("session-1")
    await store.create_run("session-1", {
        "run_id": "run-1", "prompt": "question",
        "models": {"worker_a": "p:a", "moderator": "p:m", "worker_b": "p:b"},
        "status": "created", "latest_seq": 0, "events": [],
    })
    await store.append_event("session-1", "run-1", {
        "run_id": "run-1", "seq": 1, "type": "seat_delta", "seat_id": "worker_a", "delta": "partial",
    }, "active")
    document = await store.load_session("session-1")
    restored = await RunRegistry(persistence=store).restore("run-1", document)
    assert restored.status == "failed"
    terminal = (await restored.events_after(1))[0]
    assert terminal == {
        "run_id": "run-1", "seq": 2, "type": "run_failed",
        "error": "Backend restarted before the run reached a terminal state",
        "reason": "backend_restart",
    }
    reloaded = await store.load_session("session-1")
    assert reloaded["session"]["runs"][0]["status"] == "failed"
    assert next(message for message in reloaded["session"]["messages"] if message["seat"] == "worker_a")["content"] == "partial"


async def test_duplicate_event_does_not_duplicate_canonical_output(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    document = await persisted_run(store)
    duplicate = {"run_id": "run-1", "seq": 9, "type": "moderator_delta", "delta": "M"}
    await store.append_event("session-1", "run-1", duplicate, "active")
    reloaded = await store.load_session("session-1")
    assert reloaded == document


async def test_malformed_and_unsupported_state_fail_safely(tmp_path):
    (tmp_path / "bad.json").write_text('{"schema_version":999,"session":{}}', encoding="utf-8")
    with pytest.raises(PersistenceError, match="Unsupported or malformed"):
        await AtomicJsonModelMixPersistence(tmp_path).load_session("bad")
    (tmp_path / "broken.json").write_text('{', encoding="utf-8")
    with pytest.raises(PersistenceError, match="Unable to read"):
        await AtomicJsonModelMixPersistence(tmp_path).load_session("broken")


async def test_persisted_usage_matches_event_exactly_and_absent_usage_stays_none(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    usage = {
        "total_tokens": 12,
        "prompt_tokens": 5,
        "completion_tokens": 7,
        "detail": {"x": [1, 2], "flag": True},
    }
    document = await _play(store, "session-1", [
        {"run_id": "run-1", "seq": 1, "type": "seat_started", "ts": 1.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 2, "type": "seat_completed", "ts": 2.0, "seat_id": "worker_a", "usage": usage},
        {"run_id": "run-1", "seq": 3, "type": "seat_started", "ts": 3.0, "seat_id": "worker_b"},
        {"run_id": "run-1", "seq": 4, "type": "seat_completed", "ts": 4.0, "seat_id": "worker_b"},
    ])
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    messages = {message["seat"]: message for message in reloaded["session"]["messages"]}
    assert messages["worker_a"]["usage"] == usage
    assert messages["worker_b"]["usage"] is None
    assert document["session"]["messages"][1]["usage"] == usage


async def test_persisted_cost_usd_survives_reload_and_absence_stays_none(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await _play(store, "session-1", [
        {"run_id": "run-1", "seq": 1, "type": "seat_started", "ts": 1.0, "seat_id": "worker_a"},
        {
            "run_id": "run-1", "seq": 2, "type": "seat_completed", "ts": 2.0, "seat_id": "worker_a",
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
            "cost_usd": 0.0045,
        },
        {"run_id": "run-1", "seq": 3, "type": "seat_started", "ts": 3.0, "seat_id": "worker_b"},
        {
            "run_id": "run-1", "seq": 4, "type": "seat_completed", "ts": 4.0, "seat_id": "worker_b",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    ])
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    messages = {message["seat"]: message for message in reloaded["session"]["messages"]}
    assert messages["worker_a"]["cost_usd"] == 0.0045
    assert messages["worker_b"]["cost_usd"] is None


async def test_moderator_cost_usd_survives_persistence_reload(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await _play(store, "session-1", [
        {"run_id": "run-1", "seq": 1, "type": "seat_started", "ts": 1.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 2, "type": "seat_completed", "ts": 2.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 3, "type": "moderator_started", "ts": 3.0, "actor": "moderator"},
        {
            "run_id": "run-1", "seq": 4, "type": "moderator_completed", "ts": 4.0, "actor": "moderator",
            "finish_reason": "stop", "cost_usd": 0.009,
        },
    ])
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    message = next(message for message in reloaded["session"]["messages"] if message["seat"] == "moderator")
    assert message["cost_usd"] == 0.009


async def test_moderator_finish_reason_and_usage_survive_persistence_reload(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await _play(store, "session-1", [
        {"run_id": "run-1", "seq": 1, "type": "seat_started", "ts": 1.0, "seat_id": "worker_a", "model": "p:a"},
        {"run_id": "run-1", "seq": 2, "type": "seat_completed", "ts": 2.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 3, "type": "seat_started", "ts": 3.0, "seat_id": "worker_b", "model": "p:b"},
        {"run_id": "run-1", "seq": 4, "type": "seat_completed", "ts": 4.0, "seat_id": "worker_b"},
        {"run_id": "run-1", "seq": 5, "type": "moderator_started", "ts": 5.0, "actor": "moderator"},
        {
            "run_id": "run-1", "seq": 6, "type": "moderator_completed", "ts": 6.0, "actor": "moderator",
            "finish_reason": "stop", "usage": {"usageMetadata": {"totalTokenCount": 5}},
        },
    ])
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    message = next(message for message in reloaded["session"]["messages"] if message["seat"] == "moderator")
    assert message["finish_reason"] == "stop"
    assert message["usage"] == {"usageMetadata": {"totalTokenCount": 5}}


async def test_completed_message_records_start_and_end_timestamps(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await _play(store, "session-1", [
        {"run_id": "run-1", "seq": 1, "type": "seat_started", "ts": 10.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 2, "type": "seat_delta", "ts": 15.0, "seat_id": "worker_a", "delta": "A"},
        {"run_id": "run-1", "seq": 3, "type": "seat_completed", "ts": 20.5, "seat_id": "worker_a"},
    ])
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    message = next(message for message in reloaded["session"]["messages"] if message["seat"] == "worker_a")
    assert message["started_at"] == 10.0
    assert message["completed_at"] == 20.5
    assert message["completed_at"] >= message["started_at"]


async def test_failed_message_gets_completed_at_but_no_usage(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await _play(store, "session-1", [
        {"run_id": "run-1", "seq": 1, "type": "seat_started", "ts": 30.0, "seat_id": "worker_a"},
        {"run_id": "run-1", "seq": 2, "type": "seat_failed", "ts": 31.0, "seat_id": "worker_a", "error": "broken", "reason": "timeout"},
    ])
    reloaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("session-1")
    message = next(message for message in reloaded["session"]["messages"] if message["seat"] == "worker_a")
    assert message["completed_at"] == 31.0
    assert message["usage"] is None
    assert message["started_at"] == 30.0


async def test_failed_atomic_replace_leaves_previous_canonical_file_readable(tmp_path, monkeypatch):
    store = AtomicJsonModelMixPersistence(tmp_path)
    original = await store.create_session("session-1")

    def fail_replace(_source, _destination):
        raise OSError("simulated interrupted replace")

    monkeypatch.setattr("backend.modelmix.persistence.os.replace", fail_replace)
    with pytest.raises(OSError, match="interrupted"):
        await store.create_run("session-1", {
            "run_id": "run-1", "prompt": "q",
            "models": {"worker_a": "p:a", "moderator": "p:m", "worker_b": "p:b"},
            "status": "created",
            "latest_seq": 0, "events": [],
        })
    assert json.loads((tmp_path / "session-1.json").read_text(encoding="utf-8")) == original
    assert not list(tmp_path.glob("*.tmp"))


def _validate_document(models):
    document = {
        "schema_version": 1,
        "session": {
            "session_id": "session-1",
            "created_at": 1.0,
            "updated_at": 1.0,
            "runs": [
                {
                    "run_id": "run-1",
                    "prompt": "question",
                    "models": models,
                    "status": "completed",
                    "latest_seq": 0,
                    "events": [],
                }
            ],
            "messages": [],
        },
    }
    return AtomicJsonModelMixPersistence._validate(document)


def test_validator_accepts_mix_compare_and_solo_model_shapes():
    for models in [
        {"worker_a": "p:a", "worker_b": "p:b", "moderator": "p:m"},
        {"worker_a": "p:a", "worker_b": "p:b", "moderator": None},
        {"worker_a": "p:a"},
        {"worker_a": "p:a", "moderator": None},
        {"worker_a": "p:a", "worker_b": "p:b"},
    ]:
        assert _validate_document(models) is None


def test_validator_rejects_missing_or_empty_worker_a():
    for models in [
        {},
        {"worker_b": "p:b", "moderator": "p:m"},
        {"worker_a": "", "worker_b": "p:b"},
        {"worker_a": 123},
    ]:
        with pytest.raises(PersistenceError, match="Malformed ModelMix model references"):
            _validate_document(models)


def test_validator_rejects_worker_b_none_and_unknown_keys():
    for models in [
        {"worker_a": "p:a", "worker_b": None},
        {"worker_a": "p:a", "worker_b": ""},
        {"worker_a": "p:a", "worker_c": "p:c"},
        {"worker_a": "p:a", "moderator": ""},
        {"worker_a": "p:a", "moderator": 7},
    ]:
        with pytest.raises(PersistenceError, match="Malformed ModelMix model references"):
            _validate_document(models)


async def test_solo_shape_survives_load_from_disk(tmp_path):
    document = {
        "schema_version": 1,
        "session": {
            "session_id": "solo",
            "created_at": 1.0,
            "updated_at": 1.0,
            "runs": [
                {
                    "run_id": "run-1",
                    "prompt": "question",
                    "models": {"worker_a": "p:a"},
                    "status": "completed",
                    "latest_seq": 0,
                    "events": [],
                }
            ],
            "messages": [],
        },
    }
    (tmp_path / "solo.json").write_text(json.dumps(document), encoding="utf-8")
    loaded = await AtomicJsonModelMixPersistence(tmp_path).load_session("solo")
    assert loaded["session"]["runs"][0]["models"] == {"worker_a": "p:a"}


async def test_mix_compare_and_solo_shapes_all_load_from_disk(tmp_path):
    for session_id, models in [
        ("mix", {"worker_a": "p:a", "worker_b": "p:b", "moderator": "p:m"}),
        ("compare", {"worker_a": "p:a", "worker_b": "p:b", "moderator": None}),
        ("solo", {"worker_a": "p:a"}),
    ]:
        document = {
            "schema_version": 1,
            "session": {
                "session_id": session_id,
                "created_at": 1.0,
                "updated_at": 1.0,
                "runs": [
                    {
                        "run_id": "run-1",
                        "prompt": "question",
                        "models": models,
                        "status": "completed",
                        "latest_seq": 0,
                        "events": [],
                    }
                ],
                "messages": [],
            },
        }
        (tmp_path / f"{session_id}.json").write_text(json.dumps(document), encoding="utf-8")
        loaded = await AtomicJsonModelMixPersistence(tmp_path).load_session(session_id)
        assert loaded["session"]["runs"][0]["models"] == models


async def test_list_sessions_empty_directory_returns_empty_list(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    assert await store.list_sessions() == []


async def test_list_sessions_summarizes_newest_first_without_message_content(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await store.create_session("alpha")
    await store.create_session("beta")
    await store.create_session("gamma")

    # Deterministic newest-first ordering independent of disk write timing.
    import os
    os.utime(tmp_path / "alpha.json", (1, 1))
    os.utime(tmp_path / "beta.json", (2, 2))
    os.utime(tmp_path / "gamma.json", (3, 3))

    summaries = await store.list_sessions()

    assert [summary["session_id"] for summary in summaries] == ["gamma", "beta", "alpha"]
    for summary in summaries:
        assert isinstance(summary["created_at"], float)
        assert isinstance(summary["updated_at"], float)
        assert summary["message_count"] == 0
        # Lightweight summary: never full run/message content.
        assert "messages" not in summary
        assert "runs" not in summary


async def test_list_sessions_reports_message_count(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await store.create_session("sess")
    await store.create_run("sess", {
        "run_id": "run-1",
        "prompt": "question",
        "models": {"worker_a": "p:a"},
        "status": "created",
        "latest_seq": 0,
        "events": [],
    })
    summaries = await store.list_sessions()
    assert summaries[0]["session_id"] == "sess"
    assert summaries[0]["message_count"] == 1  # create_run appends the user message


async def test_delete_session_removes_file_and_load_returns_none(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    await store.create_session("gone")
    assert (tmp_path / "gone.json").exists()

    assert await store.delete_session("gone") is True
    assert not (tmp_path / "gone.json").exists()
    assert await store.load_session("gone") is None


async def test_delete_session_nonexistent_returns_false_without_raising(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    assert await store.delete_session("does-not-exist") is False


async def test_delete_session_invalid_id_raises_persistence_error(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    with pytest.raises(PersistenceError, match="Invalid ModelMix session id"):
        await store.delete_session("../../evil")
    with pytest.raises(PersistenceError, match="Invalid ModelMix session id"):
        await store.delete_session("")
    with pytest.raises(PersistenceError, match="Invalid ModelMix session id"):
        await store.delete_session("a" * 129)
