"""Write test results and sign-off verdicts to the QA schema, where the dashboard reads them.

Every table is keyed by RUN_ID, so one sign-off run's verdict, gates, requirement statuses,
pytest results, and dbt results join on it.
"""

import datetime as dt
import uuid
from collections.abc import Iterable
from typing import Any

from reconcile.results import TestResult

QA = "PAGILA_MIG.QA"
MAX_MESSAGE = 2000

TABLES = {
    "RECON_RESULTS": """
        RUN_ID VARCHAR NOT NULL,
        RECORDED_AT TIMESTAMP_TZ(6) NOT NULL,
        TEST_ID VARCHAR NOT NULL,
        REQUIREMENT VARCHAR,
        LAYER VARCHAR,
        OUTCOME VARCHAR NOT NULL,
        MESSAGE VARCHAR""",
    "DBT_TEST_RESULTS": """
        RUN_ID VARCHAR NOT NULL,
        RECORDED_AT TIMESTAMP_TZ(6) NOT NULL,
        TEST_NAME VARCHAR NOT NULL,
        KIND VARCHAR NOT NULL,
        REQUIREMENT VARCHAR,
        STATUS VARCHAR NOT NULL,
        MESSAGE VARCHAR""",
    "SIGNOFF_RUNS": """
        RUN_ID VARCHAR NOT NULL,
        RECORDED_AT TIMESTAMP_TZ(6) NOT NULL,
        COMMIT_SHA VARCHAR NOT NULL,
        VERDICT VARCHAR NOT NULL""",
    "SIGNOFF_GATES": """
        RUN_ID VARCHAR NOT NULL,
        GATE VARCHAR NOT NULL,
        CRITERION VARCHAR NOT NULL,
        MET BOOLEAN NOT NULL,
        DETAIL VARCHAR""",
    "SIGNOFF_REQUIREMENTS": """
        RUN_ID VARCHAR NOT NULL,
        REQUIREMENT VARCHAR NOT NULL,
        TITLE VARCHAR NOT NULL,
        LAYER VARCHAR,
        STATUS VARCHAR NOT NULL""",
}


def new_run_id() -> str:
    """Sortable, unique run ID: UTC timestamp plus a random suffix."""
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def insert(cur: Any, table: str, rows: Iterable[tuple]) -> None:
    """Create the QA table if needed and append rows to it."""
    rows = list(rows)
    cur.execute(f"CREATE TABLE IF NOT EXISTS {QA}.{table} ({TABLES[table]})")
    if rows:
        placeholders = ", ".join(["%s"] * len(rows[0]))
        cur.executemany(f"INSERT INTO {QA}.{table} VALUES ({placeholders})", rows)


def store_pytest(
    cur: Any, run_id: str, recorded_at: dt.datetime, results: list[TestResult]
) -> None:
    insert(
        cur,
        "RECON_RESULTS",
        (
            (
                run_id,
                recorded_at,
                r.test_id,
                r.requirement,
                r.layer,
                r.outcome,
                r.message[:MAX_MESSAGE],
            )
            for r in results
        ),
    )


def store_dbt(cur: Any, run_id: str, recorded_at: dt.datetime, tests: list[dict]) -> None:
    """One row per dbt test and requirement it declares (REQUIREMENT is NULL if none)."""
    insert(
        cur,
        "DBT_TEST_RESULTS",
        (
            (
                run_id,
                recorded_at,
                t["name"],
                t["kind"],
                req_id,
                t["status"],
                t["message"][:MAX_MESSAGE],
            )
            for t in tests
            for req_id in t["requirements"] or [None]
        ),
    )
