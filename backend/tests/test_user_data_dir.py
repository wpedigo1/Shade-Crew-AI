"""Tests for frozen-aware user data directory resolution (Mission 034).

Dev-mode behavior must remain byte-for-byte unchanged: when not frozen the
resolved data directory is the same repository ``data/`` folder the three
user-data files already used. Frozen-mode resolution, the LOCALAPPDATA
fallback, and derivation of the three module-level data-file constants are
covered here.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import backend.personas as personas_module
from backend import settings as settings_module
from backend.credentials import file_backend
from backend.user_data_dir import is_frozen, resolve_user_data_dir


# --- Acceptance 1: not frozen -> exact historical repo data dir ---------------

def test_not_frozen_returns_historical_repo_data_dir(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    # Recompute the pre-Mission-034 module-relative formulas in place.
    historical = Path(file_backend.__file__).parent.parent.parent / "data"
    assert not is_frozen()
    assert resolve_user_data_dir() == historical


def test_not_frozen_ignores_localappdata_env(monkeypatch):
    """LOCALAPPDATA must only matter when frozen (dev mode never changes)."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", r"C:\should\not\matter")
    historical = Path(file_backend.__file__).parent.parent.parent / "data"
    assert resolve_user_data_dir() == historical


# --- Acceptance 2: frozen -> <LOCALAPPDATA>/ModelMix --------------------------

def test_frozen_uses_localappdata_modelmix(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    resolved = resolve_user_data_dir()
    assert resolved == tmp_path / "ModelMix"
    assert resolved.is_dir(), "resolved directory must be created"


# --- Acceptance 3: missing LOCALAPPDATA -> executable dir + warning -----------

def test_frozen_without_localappdata_falls_back_to_executable_dir(
    tmp_path, monkeypatch, caplog
):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    exe_dir = tmp_path / "bundle"
    exe_dir.mkdir()
    monkeypatch.setattr(sys, "executable", str(exe_dir / "modelmix-backend.exe"))
    with caplog.at_level(logging.WARNING, logger="backend.user_data_dir"):
        resolved = resolve_user_data_dir()
    assert resolved == exe_dir
    assert any(
        r.levelno == logging.WARNING and "LOCALAPPDATA" in r.getMessage()
        for r in caplog.records
    ), "missing LOCALAPPDATA must log a clear warning"


# --- Acceptance 4: the three data-file constants derive from the helper -------

def test_credentials_file_derives_from_helper(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert (
        file_backend.CREDENTIALS_FILE
        == resolve_user_data_dir() / "credentials.json"
    )


def test_settings_file_derives_from_helper(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert (
        settings_module.SETTINGS_FILE
        == resolve_user_data_dir() / "settings.json"
    )


def test_personas_data_dir_derives_from_helper(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert personas_module._DATA_DIR == resolve_user_data_dir()
    assert (
        personas_module._OVERRIDES_FILE
        == resolve_user_data_dir() / "persona_overrides.json"
    )