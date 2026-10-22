"""Summarize a recorded run's failures with Cortex AI_SUMMARIZE_AGG, then fact-check it.

The check is mechanical: every requirement ID, table, and number the summary states must
appear in the run's failures (else it's invented), and every failing requirement must be
named (else it's omitted). It can't judge wording, such as a metric attributed to the wrong
column, so a clean check means "no invented facts", not "accurate".

Usage: python -m reconcile.summarize [RUN_ID]   (default: latest run)
"""

import re
import sys

from migrate.mapping import load_spec
from migrate.snowflake_conn import connect
from reconcile.record import RECON_RESULTS

FAILURES_SQL = f"""SELECT REQUIREMENT, TEST_ID, MESSAGE FROM {RECON_RESULTS}
WHERE RUN_ID = %s AND OUTCOME IN ('failed', 'error') ORDER BY REQUIREMENT, TEST_ID"""

SUMMARY_SQL = f"""SELECT AI_SUMMARIZE_AGG(
    COALESCE(REQUIREMENT, 'untraced') || ' FAILED in ' || TEST_ID || ': ' || MESSAGE)
FROM {RECON_RESULTS} WHERE RUN_ID = %s AND OUTCOME IN ('failed', 'error')"""


REQUIREMENT_ID = re.compile(r"\b(?:MIG|ETL)-\d{3}\b")
NUMBER = re.compile(r"(?<![\w.-])-?\d+(?:\.\d+)?(?![\w-])")
THOUSANDS_SEPARATOR = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def numbers(text: str) -> set[str]:
    """Whole numbers in text, with thousands separators removed ("16,049" -> "16049")."""
    return set(NUMBER.findall(THOUSANDS_SEPARATOR.sub("", text)))


def names_table(text: str, table: str) -> bool:
    # Whole word only: "customer" must not match inside "customer_id".
    return re.search(rf"\b{table}\b", text, re.IGNORECASE) is not None


def fact_check(summary: str, failures: list[tuple], tables: set[str]) -> dict[str, list[str]]:
    """Compare what the summary names with what actually failed."""
    failed_reqs = {f[0] for f in failures if f[0]}
    failed_text = " ".join(f"{f[1]} {f[2]}" for f in failures).lower()
    named_reqs = set(REQUIREMENT_ID.findall(summary))
    named_tables = {t for t in tables if names_table(summary, t)}
    # Numbers must match a whole number in the failures; "3" doesn't match inside "51061".
    stated_numbers = numbers(REQUIREMENT_ID.sub("", summary))
    failure_numbers = {n.lstrip("-") for n in numbers(failed_text)}
    return {
        "invented_requirements": sorted(named_reqs - failed_reqs),
        "omitted_requirements": sorted(failed_reqs - named_reqs),
        "invented_tables": sorted(t for t in named_tables if not names_table(failed_text, t)),
        "invented_numbers": sorted(
            n for n in stated_numbers if n.lstrip("-") not in failure_numbers
        ),
    }


def main() -> None:
    tables = set(load_spec()["tables"])
    with connect() as sf:
        cur = sf.cursor()
        run_id = (
            sys.argv[1]
            if len(sys.argv) > 1
            else cur.execute(
                f"SELECT RUN_ID FROM {RECON_RESULTS} ORDER BY RECORDED_AT DESC LIMIT 1"
            ).fetchone()[0]
        )
        cur.execute("ALTER SESSION SET QUERY_TAG = 'pagila-cortex-summary'")
        failures = cur.execute(FAILURES_SQL, (run_id,)).fetchall()
        if not failures:
            print(f"{run_id}: no failures to summarize")
            return
        summary = cur.execute(SUMMARY_SQL, (run_id,)).fetchone()[0]

    print(f"run {run_id}: {len(failures)} failing results")
    print(f"\nAI summary (AI_SUMMARIZE_AGG):\n{summary}\n")
    check = fact_check(summary, failures, tables)
    for name, items in check.items():
        print(f"{name.replace('_', ' ')}: {items or 'none'}")
    print(
        "\nverdict:",
        "consistent with the results" if not any(check.values()) else "DO NOT TRUST without review",
    )


if __name__ == "__main__":
    main()
