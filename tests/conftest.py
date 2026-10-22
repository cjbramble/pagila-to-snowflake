"""Requirement traceability and shared database fixtures.

Validates @pytest.mark.req IDs, summarizes results by requirement, and provides
session-scoped connections to the source (pg) and target (sf).
"""

from collections import defaultdict

import psycopg
import pytest

from migrate.mapping import load_spec
from migrate.snowflake_conn import connect
from reconcile.results import REQUIREMENTS, requirement_status

# requirement ID -> list of (test node id, outcome)
_results: dict[str, list[tuple[str, str]]] = defaultdict(list)


def pytest_configure(config):
    config.addinivalue_line("markers", "req(id): requirement ID(s) this test verifies")


def pytest_collection_modifyitems(config, items):
    unknown = sorted(
        f"{item.nodeid}: {req_id}"
        for item in items
        for marker in item.iter_markers("req")
        for req_id in marker.args
        if req_id not in REQUIREMENTS
    )
    if unknown:
        raise pytest.UsageError("Unknown requirement IDs:\n  " + "\n  ".join(unknown))
    # Carried into --junitxml output, so reports can map results back to requirements.
    for item in items:
        for marker in item.iter_markers("req"):
            for req_id in marker.args:
                item.user_properties.append(("requirement", req_id))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    # Record the call phase, or setup/teardown when they fail or skip.
    if report.when == "call" or report.outcome != "passed":
        for marker in item.iter_markers("req"):
            for req_id in marker.args:
                _results[req_id].append((item.nodeid, report.outcome))
    return report


def pytest_terminal_summary(terminalreporter):
    if not _results:
        return
    tr = terminalreporter
    tr.section("requirements")
    for req_id in sorted(REQUIREMENTS):
        tests = _results.get(req_id)
        if not tests:
            tr.write_line(f"{req_id}  NOT RUN     {REQUIREMENTS[req_id]['title']}")
            continue
        outcomes = [o for _, o in tests]
        status = requirement_status(outcomes)
        tr.write_line(
            f"{req_id}  {status:10}  {REQUIREMENTS[req_id]['title']}"
            f"  ({outcomes.count('passed')}/{len(tests)} passed)",
            red=status == "FAIL",
            green=status == "PASS",
            yellow=status == "INCOMPLETE",
        )


@pytest.fixture(scope="session")
def spec():
    return load_spec()


@pytest.fixture(scope="session")
def pg():
    # UTC session, so interval arithmetic on timestamptz never crosses a DST change.
    with psycopg.connect(autocommit=True, options="-c TimeZone=UTC") as conn:
        conn.read_only = True
        yield conn


@pytest.fixture(scope="session")
def sf():
    with connect() as conn:
        yield conn
