"""Tests for durable structured logging (Mission 040).

All six acceptance criteria are covered without writing real log files in the
user-data tree and without ever invoking a real ``icacls``.  The log directory
location and the ACL hardening call are both mocked.
"""

import logging
import logging.config
import os
from pathlib import Path

import pytest

from backend import logging_config


@pytest.fixture(autouse=True)
def _isolate_logging_config(monkeypatch):
    """Keep each test's logging setup isolated and hermetic."""
    monkeypatch.delenv("LLM_COUNCIL_LOG_LEVEL", raising=False)
    # The one-shot guard lives on the function object, not the module.
    logging_config.configure_logging._done = False
    # Snapshot/restore the real logging state around each test so no test
    # leaks handlers or a configured root into the rest of the suite.
    root_logger = logging.getLogger()
    before_handlers = list(root_logger.handlers)
    before_level = root_logger.level
    yield
    root_logger.handlers = before_handlers
    root_logger.setLevel(before_level)
    logging_config.configure_logging._done = False


@pytest.fixture()
def fake_log_dir(monkeypatch, tmp_path):
    """Point resolve_user_data_dir at tmp_path and capture dictConfig."""
    config_calls = []
    monkeypatch.setattr(
        logging_config, "resolve_user_data_dir", lambda: Path(tmp_path)
    )
    monkeypatch.setattr(
        logging.config,
        "dictConfig",
        lambda cfg: config_calls.append(cfg),
    )
    return config_calls


# --- Acceptance 1: rotating handler at the expected location ---------------


def test_rotating_handler_at_expected_location(fake_log_dir):
    logging_config.configure_logging()
    cfg = fake_log_dir[-1]
    file_handler = cfg["handlers"]["file"]

    assert file_handler["class"] == "logging.handlers.RotatingFileHandler"
    assert file_handler["maxBytes"] == 5 * 1024 * 1024
    assert file_handler["backupCount"] == 3
    assert file_handler["filename"].endswith(
        "logs" + os.sep + "modelmix.log"
    ), "log file must live under <user_data_dir>/logs/modelmix.log"


# --- Acceptance 2: LLM_COUNCIL_LOG_LEVEL controls the effective level -----


def test_env_level_controls_root_level(monkeypatch, fake_log_dir):
    monkeypatch.setenv("LLM_COUNCIL_LOG_LEVEL", "DEBUG")
    logging_config.configure_logging()
    assert fake_log_dir[-1]["root"]["level"] == logging.DEBUG


def test_default_level_is_info_when_unset(fake_log_dir):
    logging_config.configure_logging()
    assert fake_log_dir[-1]["root"]["level"] == logging.INFO


def test_invalid_env_level_falls_back_to_info(monkeypatch, fake_log_dir):
    monkeypatch.setenv("LLM_COUNCIL_LOG_LEVEL", "NOT-A-LEVEL")
    logging_config.configure_logging()
    assert fake_log_dir[-1]["root"]["level"] == logging.INFO


# --- Acceptance 3: ACL hardening applied to the log path on Windows --------


def test_hardens_log_file_path(monkeypatch, tmp_path):
    log_dir = Path(tmp_path) / "logs"
    (log_dir).mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "modelmix.log"
    log_path.touch()
    hardened = []
    monkeypatch.setattr(logging_config, "resolve_user_data_dir", lambda: Path(tmp_path))
    monkeypatch.setattr(
        logging.config, "dictConfig", lambda cfg: None
    )
    monkeypatch.setattr(
        logging_config,
        "harden_user_dir",
        lambda path: hardened.append(path) or True,
    )

    logging_config.configure_logging()

    assert hardened == [log_path], (
        "the log file must get the same ACL hardening as the credentials file"
    )


# --- Acceptance 4: console handler still present alongside file handler ----


def test_console_handler_present_alongside_file(fake_log_dir):
    logging_config.configure_logging()
    cfg = fake_log_dir[-1]
    assert "console" in cfg["handlers"], "console handler must be configured"
    assert "file" in cfg["handlers"], "file handler must be configured"
    assert set(cfg["root"]["handlers"]) == {"console", "file"}, (
        "root must attach both console and file handlers"
    )


# --- Acceptance 5: credential-leak audit across logger.* call sites --------


# Credential-like tokens that must never appear in a logged message.  The
# tokens are chosen to be credential *identifiers*, avoiding harmless false
# positives like the word "token" in "access token".
_FORBIDDEN_TOKENS = [
    "api_key",
    "apiKey",
    "apikey",
    "refresh_token",
    "password",
    "csrf",
    "authorization_header",
    "secret_key",
    "access_token=",
    "client_secret",
]


def _backend_source_files():
    root = Path(__file__).parent.parent
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in str(path) or path.name.startswith("test_"):
            continue
        yield path


def test_no_credential_leak_in_logger_log_calls():
    """Every ``logger.*`` call must not interpolate a secret into its message.

    This is a structural audit: it fails in the future if a developer adds a
    ``logger.info("...client_secret...", ...)`` whose static message contains a
    forbidden credential identifier.  It cannot prove a runtime value is safe,
    so it complements (not replaces) manual review; see the Mission 040 report
    for the call-by-call review.
    """
    offenders = []
    for file_path in _backend_source_files():
        for line_no, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("logger."):
                continue
            if any(tok in line for tok in _FORBIDDEN_TOKENS):
                offenders.append((file_path, line_no, stripped))
    assert offenders == [], (
        "logger.* call sites contain credential-like tokens:\n"
        + "\n".join(f"{p}:{n}: {s}" for p, n, s in offenders)
    )


# --- Acceptance 6 (suite-level) is exercised by the full backend run --------


def test_configure_logging_is_idempotent(fake_log_dir):
    logging_config.configure_logging()
    logging_config.configure_logging()
    assert len(fake_log_dir) == 1, "second call must be a no-op"
