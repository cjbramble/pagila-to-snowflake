"""Unit tests for the agent, harness, and sign-off guards; no database needed."""

import datetime as dt
from pathlib import Path

from faults import dbt_mutations, pair_matrix
from reconcile import signoff
from triage import dbt_check


def make(root: Path, *files: str) -> Path:
    for rel in files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x")
    return root


def test_dbt_check_overlays_only_test_files(tmp_path):
    proposals = make(
        tmp_path,
        "README.md",
        "models/marts/_tests.yml",
        "tests/assert_x.sql",
        "profiles.yml",
        "dbt_project.yml",
        "macros/evil.sql",
        "models/marts/new_model.sql",
        "tests/notes.md",
        "models/top.yml",
    )
    allowed, rejected = dbt_check.proposal_files(proposals)
    assert allowed == [
        Path("models/marts/_tests.yml"),
        Path("models/top.yml"),
        Path("tests/assert_x.sql"),
    ]
    assert rejected == [
        Path("dbt_project.yml"),
        Path("macros/evil.sql"),
        Path("models/marts/new_model.sql"),
        Path("profiles.yml"),
        Path("tests/notes.md"),
    ]


def test_dbt_check_withholds_writable_credentials(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_PATH", "/keys/writable.p8")
    monkeypatch.setenv("SNOWFLAKE_TRIAGE_PRIVATE_KEY_PATH", "/keys/readonly.p8")
    env = dbt_check.dbt_env()
    assert env["SNOWFLAKE_PRIVATE_KEY_PATH"] != "/keys/writable.p8"
    assert env["SNOWFLAKE_TRIAGE_PRIVATE_KEY_PATH"] == "/keys/readonly.p8"


def mutation_row(**overrides) -> dict:
    row = {
        "mutation": dbt_mutations.MUTATIONS[0],
        "invalid": [],
        "unit": [],
        "data": [],
        "stillborn": [],
    }
    return row | overrides


def test_dbt_mutations_does_not_score_invalid_runs():
    rows = [
        mutation_row(unit=["some_unit_test"]),
        mutation_row(),
        mutation_row(invalid=["data"]),
        mutation_row(stillborn=["mart_rental_returns"]),
    ]
    assert [dbt_mutations.verdict_of(r) for r in rows] == [
        "killed",
        "SURVIVED",
        "invalid run (data pass)",
        "stillborn",
    ]
    assert "**Kill score: 1/2**" in dbt_mutations.render(rows, "t", Path("dbt"))


def test_pair_matrix_does_not_score_unapplied_faults():
    rows = [
        {"fault": "a", "table": "payment", "applied": True, "failed": ["c1"]},
        {"fault": "b", "table": "film", "applied": True, "failed": []},
        {"fault": "c", "table": "address", "applied": False, "failed": []},
    ]
    report = pair_matrix.render("t", Path("checks"), ["c1"], [], rows)
    assert "**Faults detected: 1/2**" in report
    assert "| `c` | address | not applied" in report
    assert "| `b` | film | **none: MISSED** |" in report


def test_signoff_requirement_status():
    status = signoff.requirement_status
    assert status(["passed", "passed"]) == "PASS"
    assert status(["passed", "fail"]) == "FAIL"
    assert status(["passed", "error"]) == "FAIL"
    assert status(["passed", "skipped"]) == "INCOMPLETE"
    assert status([]) == "INCOMPLETE"


def test_signoff_waiver_needs_approver_and_must_not_be_expired():
    today = dt.date(2026, 10, 21)
    ok = {"requirement": "MIG-004", "approved_by": "Data owner", "expires": "2026-10-21"}
    assert signoff.active_waiver([ok], "MIG-004", today) == ok
    assert signoff.active_waiver([ok], "MIG-003", today) is None
    assert signoff.active_waiver([ok | {"approved_by": None}], "MIG-004", today) is None
    assert signoff.active_waiver([ok | {"expires": "2026-10-20"}], "MIG-004", today) is None


def test_signoff_gate_is_no_go_on_any_unmet_criterion():
    traces = {"MIG-001": signoff.Trace(), "MIG-002": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("passed")
    accepted = {s: {"status": "accepted", "decided_by": "Data owner"} for s in signoff.KNOWN_ISSUES}
    gates = signoff.gate({"MIG-001": "PASS", "MIG-002": "FAIL"}, traces, accepted, [], [])
    met = {g: ok for g, _, ok, _ in gates}
    assert met == {"G1": False, "G2": False, "G3": True, "G4": True, "G5": True}

    traces["MIG-002"].pytest["t"].append("passed")
    pending = accepted | {"SRC-001": {"status": "pending"}}
    gates = signoff.gate({"MIG-001": "PASS", "MIG-002": "PASS"}, traces, pending, ["x.py"], [])
    assert {g: ok for g, _, ok, _ in gates} == {
        "G1": True,
        "G2": True,
        "G3": False,
        "G4": False,
        "G5": True,
    }

    gates = signoff.gate({"MIG-001": "PASS", "MIG-002": "PASS"}, traces, accepted, [], [])
    assert all(ok for _, _, ok, _ in gates)

    unnamed = accepted | {"SRC-002": {"status": "accepted", "decided_by": None}}
    gates = signoff.gate({"MIG-001": "PASS", "MIG-002": "PASS"}, traces, unnamed, [], [])
    assert [g for g, _, ok, _ in gates if not ok] == ["G3"]


def test_signoff_g1_needs_a_test_that_actually_ran():
    traces = {"MIG-001": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("skipped")
    accepted = {s: {"status": "accepted", "decided_by": "Data owner"} for s in signoff.KNOWN_ISSUES}
    # Even with the requirement waived to PASS, a skipped-only trace is uncovered.
    gates = signoff.gate({"MIG-001": "PASS"}, traces, accepted, [], [])
    assert [g for g, _, ok, _ in gates if not ok] == ["G1"]


def test_signoff_g5_fails_on_untraced_test_failures():
    traces = {"MIG-001": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("passed")
    accepted = {s: {"status": "accepted", "decided_by": "Data owner"} for s in signoff.KNOWN_ISSUES}
    untraced = ["tests.test_loader::test_x"]
    gates = signoff.gate({"MIG-001": "PASS"}, traces, accepted, [], untraced)
    assert [g for g, _, ok, _ in gates if not ok] == ["G5"]
