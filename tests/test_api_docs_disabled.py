"""Regression coverage for FULL_SYSTEM_AUDIT.md P1 #15: FastAPI's interactive
/docs, /redoc, and /openapi.json were reachable by default, leaking the full API
schema (including admin request/response models) to anyone probing. Reimports
app.api.main with ENABLE_API_DOCS unset/false/true to confirm the toggle actually
takes effect, since the FastAPI app object is built once at module import time.
"""
import importlib

import pytest


@pytest.fixture
def reload_main():
    import app.api.main as main_module

    def _reload():
        importlib.reload(main_module)
        return main_module

    yield _reload
    # Restore the default (docs disabled) for any other test that imports this module.
    import os
    os.environ.pop("ENABLE_API_DOCS", None)
    importlib.reload(main_module)


def test_docs_disabled_when_env_var_unset(monkeypatch, reload_main):
    monkeypatch.delenv("ENABLE_API_DOCS", raising=False)
    main_module = reload_main()
    assert main_module.app.docs_url is None
    assert main_module.app.redoc_url is None
    assert main_module.app.openapi_url is None


def test_docs_disabled_when_env_var_false(monkeypatch, reload_main):
    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    main_module = reload_main()
    assert main_module.app.docs_url is None


def test_docs_enabled_when_env_var_true(monkeypatch, reload_main):
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    main_module = reload_main()
    assert main_module.app.docs_url == "/docs"
    assert main_module.app.redoc_url == "/redoc"
    assert main_module.app.openapi_url == "/openapi.json"
