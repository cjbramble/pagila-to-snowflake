"""Unit tests for the agent, harness, and sign-off guards; no database needed."""

import datetime as dt
from pathlib import Path

import pytest

from faults import dbt_mutations, inject, pair_matrix
from faults.catalog import Fault
from reconcile import signoff, store
from triage import check_pair, dbt_check, query


def make(root: Path, *files: str) -> Path:
    for rel in files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x")
    return root


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


def test_signoff_gate_is_no_go_on_any_unmet_criterion():
    traces = {"MIG-001": signoff.Trace(), "MIG-002": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("passed")
    gates = signoff.gate({"MIG-001": "PASS", "MIG-002": "FAIL"}, traces, [])
    assert {g: ok for g, _, ok, _ in gates} == {"G1": False, "G2": False, "G3": True}

    traces["MIG-002"].pytest["t"].append("passed")
    gates = signoff.gate({"MIG-001": "PASS", "MIG-002": "PASS"}, traces, [])
    assert all(ok for _, _, ok, _ in gates)


def test_signoff_g1_needs_a_test_that_actually_ran():
    traces = {"MIG-001": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("skipped")
    # Even if the requirement's status were PASS, a skipped-only trace is uncovered.
    gates = signoff.gate({"MIG-001": "PASS"}, traces, [])
    assert [g for g, _, ok, _ in gates if not ok] == ["G1"]


def test_signoff_g3_fails_on_untraced_test_failures():
    traces = {"MIG-001": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("passed")
    untraced = ["tests.test_loader::test_x"]
    gates = signoff.gate({"MIG-001": "PASS"}, traces, untraced)
    assert [g for g, _, ok, _ in gates if not ok] == ["G3"]


@pytest.mark.parametrize(
    "sql",
    [
        "EXPLAIN ANALYZE DELETE FROM payment",
        "WITH d AS (DELETE FROM payment RETURNING *) SELECT * FROM d",
        "WITH u AS (UPDATE film SET title = 'x' RETURNING *) SELECT 1",
        "INSERT INTO payment SELECT * FROM payment",
        "SELECT 1; DROP TABLE payment",
    ],
)
def test_triage_query_rejects_writes(sql):
    with pytest.raises(SystemExit):
        query.check_statement(sql)


def test_triage_query_allows_reads():
    sql = "WITH x AS (SELECT last_update, create_date FROM customer) SELECT * FROM x;"
    assert query.check_statement(sql) == sql.rstrip(";")


def test_check_pair_keeps_double_dash_inside_literals():
    sql = "-- requirement: MIG-004\nSELECT '--' AS a, 'it''s -- x' AS b -- trailing\nFROM t"
    assert (
        check_pair.statement_of(sql, "postgres") == "SELECT '--' AS a, 'it''s -- x' AS b \nFROM t"
    )
    sf_sql = "SELECT 'it\\'s -- x' AS b -- trailing\nFROM t"
    assert check_pair.statement_of(sf_sql, "snowflake") == "SELECT 'it\\'s -- x' AS b \nFROM t"


def test_dbt_mutations_uses_trusted_profile_and_schema_macro(tmp_path):
    dbt_dir = make(tmp_path / "agent", "dbt_project.yml", "models/marts/m.sql")
    (dbt_dir / "profiles.yml").write_text("evil")
    (dbt_dir / "macros").mkdir()
    (dbt_dir / "macros" / "generate_schema_name.sql").write_text("evil")
    project = dbt_mutations.copy_project(dbt_dir, tmp_path / "copy")
    trusted = dbt_mutations.ROOT / "dbt"
    for rel in dbt_mutations.TRUSTED_FILES:
        assert (project / rel).read_text() == (trusted / rel).read_text()


class FailingCursor:
    def __init__(self, log: list[str]):
        self.log = log

    def execute(self, statement: str):
        self.log.append(statement)
        if statement.startswith("BREAK"):
            raise RuntimeError("fault statement failed")
        return self


class FakeConnection:
    def __init__(self):
        self.log: list[str] = []

    def cursor(self):
        return FailingCursor(self.log)


def test_fault_apply_restores_when_a_statement_fails(monkeypatch):
    restored = []
    monkeypatch.setattr(inject, "backup_exists", lambda sf, table: False)
    monkeypatch.setattr(inject, "restore", lambda sf, table: restored.append(table))
    fault = Fault("broken", "payment", "fails halfway", ("UPDATE {t} SET x = 1", "BREAK {t}"))
    with pytest.raises(RuntimeError):
        inject.apply(FakeConnection(), fault)
    assert restored == ["payment"]


def test_signoff_g3_fails_on_unknown_dbt_requirement():
    traces = {"MIG-001": signoff.Trace()}
    traces["MIG-001"].pytest["t"].append("passed")
    unknown = ["dbt assert_x (unknown ETL-099)"]
    gates = signoff.gate({"MIG-001": "PASS"}, traces, unknown)
    assert [g for g, _, ok, _ in gates if not ok] == ["G3"]


class FakeCursor:
    def __init__(self):
        self.statements, self.rows = [], []

    def execute(self, sql):
        self.statements.append(sql)

    def executemany(self, sql, rows):
        self.statements.append(sql)
        self.rows += rows


def test_store_dbt_writes_one_row_per_requirement():
    tests = [
        {
            "name": "t1",
            "kind": "unit",
            "requirements": ["ETL-001", "ETL-002"],
            "status": "passed",
            "message": "",
        },
        {"name": "t2", "kind": "data", "requirements": [], "status": "fail", "message": "x" * 5000},
    ]
    cur = FakeCursor()
    store.store_dbt(cur, "run", dt.datetime(2026, 10, 21, tzinfo=dt.UTC), tests)
    assert cur.statements[0].startswith("CREATE TABLE IF NOT EXISTS PAGILA_MIG.QA.DBT_TEST_RESULTS")
    assert [(r[2], r[4]) for r in cur.rows] == [("t1", "ETL-001"), ("t1", "ETL-002"), ("t2", None)]
    assert len(cur.rows[2][6]) == store.MAX_MESSAGE
    assert all(len(r) == store.TABLES["DBT_TEST_RESULTS"].count(",") + 1 for r in cur.rows)


def test_signoff_writes_the_run_header_last(monkeypatch):
    cur = FakeCursor()

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return cur

    monkeypatch.setattr(signoff, "connect", Conn)
    req_id = next(iter(signoff.REQUIREMENTS))
    signoff.record_run(
        started=dt.datetime(2026, 10, 21, tzinfo=dt.UTC),
        sha="abc1234",
        go=True,
        gates=[("G1", "c", True, "d")],
        statuses={req_id: "PASS"},
        pytest_results=[],
        dbt_results=[],
    )
    inserts = [s for s in cur.statements if s.startswith("INSERT")]
    assert "SIGNOFF_RUNS" in inserts[-1]
    assert cur.rows[-1][2:] == ("abc1234", "GO")
