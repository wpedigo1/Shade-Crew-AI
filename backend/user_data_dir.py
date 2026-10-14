"""Frozen-aware user data directory resolution.

Dev mode (source checkout) stores user data in the repository's ``data/``
folder, exactly as it always has. In a frozen build ``__file__`` resolves
inside the app bundle, so module-relative arithmetic would store user data in
the install folder itself -- the Mission 033 finding
(``_internal\\data\\credentials.json``). Frozen builds therefore use the
OS-conventional per-user directory ``%LOCALAPPDATA%\\ModelMix`` instead.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo-relative data directory. From this module's own location this is the
# same two-``.parent`` arithmetic settings.py and personas.py already used,
# landing on the repository's ``data/`` folder.
_REPO_DATA_DIR = Path(__file__).parent.parent / "data"

# Per-user application data folder name used by frozen Windows builds.
_APP_DIR_NAME = "ModelMix"


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller frozen build."""
    return getattr(sys, "frozen", False)


def resolve_user_data_dir() -> Path:
    """Return the directory where user data files live, creating it if needed.

    When not frozen: the existing repository ``data/`` directory, byte-for-byte
    the same location the three user-data files already use.

    When frozen (Windows): ``%LOCALAPPDATA%/ModelMix``. If ``LOCALAPPDATA``
    is absent, fall back to the directory containing the running executable
    and log a clear warning rather than crashing.
    """
    if not is_frozen():
        data_dir = _REPO_DATA_DIR
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            data_dir = Path(local_app_data) / _APP_DIR_NAME
        else:
            data_dir = Path(sys.executable).parent
            logger.warning(
                "LOCALAPPDATA is not set; falling back to the executable "
                "directory %s for user data", data_dir
            )
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def is_windows() -> bool:
    """Return whether the current platform is Windows (loopback-safe for tests)."""
    return sys.platform == "win32"


def resolve_windows_current_user() -> Optional[str]:
    """Resolve the current Windows user for an icacls grant principal.

    Prefer the USERNAME/USERDOMAIN environment variables (set reliably for a
    logged-in interactive session and for a user-run service), falling back to
    os.getlogin(), which can raise OSError when no controlling terminal is
    present (e.g. some service or SSH contexts).

    Extracted verbatim from the credential-file hardener so the same logic
    serves both the credentials file and durable log files.
    """
    user = os.environ.get("USERNAME")
    if user:
        domain = os.environ.get("USERDOMAIN")
        return f"{domain}\\{user}" if domain else user
    try:
        user = os.getlogin()
        if user:
            return user
    except OSError:
        pass
    return None


def harden_user_dir(path: Path) -> bool:
    """Restrict ``path`` (a file or directory) to the current user on Windows.

    Uses ``icacls "<path>" /inheritance:r /grant:r "<user>":F`` with no pywin32
    dependency, because ``os.chmod(0o600)`` has no meaningful per-user effect on
    Windows. No-op (returns False) off Windows. Never raises: any icacls
    failure is caught and logged so the caller's primary operation still
    succeeds, mirroring the existing ``os.chmod ... except OSError: pass``
    philosophy but with an operator-visible warning. Returns True only on a
    successful hardening.

    Shared by the credential-file backend and the durable log directory/file so
    the ``icacls`` invocation logic is not duplicated.
    """
    if not is_windows():
        return False
    user = resolve_windows_current_user()
    if not user:
        logger.warning(
            "Could not resolve the current Windows user; skipping ACL hardening for %s",
            path,
        )
        return False
    cmd = ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Failed to harden %s ACLs with icacls: %s", path, exc)
        return False
    if result.returncode != 0:
        logger.warning(
            "icacls exited %s hardening %s: %s",
            result.returncode,
            path,
            (result.stderr or result.stdout or "").strip(),
        )
        return False
    return True