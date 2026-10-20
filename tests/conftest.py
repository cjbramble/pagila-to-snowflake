"""Requirement traceability: validate @pytest.mark.req IDs and summarize results by requirement."""

from collections import defaultdict
from pathlib import Path

import pytest
import yaml

REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements" / "requirements.yml"
REQUIREMENTS = yaml.safe_load(REQUIREMENTS_PATH.read_text())["migration"]

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


def requirement_status(outcomes: list[str]) -> str:
    if "failed" in outcomes:
        return "FAIL"
    if outcomes and all(o == "passed" for o in outcomes):
        return "PASS"
    return "INCOMPLETE"


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
        failed = outcomes.count("failed")
        status = requirement_status(outcomes)
        tr.write_line(
            f"{req_id}  {status:10}  {REQUIREMENTS[req_id]['title']}"
            f"  ({len(tests) - failed}/{len(tests)} passed)",
            red=status == "FAIL",
            green=status == "PASS",
            yellow=status == "INCOMPLETE",
        )
