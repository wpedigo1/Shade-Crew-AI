"""ModelMix-owned durable session persistence.

The alpha implementation intentionally uses one versioned JSON document per
session.  Callers depend on the interface, not the on-disk representation.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1
DEFAULT_MODELMIX_DATA_DIR = Path("data/modelmix/sessions")
TERMINAL_STATUSES = {"completed", "partial", "failed", "cancelled"}
RUN_STATUSES = {"created", "active", *TERMINAL_STATUSES}


class PersistenceError(RuntimeError):
    """Persisted state is malformed, unsupported, or cannot be written safely."""


class ModelMixPersistence(ABC):
    """Replaceable ownership boundary for canonical ModelMix session state."""

    @abstractmethod
    async def create_session(self, session_id: str) -> Dict[str, Any]: ...

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    async def latest_session(self) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    async def find_run(self, run_id: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]: ...

    @abstractmethod
    async def create_run(self, session_id: str, run: Dict[str, Any]) -> None: ...

    @abstractmethod
    async def append_event(self, session_id: str, run_id: str, event: Dict[str, Any], status: str) -> None: ...

    @abstractmethod
    async def list_sessions(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool: ...


class AtomicJsonModelMixPersistence(ModelMixPersistence):
    """Versioned JSON persistence with fsync + atomic replace."""

    def __init__(self, root: Path | str = DEFAULT_MODELMIX_DATA_DIR) -> None:
        self.root = Path(root)
        self._lock = asyncio.Lock()

    def _path(self, session_id: str) -> Path:
        if (
            not session_id
            or len(session_id) > 128
            or any(
                char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                for char in session_id
            )
        ):
            raise PersistenceError("Invalid ModelMix session id")
        return self.root / f"{session_id}.json"

    async def create_session(self, session_id: str) -> Dict[str, Any]:
        async with self._lock:
            existing = self._read(self._path(session_id), missing_ok=True)
            if existing is not None:
                return existing
            now = time.time()
            session = {
                "schema_version": SCHEMA_VERSION,
                "session": {
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "messages": [],
                    "runs": [],
                },
            }
            self._write_atomic(self._path(session_id), session)
            return deepcopy(session)

    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            value = self._read(self._path(session_id), missing_ok=True)
            return deepcopy(value) if value is not None else None

    async def latest_session(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if not self.root.exists():
                return None
            candidates = sorted(self.root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
            for path in candidates:
                return deepcopy(self._read(path))
            return None

    async def find_run(self, run_id: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Find a durable run across sessions without assuming it is in the latest one."""
        async with self._lock:
            if not self.root.exists():
                return None
            for path in self.root.glob("*.json"):
                document = self._read(path)
                snapshot = next(
                    (item for item in document["session"]["runs"] if item["run_id"] == run_id),
                    None,
                )
                if snapshot is not None:
                    return deepcopy(document), deepcopy(snapshot)
            return None

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """Return lightweight per-session summaries, newest-first.

        Only summary fields are returned (session_id, created_at, updated_at,
        message_count) — never full message/run content. Ordering matches
        ``latest_session()``: files scanned newest-first by modification time.
        """
        async with self._lock:
            if not self.root.exists():
                return []
            candidates = sorted(
                self.root.glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            summaries: List[Dict[str, Any]] = []
            for path in candidates:
                document = self._read(path)
                session = document["session"]
                summaries.append({
                    "session_id": session["session_id"],
                    "created_at": session.get("created_at"),
                    "updated_at": session.get("updated_at"),
                    "message_count": len(session.get("messages", [])),
                })
            return summaries

    async def delete_session(self, session_id: str) -> bool:
        """Remove the durable session file. Returns True if it existed.

        The id is validated by the existing ``_path()`` (same as every other
        method); no id ever touches the filesystem unvalidated.
        """
        async with self._lock:
            path = self._path(session_id)
            try:
                path.unlink()
            except FileNotFoundError:
                return False
            return True

    async def create_run(self, session_id: str, run: Dict[str, Any]) -> None:
        async with self._lock:
            path = self._path(session_id)
            document = self._read(path)
            if any(item["run_id"] == run["run_id"] for item in document["session"]["runs"]):
                raise PersistenceError("ModelMix run already exists")
            document["session"]["runs"].append(deepcopy(run))
            document["session"]["messages"].append({
                "message_id": f"{run['run_id']}:user",
                "run_id": run["run_id"],
                "seat": "shared",
                "audience": ["worker_a", "worker_b", "moderator"],
                "role": "user",
                "content": run["prompt"],
            })
            document["session"]["updated_at"] = time.time()
            self._write_atomic(path, document)

    async def append_event(self, session_id: str, run_id: str, event: Dict[str, Any], status: str) -> None:
        async with self._lock:
            path = self._path(session_id)
            document = self._read(path)
            run = next((item for item in document["session"]["runs"] if item["run_id"] == run_id), None)
            if run is None:
                raise PersistenceError("ModelMix run does not exist")
            if event["seq"] <= run["latest_seq"]:
                return
            if run["status"] in TERMINAL_STATUSES:
                raise PersistenceError("Cannot mutate a terminal ModelMix run snapshot")
            if event["seq"] != run["latest_seq"] + 1:
                raise PersistenceError("ModelMix event sequence is not contiguous")
            run["events"].append(deepcopy(event))
            run["latest_seq"] = event["seq"]
            if event["type"] == "run_completed":
                status = str(event.get("status") or "completed")
            elif event["type"] == "run_failed":
                status = "failed"
            elif event["type"] == "run_cancelled":
                status = "cancelled"
            run["status"] = status
            self._apply_event(document["session"]["messages"], run, event)
            if event["type"] in {"run_cancelled", "run_failed"}:
                terminal = "cancelled" if event["type"] == "run_cancelled" else "failed"
                for message in document["session"]["messages"]:
                    if message.get("run_id") == run_id and message.get("role") == "assistant" and message.get("status") in {"waiting", "running"}:
                        message["status"] = terminal
            document["session"]["updated_at"] = time.time()
            self._write_atomic(path, document)

    @staticmethod
    def _apply_event(messages: list[Dict[str, Any]], run: Dict[str, Any], event: Dict[str, Any]) -> None:
        event_type = event["type"]
        seat = event.get("seat_id")
        if event_type.startswith("moderator_"):
            seat = "moderator"
        if seat not in {"worker_a", "worker_b", "moderator"}:
            return
        message_id = f"{run['run_id']}:{seat}"
        message = next((item for item in messages if item["message_id"] == message_id), None)
        if message is None:
            message = {
                "message_id": message_id,
                "run_id": run["run_id"],
                "seat": seat,
                "audience": [seat] if seat != "moderator" else ["moderator", "user"],
                "role": "assistant",
                "content": "",
                "status": "waiting",
                "error": None,
                "usage": None,
                "finish_reason": None,
                "cost_usd": None,
                "started_at": None,
                "completed_at": None,
            }
            messages.append(message)
        if event_type in {"seat_started", "moderator_started"}:
            message["status"] = "running"
            message["started_at"] = event["ts"]
        elif event_type in {"seat_delta", "moderator_delta"}:
            message["content"] += str(event.get("delta") or "")
        elif event_type in {"seat_completed", "moderator_completed"}:
            message["status"] = "completed"
            message["completed_at"] = event["ts"]
            if event.get("usage") is not None:
                message["usage"] = event["usage"]
            if event.get("finish_reason") is not None:
                message["finish_reason"] = event["finish_reason"]
            if event.get("cost_usd") is not None:
                message["cost_usd"] = event["cost_usd"]
        elif event_type in {"seat_failed", "moderator_failed"}:
            message["status"] = "failed"
            message["error"] = str(event.get("error") or "Participant failed")
            message["completed_at"] = event["ts"]
        elif event_type == "seat_cancelled":
            message["status"] = "cancelled"
            message["completed_at"] = event["ts"]

    def _read(self, path: Path, *, missing_ok: bool = False) -> Optional[Dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except FileNotFoundError:
            if missing_ok:
                return None
            raise PersistenceError("ModelMix session was not found") from None
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError(f"Unable to read ModelMix session: {exc}") from exc
        self._validate(value)
        if value["session"]["session_id"] != path.stem:
            raise PersistenceError("ModelMix session identity does not match its canonical file")
        return value

    @staticmethod
    def _validate(value: Any) -> None:
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise PersistenceError("Unsupported or malformed ModelMix persistence schema")
        session = value.get("session")
        if not isinstance(session, dict) or not isinstance(session.get("session_id"), str):
            raise PersistenceError("Malformed ModelMix session")
        if not isinstance(session.get("created_at"), (int, float)) or not isinstance(
            session.get("updated_at"), (int, float)
        ):
            raise PersistenceError("Malformed ModelMix session timestamps")
        if not isinstance(session.get("messages"), list) or not isinstance(session.get("runs"), list):
            raise PersistenceError("Malformed ModelMix canonical collections")
        for run in session["runs"]:
            required = {"run_id", "prompt", "models", "status", "latest_seq", "events"}
            if not isinstance(run, dict) or not required.issubset(run):
                raise PersistenceError("Malformed ModelMix run snapshot")
            if not isinstance(run["run_id"], str) or not isinstance(run["prompt"], str):
                raise PersistenceError("Malformed ModelMix run identity or prompt")
            if run["status"] not in RUN_STATUSES:
                raise PersistenceError("Malformed ModelMix run status")
            if not isinstance(run["models"], dict) or not set(run["models"]).issubset(
                {"worker_a", "worker_b", "moderator"}
            ):
                raise PersistenceError("Malformed ModelMix model references")
            if not (
                isinstance(run["models"].get("worker_a"), str)
                and run["models"].get("worker_a")
            ):
                raise PersistenceError("Malformed ModelMix model references")
            if not all(
                isinstance(model, str) and model
                for seat, model in run["models"].items()
                if seat != "moderator" or model is not None
            ):
                raise PersistenceError("Malformed ModelMix model references")
            if not isinstance(run["events"], list) or run["latest_seq"] != len(run["events"]):
                raise PersistenceError("Malformed ModelMix replay position")
            if any(
                not isinstance(event, dict)
                or event.get("seq") != index
                or event.get("run_id") != run["run_id"]
                or not isinstance(event.get("type"), str)
                for index, event in enumerate(run["events"], 1)
            ):
                raise PersistenceError("Malformed ModelMix event ordering")
        for message in session["messages"]:
            required = {"message_id", "run_id", "seat", "audience", "role", "content"}
            if not isinstance(message, dict) or not required.issubset(message):
                raise PersistenceError("Malformed ModelMix canonical message")
            if message["seat"] not in {"shared", "worker_a", "moderator", "worker_b"} or not isinstance(message["audience"], list):
                raise PersistenceError("Malformed ModelMix seat or audience metadata")
            expected = {
                "shared": ("user", ["worker_a", "worker_b", "moderator"]),
                "worker_a": ("assistant", ["worker_a"]),
                "worker_b": ("assistant", ["worker_b"]),
                "moderator": ("assistant", ["moderator", "user"]),
            }[message["seat"]]
            if (message["role"], message["audience"]) != expected:
                raise PersistenceError("Malformed ModelMix role or audience metadata")
            if not isinstance(message["content"], str):
                raise PersistenceError("Malformed ModelMix message content")

    def _write_atomic(self, path: Path, value: Dict[str, Any]) -> None:
        self._validate(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
            if os.name != "nt":
                directory_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise


modelmix_persistence = AtomicJsonModelMixPersistence(
    os.environ.get("MODELMIX_DATA_DIR", DEFAULT_MODELMIX_DATA_DIR)
)
