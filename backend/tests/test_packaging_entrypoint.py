import importlib.util
from pathlib import Path


ENTRY_PATH = Path(__file__).resolve().parents[2] / "packaging" / "backend_entry.py"


def _load_entry_module():
    spec = importlib.util.spec_from_file_location("modelmix_backend_entry", ENTRY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backend_entry_executes_backend_main_with_package_context(monkeypatch):
    backend_entry = _load_entry_module()
    calls = []

    def fake_run_module(name, *, run_name, alter_sys):
        calls.append((name, run_name, alter_sys))

    monkeypatch.setattr(backend_entry.runpy, "run_module", fake_run_module)

    backend_entry.main()

    assert calls == [("backend.main", "__main__", True)]
