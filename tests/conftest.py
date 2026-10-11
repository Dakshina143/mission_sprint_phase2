"""Test fixtures. Tests run on in-memory SQLite by default.

Set TEST_DATABASE_URL to run the same suite on PostgreSQL. As a safety guard the database name must end in
"_test" and must differ from DATABASE_URL, because every test creates and drops all tables.
"""
import os
import sys

import pytest
from sqlalchemy.engine import make_url

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from config import TestConfig  # noqa: E402


def _test_config():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        return TestConfig
    parsed = make_url(url)
    if not (parsed.database or "").endswith("_test"):
        raise RuntimeError(f"Refusing to run tests: database name {parsed.database!r} must end with '_test'")
    if url == os.getenv("DATABASE_URL"):
        raise RuntimeError("Refusing to run tests: TEST_DATABASE_URL equals DATABASE_URL")

    class PgTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = url

    return PgTestConfig


@pytest.fixture()
def app():
    app = create_app(_test_config())
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def mk(client, path, **body):
    r = client.post(f"/api/{path}", json=body)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]
