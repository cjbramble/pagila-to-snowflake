"""Unit tests for the agent and harness guards; no database needed."""

from pathlib import Path

from faults import dbt_mutations, pair_matrix
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
