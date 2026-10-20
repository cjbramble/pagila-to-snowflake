"""Shared connections for the source ↔ target reconciliation suite."""

import psycopg
import pytest

from migrate.mapping import load_spec
from migrate.snowflake_conn import connect


def pytest_collection_modifyitems(items):
    # Every reconciliation test needs both systems.
    for item in items:
        item.add_marker(pytest.mark.source_db)
        item.add_marker(pytest.mark.target_db)


@pytest.fixture(scope="session")
def spec():
    return load_spec()


@pytest.fixture(scope="session")
def pg():
    with psycopg.connect(autocommit=True) as conn:
        conn.read_only = True
        yield conn


@pytest.fixture(scope="session")
def sf():
    with connect() as conn:
        yield conn
