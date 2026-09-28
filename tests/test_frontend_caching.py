"""The page and its scripts are revalidated on every load, so a deploy reaches browsers.

With no Cache-Control, browsers kept an old app.js after a deploy until a hard refresh —
and an old script calls routes the new backend may no longer serve.
"""
from __future__ import annotations

import pytest

pytest.importorskip("torch")  # app.api.main imports the model stack; runs in the container

from fastapi.testclient import TestClient  # noqa: E402

from app.api.main import app  # noqa: E402

client = TestClient(app)  # no `with`: the startup work (migrations checks, seeding) is not needed


@pytest.mark.parametrize("path", ["/", "/static/app.js", "/static/styles.css", "/static/index.html"])
def test_the_frontend_is_revalidated_on_every_load(path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("etag"), "no ETag: every revalidation would re-download the file"


def test_an_unchanged_script_costs_a_304_not_a_download():
    first = client.get("/static/app.js")
    again = client.get("/static/app.js", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


def test_api_responses_are_left_alone():
    assert "cache-control" not in client.get("/health").headers
