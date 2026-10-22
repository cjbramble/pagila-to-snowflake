"""Run the full test suite and store the results in QA.RECON_RESULTS.

The whole suite runs, not just tests/reconciliation and tests/etl, because requirements
live elsewhere too (MIG-001 is in tests/test_mapping_spec.py); a recorded run must cover
every requirement or a failing run can be stored, and summarized, as clean.

Usage: python -m reconcile.record   (prints the new run id)
"""

import datetime as dt

from migrate.snowflake_conn import connect
from reconcile.results import run_pytest
from reconcile.store import new_run_id, store_pytest

SUITES = ["tests"]


def main() -> None:
    run_id = new_run_id()
    results = run_pytest(SUITES)
    recorded_at = dt.datetime.now(dt.UTC)
    with connect() as sf:
        store_pytest(sf.cursor(), run_id, recorded_at, results)
    failed = sum(r.outcome in ("failed", "error") for r in results)
    print(f"{run_id}: {len(results)} results, {failed} failed or errored")


if __name__ == "__main__":
    main()
