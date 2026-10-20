"""Markers for the source ↔ target reconciliation suite (fixtures live in tests/conftest.py)."""

import pytest


def pytest_collection_modifyitems(items):
    # Every reconciliation test needs both systems.
    for item in items:
        item.add_marker(pytest.mark.source_db)
        item.add_marker(pytest.mark.target_db)
