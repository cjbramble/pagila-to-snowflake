"""Markers for the source ↔ target reconciliation suite (fixtures live in tests/conftest.py)."""

from pathlib import Path

import pytest

HERE = Path(__file__).parent


def pytest_collection_modifyitems(items):
    # Every reconciliation test needs both systems. The hook sees the whole session's
    # items, not just this directory's, so mark only the tests that live here.
    for item in items:
        if item.path.is_relative_to(HERE):
            item.add_marker(pytest.mark.source_db)
            item.add_marker(pytest.mark.target_db)
