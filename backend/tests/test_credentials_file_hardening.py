"""Tests for Windows ACL hardening of the file credential backend (Mission 026).

These tests never invoke a real ``icacls``; ``subprocess.run`` and
``sys.platform`` are mocked. The Windows-path tests here require
``sys.platform == "win32"`` at call time.
"""

import json
import logging
import subprocess
import sys

import pytest

from backend.credentials import file_backend
from backend import user_data_dir


@pytest.fixture()
def cred_file(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    monkeypatch.setattr(file_backend, "CREDENTIALS_FILE", path)
    yield path


@pytest.fixture(autouse=True)
def _reset_process_guards():
    """Module-level once-per-process flags must not leak between tests."""
    file_backend._startup_warned = False
    file_backend._hardened = False
    yield
    file_backend._startup_warned = False
    file_backend._hardened = False


def _windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(user_data_dir, "is_windows", lambda: True)
    monkeypatch.setattr(
        user_data_dir, "resolve_windows_current_user", lambda: "ACME\\alice"
    )


class _Result:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _raising(exc):
    def _fn(*args, **kwargs):
        raise exc
    return _fn


# --- Acceptance 1: Windows write invokes icacls with correct path + user ----


def test_windows_write_invokes_icacls_args(cred_file, monkeypatch):
    _windows(monkeypatch)
    calls = []
    monkeypatch.setattr(
        user_data_dir.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args) or _Result(0),
    )

    file_backend.set_secret("api:openai", "sk-test")

    assert len(calls) == 1
    cmd = calls[0][0]
    assert cmd[0] == "icacls"
    assert cmd[1] == str(cred_file)
    assert "/inheritance:r" in cmd
    assert "/grant:r" in cmd
    assert cmd[4].endswith(":F")
    assert "ACME\\alice" in cmd[4]


# --- Acceptance 2: non-Windows never invokes icacls -------------------------


def test_non_windows_never_invokes_icacls(cred_file, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(user_data_dir, "is_windows", lambda: False)
    calls = []
    monkeypatch.setattr(
        user_data_dir.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args) or _Result(0),
    )

    file_backend.set_secret("api:openai", "sk-test")

    assert calls == [], "icacls must never be invoked off Windows"


# --- Acceptance 3: failing icacls does not raise; write still succeeds -------


@pytest.mark.parametrize(
    "hardener",
    [
        lambda: _Result(1, stderr="Access is denied."),
        lambda: (_ for _ in ()).throw(OSError("icacls not found")),
    ],
)
def test_failing_icacls_does_not_raise_and_value_survives(
    cred_file, monkeypatch, hardener
):
    _windows(monkeypatch)
    monkeypatch.setattr(user_data_dir.subprocess, "run", lambda *a, **k: hardener())

    file_backend.set_secret("api:openai", "sk-test")  # must not raise

    data = json.loads(cred_file.read_text())
    assert data["api:openai"] == "sk-test"


# --- Acceptance 4: failing case logs a warning -------------------------------


def test_failing_icacls_logs_warning(cred_file, monkeypatch, caplog):
    _windows(monkeypatch)
    monkeypatch.setattr(
        user_data_dir.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("boom"))
    )
    with caplog.at_level(logging.WARNING, logger="backend.credentials.file_backend"):
        file_backend.set_secret("api:openai", "sk-test")

    assert any(
        r.levelno == logging.WARNING for r in caplog.records
    ), "no warning logged on icacls failure"


# --- Mission 026 acceptance 5: once-per-process startup handling on Windows + an
# ---              existing unhardened file, and not a second time.
# ---
# --- NOTE (Mission 027): this test is necessarily reconciled from Mission 026.
# --- Mission 026 asserted reads never invoke icacls and always warn. Mission 027
# --- intentionally turns detection into remediation: the first touch of an
# --- existing unhardened file now attempts `_harden_credentials_file()`, so the
# --- single once-per-process attempt is what the test verifies (not zero icacls).


def test_startup_remediation_runs_once_on_existing_unhardened_file(
    cred_file, monkeypatch, caplog
):
    _windows(monkeypatch)
    cred_file.write_text(json.dumps({"api:old": "sk-old"}))
    calls = []
    monkeypatch.setattr(
        user_data_dir.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args) or _Result(0),
    )

    with caplog.at_level(
        logging.INFO, logger="backend.credentials.file_backend"
    ):
        file_backend.get_secret("api:old")
        file_backend.get_secret("api:old")

    # Exactly one icacls attempt across the two reads (once per process).
    assert len(calls) == 1, "remediation must run exactly once per process"
    cmd = calls[0][0]
    assert cmd[0] == "icacls"
    # Successful remediation logs INFO (success), not a warning.
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Restricted" in r.getMessage() for r in infos), "no success log"
    assert len(warnings) == 0, "successful remediation must not warn"


def test_startup_remediation_failure_warns_once(
    cred_file, monkeypatch, caplog
):
    _windows(monkeypatch)
    cred_file.write_text(json.dumps({"api:old": "sk-old"}))
    calls = []
    monkeypatch.setattr(
        user_data_dir.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args)
        or _Result(1, stderr="Access is denied."),
    )

    with caplog.at_level(
        logging.WARNING, logger="backend.credentials.file_backend"
    ):
        file_backend.get_secret("api:old")
        file_backend.get_secret("api:old")

    # One icacls attempt; the operator-facing "not restricted" warning fires once
    # (Mission 026 already produced the inner icacls-exit warning as well).
    assert len(calls) == 1
    not_restricted = [r for r in caplog.records if "not restricted" in r.getMessage()]
    assert len(not_restricted) == 1, (
        "operator-facing warning must fire exactly once per process"
    )


# --- Acceptance 6: no startup warning on non-Windows regardless of file ----


def test_no_startup_warning_on_non_windows(cred_file, monkeypatch, caplog):
    monkeypatch.setattr(sys, "platform", "linux")
    cred_file.write_text(json.dumps({"api:old": "sk-old"}))
    calls = []
    monkeypatch.setattr(
        user_data_dir.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args) or _Result(0),
    )

    with caplog.at_level(logging.WARNING, logger="backend.credentials.file_backend"):
        file_backend.get_secret("api:old")

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]
    assert calls == [], "icacls must never be invoked off Windows"


# --- Mission 027: a file already hardened THIS session gets no redundant
# ---              icacls on a subsequent read --------------------------------


def test_already_hardened_this_session_no_icacls_on_read(
    cred_file, monkeypatch
):
    _windows(monkeypatch)
    calls = []
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args[0]) or _Result(0),
    )

    # First touch writes the file and hardens it (write path) -> icacls.
    file_backend.set_secret("api:new", "sk-new")
    after_write = len(calls)
    assert after_write >= 1

    # A subsequent read must not trigger any additional icacls invocation.
    file_backend.get_secret("api:new")
    assert len(calls) == after_write, (
        "read of an already-hardened file must not re-run icacls"
    )


# --- Mission 027: explicit read-triggered remediation on Windows -------------


def test_read_triggers_remediation_on_existing_unhardened_file(
    cred_file, monkeypatch
):
    _windows(monkeypatch)
    cred_file.write_text(json.dumps({"api:old": "sk-old"}))
    calls = []
    monkeypatch.setattr(
        user_data_dir.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args) or _Result(0),
    )

    file_backend.get_secret("api:old")

    assert len(calls) == 1
    cmd = calls[0][0]
    assert cmd[0] == "icacls"
    assert cmd[1] == str(cred_file)
    assert "/inheritance:r" in cmd and "/grant:r" in cmd
    assert "ACME\\alice" in cmd[4]
