"""Run the reconciliation and ETL suites and store the results in QA.RECON_RESULTS.

Usage: python -m reconcile.record   (prints the new run id)
"""

import datetime as dt
import uuid

from migrate.snowflake_conn import connect
from reconcile.results import run_pytest

RECON_RESULTS = "PAGILA_MIG.QA.RECON_RESULTS"
SUITES = ["tests/reconciliation", "tests/etl"]
MAX_MESSAGE = 2000

CREATE_SQL = f"""CREATE TABLE IF NOT EXISTS {RECON_RESULTS} (
    RUN_ID VARCHAR NOT NULL,
    RECORDED_AT TIMESTAMP_TZ(6) NOT NULL,
    TEST_ID VARCHAR NOT NULL,
    REQUIREMENT VARCHAR,
    LAYER VARCHAR,
    OUTCOME VARCHAR NOT NULL,
    MESSAGE VARCHAR
)"""


def main() -> None:
    run_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    results = run_pytest(SUITES)
    recorded_at = dt.datetime.now(dt.UTC)
    with connect() as sf:
        cur = sf.cursor()
        cur.execute(CREATE_SQL)
        cur.executemany(
            f"INSERT INTO {RECON_RESULTS} VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
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
            ],
        )
    failed = sum(r.outcome in ("failed", "error") for r in results)
    print(f"{run_id}: {len(results)} results, {failed} failed or errored")


if __name__ == "__main__":
    main()
